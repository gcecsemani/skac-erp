"""Inventory: stock receipt (GRN), on-hand view, and demand forecasting."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.models.inventory import Batch, Stock
from app.models.product import Product
from app.schemas.masters import StockReceiptIn
from app.services import inventory as inv
from app.services.ai import forecasting

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("/receive", status_code=201)
def receive_stock(
    payload: StockReceiptIn,
    current: CurrentUser = Depends(require_permission(rbac.P_INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    """Goods receipt: create/find the batch and add stock to a branch."""
    current.assert_branch_access(payload.branch_id)

    batch = db.scalar(
        select(Batch).where(
            Batch.product_id == payload.product_id, Batch.batch_no == payload.batch_no
        )
    )
    if batch is None:
        batch = Batch(
            organization_id=current.organization_id,
            product_id=payload.product_id,
            batch_no=payload.batch_no,
            mfg_date=payload.mfg_date,
            expiry_date=payload.expiry_date,
            purchase_price=payload.purchase_price,
        )
        db.add(batch)
        db.flush()

    stock = inv.receive_stock(
        db,
        organization_id=current.organization_id,
        branch_id=payload.branch_id,
        product_id=payload.product_id,
        batch_id=batch.id,
        quantity=payload.quantity,
    )
    record_audit(
        db, action="create", entity_type="stock_receipt", entity_id=batch.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=payload.branch_id, changes=payload.model_dump(mode="json"),
    )
    db.commit()
    return {"batch_id": batch.id, "on_hand": float(stock.quantity)}


@router.get("/stock")
def list_stock(
    branch_id: int | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = (
        select(Stock, Batch, Product)
        .join(Batch, Batch.id == Stock.batch_id)
        .join(Product, Product.id == Stock.product_id)
        .where(Stock.organization_id == current.organization_id, Stock.quantity > 0)
    )
    if branch_id is not None:
        current.assert_branch_access(branch_id)
        stmt = stmt.where(Stock.branch_id == branch_id)
    elif not current.sees_all_branches:
        stmt = stmt.where(Stock.branch_id.in_(current.branch_ids or [-1]))

    out = []
    for stock, batch, product in db.execute(stmt).all():
        out.append({
            "branch_id": stock.branch_id,
            "product_id": product.id,
            "product": product.name,
            "batch_no": batch.batch_no,
            "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
            "quantity": float(stock.quantity),
        })
    return out


@router.get("/forecast")
def forecast(
    branch_id: int | None = None,
    only_needing_purchase: bool = False,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    if branch_id is not None:
        current.assert_branch_access(branch_id)
    return forecasting.forecast_all(
        db,
        organization_id=current.organization_id,
        branch_id=branch_id,
        only_needing_purchase=only_needing_purchase,
    )
