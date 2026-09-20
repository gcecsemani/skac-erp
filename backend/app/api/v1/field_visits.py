"""Field visits: crop-complaint visits with GPS proof and photos."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from pathlib import Path
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased, joinedload, selectinload

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.models.customer import Customer
from app.models.enums import FieldVisitStatus
from app.models.field_visit import FieldVisit, FieldVisitPhoto
from app.models.organization import Branch
from app.models.user import User

router = APIRouter(prefix="/field-visits", tags=["field-visits"])

UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads" / "field_visits"
ALLOWED_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic", "image/heif",
}
MAX_PHOTOS = 8
MAX_BYTES = 6 * 1024 * 1024


class VisitIn(BaseModel):
    branch_id: int
    visited_by_user_id: int | None = None
    customer_id: int | None = None
    visit_date: date | None = None
    farmer_name: str = Field(min_length=2, max_length=150)
    farmer_phone: str | None = None
    village: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    gps_accuracy: float | None = None
    complaint_notes: str | None = None
    prescription_notes: str | None = None


class ResolveIn(BaseModel):
    note: str | None = Field(default=None, max_length=255)


def _uploads() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def _serialize(
    v: FieldVisit,
    *,
    branch_name: str | None = None,
    visitor_name: str | None = None,
    resolver_name: str | None = None,
) -> dict:
    return {
        "id": v.id,
        "visit_no": v.visit_no,
        "branch_id": v.branch_id,
        "branch_name": branch_name,
        "visited_by_user_id": v.visited_by_user_id,
        "visited_by": visitor_name,
        "customer_id": v.customer_id,
        "visit_date": v.visit_date.isoformat(),
        "farmer_name": v.farmer_name,
        "farmer_phone": v.farmer_phone,
        "village": v.village,
        "latitude": v.latitude,
        "longitude": v.longitude,
        "gps_accuracy": v.gps_accuracy,
        "gps_captured_at": v.gps_captured_at.isoformat() if v.gps_captured_at else None,
        "complaint_notes": v.complaint_notes,
        "prescription_notes": v.prescription_notes,
        "status": v.status.value,
        "resolution_note": v.resolution_note,
        "resolved_by": resolver_name,
        "resolved_at": v.resolved_at.isoformat() if v.resolved_at else None,
        "photo_count": len(v.photos),
        "photos": [
            {
                "id": p.id,
                "original_name": p.original_name,
                "content_type": p.content_type,
            }
            for p in v.photos
        ],
    }


def _load_names(db: Session, v: FieldVisit) -> dict:
    visitor = db.get(User, v.visited_by_user_id)
    resolver = db.get(User, v.resolved_by_user_id) if v.resolved_by_user_id else None
    branch = db.get(Branch, v.branch_id)
    return _serialize(
        v,
        branch_name=branch.name if branch else None,
        visitor_name=visitor.full_name if visitor else None,
        resolver_name=resolver.full_name if resolver else None,
    )


def _owned(db: Session, visit_id: int, current: CurrentUser) -> FieldVisit:
    visit = db.get(FieldVisit, visit_id)
    if visit is None or visit.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Field visit not found")
    current.assert_branch_access(visit.branch_id)
    return visit


@router.get("/staff")
def list_staff(
    current: CurrentUser = Depends(require_permission(rbac.P_FIELD_VISIT)),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.scalars(select(User).options(joinedload(User.role)).where(
        User.organization_id == current.organization_id,
        User.is_deleted.is_(False),
        User.is_active.is_(True),
    ).order_by(User.full_name.asc())).all()
    return [{"id": u.id, "full_name": u.full_name, "role": u.role.key} for u in rows]


@router.get("")
def list_visits(
    status: str | None = None,
    branch_id: int | None = None,
    search: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    current: CurrentUser = Depends(require_permission(rbac.P_FIELD_VISIT)),
    db: Session = Depends(get_db),
) -> list[dict]:
    Visitor = aliased(User)
    Resolver = aliased(User)
    stmt = (
        select(FieldVisit, Branch.name, Visitor.full_name, Resolver.full_name)
        .join(Branch, Branch.id == FieldVisit.branch_id)
        .join(Visitor, Visitor.id == FieldVisit.visited_by_user_id)
        .outerjoin(Resolver, Resolver.id == FieldVisit.resolved_by_user_id)
        .options(selectinload(FieldVisit.photos))
        .where(FieldVisit.organization_id == current.organization_id)
    )
    if not current.sees_all_branches:
        stmt = stmt.where(FieldVisit.branch_id.in_(current.branch_ids or [-1]))
    if branch_id:
        current.assert_branch_access(branch_id)
        stmt = stmt.where(FieldVisit.branch_id == branch_id)
    if status and status != "all":
        try:
            stmt = stmt.where(FieldVisit.status == FieldVisitStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(
            FieldVisit.farmer_name.ilike(like),
            FieldVisit.farmer_phone.ilike(like),
            FieldVisit.village.ilike(like),
            FieldVisit.visit_no.ilike(like),
        ))
    rows = db.execute(stmt.order_by(FieldVisit.id.desc()).limit(limit)).unique().all()
    return [
        _serialize(v, branch_name=bname, visitor_name=vname, resolver_name=rname)
        for v, bname, vname, rname in rows
    ]


@router.post("", status_code=201)
def create_visit(
    payload: VisitIn,
    current: CurrentUser = Depends(require_permission(rbac.P_FIELD_VISIT)),
    db: Session = Depends(get_db),
) -> dict:
    current.assert_branch_access(payload.branch_id)
    visitor_id = payload.visited_by_user_id or current.id
    if not current.sees_all_branches:
        visitor_id = current.id
    visitor = db.get(User, visitor_id)
    if visitor is None or visitor.organization_id != current.organization_id or visitor.is_deleted:
        raise HTTPException(status_code=400, detail="Staff member not found")

    farmer_name = payload.farmer_name.strip()
    village = (payload.village or "").strip() or None
    phone = (payload.farmer_phone or "").strip() or None
    if payload.customer_id:
        cust = db.get(Customer, payload.customer_id)
        if cust is None or cust.organization_id != current.organization_id or cust.is_deleted:
            raise HTTPException(status_code=400, detail="Farmer not found")
        farmer_name = farmer_name or cust.name
        phone = phone or cust.phone
        village = village or cust.village

    if payload.latitude is None or payload.longitude is None:
        raise HTTPException(
            status_code=400,
            detail="Capture GPS location in the field so the shop can verify this visit.",
        )

    visit = FieldVisit(
        organization_id=current.organization_id,
        branch_id=payload.branch_id,
        visited_by_user_id=visitor_id,
        customer_id=payload.customer_id,
        visit_date=payload.visit_date or date.today(),
        farmer_name=farmer_name,
        farmer_phone=phone,
        village=village,
        latitude=payload.latitude,
        longitude=payload.longitude,
        gps_accuracy=payload.gps_accuracy,
        gps_captured_at=datetime.utcnow(),
        complaint_notes=(payload.complaint_notes or "").strip() or None,
        prescription_notes=(payload.prescription_notes or "").strip() or None,
        status=FieldVisitStatus.open,
    )
    db.add(visit)
    db.flush()
    count = db.scalar(select(func.count(FieldVisit.id)).where(
        FieldVisit.organization_id == current.organization_id)) or 0
    visit.visit_no = f"FV/{date.today().year}/{count:05d}"
    record_audit(
        db, action="create", entity_type="field_visit", entity_id=visit.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=visit.branch_id, changes={"farmer_name": farmer_name},
    )
    db.commit()
    db.refresh(visit)
    return _load_names(db, visit)


@router.get("/{visit_id}")
def get_visit(
    visit_id: int,
    current: CurrentUser = Depends(require_permission(rbac.P_FIELD_VISIT)),
    db: Session = Depends(get_db),
) -> dict:
    return _load_names(db, _owned(db, visit_id, current))


@router.post("/{visit_id}/photos", status_code=201)
async def upload_photos(
    visit_id: int,
    photos: list[UploadFile] = File(...),
    current: CurrentUser = Depends(require_permission(rbac.P_FIELD_VISIT)),
    db: Session = Depends(get_db),
) -> dict:
    visit = _owned(db, visit_id, current)
    if visit.status != FieldVisitStatus.open:
        raise HTTPException(status_code=409, detail="Photos can only be added on an open visit")
    existing = len(visit.photos)
    if existing + len(photos) > MAX_PHOTOS:
        raise HTTPException(status_code=400, detail=f"At most {MAX_PHOTOS} photos per visit")
    folder = _uploads() / str(visit.id)
    folder.mkdir(parents=True, exist_ok=True)
    saved = 0
    for up in photos:
        ctype = (up.content_type or "").lower()
        if ctype not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail="Photos must be JPG, PNG or WebP")
        data = await up.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(status_code=400, detail="Each photo must be under 6 MB")
        ext = { "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png",
                "image/webp": ".webp", "image/heic": ".heic", "image/heif": ".heif" }.get(ctype, ".jpg")
        stored = f"{uuid.uuid4().hex}{ext}"
        (folder / stored).write_bytes(data)
        visit.photos.append(FieldVisitPhoto(
            stored_name=stored,
            original_name=up.filename,
            content_type=ctype,
            size_bytes=len(data),
        ))
        saved += 1
    db.commit()
    db.refresh(visit)
    return {"uploaded": saved, "photos": _load_names(db, visit)["photos"]}


@router.get("/{visit_id}/photos/{photo_id}")
def get_photo(
    visit_id: int,
    photo_id: int,
    current: CurrentUser = Depends(require_permission(rbac.P_FIELD_VISIT)),
    db: Session = Depends(get_db),
):
    visit = _owned(db, visit_id, current)
    photo = next((p for p in visit.photos if p.id == photo_id), None)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    path = _uploads() / str(visit.id) / photo.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Photo file missing")
    return FileResponse(path, media_type=photo.content_type or "image/jpeg", filename=photo.original_name)


def _remove_photo_file(visit_id: int, stored_name: str) -> None:
    path = _uploads() / str(visit_id) / stored_name
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _remove_visit_folder_if_empty(visit_id: int) -> None:
    folder = _uploads() / str(visit_id)
    try:
        if folder.exists() and not any(folder.iterdir()):
            folder.rmdir()
    except OSError:
        pass


@router.delete("/{visit_id}/photos/{photo_id}")
def delete_photo(
    visit_id: int,
    photo_id: int,
    current: CurrentUser = Depends(require_permission(rbac.P_FIELD_VISIT)),
    db: Session = Depends(get_db),
) -> dict:
    visit = _owned(db, visit_id, current)
    if visit.status == FieldVisitStatus.open:
        raise HTTPException(
            status_code=409,
            detail="Delete photos only after the visit is completed or cancelled.",
        )
    photo = next((p for p in visit.photos if p.id == photo_id), None)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    _remove_photo_file(visit.id, photo.stored_name)
    db.delete(photo)
    db.commit()
    _remove_visit_folder_if_empty(visit.id)
    db.refresh(visit)
    return _load_names(db, visit)


@router.delete("/{visit_id}/photos")
def delete_all_photos(
    visit_id: int,
    current: CurrentUser = Depends(require_permission(rbac.P_FIELD_VISIT)),
    db: Session = Depends(get_db),
) -> dict:
    visit = _owned(db, visit_id, current)
    if visit.status == FieldVisitStatus.open:
        raise HTTPException(
            status_code=409,
            detail="Delete photos only after the visit is completed or cancelled.",
        )
    folder = _uploads() / str(visit.id)
    for photo in list(visit.photos):
        db.delete(photo)
    db.commit()
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
    db.refresh(visit)
    return _load_names(db, visit)


@router.post("/{visit_id}/complete")
def complete_visit(
    visit_id: int,
    payload: ResolveIn,
    current: CurrentUser = Depends(require_permission(rbac.P_FIELD_VISIT)),
    db: Session = Depends(get_db),
) -> dict:
    visit = _owned(db, visit_id, current)
    if visit.status != FieldVisitStatus.open:
        raise HTTPException(status_code=409, detail="This visit is already closed")
    visit.status = FieldVisitStatus.completed
    visit.resolution_note = (payload.note or "").strip() or "Farmer came and took the order"
    visit.resolved_by_user_id = current.id
    visit.resolved_at = datetime.utcnow()
    record_audit(
        db, action="update", entity_type="field_visit", entity_id=visit.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=visit.branch_id, changes={"status": "completed"},
    )
    db.commit()
    db.refresh(visit)
    return _load_names(db, visit)


@router.post("/{visit_id}/cancel")
def cancel_visit(
    visit_id: int,
    payload: ResolveIn,
    current: CurrentUser = Depends(require_permission(rbac.P_FIELD_VISIT)),
    db: Session = Depends(get_db),
) -> dict:
    visit = _owned(db, visit_id, current)
    if visit.status != FieldVisitStatus.open:
        raise HTTPException(status_code=409, detail="This visit is already closed")
    visit.status = FieldVisitStatus.cancelled
    visit.resolution_note = (payload.note or "").strip() or "Farmer did not come"
    visit.resolved_by_user_id = current.id
    visit.resolved_at = datetime.utcnow()
    record_audit(
        db, action="update", entity_type="field_visit", entity_id=visit.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=visit.branch_id, changes={"status": "cancelled"},
    )
    db.commit()
    db.refresh(visit)
    return _load_names(db, visit)
