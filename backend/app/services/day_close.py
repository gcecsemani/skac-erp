"""Compute expected cash / UPI for a branch day, and snapshot a close."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import CustomerPayment
from app.models.day_close import DayClose
from app.models.enums import InvoiceStatus
from app.models.expense import Expense
from app.models.organization import Branch
from app.models.purchase import VendorPayment
from app.models.sales import Invoice

TWO = Decimal("0.01")
DIGITAL = {"upi", "card", "bank"}


def _n(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(TWO)


def _mode_str(v) -> str:
    if hasattr(v, "value"):
        return str(v.value).lower()
    return str(v or "").lower()


def _bucket(mode: str) -> str:
    """Money actually received: UPI/card/bank vs everything else (cash, or cash taken on a khata bill)."""
    m = _mode_str(mode)
    if m in DIGITAL:
        return "digital"
    return "cash"


def _add(dest: dict[str, Decimal], key: str, amount: Decimal) -> None:
    dest[key] = dest.get(key, Decimal("0")) + amount


def _payment_shop_date(paid_at: datetime | None) -> date | None:
    """Calendar date a receipt belongs to for day close.

    New collections store local `datetime.now()`. Older rows used UTC.
    If treating the naive timestamp as UTC lands on today or yesterday,
    use that local date so an evening collection is not lost after UTC midnight.
    """
    if paid_at is None:
        return None
    stored = paid_at.date() if hasattr(paid_at, "date") else paid_at
    try:
        naive = paid_at.replace(tzinfo=None) if getattr(paid_at, "tzinfo", None) else paid_at
        local_from_utc = naive.replace(tzinfo=timezone.utc).astimezone().date()
    except Exception:
        return stored
    today = date.today()
    if local_from_utc in {today, today - timedelta(days=1)}:
        return local_from_utc
    return stored


def _infer_payment_branch(db: Session, payment: CustomerPayment) -> int | None:
    """Attribute an untagged khata receipt to the farmer's latest billed shop."""
    if payment.branch_id is not None:
        return payment.branch_id
    return db.scalar(
        select(Invoice.branch_id)
        .where(
            Invoice.customer_id == payment.customer_id,
            Invoice.organization_id == payment.organization_id,
            Invoice.status == InvoiceStatus.finalized,
        )
        .order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
        .limit(1)
    )


def compute_expected(
    db: Session,
    *,
    org_id: int,
    branch_id: int,
    close_date: date,
    include_unscoped: bool,
) -> dict:
    start_dt = datetime.combine(close_date, datetime.min.time())
    end_dt = datetime.combine(close_date + timedelta(days=1), datetime.min.time())
    pay_start = start_dt - timedelta(days=1)
    pay_end = end_dt + timedelta(days=1)

    in_by: dict[str, Decimal] = {}
    out_by: dict[str, Decimal] = {}
    unscoped_in = Decimal("0")
    unscoped_out = Decimal("0")

    inv_stmt = select(Invoice).where(
        Invoice.organization_id == org_id,
        Invoice.branch_id == branch_id,
        Invoice.status == InvoiceStatus.finalized,
        Invoice.invoice_date == close_date,
    )
    bills = 0
    sales = Decimal("0")
    collected_inv = Decimal("0")
    khata_new = Decimal("0")
    for inv in db.scalars(inv_stmt).all():
        bills += 1
        sales += _n(inv.grand_total)
        paid = _n(inv.amount_paid)
        due = _n(inv.grand_total) - paid
        khata_new += due
        # Credit bills are unpaid at the till. Later farmer receipts are
        # CustomerPayment rows (khata_collected). Do not treat amount_paid
        # that was allocated onto a credit invoice as cash taken at billing.
        if _mode_str(inv.payment_mode) == "credit":
            continue
        collected_inv += paid
        if paid > 0:
            _add(in_by, _bucket(inv.payment_mode), paid)

    pay_stmt = select(CustomerPayment).where(
        CustomerPayment.organization_id == org_id,
        CustomerPayment.paid_at >= pay_start,
        CustomerPayment.paid_at < pay_end,
    )
    branch_count = db.scalar(
        select(func.count(Branch.id)).where(Branch.organization_id == org_id)
    ) or 0
    khata_collected = Decimal("0")
    for p in db.scalars(pay_stmt).all():
        if p.reversed_at is not None:
            continue
        if _payment_shop_date(p.paid_at) != close_date:
            continue
        amt = _n(p.amount)
        effective = _infer_payment_branch(db, p)
        if effective == branch_id:
            khata_collected += amt
            _add(in_by, _bucket(p.mode), amt)
        elif effective is None:
            if include_unscoped or branch_count <= 1:
                khata_collected += amt
                _add(in_by, _bucket(p.mode), amt)
            else:
                unscoped_in += amt

    exp_stmt = select(Expense).where(
        Expense.organization_id == org_id,
        Expense.branch_id == branch_id,
        Expense.expense_date == close_date,
    )
    expense_total = Decimal("0")
    for e in db.scalars(exp_stmt).all():
        amt = _n(e.amount)
        expense_total += amt
        _add(out_by, _bucket(e.mode), amt)

    vp_stmt = select(VendorPayment).where(
        VendorPayment.organization_id == org_id,
        VendorPayment.paid_at >= start_dt,
        VendorPayment.paid_at < end_dt,
    )
    vendor_paid = Decimal("0")
    for p in db.scalars(vp_stmt).all():
        if p.reversed_at is not None:
            continue
        amt = _n(p.amount)
        if p.branch_id == branch_id:
            vendor_paid += amt
            _add(out_by, _bucket(p.mode), amt)
        elif p.branch_id is None:
            if include_unscoped:
                vendor_paid += amt
                _add(out_by, _bucket(p.mode), amt)
            else:
                unscoped_out += amt

    prev = db.scalar(
        select(DayClose)
        .where(DayClose.branch_id == branch_id, DayClose.close_date < close_date)
        .order_by(DayClose.close_date.desc())
        .limit(1)
    )
    opening = _n(prev.counted_cash) if prev else Decimal("0")

    cash_in = in_by.get("cash", Decimal("0"))
    cash_out = out_by.get("cash", Decimal("0"))
    digital_in = in_by.get("digital", Decimal("0"))
    digital_out = out_by.get("digital", Decimal("0"))

    return {
        "opening_cash": opening,
        "previous_close_date": prev.close_date.isoformat() if prev else None,
        "cash_in": cash_in,
        "cash_out": cash_out,
        "expected_cash": opening + cash_in - cash_out,
        "digital_in": digital_in,
        "digital_out": digital_out,
        "expected_digital": digital_in - digital_out,
        "sales_total": sales,
        "collected_total": collected_inv + khata_collected,
        "khata_new": khata_new,
        "khata_collected": khata_collected,
        "expense_total": expense_total,
        "vendor_paid": vendor_paid,
        "bill_count": bills,
        "in_by": {k: float(v) for k, v in in_by.items()},
        "out_by": {k: float(v) for k, v in out_by.items()},
        "unscoped_in": unscoped_in,
        "unscoped_out": unscoped_out,
        "include_unscoped": include_unscoped,
    }


