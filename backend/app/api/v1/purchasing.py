"""Purchase cycle: vendors, purchase orders, GRN receipt, vendor payments."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.models.enums import MovementType, PurchaseOrderStatus
from app.models.inventory import Batch
from app.models.product import Product
from app.models.purchase import (
    GRN,
    GRNItem,
    PurchaseOrder,
    PurchaseOrderItem,
    VendorPayment,
)
from app.models.vendor import Vendor
from app.services import accounting, inventory as inv

router = APIRouter(prefix="/purchasing", tags=["purchasing"])


# --- Schemas ---
class VendorIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    gstin: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None


class POItemIn(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)


class POIn(BaseModel):
    branch_id: int
    vendor_id: int
    order_date: date | None = None
    notes: str | None = None
    items: list[POItemIn] = Field(min_length=1)


class GRNItemIn(BaseModel):
    product_id: int
    batch_no: str = Field(min_length=1, max_length=80)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    mfg_date: date | None = None
    expiry_date: date | None = None


class GRNIn(BaseModel):
    branch_id: int
    vendor_id: int
    purchase_order_id: int | None = None
    received_date: date | None = None
    vendor_invoice_no: str | None = None
    items: list[GRNItemIn] = Field(min_length=1)


class VendorPaymentIn(BaseModel):
    vendor_id: int
    branch_id: int | None = None
    amount: Decimal = Field(gt=0)
    mode: str = "cash"
    note: str | None = None


# --- Vendors ---
@router.get("/vendors")
def list_vendors(
    search: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    stmt = select(Vendor).where(
        Vendor.organization_id == current.organization_id, Vendor.is_deleted.is_(False)
    )
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(
            Vendor.name.ilike(like),
            Vendor.gstin.ilike(like),
            Vendor.phone.ilike(like),
        ))
    rows = db.scalars(stmt.order_by(Vendor.name.asc()).limit(limit)).all()
    return [
        {"id": v.id, "name": v.name, "gstin": v.gstin, "phone": v.phone,
         "email": v.email, "outstanding_balance": float(v.outstanding_balance)}
        for v in rows
    ]


@router.post("/vendors", status_code=201)
def create_vendor(
    payload: VendorIn,
    current: CurrentUser = Depends(require_permission(rbac.P_PURCHASE_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    vendor = Vendor(organization_id=current.organization_id, **payload.model_dump())
    db.add(vendor)
    db.flush()
    record_audit(db, action="create", entity_type="vendor", entity_id=vendor.id,
                 actor_user_id=current.id, organization_id=current.organization_id,
                 changes=payload.model_dump(mode="json"))
    db.commit()
    return {"id": vendor.id, "name": vendor.name}


@router.put("/vendors/{vendor_id}")
def update_vendor(
    vendor_id: int,
    payload: VendorIn,
    current: CurrentUser = Depends(require_permission(rbac.P_PURCHASE_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    vendor = db.get(Vendor, vendor_id)
    if vendor is None or vendor.organization_id != current.organization_id or vendor.is_deleted:
        raise HTTPException(status_code=404, detail="Vendor not found")
    for key, value in payload.model_dump().items():
        setattr(vendor, key, value)
    record_audit(db, action="update", entity_type="vendor", entity_id=vendor.id,
                 actor_user_id=current.id, organization_id=current.organization_id,
                 changes=payload.model_dump(mode="json"))
    db.commit()
    return {"id": vendor.id, "name": vendor.name}


@router.delete("/vendors/{vendor_id}")
def delete_vendor(
    vendor_id: int,
    current: CurrentUser = Depends(require_permission(rbac.P_PURCHASE_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    vendor = db.get(Vendor, vendor_id)
    if vendor is None or vendor.organization_id != current.organization_id or vendor.is_deleted:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if vendor.outstanding_balance and vendor.outstanding_balance != 0:
        raise HTTPException(status_code=409, detail="Cannot delete a vendor with an outstanding payable.")
    vendor.is_deleted = True
    record_audit(db, action="delete", entity_type="vendor", entity_id=vendor.id,
                 actor_user_id=current.id, organization_id=current.organization_id)
    db.commit()
    return {"status": "deleted", "id": vendor_id}


@router.get("/vendors/{vendor_id}/ledger")
def vendor_ledger(
    vendor_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    vendor = db.get(Vendor, vendor_id)
    if vendor is None or vendor.organization_id != current.organization_id or vendor.is_deleted:
        raise HTTPException(status_code=404, detail="Vendor not found")
    grns = db.scalars(
        select(GRN).where(
            GRN.organization_id == current.organization_id, GRN.vendor_id == vendor_id,
        ).order_by(GRN.received_date.asc(), GRN.id.asc())
    ).all()
    payments = db.scalars(
        select(VendorPayment).where(
            VendorPayment.organization_id == current.organization_id,
            VendorPayment.vendor_id == vendor_id,
        ).order_by(VendorPayment.paid_at.asc(), VendorPayment.id.asc())
    ).all()
    entries: list[dict] = []
    for g in grns:
        entries.append({
            "kind": "grn",
            "date": g.received_date.isoformat(),
            "ref": g.grn_no,
            "debit": float(g.total_value),
            "credit": 0,
            "note": g.vendor_invoice_no,
        })
    for p in payments:
        entries.append({
            "kind": "payment",
            "date": (p.paid_at.date().isoformat() if p.paid_at else None),
            "ref": f"PAY-{p.id}",
            "debit": 0,
            "credit": float(p.amount),
            "note": p.note or p.mode,
        })
    entries.sort(key=lambda e: (e["date"] or "", e["ref"] or ""))
    running = 0.0
    for e in entries:
        running += e["debit"] - e["credit"]
        e["balance"] = round(running, 2)
    return {
        "id": vendor.id,
        "name": vendor.name,
        "gstin": vendor.gstin,
        "phone": vendor.phone,
        "outstanding_balance": float(vendor.outstanding_balance),
        "entries": entries,
        "payments": [
            {
                "id": p.id,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "amount": float(p.amount),
                "mode": p.mode,
                "note": p.note,
            }
            for p in reversed(list(payments))
        ],
    }


# --- Purchase Orders ---
@router.get("/orders")
def list_orders(
    search: str | None = None,
    limit: int = Query(100, ge=1, le=300),
    current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    stmt = select(PurchaseOrder).where(
        PurchaseOrder.organization_id == current.organization_id
    )
    if not current.sees_all_branches:
        stmt = stmt.where(PurchaseOrder.branch_id.in_(current.branch_ids or [-1]))
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.join(Vendor, Vendor.id == PurchaseOrder.vendor_id).where(
            or_(PurchaseOrder.po_no.ilike(like), Vendor.name.ilike(like))
        )
    stmt = stmt.order_by(PurchaseOrder.id.desc()).limit(limit)
    out = []
    for po in db.scalars(stmt).unique().all():
        vendor = db.get(Vendor, po.vendor_id)
        out.append({
            "id": po.id, "po_no": po.po_no, "branch_id": po.branch_id,
            "vendor": vendor.name if vendor else None,
            "order_date": po.order_date.isoformat(), "status": po.status.value,
            "expected_total": float(po.expected_total),
            "items": [{"product_id": i.product_id, "product_name": i.product_name,
                       "quantity": float(i.quantity),
                       "received_quantity": float(i.received_quantity),
                       "unit_price": float(i.unit_price)} for i in po.items],
        })
    return out


@router.post("/orders", status_code=201)
def create_order(
    payload: POIn,
    current: CurrentUser = Depends(require_permission(rbac.P_PURCHASE_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    current.assert_branch_access(payload.branch_id)
    po = PurchaseOrder(
        organization_id=current.organization_id, branch_id=payload.branch_id,
        vendor_id=payload.vendor_id, created_by_user_id=current.id,
        order_date=payload.order_date or date.today(),
        status=PurchaseOrderStatus.placed, notes=payload.notes,
    )
    db.add(po)
    db.flush()
    total = Decimal("0")
    for it in payload.items:
        product = db.get(Product, it.product_id)
        po.items.append(PurchaseOrderItem(
            product_id=it.product_id,
            product_name=product.name if product else str(it.product_id),
            quantity=it.quantity, unit_price=it.unit_price,
        ))
        total += it.quantity * it.unit_price
    po.expected_total = total
    count = db.scalar(select(func.count(PurchaseOrder.id)).where(
        PurchaseOrder.organization_id == current.organization_id)) or 0
    po.po_no = f"PO/{date.today().year}/{count:05d}"
    db.flush()
    record_audit(db, action="create", entity_type="purchase_order", entity_id=po.id,
                 actor_user_id=current.id, organization_id=current.organization_id,
                 branch_id=po.branch_id)
    db.commit()
    return {"id": po.id, "po_no": po.po_no, "expected_total": float(total)}


# --- GRN (goods receipt) ---
@router.post("/grn", status_code=201)
def create_grn(
    payload: GRNIn,
    current: CurrentUser = Depends(require_permission(rbac.P_PURCHASE_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    current.assert_branch_access(payload.branch_id)
    grn = GRN(
        organization_id=current.organization_id, branch_id=payload.branch_id,
        vendor_id=payload.vendor_id, purchase_order_id=payload.purchase_order_id,
        created_by_user_id=current.id, received_date=payload.received_date or date.today(),
        vendor_invoice_no=payload.vendor_invoice_no,
    )
    db.add(grn)
    db.flush()

    total = Decimal("0")
    for it in payload.items:
        product = db.get(Product, it.product_id)
        if product is None:
            raise HTTPException(status_code=400, detail=f"Product {it.product_id} not found")
        batch = db.scalar(select(Batch).where(
            Batch.product_id == it.product_id, Batch.batch_no == it.batch_no))
        if batch is None:
            batch = Batch(
                organization_id=current.organization_id, product_id=it.product_id,
                batch_no=it.batch_no, mfg_date=it.mfg_date, expiry_date=it.expiry_date,
                purchase_price=it.unit_price,
            )
            db.add(batch)
            db.flush()
        inv.receive_stock(
            db, organization_id=current.organization_id, branch_id=payload.branch_id,
            product_id=it.product_id, batch_id=batch.id, quantity=it.quantity,
            movement_type=MovementType.grn, ref_type="grn", ref_id=grn.id,
        )
        grn.items.append(GRNItem(
            product_id=it.product_id, batch_id=batch.id, batch_no=it.batch_no,
            mfg_date=it.mfg_date, expiry_date=it.expiry_date,
            quantity=it.quantity, unit_price=it.unit_price,
        ))
        total += it.quantity * it.unit_price

        # Update matching PO line received quantity.
        if payload.purchase_order_id:
            po_item = db.scalar(select(PurchaseOrderItem).where(
                PurchaseOrderItem.order_id == payload.purchase_order_id,
                PurchaseOrderItem.product_id == it.product_id))
            if po_item:
                po_item.received_quantity = po_item.received_quantity + it.quantity

    grn.total_value = total
    count = db.scalar(select(func.count(GRN.id)).where(
        GRN.organization_id == current.organization_id)) or 0
    grn.grn_no = f"GRN/{date.today().year}/{count:05d}"

    # Vendor payable + accounting.
    vendor = db.get(Vendor, payload.vendor_id)
    if vendor:
        vendor.outstanding_balance = vendor.outstanding_balance + total
    accounting.post_purchase(
        db, organization_id=current.organization_id, branch_id=payload.branch_id,
        entry_date=grn.received_date, grn_id=grn.id, total_value=total)

    # Update PO status.
    if payload.purchase_order_id:
        po = db.get(PurchaseOrder, payload.purchase_order_id)
        if po:
            fully = all(i.received_quantity >= i.quantity for i in po.items)
            po.status = (PurchaseOrderStatus.received if fully
                         else PurchaseOrderStatus.partially_received)

    record_audit(db, action="create", entity_type="grn", entity_id=grn.id,
                 actor_user_id=current.id, organization_id=current.organization_id,
                 branch_id=grn.branch_id, changes={"total_value": str(total)})
    db.commit()
    return {"id": grn.id, "grn_no": grn.grn_no, "total_value": float(total)}


@router.get("/grn")
def list_grn(
    search: str | None = None,
    limit: int = Query(100, ge=1, le=300),
    current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    stmt = select(GRN).where(GRN.organization_id == current.organization_id)
    if not current.sees_all_branches:
        stmt = stmt.where(GRN.branch_id.in_(current.branch_ids or [-1]))
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.join(Vendor, Vendor.id == GRN.vendor_id).where(
            or_(
                GRN.grn_no.ilike(like),
                GRN.vendor_invoice_no.ilike(like),
                Vendor.name.ilike(like),
            )
        )
    out = []
    for g in db.scalars(stmt.order_by(GRN.id.desc()).limit(limit)).unique().all():
        vendor = db.get(Vendor, g.vendor_id)
        out.append({
            "id": g.id, "grn_no": g.grn_no, "branch_id": g.branch_id,
            "vendor_id": g.vendor_id,
            "vendor": vendor.name if vendor else None,
            "received_date": g.received_date.isoformat(),
            "vendor_invoice_no": g.vendor_invoice_no, "total_value": float(g.total_value),
        })
    return out


# --- Vendor payments ---
@router.post("/payments", status_code=201)
def create_payment(
    payload: VendorPaymentIn,
    current: CurrentUser = Depends(require_permission(rbac.P_PURCHASE_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    vendor = db.get(Vendor, payload.vendor_id)
    if vendor is None or vendor.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Vendor not found")
    payment = VendorPayment(
        organization_id=current.organization_id, branch_id=payload.branch_id,
        vendor_id=payload.vendor_id, amount=payload.amount, mode=payload.mode,
        note=payload.note,
    )
    db.add(payment)
    db.flush()
    vendor.outstanding_balance = vendor.outstanding_balance - Decimal(payload.amount)
    accounting.post_vendor_payment(
        db, organization_id=current.organization_id, branch_id=payload.branch_id,
        entry_date=date.today(), payment_id=payment.id, amount=payload.amount,
        mode=payload.mode)
    record_audit(db, action="create", entity_type="vendor_payment", entity_id=payment.id,
                 actor_user_id=current.id, organization_id=current.organization_id)
    db.commit()
    return {"id": payment.id, "vendor_outstanding": float(vendor.outstanding_balance)}


@router.get("/payments")
def list_payments(
    vendor_id: int | None = None,
    limit: int = Query(100, ge=1, le=300),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(VendorPayment).where(VendorPayment.organization_id == current.organization_id)
    if vendor_id is not None:
        stmt = stmt.where(VendorPayment.vendor_id == vendor_id)
    rows = db.scalars(stmt.order_by(VendorPayment.id.desc()).limit(limit)).all()
    out = []
    for p in rows:
        vendor = db.get(Vendor, p.vendor_id)
        out.append({
            "id": p.id,
            "vendor_id": p.vendor_id,
            "vendor": vendor.name if vendor else None,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            "amount": float(p.amount),
            "mode": p.mode,
            "note": p.note,
        })
    return out
