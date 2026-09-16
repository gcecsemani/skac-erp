"""Inventory: stock receipt (GRN), on-hand view, and demand forecasting."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.models.enums import MovementType
from app.models.inventory import Batch, Stock
from app.models.product import Product
from app.models.purchase import GRN, GRNItem, PurchaseReturn, PurchaseReturnItem
from app.schemas.masters import StockAdjustIn, StockReceiptIn
from app.services import inventory as inv
from app.services.ai import forecasting
from app.services.inventory import InsufficientStock

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _grn_locked_qty(db: Session, *, branch_id: int, batch_id: int) -> Decimal:
    """Qty of this batch at this branch that still belongs to an open GRN line."""
    received = db.scalar(
        select(func.coalesce(func.sum(GRNItem.quantity), 0))
        .join(GRN, GRN.id == GRNItem.grn_id)
        .where(GRN.branch_id == branch_id, GRNItem.batch_id == batch_id)
    ) or 0
    returned = db.scalar(
        select(func.coalesce(func.sum(PurchaseReturnItem.quantity), 0))
        .join(PurchaseReturn, PurchaseReturn.id == PurchaseReturnItem.purchase_return_id)
        .join(GRN, GRN.id == PurchaseReturn.grn_id)
        .where(GRN.branch_id == branch_id, PurchaseReturnItem.batch_id == batch_id)
    ) or 0
    locked = Decimal(received) - Decimal(returned)
    return locked if locked > 0 else Decimal("0")


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


@router.post("/adjust")
def adjust_stock(
    payload: StockAdjustIn,
    current: CurrentUser = Depends(require_permission(rbac.P_INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    """Reverse an incorrect Stock-on-Hand receive. Does not touch vendor bills.

    Qty that still belongs to a GRN must be reversed with a purchase return.
    Optionally load the same qty onto another product or branch in one step.
    """
    current.assert_branch_access(payload.branch_id)
    relocating = payload.correct_branch_id is not None or payload.correct_product_id is not None
    if relocating:
        if payload.correct_branch_id is None or payload.correct_product_id is None:
            raise HTTPException(
                status_code=400,
                detail="Select both the correct branch and the correct product.",
            )
        current.assert_branch_access(payload.correct_branch_id)
        if (
            payload.correct_branch_id == payload.branch_id
            and payload.correct_product_id == payload.product_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Pick a different product or branch, or reverse without reloading.",
            )

    stock = db.scalar(
        select(Stock).where(
            Stock.branch_id == payload.branch_id, Stock.batch_id == payload.batch_id
        )
    )
    if stock is None or stock.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Stock row not found")
    if stock.product_id != payload.product_id:
        raise HTTPException(status_code=400, detail="Product does not match this batch")

    qty = Decimal(payload.quantity)
    on_hand = Decimal(stock.quantity or 0)
    locked = _grn_locked_qty(db, branch_id=payload.branch_id, batch_id=payload.batch_id)
    adjustable = on_hand - locked
    if adjustable < 0:
        adjustable = Decimal("0")
    if qty > on_hand:
        raise HTTPException(
            status_code=409,
            detail=f"Only {float(on_hand):g} is on hand at this branch.",
        )
    if qty > adjustable:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Only {float(adjustable):g} of this batch can be corrected here. "
                f"The rest came from a GRN — reverse it with a purchase return (debit note) "
                f"on Purchasing."
            ),
        )

    reason = payload.reason.strip()
    src_batch = db.get(Batch, payload.batch_id)
    try:
        inv.issue_from_batch(
            db,
            organization_id=current.organization_id,
            branch_id=payload.branch_id,
            product_id=payload.product_id,
            batch_id=payload.batch_id,
            quantity=qty,
            movement_type=MovementType.adjustment,
            ref_type="adjustment",
            note=reason,
        )
    except InsufficientStock as exc:
        raise HTTPException(status_code=409, detail=inv.describe_shortfall(db, exc))

    dest: dict | None = None
    if relocating:
        dest_product = db.get(Product, payload.correct_product_id)
        if dest_product is None or dest_product.organization_id != current.organization_id:
            raise HTTPException(status_code=400, detail="Correct product not found")
        batch_no = (payload.correct_batch_no or (src_batch.batch_no if src_batch else "")).strip()
        if not batch_no:
            raise HTTPException(status_code=400, detail="Enter a batch number for the correct product")
        dest_batch = db.scalar(
            select(Batch).where(
                Batch.product_id == payload.correct_product_id, Batch.batch_no == batch_no
            )
        )
        if dest_batch is None:
            dest_batch = Batch(
                organization_id=current.organization_id,
                product_id=payload.correct_product_id,
                batch_no=batch_no,
                mfg_date=payload.correct_mfg_date or (src_batch.mfg_date if src_batch else None),
                expiry_date=payload.correct_expiry_date or (src_batch.expiry_date if src_batch else None),
                purchase_price=(
                    payload.correct_purchase_price
                    if payload.correct_purchase_price is not None
                    else (src_batch.purchase_price if src_batch else Decimal("0"))
                ),
            )
            db.add(dest_batch)
            db.flush()
        dest_stock = inv.receive_stock(
            db,
            organization_id=current.organization_id,
            branch_id=payload.correct_branch_id,
            product_id=payload.correct_product_id,
            batch_id=dest_batch.id,
            quantity=qty,
            movement_type=MovementType.adjustment,
            ref_type="adjustment",
            note=reason,
        )
        dest = {
            "branch_id": payload.correct_branch_id,
            "product_id": payload.correct_product_id,
            "batch_id": dest_batch.id,
            "batch_no": dest_batch.batch_no,
            "on_hand": float(dest_stock.quantity),
        }

    record_audit(
        db, action="update", entity_type="stock_adjustment", entity_id=payload.batch_id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=payload.branch_id,
        changes=payload.model_dump(mode="json"),
    )
    db.commit()
    return {
        "on_hand": float(stock.quantity),
        "reversed_qty": float(qty),
        "relocated": dest,
    }


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
            "batch_id": batch.id,
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
