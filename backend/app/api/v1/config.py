"""Owner-managed picklists used across POS, farmers, products, expenses, branches."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.models.config import (
    ALL_KINDS, KIND_DISTRICT, KIND_EXPENSE, KIND_GST, KIND_HSN, KIND_PAYMENT,
    KIND_STATE, KIND_TOXICITY, KIND_UNIT, KIND_VILLAGE, ConfigItem,
)
from app.services.config_defaults import FALLBACK_EXPENSE_CATEGORIES, slug

router = APIRouter(prefix="/config", tags=["config"])


class ConfigIn(BaseModel):
    kind: str
    parent_id: int | None = None
    name: str = Field(min_length=1, max_length=160)
    code: str | None = None
    extra: dict | None = None
    is_active: bool = True
    sort_order: int | None = None


class ConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    code: str | None = None
    parent_id: int | None = None
    extra: dict | None = None
    is_active: bool | None = None
    sort_order: int | None = None


def _row(item: ConfigItem) -> dict:
    return {
        "id": item.id,
        "kind": item.kind,
        "parent_id": item.parent_id,
        "code": item.code,
        "name": item.name,
        "extra": item.extra or {},
        "is_active": item.is_active,
        "sort_order": item.sort_order,
    }


def _active_items(db: Session, org_id: int, kind: str) -> list[ConfigItem]:
    return list(db.scalars(
        select(ConfigItem).where(
            ConfigItem.organization_id == org_id,
            ConfigItem.kind == kind,
            ConfigItem.is_deleted.is_(False),
            ConfigItem.is_active.is_(True),
        ).order_by(ConfigItem.sort_order, ConfigItem.name)
    ).all())


def expense_category_rows(db: Session, org_id: int) -> list[dict]:
    rows = _active_items(db, org_id, KIND_EXPENSE)
    if rows:
        return [
            {"key": r.code, "label": r.name, "account": (r.extra or {}).get("account") or "4500"}
            for r in rows
        ]
    return [{"key": c, "label": n, "account": a} for c, n, a in FALLBACK_EXPENSE_CATEGORIES]


def _next_sort(db: Session, org_id: int, kind: str, parent_id: int | None) -> int:
    stmt = select(func.coalesce(func.max(ConfigItem.sort_order), -1)).where(
        ConfigItem.organization_id == org_id,
        ConfigItem.kind == kind,
        ConfigItem.is_deleted.is_(False),
    )
    if parent_id is None:
        stmt = stmt.where(ConfigItem.parent_id.is_(None))
    else:
        stmt = stmt.where(ConfigItem.parent_id == parent_id)
    return int(db.scalar(stmt) or -1) + 1


def _get(db: Session, org_id: int, item_id: int) -> ConfigItem:
    item = db.get(ConfigItem, item_id)
    if item is None or item.organization_id != org_id or item.is_deleted:
        raise HTTPException(status_code=404, detail="Config item not found")
    return item


# Masters (districts, villages, GST slabs, units...) change a few times a
# year but every form loads them. Cache per org and drop it on any write.
_bundle_cache: dict[int, dict] = {}


def _invalidate_bundle(org_id: int) -> None:
    _bundle_cache.pop(org_id, None)


@router.get("/bundle")
def config_bundle(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    org_id = current.organization_id
    cached = _bundle_cache.get(org_id)
    if cached is not None:
        return cached
    items = list(db.scalars(
        select(ConfigItem).where(
            ConfigItem.organization_id == org_id,
            ConfigItem.is_deleted.is_(False),
            ConfigItem.is_active.is_(True),
        ).order_by(ConfigItem.sort_order, ConfigItem.name)
    ).all())
    by_kind: dict[str, list[dict]] = {k: [] for k in ALL_KINDS}
    villages: list[ConfigItem] = []
    for it in items:
        if it.kind == KIND_VILLAGE:
            villages.append(it)
            continue
        by_kind.setdefault(it.kind, []).append(_row(it))
    district_villages: dict[int, list[dict]] = {}
    for v in villages:
        district_villages.setdefault(v.parent_id or 0, []).append(_row(v))
    districts = []
    for d in by_kind.get(KIND_DISTRICT, []):
        districts.append({**d, "villages": district_villages.get(d["id"], [])})
    expense_rows = by_kind.get(KIND_EXPENSE, [])
    bundle = {
        "districts": districts,
        "units": by_kind.get(KIND_UNIT, []),
        "gst_rates": by_kind.get(KIND_GST, []),
        "hsn": by_kind.get(KIND_HSN, []),
        "expense_categories": [
            {
                "key": r["code"],
                "label": r["name"],
                "account": (r.get("extra") or {}).get("account") or "4500",
                **r,
            }
            for r in expense_rows
        ] or expense_category_rows(db, org_id),
        "toxicity_classes": by_kind.get(KIND_TOXICITY, []),
        "payment_modes": by_kind.get(KIND_PAYMENT, []),
        "states": by_kind.get(KIND_STATE, []),
    }
    _bundle_cache[org_id] = bundle
    return bundle


@router.get("/items")
def list_items(
    kind: str = Query(...),
    parent_id: int | None = None,
    include_inactive: bool = False,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    if kind not in ALL_KINDS:
        raise HTTPException(status_code=400, detail="Unknown config kind")
    stmt = select(ConfigItem).where(
        ConfigItem.organization_id == current.organization_id,
        ConfigItem.kind == kind,
        ConfigItem.is_deleted.is_(False),
    )
    if parent_id is not None:
        stmt = stmt.where(ConfigItem.parent_id == parent_id)
    if not include_inactive:
        stmt = stmt.where(ConfigItem.is_active.is_(True))
    rows = db.scalars(stmt.order_by(ConfigItem.sort_order, ConfigItem.name)).all()
    return [_row(r) for r in rows]


@router.post("/items", status_code=201)
def create_item(
    payload: ConfigIn,
    current: CurrentUser = Depends(require_permission(rbac.P_CONFIG_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    kind = payload.kind.strip().lower()
    if kind not in ALL_KINDS:
        raise HTTPException(status_code=400, detail="Unknown config kind")
    if kind == KIND_VILLAGE and not payload.parent_id:
        raise HTTPException(status_code=400, detail="Select a district for this village")
    parent_id = payload.parent_id
    if parent_id:
        parent = _get(db, current.organization_id, parent_id)
        if kind == KIND_VILLAGE and parent.kind != KIND_DISTRICT:
            raise HTTPException(status_code=400, detail="Village must belong to a district")
    code = slug(payload.code or payload.name)
    dup = select(ConfigItem).where(
        ConfigItem.organization_id == current.organization_id,
        ConfigItem.kind == kind,
        ConfigItem.code == code,
        ConfigItem.is_deleted.is_(False),
    )
    if parent_id is None:
        dup = dup.where(ConfigItem.parent_id.is_(None))
    else:
        dup = dup.where(ConfigItem.parent_id == parent_id)
    if db.scalar(dup):
        raise HTTPException(status_code=409, detail="An item with this name already exists")
    item = ConfigItem(
        organization_id=current.organization_id,
        kind=kind,
        parent_id=parent_id,
        code=code,
        name=payload.name.strip(),
        extra=payload.extra or {},
        is_active=payload.is_active,
        sort_order=payload.sort_order if payload.sort_order is not None else _next_sort(
            db, current.organization_id, kind, parent_id
        ),
    )
    db.add(item)
    db.flush()
    record_audit(
        db, action="create", entity_type="config_item", entity_id=item.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        changes={"kind": kind, "name": item.name},
    )
    _invalidate_bundle(current.organization_id)
    db.commit()
    db.refresh(item)
    return _row(item)


@router.put("/items/{item_id}")
def update_item(
    item_id: int,
    payload: ConfigUpdate,
    current: CurrentUser = Depends(require_permission(rbac.P_CONFIG_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    item = _get(db, current.organization_id, item_id)
    if payload.name is not None:
        item.name = payload.name.strip()
    if payload.code is not None:
        item.code = slug(payload.code)
    if payload.extra is not None:
        item.extra = payload.extra
    if payload.is_active is not None:
        item.is_active = payload.is_active
    if payload.sort_order is not None:
        item.sort_order = payload.sort_order
    if payload.parent_id is not None:
        if item.kind == KIND_VILLAGE:
            parent = _get(db, current.organization_id, payload.parent_id)
            if parent.kind != KIND_DISTRICT:
                raise HTTPException(status_code=400, detail="Village must belong to a district")
            item.parent_id = parent.id
    record_audit(
        db, action="update", entity_type="config_item", entity_id=item.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        changes=payload.model_dump(mode="json", exclude_none=True),
    )
    _invalidate_bundle(current.organization_id)
    db.commit()
    db.refresh(item)
    return _row(item)


@router.delete("/items/{item_id}")
def delete_item(
    item_id: int,
    current: CurrentUser = Depends(require_permission(rbac.P_CONFIG_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    item = _get(db, current.organization_id, item_id)
    if item.kind == KIND_PAYMENT and item.code == "cash":
        raise HTTPException(status_code=400, detail="Cash payment mode cannot be deleted")
    if item.kind == KIND_DISTRICT:
        kids = db.scalars(select(ConfigItem).where(
            ConfigItem.parent_id == item.id, ConfigItem.is_deleted.is_(False)
        )).all()
        for kid in kids:
            kid.is_deleted = True
    item.is_deleted = True
    item.is_active = False
    record_audit(
        db, action="delete", entity_type="config_item", entity_id=item.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        changes={"kind": item.kind, "name": item.name},
    )
    _invalidate_bundle(current.organization_id)
    db.commit()
    return {"status": "deleted", "id": item_id}
