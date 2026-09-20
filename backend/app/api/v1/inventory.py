"""Inventory: stock receipt (GRN), on-hand view, and demand forecasting."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.models.enums import MovementType, StockDiscrepancyStatus
from app.models.inventory import Batch, Stock, StockDiscrepancy, StockMovement
from app.models.product import Product
from app.models.purchase import GRN, GRNItem, PurchaseReturn, PurchaseReturnItem
from app.schemas.masters import (
    BatchCostIn,
    StockAdjustIn,
    StockDiscrepancyIn,
    StockDiscrepancyResolveIn,
    StockReceiptIn,
)
from app.services import inventory as inv
from app.services.ai import forecasting
from app.services.inventory import InsufficientStock

router = APIRouter(prefix="/inventory", tags=["inventory"])

_MOVEMENT_LABELS = {
    "grn": "Purchase (GRN)",
    "sale": "Sale",
    "sale_return": "Sales return",
    "purchase_return": "Purchase return",
    "transfer_out": "Transfer out",
    "transfer_in": "Transfer in",
    "adjustment": "Adjustment",
}


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
    """Add opening / correction stock to a branch without a supplier bill.

    This is NOT a purchase. It raises no payable and posts no purchase entry,
    so it is tagged as an adjustment in the movement ledger. Stock bought from
    a supplier must go through POST /purchasing/grn to keep the books right.
    """
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
        movement_type=MovementType.adjustment,
        note="Opening / correction stock (no supplier bill)",
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
    search: str | None = None,
    limit: int = Query(1000, ge=1, le=5000),
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
    if search and search.strip():
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(Product.name.ilike(like), Product.sku.ilike(like), Batch.batch_no.ilike(like))
        )
    stmt = stmt.order_by(Product.name.asc(), Batch.expiry_date.asc()).limit(limit)

    out = []
    for stock, batch, product in db.execute(stmt).all():
        out.append({
            "branch_id": stock.branch_id,
            "product_id": product.id,
            "product": product.name,
            "sku": product.sku,
            "batch_id": batch.id,
            "batch_no": batch.batch_no,
            "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
            "quantity": float(stock.quantity),
            "purchase_price": float(batch.purchase_price or 0),
            "product_purchase_price": float(product.purchase_price or 0),
        })
    return out


@router.put("/batches/{batch_id}")
def update_batch_cost(
    batch_id: int,
    payload: BatchCostIn,
    current: CurrentUser = Depends(require_permission(rbac.P_INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    """Correct the pack cost on a batch. Product margin and P&L read this value."""
    batch = db.get(Batch, batch_id)
    if batch is None or batch.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Batch not found")
    before = batch.purchase_price
    batch.purchase_price = payload.purchase_price
    record_audit(
        db, action="update", entity_type="batch", entity_id=batch.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        changes={
            "batch_no": batch.batch_no,
            "purchase_price": {"from": float(before or 0), "to": float(payload.purchase_price)},
        },
    )
    db.commit()
    db.refresh(batch)
    return {
        "batch_id": batch.id,
        "batch_no": batch.batch_no,
        "purchase_price": float(batch.purchase_price or 0),
    }


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


def _case_out(row: StockDiscrepancy, product_name: str | None = None, branch_name: str | None = None) -> dict:
    st = row.status.value if hasattr(row.status, "value") else str(row.status)
    return {
        "id": row.id,
        "branch_id": row.branch_id,
        "product_id": row.product_id,
        "product": product_name,
        "branch": branch_name,
        "count_date": row.count_date.isoformat(),
        "book_qty": float(row.book_qty),
        "counted_qty": float(row.counted_qty),
        "variance": float(row.variance),
        "status": st,
        "note": row.note,
        "resolution": row.resolution,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
    }


@router.get("/discrepancies")
def list_discrepancies(
    status: str | None = Query(None),
    branch_id: int | None = None,
    current: CurrentUser = Depends(require_permission(rbac.P_REPORT_VIEW)),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(StockDiscrepancy, Product.name).join(
        Product, Product.id == StockDiscrepancy.product_id
    ).where(StockDiscrepancy.organization_id == current.organization_id)
    if branch_id is not None:
        current.assert_branch_access(branch_id)
        stmt = stmt.where(StockDiscrepancy.branch_id == branch_id)
    elif not current.sees_all_branches:
        stmt = stmt.where(StockDiscrepancy.branch_id.in_(current.branch_ids or [-1]))
    if status:
        try:
            st = StockDiscrepancyStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Unknown status")
        stmt = stmt.where(StockDiscrepancy.status == st)
    stmt = stmt.order_by(StockDiscrepancy.updated_at.desc(), StockDiscrepancy.id.desc())
    rows = [
        _case_out(c, product_name=name)
        for c, name in db.execute(stmt).all()
    ]
    open_n = sum(1 for r in rows if r["status"] in {"open", "investigating"})
    return {"items": rows, "open_count": open_n}


@router.get("/trail")
def stock_trail(
    product_id: int,
    branch_id: int,
    start: date | None = None,
    end: date | None = None,
    current: CurrentUser = Depends(require_permission(rbac.P_REPORT_VIEW)),
    db: Session = Depends(get_db),
) -> dict:
    """Movement rollforward for one SKU at one branch — used to trace a count mismatch."""
    current.assert_branch_access(branch_id)
    product = db.get(Product, product_id)
    if product is None or product.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Product not found")
    start_d = start or date.today().replace(day=1)
    end_d = end or date.today()
    if end_d < start_d:
        raise HTTPException(status_code=400, detail="End date is before start date")
    start_dt = datetime.combine(start_d, datetime.min.time())
    end_dt = datetime.combine(end_d + timedelta(days=1), datetime.min.time())

    opening = float(db.scalar(
        select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
            StockMovement.organization_id == current.organization_id,
            StockMovement.product_id == product_id,
            StockMovement.branch_id == branch_id,
            StockMovement.occurred_at < start_dt,
        )
    ) or 0)
    stmt = (
        select(StockMovement, Batch.batch_no)
        .join(Batch, Batch.id == StockMovement.batch_id)
        .where(
            StockMovement.organization_id == current.organization_id,
            StockMovement.product_id == product_id,
            StockMovement.branch_id == branch_id,
            StockMovement.occurred_at >= start_dt,
            StockMovement.occurred_at < end_dt,
        )
        .order_by(StockMovement.occurred_at.asc(), StockMovement.id.asc())
        .limit(500)
    )
    running = opening
    rows = []
    for m, batch in db.execute(stmt).all():
        qty = float(m.quantity)
        running = round(running + qty, 3)
        mt = m.movement_type.value if hasattr(m.movement_type, "value") else str(m.movement_type)
        rows.append({
            "when": m.occurred_at.strftime("%Y-%m-%d %H:%M"),
            "type": _MOVEMENT_LABELS.get(mt, mt),
            "qty": round(qty, 3),
            "running": running,
            "batch": batch,
            "note": m.note or m.ref_type or "—",
        })
    on_hand = float(db.scalar(
        select(func.coalesce(func.sum(Stock.quantity), 0)).where(
            Stock.organization_id == current.organization_id,
            Stock.branch_id == branch_id,
            Stock.product_id == product_id,
        )
    ) or 0)
    return {
        "product": product.name,
        "sku": product.sku,
        "branch_id": branch_id,
        "opening": round(opening, 3),
        "closing": round(running, 3),
        "on_hand_now": round(on_hand, 3),
        "start": start_d.isoformat(),
        "end": end_d.isoformat(),
        "rows": rows,
    }


@router.post("/discrepancies", status_code=201)
def log_discrepancy(
    payload: StockDiscrepancyIn,
    current: CurrentUser = Depends(require_permission(rbac.P_INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    current.assert_branch_access(payload.branch_id)
    product = db.get(Product, payload.product_id)
    if product is None or product.organization_id != current.organization_id:
        raise HTTPException(status_code=400, detail="Product not found")
    book = db.scalar(
        select(func.coalesce(func.sum(Stock.quantity), 0)).where(
            Stock.organization_id == current.organization_id,
            Stock.branch_id == payload.branch_id,
            Stock.product_id == payload.product_id,
        )
    ) or 0
    book_qty = Decimal(book)
    counted = Decimal(payload.counted_qty)
    variance = counted - book_qty
    note = payload.note.strip()
    count_date = payload.count_date or date.today()

    existing = db.scalar(
        select(StockDiscrepancy).where(
            StockDiscrepancy.organization_id == current.organization_id,
            StockDiscrepancy.branch_id == payload.branch_id,
            StockDiscrepancy.product_id == payload.product_id,
            StockDiscrepancy.status.in_(
                (StockDiscrepancyStatus.open, StockDiscrepancyStatus.investigating)
            ),
        ).order_by(StockDiscrepancy.id.desc())
    )
    if existing is not None:
        existing.book_qty = book_qty
        existing.counted_qty = counted
        existing.variance = variance
        existing.note = note
        existing.count_date = count_date
        if variance == 0:
            existing.status = StockDiscrepancyStatus.resolved
            existing.resolution = "Count matches book"
            existing.resolved_by_user_id = current.id
            existing.resolved_at = datetime.utcnow()
        row = existing
        action = "update"
    else:
        status = StockDiscrepancyStatus.resolved if variance == 0 else StockDiscrepancyStatus.open
        row = StockDiscrepancy(
            organization_id=current.organization_id,
            branch_id=payload.branch_id,
            product_id=payload.product_id,
            count_date=count_date,
            book_qty=book_qty,
            counted_qty=counted,
            variance=variance,
            status=status,
            note=note,
            created_by_user_id=current.id,
            resolution="Count matches book" if variance == 0 else None,
            resolved_by_user_id=current.id if variance == 0 else None,
            resolved_at=datetime.utcnow() if variance == 0 else None,
        )
        db.add(row)
        db.flush()
        action = "create"
    record_audit(
        db, action=action, entity_type="stock_discrepancy", entity_id=row.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=payload.branch_id,
        changes={"book_qty": float(book_qty), "counted_qty": float(counted),
                 "variance": float(variance), "note": note},
    )
    db.commit()
    db.refresh(row)
    return _case_out(row, product_name=product.name)


@router.post("/discrepancies/{case_id}/investigate")
def investigate_discrepancy(
    case_id: int,
    current: CurrentUser = Depends(require_permission(rbac.P_INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(StockDiscrepancy, case_id)
    if row is None or row.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Case not found")
    current.assert_branch_access(row.branch_id)
    if row.status == StockDiscrepancyStatus.resolved:
        raise HTTPException(status_code=400, detail="This case is already resolved.")
    row.status = StockDiscrepancyStatus.investigating
    record_audit(
        db, action="update", entity_type="stock_discrepancy", entity_id=row.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=row.branch_id, changes={"status": "investigating"},
    )
    db.commit()
    db.refresh(row)
    return _case_out(row)


@router.post("/discrepancies/{case_id}/resolve")
def resolve_discrepancy(
    case_id: int,
    payload: StockDiscrepancyResolveIn,
    current: CurrentUser = Depends(require_permission(rbac.P_INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(StockDiscrepancy, case_id)
    if row is None or row.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Case not found")
    current.assert_branch_access(row.branch_id)
    if row.status == StockDiscrepancyStatus.resolved:
        raise HTTPException(status_code=400, detail="This case is already resolved.")
    row.status = StockDiscrepancyStatus.resolved
    row.resolution = payload.resolution.strip()
    row.resolved_by_user_id = current.id
    row.resolved_at = datetime.utcnow()
    record_audit(
        db, action="update", entity_type="stock_discrepancy", entity_id=row.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=row.branch_id, changes={"status": "resolved", "resolution": row.resolution},
    )
    db.commit()
    db.refresh(row)
    return _case_out(row)

