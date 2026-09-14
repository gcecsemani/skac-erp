"""Product master management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.models.enums import ProductCategory
from app.models.inventory import Stock
from app.models.product import Product, ProductUnit
from app.schemas.masters import ProductBase, ProductCreate, ProductOut

router = APIRouter(prefix="/products", tags=["products"])


def _attrs_dict(product: Product) -> dict:
    extra = product.attributes if isinstance(product.attributes, dict) else {}
    return dict(extra or {})


def _apply_product_fields(product: Product, data: dict) -> None:
    sell_loose = data.pop("sell_loose", None)
    data.pop("units", None)
    for key, value in data.items():
        setattr(product, key, value)
    if sell_loose is None:
        return
    extra = _attrs_dict(product)
    extra["sell_loose"] = bool(sell_loose)
    product.attributes = extra


@router.get("", response_model=list[ProductOut])
def list_products(
    category: ProductCategory | None = None,
    search: str | None = None,
    limit: int | None = Query(None, ge=1, le=10000),
    branch_id: int | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProductOut]:
    stmt = select(Product).where(
        Product.organization_id == current.organization_id,
        Product.is_deleted.is_(False),
    )
    if category:
        stmt = stmt.where(Product.category == category)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(Product.name.ilike(like) | Product.sku.ilike(like) | Product.barcode.ilike(like))
    stmt = stmt.order_by(Product.is_favorite.desc(), Product.name.asc())
    if limit:
        stmt = stmt.limit(limit)
    products = list(db.scalars(stmt).all())

    qty_map: dict[int, float] = {}
    if branch_id:
        current.assert_branch_access(branch_id)
        qty_map = {
            pid: float(qty or 0)
            for pid, qty in db.execute(
                select(Stock.product_id, func.coalesce(func.sum(Stock.quantity), 0))
                .where(
                    Stock.organization_id == current.organization_id,
                    Stock.branch_id == branch_id,
                )
                .group_by(Stock.product_id)
            ).all()
        }

    return [
        ProductOut.model_validate(p).model_copy(
            update={"stock_qty": qty_map.get(p.id, 0.0) if branch_id else None}
        )
        for p in products
    ]


@router.post("", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductCreate,
    current: CurrentUser = Depends(require_permission(rbac.P_PRODUCT_MANAGE)),
    db: Session = Depends(get_db),
) -> Product:
    data = payload.model_dump(exclude={"units"})
    sell_loose = data.pop("sell_loose", None)
    product = Product(organization_id=current.organization_id, **data)
    if sell_loose is not None:
        product.attributes = {**(_attrs_dict(product)), "sell_loose": bool(sell_loose)}
    for u in payload.units:
        product.units.append(ProductUnit(unit=u.unit, factor_to_base=u.factor_to_base))
    db.add(product)
    db.flush()
    record_audit(
        db, action="create", entity_type="product", entity_id=product.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        changes=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Product:
    product = db.get(Product, product_id)
    if product is None or product.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def _get_owned_product(db: Session, product_id: int, org_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None or product.organization_id != org_id or product.is_deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductBase,
    current: CurrentUser = Depends(require_permission(rbac.P_PRODUCT_MANAGE)),
    db: Session = Depends(get_db),
) -> Product:
    product = _get_owned_product(db, product_id, current.organization_id)
    _apply_product_fields(product, payload.model_dump())
    record_audit(
        db, action="update", entity_type="product", entity_id=product.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        changes=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    current: CurrentUser = Depends(require_permission(rbac.P_PRODUCT_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    product = _get_owned_product(db, product_id, current.organization_id)
    product.is_deleted = True
    product.is_active = False
    record_audit(
        db, action="delete", entity_type="product", entity_id=product.id,
        actor_user_id=current.id, organization_id=current.organization_id,
    )
    db.commit()
    return {"status": "deleted", "id": product_id}


class FavoriteIn(BaseModel):
    is_favorite: bool


@router.post("/{product_id}/favorite")
def set_favorite(
    product_id: int,
    payload: FavoriteIn,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Cashiers can pin counter favorites without full product-edit rights."""
    product = _get_owned_product(db, product_id, current.organization_id)
    product.is_favorite = payload.is_favorite
    db.commit()
    return {"id": product.id, "is_favorite": product.is_favorite}
