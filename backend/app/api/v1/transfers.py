"""Inter-branch stock transfers with a request -> approve workflow."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.models.enums import MovementType, TransferStatus
from app.models.inventory import Batch
from app.models.organization import Branch
from app.models.product import Product
from app.models.transfer import StockTransfer, StockTransferItem
from app.services import inventory as inv
from app.services.inventory import InsufficientStock, describe_shortfall

router = APIRouter(prefix="/transfers", tags=["transfers"])


class TransferItemIn(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0)


class TransferIn(BaseModel):
    from_branch_id: int
    to_branch_id: int
    transfer_date: date | None = None
    notes: str | None = None
    items: list[TransferItemIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _distinct_branches(self):
        if self.from_branch_id == self.to_branch_id:
            raise ValueError("From and to branches must be different")
        return self


def _branch_address(b: Branch | None) -> str | None:
    if b is None:
        return None
    parts = [p for p in [b.address_line1, b.address_line2, b.city, b.district, b.state, b.pincode] if p]
    return ", ".join(parts) or None


def _batches_by_id(db: Session, batch_ids) -> dict[int, Batch]:
    ids = {b for b in batch_ids if b}
    if not ids:
        return {}
    return {b.id: b for b in db.scalars(select(Batch).where(Batch.id.in_(ids))).all()}


def _serialize(
    db: Session, t: StockTransfer, batches: dict[int, Batch] | None = None
) -> dict:
    from_b = db.get(Branch, t.from_branch_id)
    to_b = db.get(Branch, t.to_branch_id)
    org = from_b.organization if from_b is not None else None
    if batches is None:
        batches = _batches_by_id(db, (i.batch_id for i in t.items))
    items = []
    for i in t.items:
        batch = batches.get(i.batch_id) if i.batch_id else None
        items.append({
            "product_id": i.product_id,
            "product_name": i.product_name,
            "quantity": float(i.quantity),
            "batch_id": i.batch_id,
            "batch_no": batch.batch_no if batch else None,
            "expiry_date": batch.expiry_date.isoformat() if batch and batch.expiry_date else None,
        })
    return {
        "id": t.id, "transfer_no": t.transfer_no,
        "from_branch_id": t.from_branch_id, "to_branch_id": t.to_branch_id,
        "from_branch": from_b.name if from_b else None,
        "to_branch": to_b.name if to_b else None,
        "transfer_date": t.transfer_date.isoformat(), "status": t.status.value,
        "notes": t.notes,
        "items": items,
        "organization_name": org.name if org is not None else None,
        "branch_name": from_b.name if from_b else None,
        "branch_phone": from_b.phone if from_b else None,
        "branch_gstin": from_b.gstin if from_b else None,
        "branch_address": _branch_address(from_b),
        "thermal_paper_mm": (from_b.thermal_paper_mm if from_b else None) or 80,
        "printer_name": from_b.printer_name if from_b else None,
        "printer_type": from_b.printer_type if from_b else None,
    }


@router.get("")
def list_transfers(
    search: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    stmt = select(StockTransfer).where(
        StockTransfer.organization_id == current.organization_id
    ).order_by(StockTransfer.id.desc())
    if not current.sees_all_branches:
        ids = current.branch_ids or [-1]
        stmt = stmt.where(
            StockTransfer.from_branch_id.in_(ids) | StockTransfer.to_branch_id.in_(ids)
        )
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            StockTransfer.transfer_no.ilike(like) | StockTransfer.notes.ilike(like)
        )
    rows = db.scalars(
        stmt.options(selectinload(StockTransfer.items)).limit(limit)
    ).all()
    # Resolve every referenced batch once for the whole page.
    batches = _batches_by_id(db, (i.batch_id for t in rows for i in t.items))
    return [_serialize(db, t, batches) for t in rows]


@router.post("", status_code=201)
def create_transfer(
    payload: TransferIn,
    current: CurrentUser = Depends(require_permission(rbac.P_INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    if payload.from_branch_id == payload.to_branch_id:
        raise HTTPException(status_code=400, detail="Source and destination must differ")
    current.assert_branch_access(payload.from_branch_id)
    transfer = StockTransfer(
        organization_id=current.organization_id,
        from_branch_id=payload.from_branch_id, to_branch_id=payload.to_branch_id,
        requested_by_user_id=current.id, transfer_date=payload.transfer_date or date.today(),
        status=TransferStatus.requested, notes=payload.notes,
    )
    db.add(transfer)
    db.flush()
    for it in payload.items:
        product = db.get(Product, it.product_id)
        transfer.items.append(StockTransferItem(
            product_id=it.product_id,
            product_name=product.name if product else str(it.product_id),
            quantity=it.quantity,
        ))
    count = db.scalar(select(func.count(StockTransfer.id)).where(
        StockTransfer.organization_id == current.organization_id)) or 0
    transfer.transfer_no = f"TR/{date.today().year}/{count:05d}"
    db.flush()
    record_audit(db, action="create", entity_type="stock_transfer", entity_id=transfer.id,
                 actor_user_id=current.id, organization_id=current.organization_id,
                 branch_id=transfer.from_branch_id)
    db.commit()
    return _serialize(db, transfer)


@router.get("/{transfer_id}")
def get_transfer(
    transfer_id: int,
    current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db),
) -> dict:
    transfer = db.get(StockTransfer, transfer_id)
    if transfer is None or transfer.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if not current.sees_all_branches:
        ids = current.branch_ids or [-1]
        if transfer.from_branch_id not in ids and transfer.to_branch_id not in ids:
            raise HTTPException(status_code=404, detail="Transfer not found")
    return _serialize(db, transfer)


@router.post("/{transfer_id}/approve")
def approve_transfer(
    transfer_id: int,
    current: CurrentUser = Depends(require_permission(rbac.P_INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    """Approve + execute the movement (FIFO out of source, into destination)."""
    transfer = db.get(StockTransfer, transfer_id)
    if transfer is None or transfer.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if transfer.status not in (TransferStatus.requested, TransferStatus.approved):
        raise HTTPException(status_code=409, detail=f"Cannot approve ({transfer.status.value})")

    original_items = list(transfer.items)
    for item in original_items:
        try:
            allocations = inv.allocate_fifo(
                db, branch_id=transfer.from_branch_id, product_id=item.product_id,
                quantity=item.quantity)
        except InsufficientStock as exc:
            raise HTTPException(status_code=409, detail=describe_shortfall(db, exc))
        inv.apply_issue(
            db, organization_id=current.organization_id, branch_id=transfer.from_branch_id,
            product_id=item.product_id, allocations=allocations,
            movement_type=MovementType.transfer_out, ref_type="transfer", ref_id=transfer.id)
        for alloc in allocations:
            inv.receive_stock(
                db, organization_id=current.organization_id, branch_id=transfer.to_branch_id,
                product_id=item.product_id, batch_id=alloc.batch_id, quantity=alloc.quantity,
                movement_type=MovementType.transfer_in, ref_type="transfer", ref_id=transfer.id)
        first, *rest = allocations
        item.batch_id = first.batch_id
        item.quantity = first.quantity
        for alloc in rest:
            transfer.items.append(StockTransferItem(
                product_id=item.product_id,
                product_name=item.product_name,
                quantity=alloc.quantity,
                batch_id=alloc.batch_id,
            ))

    transfer.status = TransferStatus.received
    transfer.approved_by_user_id = current.id
    record_audit(db, action="update", entity_type="stock_transfer", entity_id=transfer.id,
                 actor_user_id=current.id, organization_id=current.organization_id,
                 branch_id=transfer.from_branch_id, changes={"status": "received"})
    db.commit()
    return _serialize(db, transfer)


@router.post("/{transfer_id}/reject")
def reject_transfer(
    transfer_id: int,
    current: CurrentUser = Depends(require_permission(rbac.P_INVENTORY_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    transfer = db.get(StockTransfer, transfer_id)
    if transfer is None or transfer.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Transfer not found")
    transfer.status = TransferStatus.rejected
    db.commit()
    return _serialize(db, transfer)
