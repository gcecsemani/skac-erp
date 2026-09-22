"""Purchase cycle: vendors, purchase orders, GRN, purchase returns, vendor payments."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.models.inventory import Batch, Stock
from app.models.enums import MovementType, PurchaseOrderStatus
from app.models.organization import Branch, Organization
from app.models.product import Product
from app.models.purchase import (
    GRN,
    GRNItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseReturn,
    PurchaseReturnItem,
    VendorPayment,
)
from app.models.vendor import Vendor
from app.services import accounting, inventory as inv
from app.services.inventory import InsufficientStock

router = APIRouter(prefix="/purchasing", tags=["purchasing"])


# --- Schemas ---
def _normalize_vendor_phone(value: str | None) -> str | None:
    """Accept Indian mobile (6–9…) and Tamil Nadu / India landline numbers."""
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("91") and len(digits) >= 12:
        digits = digits[2:]

    def is_mobile(n: str) -> bool:
        return len(n) == 10 and n[:1] in "6789"

    if is_mobile(digits) or (len(digits) == 11 and digits.startswith("0") and is_mobile(digits[1:])):
        return raw
    if len(digits) in (10, 11) and digits.startswith("0") and len(digits) > 1 and digits[1] in "2345678":
        return raw
    if len(digits) == 10 and digits[:1] in "2345":
        return raw
    if 6 <= len(digits) <= 8 and digits[:1] in "2345678":
        return raw
    raise ValueError("Enter a valid Indian mobile or landline number")


class VendorIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    gstin: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None

    @field_validator("name")
    @classmethod
    def _vendor_name(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) < 2:
            raise ValueError("Vendor name must be at least 2 characters")
        return v

    @field_validator("phone")
    @classmethod
    def _vendor_phone(cls, v: str | None) -> str | None:
        return _normalize_vendor_phone(v)


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


class PurchaseReturnItemIn(BaseModel):
    grn_item_id: int
    quantity: Decimal = Field(gt=0)


class PurchaseReturnIn(BaseModel):
    grn_id: int
    reason: str = Field(min_length=3, max_length=255)
    items: list[PurchaseReturnItemIn] = Field(min_length=1)


class ReverseIn(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


def _gstin_state(gstin: str | None, fallback: str | None = None) -> str | None:
    g = (gstin or "").strip().upper()
    if len(g) >= 2 and g[:2].isdigit():
        return g[:2]
    return fallback or None


def _pan_from_gstin(gstin: str | None, fallback: str | None = None) -> str | None:
    g = (gstin or "").strip().upper()
    if len(g) >= 12:
        return g[2:12]
    return fallback or None


def _branch_address(b: Branch | None) -> str | None:
    if b is None:
        return None
    parts = [p for p in [b.address_line1, b.address_line2, b.city, b.district, b.state, b.pincode] if p]
    return ", ".join(parts) or None


def _line_gst(qty: Decimal, unit_price: Decimal, gst_rate: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    TWO = Decimal("0.01")
    taxable = (qty * unit_price).quantize(TWO)
    rate = gst_rate or Decimal("0")
    tax = (taxable * rate / Decimal("100")).quantize(TWO)
    return taxable, tax, (taxable + tax).quantize(TWO)


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
    rows = db.scalars(stmt.order_by(Vendor.outstanding_balance.desc(), Vendor.name.asc()).limit(limit)).all()
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
        paid_at = p.paid_at.strftime("%Y-%m-%d %H:%M") if p.paid_at else None
        entries.append({
            "kind": "payment",
            "id": p.id,
            "date": paid_at,
            "ref": f"PAY-{p.id}",
            "debit": 0,
            "credit": float(p.amount),
            "note": " · ".join(part for part in (p.mode, p.note) if part) or "Payment",
            "reversed": p.reversed_at is not None,
        })
        if p.reversed_at is not None:
            entries.append({
                "kind": "payment_reversal",
                "date": p.reversed_at.strftime("%Y-%m-%d %H:%M"),
                "ref": f"REV-{p.id}",
                "debit": float(p.amount),
                "credit": 0,
                "note": p.reversal_reason or "Reversed",
                "reversed": True,
            })
    returns = db.scalars(
        select(PurchaseReturn).where(
            PurchaseReturn.organization_id == current.organization_id,
            PurchaseReturn.vendor_id == vendor_id,
        ).order_by(PurchaseReturn.note_date.asc(), PurchaseReturn.id.asc())
    ).all()
    for r in returns:
        entries.append({
            "kind": "return",
            "date": r.note_date.isoformat(),
            "ref": r.note_no,
            "debit": 0,
            "credit": float(r.total),
            "note": r.reason,
        })
    entries.sort(key=lambda e: (
        e["date"] or "",
        {"grn": 0, "return": 1, "payment": 2, "payment_reversal": 3}.get(e["kind"], 9),
        e["ref"] or "",
    ))
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
                "reversed_at": p.reversed_at.isoformat() if p.reversed_at else None,
                "reversal_reason": p.reversal_reason,
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
    stmt = (
        select(PurchaseOrder, Vendor.name)
        .join(Vendor, Vendor.id == PurchaseOrder.vendor_id)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.organization_id == current.organization_id)
    )
    if not current.sees_all_branches:
        stmt = stmt.where(PurchaseOrder.branch_id.in_(current.branch_ids or [-1]))
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(PurchaseOrder.po_no.ilike(like), Vendor.name.ilike(like))
        )
    stmt = stmt.order_by(PurchaseOrder.id.desc()).limit(limit)
    out = []
    for po, vendor_name in db.execute(stmt).unique().all():
        out.append({
            "id": po.id, "po_no": po.po_no, "branch_id": po.branch_id,
            "vendor": vendor_name,
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

    # Resolve every line's product and existing batch up front; a large GRN
    # was otherwise doing three round-trips per line.
    products = _products_by_id(db, (it.product_id for it in payload.items))
    line_product_ids = {it.product_id for it in payload.items}
    existing_batches: dict[tuple[int, str], Batch] = {
        (b.product_id, b.batch_no): b
        for b in db.scalars(
            select(Batch).where(
                Batch.product_id.in_(line_product_ids),
                Batch.batch_no.in_({it.batch_no for it in payload.items}),
            )
        ).all()
    }
    po_items_by_product: dict[int, PurchaseOrderItem] = {}
    if payload.purchase_order_id:
        po_items_by_product = {
            pi.product_id: pi
            for pi in db.scalars(
                select(PurchaseOrderItem).where(
                    PurchaseOrderItem.order_id == payload.purchase_order_id
                )
            ).all()
        }

    total = Decimal("0")
    for it in payload.items:
        product = products.get(it.product_id)
        if product is None:
            raise HTTPException(status_code=400, detail=f"Product {it.product_id} not found")
        batch = existing_batches.get((it.product_id, it.batch_no))
        if batch is None:
            batch = Batch(
                organization_id=current.organization_id, product_id=it.product_id,
                batch_no=it.batch_no, mfg_date=it.mfg_date, expiry_date=it.expiry_date,
                purchase_price=it.unit_price,
            )
            db.add(batch)
            db.flush()
            existing_batches[(it.product_id, it.batch_no)] = batch
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
        po_item = po_items_by_product.get(it.product_id)
        if po_item is not None:
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
    stmt = (
        select(GRN, Vendor.name)
        .join(Vendor, Vendor.id == GRN.vendor_id)
        .options(selectinload(GRN.items))
        .where(GRN.organization_id == current.organization_id)
    )
    if not current.sees_all_branches:
        stmt = stmt.where(GRN.branch_id.in_(current.branch_ids or [-1]))
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                GRN.grn_no.ilike(like),
                GRN.vendor_invoice_no.ilike(like),
                Vendor.name.ilike(like),
            )
        )
    out = []
    for g, vendor_name in db.execute(stmt.order_by(GRN.id.desc()).limit(limit)).unique().all():
        out.append({
            "id": g.id, "grn_no": g.grn_no, "branch_id": g.branch_id,
            "vendor_id": g.vendor_id,
            "vendor": vendor_name,
            "received_date": g.received_date.isoformat(),
            "vendor_invoice_no": g.vendor_invoice_no, "total_value": float(g.total_value),
            "item_count": len(g.items),
        })
    return out


def _products_by_id(db: Session, product_ids) -> dict[int, Product]:
    ids = {pid for pid in product_ids if pid}
    if not ids:
        return {}
    return {
        p.id: p for p in db.scalars(select(Product).where(Product.id.in_(ids))).all()
    }


def _returned_qty_by_grn_item(db: Session, grn_id: int) -> dict[int, Decimal]:
    rows = db.execute(
        select(
            PurchaseReturnItem.grn_item_id,
            func.coalesce(func.sum(PurchaseReturnItem.quantity), 0),
        )
        .join(PurchaseReturn, PurchaseReturn.id == PurchaseReturnItem.purchase_return_id)
        .where(PurchaseReturn.grn_id == grn_id)
        .group_by(PurchaseReturnItem.grn_item_id)
    ).all()
    return {int(item_id): Decimal(qty) for item_id, qty in rows}


def _serialize_grn(db: Session, g: GRN) -> dict:
    vendor = db.get(Vendor, g.vendor_id)
    returned = _returned_qty_by_grn_item(db, g.id)

    # One query each for the line products and their on-hand rows, instead of
    # two per line.
    products = _products_by_id(db, (it.product_id for it in g.items))
    batch_ids = {it.batch_id for it in g.items if it.batch_id}
    on_hand_by_batch: dict[int, Decimal] = (
        {
            s.batch_id: s.quantity
            for s in db.scalars(
                select(Stock).where(
                    Stock.branch_id == g.branch_id, Stock.batch_id.in_(batch_ids)
                )
            ).all()
        }
        if batch_ids
        else {}
    )

    items = []
    for it in g.items:
        product = products.get(it.product_id)
        already = returned.get(it.id, Decimal("0"))
        remaining = it.quantity - already
        on_hand = on_hand_by_batch.get(it.batch_id, Decimal("0")) if it.batch_id else Decimal("0")
        returnable = remaining if remaining < on_hand else on_hand
        if returnable < 0:
            returnable = Decimal("0")
        items.append({
            "id": it.id,
            "product_id": it.product_id,
            "product_name": product.name if product else str(it.product_id),
            "hsn_code": product.hsn_code if product else None,
            "packing": product.sale_unit if product else None,
            "gst_rate": float(product.gst_rate) if product else 0,
            "batch_id": it.batch_id,
            "batch_no": it.batch_no,
            "expiry_date": it.expiry_date.isoformat() if it.expiry_date else None,
            "quantity": float(it.quantity),
            "unit_price": float(it.unit_price),
            "returned_quantity": float(already),
            "on_hand": float(on_hand),
            "returnable": float(returnable),
        })
    return {
        "id": g.id, "grn_no": g.grn_no, "branch_id": g.branch_id,
        "vendor_id": g.vendor_id,
        "vendor": vendor.name if vendor else None,
        "received_date": g.received_date.isoformat(),
        "vendor_invoice_no": g.vendor_invoice_no,
        "total_value": float(g.total_value),
        "item_count": len(g.items),
        "items": items,
    }


@router.get("/grn/{grn_id}")
def get_grn(
    grn_id: int,
    current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db),
) -> dict:
    grn = db.scalar(
        select(GRN).options(selectinload(GRN.items)).where(GRN.id == grn_id)
    )
    if grn is None or grn.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="GRN not found")
    current.assert_branch_access(grn.branch_id)
    return _serialize_grn(db, grn)


def _serialize_purchase_return(db: Session, note: PurchaseReturn) -> dict:
    vendor = db.get(Vendor, note.vendor_id)
    grn = db.get(GRN, note.grn_id)
    branch = db.get(Branch, note.branch_id)
    org = db.get(Organization, note.organization_id)
    our_gstin = branch.gstin if branch else None
    vendor_gstin = vendor.gstin if vendor else None
    our_state = _gstin_state(our_gstin, branch.state_code if branch else None)
    vendor_state = _gstin_state(vendor_gstin, our_state)
    tax_type = "inter" if our_state and vendor_state and our_state != vendor_state else "intra"
    taxable_total = tax_total = Decimal("0")
    grn_item_ids = {i.grn_item_id for i in note.items if i.grn_item_id}
    grn_items: dict[int, GRNItem] = (
        {
            gi.id: gi
            for gi in db.scalars(
                select(GRNItem).where(GRNItem.id.in_(grn_item_ids))
            ).all()
        }
        if grn_item_ids
        else {}
    )
    items = []
    for i in note.items:
        gst_rate = i.gst_rate or Decimal("0")
        taxable = i.taxable_value if i.taxable_value else (i.quantity * i.unit_price)
        tax = i.tax_amount if i.tax_amount else Decimal("0")
        # Older debit notes stored qty × rate only; keep printed GST at zero for those.
        if not i.tax_amount and gst_rate == 0:
            taxable = i.line_total or taxable
            tax = Decimal("0")
        taxable_total += Decimal(taxable)
        tax_total += Decimal(tax)
        grn_item = grn_items.get(i.grn_item_id) if i.grn_item_id else None
        items.append({
            "grn_item_id": i.grn_item_id,
            "product_id": i.product_id,
            "product_name": i.product_name,
            "hsn_code": i.hsn_code,
            "packing": i.packing,
            "batch_no": i.batch_no,
            "expiry_date": grn_item.expiry_date.isoformat() if grn_item and grn_item.expiry_date else None,
            "quantity": float(i.quantity),
            "unit_price": float(i.unit_price),
            "gst_rate": float(gst_rate),
            "taxable_value": float(taxable),
            "tax_amount": float(tax),
            "line_total": float(i.line_total),
        })
    return {
        "id": note.id,
        "note_no": note.note_no,
        "note_date": note.note_date.isoformat(),
        "reason": note.reason,
        "taxable_total": float(taxable_total),
        "tax_total": float(tax_total),
        "total": float(note.total),
        "tax_type": tax_type,
        "vendor_id": note.vendor_id,
        "vendor": vendor.name if vendor else None,
        "vendor_gstin": vendor_gstin,
        "vendor_phone": vendor.phone if vendor else None,
        "vendor_address": vendor.address if vendor else None,
        "vendor_pan": _pan_from_gstin(vendor_gstin),
        "grn_id": note.grn_id,
        "grn_no": grn.grn_no if grn else None,
        "vendor_invoice_no": grn.vendor_invoice_no if grn else None,
        "grn_date": grn.received_date.isoformat() if grn else None,
        "branch_id": note.branch_id,
        "organization_name": org.name if org else None,
        "organization_pan": (org.pan if org and org.pan else None) or _pan_from_gstin(our_gstin),
        "branch_name": branch.name if branch else None,
        "branch_phone": branch.phone if branch else None,
        "branch_gstin": our_gstin,
        "branch_address": _branch_address(branch),
        "branch_state": branch.state if branch else None,
        "branch_state_code": our_state,
        "printer_name": branch.printer_name if branch else None,
        "printer_type": branch.printer_type if branch else None,
        "thermal_paper_mm": branch.thermal_paper_mm if branch else None,
        "items": items,
    }


@router.get("/returns")
def list_purchase_returns(
    search: str | None = None,
    limit: int = Query(100, ge=1, le=300),
    current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(PurchaseReturn).where(
        PurchaseReturn.organization_id == current.organization_id
    )
    if not current.sees_all_branches:
        stmt = stmt.where(PurchaseReturn.branch_id.in_(current.branch_ids or [-1]))
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.join(Vendor, Vendor.id == PurchaseReturn.vendor_id).join(
            GRN, GRN.id == PurchaseReturn.grn_id
        ).where(or_(
            PurchaseReturn.note_no.ilike(like),
            PurchaseReturn.reason.ilike(like),
            Vendor.name.ilike(like),
            GRN.grn_no.ilike(like),
        ))
    rows = (
        db.scalars(
            stmt.options(selectinload(PurchaseReturn.items))
            .order_by(PurchaseReturn.id.desc())
            .limit(limit)
        )
        .unique()
        .all()
    )
    return [_serialize_purchase_return(db, r) for r in rows]


@router.post("/returns", status_code=201)
def create_purchase_return(
    payload: PurchaseReturnIn,
    current: CurrentUser = Depends(require_permission(rbac.P_PURCHASE_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    grn = db.get(GRN, payload.grn_id)
    if grn is None or grn.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="GRN not found")
    current.assert_branch_access(grn.branch_id)

    already = _returned_qty_by_grn_item(db, grn.id)
    note = PurchaseReturn(
        organization_id=current.organization_id, branch_id=grn.branch_id,
        vendor_id=grn.vendor_id, grn_id=grn.id, created_by_user_id=current.id,
        note_date=date.today(), reason=payload.reason.strip(),
    )
    db.add(note)
    db.flush()

    total = Decimal("0")
    seen: set[int] = set()
    for it in payload.items:
        if it.grn_item_id in seen:
            raise HTTPException(status_code=400, detail="Duplicate product line on this return")
        seen.add(it.grn_item_id)
        line = db.get(GRNItem, it.grn_item_id)
        if line is None or line.grn_id != grn.id:
            raise HTTPException(status_code=400, detail="Item is not on this GRN")
        remaining = line.quantity - already.get(line.id, Decimal("0"))
        if it.quantity <= 0 or it.quantity > remaining:
            raise HTTPException(
                status_code=400,
                detail=f"Return qty cannot exceed remaining GRN qty ({float(remaining)})",
            )
        product = db.get(Product, line.product_id)
        name = product.name if product else str(line.product_id)
        if not line.batch_id:
            raise HTTPException(status_code=400, detail=f"{name} has no batch to return")
        try:
            inv.issue_from_batch(
                db, organization_id=current.organization_id, branch_id=grn.branch_id,
                product_id=line.product_id, batch_id=line.batch_id, quantity=it.quantity,
                movement_type=MovementType.purchase_return,
                ref_type="purchase_return", ref_id=note.id,
            )
        except InsufficientStock as exc:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Cannot return {float(it.quantity):g} of {name} "
                    f"(batch {line.batch_no}). Only {float(exc.available):g} is still "
                    f"on hand at this branch — the rest has already been sold or transferred."
                ),
            )
        gst_rate = product.gst_rate if product else Decimal("0")
        packing = product.sale_unit if product else None
        hsn_code = product.hsn_code if product else None
        taxable, tax, line_total = _line_gst(it.quantity, line.unit_price, gst_rate)
        note.items.append(PurchaseReturnItem(
            grn_item_id=line.id, product_id=line.product_id, batch_id=line.batch_id,
            product_name=name, batch_no=line.batch_no, hsn_code=hsn_code, packing=packing,
            quantity=it.quantity, unit_price=line.unit_price, gst_rate=gst_rate,
            taxable_value=taxable, tax_amount=tax, line_total=line_total,
        ))
        total += line_total
        if grn.purchase_order_id:
            po_item = db.scalar(select(PurchaseOrderItem).where(
                PurchaseOrderItem.order_id == grn.purchase_order_id,
                PurchaseOrderItem.product_id == line.product_id,
            ))
            if po_item:
                po_item.received_quantity = po_item.received_quantity - it.quantity
                if po_item.received_quantity < 0:
                    po_item.received_quantity = Decimal("0")

    note.total = total
    count = db.scalar(select(func.count(PurchaseReturn.id)).where(
        PurchaseReturn.organization_id == current.organization_id)) or 0
    note.note_no = f"DN/{date.today().year}/{count:05d}"

    vendor = db.get(Vendor, grn.vendor_id)
    if vendor:
        vendor.outstanding_balance = vendor.outstanding_balance - total
    accounting.post_purchase_return(
        db, organization_id=current.organization_id, branch_id=grn.branch_id,
        entry_date=note.note_date, purchase_return_id=note.id, total_value=total)

    if grn.purchase_order_id:
        po = db.get(PurchaseOrder, grn.purchase_order_id)
        if po:
            fully = all(i.received_quantity >= i.quantity for i in po.items)
            any_recv = any(i.received_quantity > 0 for i in po.items)
            if fully:
                po.status = PurchaseOrderStatus.received
            elif any_recv:
                po.status = PurchaseOrderStatus.partially_received
            else:
                po.status = PurchaseOrderStatus.placed

    record_audit(db, action="create", entity_type="purchase_return", entity_id=note.id,
                 actor_user_id=current.id, organization_id=current.organization_id,
                 branch_id=grn.branch_id, changes={"total": str(total)})
    db.commit()
    db.refresh(note)
    return _serialize_purchase_return(db, note)


@router.post("/grn/{grn_id}/reverse", status_code=201)
def reverse_grn(
    grn_id: int,
    payload: ReverseIn,
    current: CurrentUser = Depends(require_permission(rbac.P_PURCHASE_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    """Issue a debit note for every returnable line still on hand."""
    grn = db.get(GRN, grn_id)
    if grn is None or grn.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="GRN not found")
    current.assert_branch_access(grn.branch_id)
    detail = _serialize_grn(db, grn)
    items: list[PurchaseReturnItemIn] = []
    skipped: list[str] = []
    for it in detail["items"]:
        qty = Decimal(str(it["returnable"]))
        if qty > 0:
            items.append(PurchaseReturnItemIn(grn_item_id=it["id"], quantity=qty))
        elif Decimal(str(it["quantity"])) > Decimal(str(it.get("returned_quantity") or 0)):
            skipped.append(str(it.get("product_name") or it["product_id"]))
    if not items:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot reverse this GRN. Remaining stock of these batches has already been "
                "sold or transferred. Raise a sales return for sold qty first, then reverse "
                "whatever is still on hand."
            ),
        )
    result = create_purchase_return(
        PurchaseReturnIn(grn_id=grn.id, reason=payload.reason.strip(), items=items),
        current,
        db,
    )
    if skipped:
        result["warning"] = (
            "Debit note issued for stock still on hand. Already sold or transferred "
            f"and not reversed: {', '.join(skipped)}."
        )
    return result


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
        note=payload.note, paid_at=datetime.now(),
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


@router.post("/payments/{payment_id}/reverse")
def reverse_vendor_payment(
    payment_id: int,
    payload: ReverseIn,
    current: CurrentUser = Depends(require_permission(rbac.P_PURCHASE_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    """Undo a vendor payment posted to the wrong supplier. Does not delete the row."""
    payment = db.get(VendorPayment, payment_id)
    if payment is None or payment.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.reversed_at is not None:
        raise HTTPException(status_code=409, detail="This payment is already reversed")
    if payment.branch_id is not None:
        current.assert_branch_access(payment.branch_id)
    vendor = db.get(Vendor, payment.vendor_id)
    if vendor is None or vendor.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Vendor not found")
    amount = Decimal(payment.amount)
    reason = payload.reason.strip()
    vendor.outstanding_balance = vendor.outstanding_balance + amount
    payment.reversed_at = datetime.now()
    payment.reversed_by_user_id = current.id
    payment.reversal_reason = reason
    accounting.post_vendor_payment_reversal(
        db, organization_id=current.organization_id, branch_id=payment.branch_id,
        entry_date=date.today(), payment_id=payment.id, amount=amount, mode=payment.mode,
    )
    record_audit(
        db, action="update", entity_type="vendor_payment", entity_id=payment.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=payment.branch_id,
        changes={"reversed": True, "reason": reason, "amount": str(amount)},
    )
    db.commit()
    return {
        "id": payment.id,
        "reversed": True,
        "vendor_id": vendor.id,
        "vendor_outstanding": float(vendor.outstanding_balance),
    }


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
    vendor_ids = {p.vendor_id for p in rows}
    vendors: dict[int, Vendor] = (
        {
            v.id: v
            for v in db.scalars(select(Vendor).where(Vendor.id.in_(vendor_ids))).all()
        }
        if vendor_ids
        else {}
    )
    out = []
    for p in rows:
        vendor = vendors.get(p.vendor_id)
        out.append({
            "id": p.id,
            "vendor_id": p.vendor_id,
            "vendor": vendor.name if vendor else None,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            "amount": float(p.amount),
            "mode": p.mode,
            "note": p.note,
            "reversed_at": p.reversed_at.isoformat() if p.reversed_at else None,
            "reversal_reason": p.reversal_reason,
        })
    return out