def serialize(row: DayClose, extra: dict | None = None) -> dict:
    breakdown = {}
    if row.breakdown:
        try:
            breakdown = json.loads(row.breakdown)
        except json.JSONDecodeError:
            breakdown = {}
    data = {
        "id": row.id,
        "branch_id": row.branch_id,
        "close_date": row.close_date.isoformat(),
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        "closed_by_user_id": row.closed_by_user_id,
        "opening_cash": float(row.opening_cash),
        "cash_in": float(row.cash_in),
        "cash_out": float(row.cash_out),
        "expected_cash": float(row.expected_cash),
        "counted_cash": float(row.counted_cash),
        "cash_variance": float(row.cash_variance),
        "digital_in": float(row.digital_in),
        "digital_out": float(row.digital_out),
        "expected_digital": float(row.expected_digital),
        "counted_digital": float(row.counted_digital),
        "digital_variance": float(row.digital_variance),
        "sales_total": float(row.sales_total),
        "collected_total": float(row.collected_total),
        "khata_new": float(row.khata_new),
        "expense_total": float(row.expense_total),
        "bill_count": int(row.bill_count or 0),
        "note": row.note,
        "breakdown": breakdown,
        "closed": True,
    }
    if extra:
        data.update(extra)
    return data


def apply_counts(expected: dict, *, opening_cash: Decimal, counted_cash: Decimal, counted_digital: Decimal) -> dict:
    cash_in = _n(expected["cash_in"])
    cash_out = _n(expected["cash_out"])
    digital_in = _n(expected["digital_in"])
    digital_out = _n(expected["digital_out"])
    expected_cash = opening_cash + cash_in - cash_out
    expected_digital = digital_in - digital_out
    return {
        "opening_cash": opening_cash,
        "cash_in": cash_in,
        "cash_out": cash_out,
        "expected_cash": expected_cash,
        "counted_cash": counted_cash,
        "cash_variance": counted_cash - expected_cash,
        "digital_in": digital_in,
        "digital_out": digital_out,
        "expected_digital": expected_digital,
        "counted_digital": counted_digital,
        "digital_variance": counted_digital - expected_digital,
        "sales_total": _n(expected["sales_total"]),
        "collected_total": _n(expected["collected_total"]),
        "khata_new": _n(expected["khata_new"]),
        "expense_total": _n(expected["expense_total"]),
        "bill_count": int(expected["bill_count"]),
    }
