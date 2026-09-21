"""Tabular operational reports returned as columns + rows for the UI/export."""
from __future__ import annotations

from calendar import month_name
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer, CustomerPayment, CustomerPaymentAllocation
from app.models.enums import InvoiceStatus, MovementType, StockDiscrepancyStatus
from app.models.expense import Expense
from app.models.field_visit import FieldVisit
from app.models.inventory import Batch, Stock, StockDiscrepancy, StockMovement
from app.models.organization import Branch
from app.models.product import Product
from app.models.purchase import GRN, GRNItem
from app.models.returns import CreditNote
from app.models.sales import Invoice, InvoiceItem
from app.models.user import User
from app.models.vendor import Vendor
from app.services import accounting
from app.services.cogs import grouped_totals, line_totals_stmt, overall_totals

GROUPS = [
    {"id": "sales", "label": "Sales & margin"},
    {"id": "collections", "label": "Cash & khata"},
    {"id": "buying", "label": "Buying"},
    {"id": "stock", "label": "Stock"},
    {"id": "accounts", "label": "GST & P&L"},
]

CATALOG = [
    {"key": "daily_sales", "label": "Sales by day", "group": "sales", "needs_dates": True,
     "blurb": "Bills, cash collected, and new khata each day. Use this to check a counter or a slow week."},
    {"key": "monthly_sales", "label": "Sales by month", "group": "sales", "needs_dates": True,
     "blurb": "Month-on-month sales. Fertilizer peaks around season — this shows whether this year is ahead or behind."},
    {"key": "product_sales", "label": "What sold", "group": "sales", "needs_dates": True,
     "blurb": "Which SKUs brought money. Push the winners; stop filling shelves with items nobody buys."},
    {"key": "product_profit", "label": "Product margin", "group": "sales", "needs_dates": True,
     "blurb": "Profit after cost, per product. High sales with thin or negative margin is a problem, not a win."},
    {"key": "farmer_profit", "label": "Top farmers", "group": "sales", "needs_dates": True,
     "blurb": "Who buys from you and how much margin those bills leave. Your best farmers to keep close."},
    {"key": "customer_outstanding", "label": "Khata outstanding", "group": "collections", "needs_dates": True,
     "blurb": "Opening, billed on khata, collected, and closing for the dates you pick. Filter by shop, then search a village to see who still owes."},
    {"key": "khata_by_village", "label": "Khata by village", "group": "collections", "needs_dates": True,
     "blurb": "The same khata movement rolled up by village. Use this to see which villages carry the most outstanding."},
    {"key": "inactive_khata", "label": "Khata not visiting", "group": "collections", "needs_dates": False,
     "blurb": "Farmers who owe money and have not billed in 30 days. These balances go stale unless you follow up."},
    {"key": "payment_collection", "label": "Money collected", "group": "collections", "needs_dates": True,
     "blurb": "Cash, UPI and khata receipts in the period. Match this to day close and the bank."},
    {"key": "purchase", "label": "Purchases", "group": "buying", "needs_dates": True,
     "blurb": "Goods received from suppliers. Check what came in versus what is selling."},
    {"key": "supplier_outstanding", "label": "Supplier payables", "group": "buying", "needs_dates": False,
     "blurb": "What the shop still owes vendors. Pay these before credit is blocked."},
    {"key": "inventory", "label": "Stock on hand", "group": "stock", "needs_dates": False,
     "blurb": "Quantity and rupee value sitting in each shop. Capital locked in bags and bottles."},
    {"key": "vendor_stock", "label": "Vendor-wise stock", "group": "stock", "needs_dates": True,
     "blurb": "Received and sold in the dates you pick, and how many are still on the shelf, by the supplier on the GRN. Search a vendor to see that supplier's movement."},
    {"key": "expiry", "label": "Expiry risk", "group": "stock", "needs_dates": False,
     "blurb": "Batches expiring in 60 days. Sell, return, or write off before they become unsaleable."},
    {"key": "low_stock", "label": "Reorder", "group": "stock", "needs_dates": False,
     "blurb": "Out of stock or below reorder level. These are lost sales if a farmer walks in tomorrow."},
    {"key": "stock_reconcile", "label": "Stock reconciliation", "group": "stock", "needs_dates": True,
     "blurb": "Opening + loaded − sold − returns − transfers should equal stock left. Log a shelf count when it does not, and keep the case open until you find the bags."},
    {"key": "gst", "label": "GST", "group": "accounts", "needs_dates": True,
     "blurb": "Taxable value and tax by slab. Hand this to your CA for the return."},
    {"key": "profit_loss", "label": "Profit & loss", "group": "accounts", "needs_dates": True,
     "blurb": "Sales minus GST, product cost, and expenses. The number that says whether the shop made money."},
    # Kept for AI / old links; not shown on the Reports screen.
    {"key": "category_sales", "label": "Category sales", "needs_dates": True, "nav": False},
    {"key": "stock_movement", "label": "Stock movement", "needs_dates": True, "nav": False},
    {"key": "field_visits", "label": "Field visit report", "needs_dates": True, "nav": False},
    {"key": "product_loss", "label": "Product loss", "needs_dates": True, "nav": False},
    {"key": "farmer_loss", "label": "Farmer loss", "needs_dates": True, "nav": False},
]


def visible_catalog() -> list[dict]:
    return [c for c in CATALOG if c.get("nav", True)]


def _n(v) -> float:
    return round(float(v or 0), 2)


def _qty(v) -> float:
    return round(float(v or 0), 3)


def _enum(v) -> str:
    return v.value if hasattr(v, "value") else str(v or "")


def _month_start(d: date) -> date:
    return d.replace(day=1)


def run_report(
    db: Session,
    *,
    org_id: int,
    scope: list[int] | None,
    key: str,
    start: date,
    end: date,
) -> dict:
    builders = {
        "daily_sales": _daily_sales,
        "monthly_sales": _monthly_sales,
        "purchase": _purchase,
        "product_sales": _product_sales,
        "category_sales": _category_sales,
        "profit_loss": _profit_loss,
        "inventory": _inventory,
        "stock_movement": _stock_movement,
        "expiry": _expiry,
        "low_stock": _low_stock,
        "customer_outstanding": _customer_outstanding,
        "khata_by_village": _khata_by_village,
        "supplier_outstanding": _supplier_outstanding,
        "gst": _gst,
        "payment_collection": _payment_collection,
        "vendor_stock": _vendor_stock,
        "field_visits": _field_visits,
        "stock_reconcile": _stock_reconcile,
        "product_profit": _product_profit,
        "product_loss": _product_loss,
        "farmer_profit": _farmer_profit,
        "farmer_loss": _farmer_loss,
        "inactive_khata": _inactive_khata,
    }
    fn = builders.get(key)
    if fn is None:
        raise HTTPException(status_code=404, detail="Unknown report")
    label = next((c["label"] for c in CATALOG if c["key"] == key), key)
    payload = fn(db, org_id, scope, start, end)
    payload["key"] = key
    payload["title"] = label
    payload["start"] = start.isoformat()
    payload["end"] = end.isoformat()
    return payload


def _inv_filter(stmt, org_id, scope, start, end):
    stmt = stmt.where(
        Invoice.organization_id == org_id,
        Invoice.status == InvoiceStatus.finalized,
        Invoice.invoice_date >= start,
        Invoice.invoice_date <= end,
    )
    if scope is not None:
        stmt = stmt.where(Invoice.branch_id.in_(scope))
    return stmt


def _daily_sales(db, org_id, scope, start, end) -> dict:
    stmt = _inv_filter(
        select(
            Invoice.invoice_date,
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.grand_total), 0),
            func.coalesce(func.sum(Invoice.tax_total), 0),
            func.coalesce(func.sum(Invoice.amount_paid), 0),
            func.coalesce(func.sum(Invoice.grand_total - Invoice.amount_paid), 0),
        ),
        org_id, scope, start, end,
    ).group_by(Invoice.invoice_date).order_by(Invoice.invoice_date)
    rows = [
        {
            "date": d.isoformat(),
            "bills": int(c),
            "sales": _n(sales),
            "tax": _n(tax),
            "collected": _n(paid),
            "credit": _n(credit),
        }
        for d, c, sales, tax, paid, credit in db.execute(stmt).all()
    ]
    return {
        "columns": [
            {"key": "date", "label": "Date"},
            {"key": "bills", "label": "Bills", "num": True},
            {"key": "sales", "label": "Sales", "num": True, "money": True},
            {"key": "tax", "label": "GST", "num": True, "money": True},
            {"key": "collected", "label": "Collected", "num": True, "money": True},
            {"key": "credit", "label": "On khata", "num": True, "money": True},
        ],
        "rows": rows,
        "summary": [
            {"label": "Bills", "value": sum(r["bills"] for r in rows)},
            {"label": "Sales", "value": round(sum(r["sales"] for r in rows), 2), "money": True},
            {"label": "Collected", "value": round(sum(r["collected"] for r in rows), 2), "money": True},
        ],
    }


def _monthly_sales(db, org_id, scope, start, end) -> dict:
    year = func.extract("year", Invoice.invoice_date)
    month = func.extract("month", Invoice.invoice_date)
    stmt = _inv_filter(
        select(
            year, month,
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.grand_total), 0),
            func.coalesce(func.sum(Invoice.tax_total), 0),
            func.coalesce(func.sum(Invoice.amount_paid), 0),
        ),
        org_id, scope, start, end,
    ).group_by(year, month).order_by(year, month)
    rows = []
    for y, m, bills, sales, tax, paid in db.execute(stmt):
        rows.append({
            "month": f"{month_name[int(m)]} {int(y)}",
            "bills": int(bills),
            "sales": _n(sales),
            "tax": _n(tax),
            "collected": _n(paid),
        })
    return {
        "columns": [
            {"key": "month", "label": "Month"},
            {"key": "bills", "label": "Bills", "num": True},
            {"key": "sales", "label": "Sales", "num": True, "money": True},
            {"key": "tax", "label": "GST", "num": True, "money": True},
            {"key": "collected", "label": "Collected", "num": True, "money": True},
        ],
        "rows": rows,
        "summary": [
            {"label": "Sales", "value": round(sum(r["sales"] for r in rows), 2), "money": True},
        ],
    }


def _purchase(db, org_id, scope, start, end) -> dict:
    stmt = (
        select(GRN, Vendor.name, Branch.name)
        .join(Vendor, Vendor.id == GRN.vendor_id)
        .join(Branch, Branch.id == GRN.branch_id)
        .where(GRN.organization_id == org_id, GRN.received_date >= start, GRN.received_date <= end)
        .order_by(GRN.received_date.desc(), GRN.id.desc())
    )
    if scope is not None:
        stmt = stmt.where(GRN.branch_id.in_(scope))
    rows = [
        {
            "date": g.received_date.isoformat(),
            "grn_no": g.grn_no,
            "vendor": vendor,
            "branch": branch,
            "vendor_invoice": g.vendor_invoice_no or "—",
            "value": _n(g.total_value),
        }
        for g, vendor, branch in db.execute(stmt).all()
    ]
    return {
        "columns": [
            {"key": "date", "label": "Date"},
            {"key": "grn_no", "label": "GRN #"},
            {"key": "vendor", "label": "Supplier"},
            {"key": "branch", "label": "Branch"},
            {"key": "vendor_invoice", "label": "Vendor invoice"},
            {"key": "value", "label": "Value", "num": True, "money": True},
        ],
        "rows": rows,
        "summary": [{"label": "Purchases", "value": round(sum(r["value"] for r in rows), 2), "money": True}],
    }


def _product_sales(db, org_id, scope, start, end) -> dict:
    stmt = (
        line_totals_stmt(InvoiceItem.product_id, InvoiceItem.product_name, Product.category)
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .outerjoin(Product, Product.id == InvoiceItem.product_id)
    )
    stmt = _inv_filter(stmt, org_id, scope, start, end)
    rows = [
        {
            "product": name,
            "category": _enum(cat).replace("_", " ").title() if cat else "—",
            "qty": _qty(t.qty),
            "taxable": _n(t.taxable),
            "tax": _n(t.tax),
            "amount": _n(t.total),
        }
        for (_pid, name, cat), t in grouped_totals(db, stmt).items()
    ]
    rows.sort(key=lambda r: r["amount"], reverse=True)
    return {
        "columns": [
            {"key": "product", "label": "Product"},
            {"key": "category", "label": "Category"},
            {"key": "qty", "label": "Qty sold", "num": True},
            {"key": "taxable", "label": "Taxable", "num": True, "money": True},
            {"key": "tax", "label": "GST", "num": True, "money": True},
            {"key": "amount", "label": "Amount", "num": True, "money": True},
        ],
        "rows": rows,
        "summary": [{"label": "Amount", "value": round(sum(r["amount"] for r in rows), 2), "money": True}],
    }


def _category_sales(db, org_id, scope, start, end) -> dict:
    stmt = (
        line_totals_stmt(Product.category)
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .join(Product, Product.id == InvoiceItem.product_id)
    )
    stmt = _inv_filter(stmt, org_id, scope, start, end)
    rows = [
        {
            "category": _enum(cat).replace("_", " ").title(),
            "qty": _qty(t.qty),
            "taxable": _n(t.taxable),
            "amount": _n(t.total),
        }
        for (cat,), t in grouped_totals(db, stmt).items()
    ]
    rows.sort(key=lambda r: r["amount"], reverse=True)
    return {
        "columns": [
            {"key": "category", "label": "Category"},
            {"key": "qty", "label": "Qty", "num": True},
            {"key": "taxable", "label": "Taxable", "num": True, "money": True},
            {"key": "amount", "label": "Amount", "num": True, "money": True},
        ],
        "rows": rows,
        "summary": [{"label": "Amount", "value": round(sum(r["amount"] for r in rows), 2), "money": True}],
    }


def _profit_loss(db, org_id, scope, start, end) -> dict:
    sales_stmt = _inv_filter(
        select(
            func.coalesce(func.sum(Invoice.subtotal), 0),
            func.coalesce(func.sum(Invoice.tax_total), 0),
            func.coalesce(func.sum(Invoice.discount_total), 0),
            func.coalesce(func.sum(Invoice.grand_total), 0),
        ),
        org_id, scope, start, end,
    )
    subtotal, tax, discount, grand = db.execute(sales_stmt).one()
    cogs_stmt = (
        line_totals_stmt()
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .join(Product, Product.id == InvoiceItem.product_id)
    )
    cogs_stmt = _inv_filter(cogs_stmt, org_id, scope, start, end)
    cogs = overall_totals(db, cogs_stmt).cogs
    exp_stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.organization_id == org_id,
        Expense.expense_date >= start,
        Expense.expense_date <= end,
    )
    if scope is not None:
        exp_stmt = exp_stmt.where(Expense.branch_id.in_(scope))
    expenses = db.scalar(exp_stmt) or 0
    # Invoice.subtotal is taxable *after* discount; list sales add it back so
    # the discount line is a real deduction instead of a dangling figure.
    net_sales = _n(subtotal)
    list_sales = round(net_sales + _n(discount), 2)
    gross = net_sales - _n(cogs)
    net = gross - _n(expenses)
    rows = [
        {"line": "Gross sales (excl. GST)", "amount": list_sales},
        {"line": "Less: Discounts", "amount": _n(discount)},
        {"line": "Net sales (excl. GST)", "amount": round(net_sales, 2)},
        {"line": "GST collected", "amount": _n(tax)},
        {"line": "Collections (incl. GST)", "amount": _n(grand)},
        {"line": "Cost of goods sold", "amount": _n(cogs)},
        {"line": "Gross profit", "amount": round(gross, 2)},
        {"line": "Operating expenses", "amount": _n(expenses)},
        {"line": "Net profit / (loss)", "amount": round(net, 2)},
    ]
    return {
        "columns": [
            {"key": "line", "label": "Particulars"},
            {"key": "amount", "label": "Amount", "num": True, "money": True},
        ],
        "rows": rows,
        "summary": [{"label": "Net profit", "value": round(net, 2), "money": True}],
    }


def _inventory(db, org_id, scope, start, end) -> dict:
    stmt = (
        select(Product.name, Product.sku, Product.category, Batch.batch_no, Batch.expiry_date,
               Branch.name, Stock.quantity, Batch.purchase_price)
        .join(Product, Product.id == Stock.product_id)
        .join(Batch, Batch.id == Stock.batch_id)
        .join(Branch, Branch.id == Stock.branch_id)
        .where(Stock.organization_id == org_id, Stock.quantity > 0)
        .order_by(Product.name, Batch.expiry_date)
    )
    if scope is not None:
        stmt = stmt.where(Stock.branch_id.in_(scope))
    rows = []
    total = 0.0
    for name, sku, cat, batch, expiry, branch, qty, cost in db.execute(stmt).all():
        value = _qty(qty) * _n(cost)
        total += value
        rows.append({
            "product": name,
            "sku": sku,
            "category": _enum(cat),
            "batch": batch,
            "expiry": expiry.isoformat() if expiry else "—",
            "branch": branch,
            "qty": _qty(qty),
            "value": round(value, 2),
        })
    return {
        "columns": [
            {"key": "product", "label": "Product"},
            {"key": "sku", "label": "SKU"},
            {"key": "batch", "label": "Batch"},
            {"key": "expiry", "label": "Expiry"},
            {"key": "branch", "label": "Branch"},
            {"key": "qty", "label": "Qty", "num": True},
            {"key": "value", "label": "Value", "num": True, "money": True},
        ],
        "rows": rows,
        "summary": [{"label": "Stock value", "value": round(total, 2), "money": True}],
    }


def _stock_movement(db, org_id, scope, start, end) -> dict:
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time())
    stmt = (
        select(StockMovement, Product.name, Batch.batch_no, Branch.name)
        .join(Product, Product.id == StockMovement.product_id)
        .join(Batch, Batch.id == StockMovement.batch_id)
        .join(Branch, Branch.id == StockMovement.branch_id)
        .where(
            StockMovement.organization_id == org_id,
            StockMovement.occurred_at >= start_dt,
            StockMovement.occurred_at < end_dt,
        )
        .order_by(StockMovement.occurred_at.desc())
        .limit(2000)
    )
    if scope is not None:
        stmt = stmt.where(StockMovement.branch_id.in_(scope))
    labels = {
        "grn": "Purchase (GRN)",
        "sale": "Sale",
        "sale_return": "Sales return",
        "purchase_return": "Purchase return",
        "transfer_out": "Transfer out",
        "transfer_in": "Transfer in",
        "adjustment": "Adjustment",
    }
    rows = [
        {
            "when": m.occurred_at.strftime("%Y-%m-%d %H:%M"),
            "product": name,
            "batch": batch,
            "branch": branch,
            "type": labels.get(_enum(m.movement_type), _enum(m.movement_type)),
            "qty": _qty(m.quantity),
            "note": m.note or m.ref_type or "—",
        }
        for m, name, batch, branch in db.execute(stmt).all()
    ]
    return {
        "columns": [
            {"key": "when", "label": "Date / time"},
            {"key": "product", "label": "Product"},
            {"key": "batch", "label": "Batch"},
            {"key": "branch", "label": "Branch"},
            {"key": "type", "label": "Type"},
            {"key": "qty", "label": "Qty", "num": True},
            {"key": "note", "label": "Note"},
        ],
        "rows": rows,
    }


def _expiry(db, org_id, scope, start, end) -> dict:
    today = date.today()
    horizon = today + timedelta(days=60)
    stmt = (
        select(Product.name, Batch.batch_no, Batch.expiry_date, Branch.name, Stock.quantity)
        .join(Product, Product.id == Stock.product_id)
        .join(Batch, Batch.id == Stock.batch_id)
        .join(Branch, Branch.id == Stock.branch_id)
        .where(
            Stock.organization_id == org_id,
            Stock.quantity > 0,
            Batch.expiry_date.is_not(None),
            Batch.expiry_date <= horizon,
        )
        .order_by(Batch.expiry_date)
    )
    if scope is not None:
        stmt = stmt.where(Stock.branch_id.in_(scope))
    rows = []
    for name, batch, expiry, branch, qty in db.execute(stmt).all():
        days = (expiry - today).days
        status = "Expired" if days < 0 else ("Expires this month" if days <= 30 else "Expires in 60 days")
        rows.append({
            "product": name,
            "batch": batch,
            "expiry": expiry.isoformat(),
            "days": days,
            "status": status,
            "branch": branch,
            "qty": _qty(qty),
        })
    return {
        "columns": [
            {"key": "product", "label": "Product"},
            {"key": "batch", "label": "Batch"},
            {"key": "expiry", "label": "Expiry"},
            {"key": "days", "label": "Days left", "num": True},
            {"key": "status", "label": "Status"},
            {"key": "branch", "label": "Branch"},
            {"key": "qty", "label": "Qty", "num": True},
        ],
        "rows": rows,
    }


def _low_stock(db, org_id, scope, start, end) -> dict:
    qty_sub = select(
        Stock.product_id.label("product_id"),
        func.coalesce(func.sum(Stock.quantity), 0).label("qty"),
    ).where(Stock.organization_id == org_id)
    if scope is not None:
        qty_sub = qty_sub.where(Stock.branch_id.in_(scope))
    qty_sub = qty_sub.group_by(Stock.product_id).subquery()

    # Outer join so SKUs with no stock row at all still show as out of stock,
    # and let the database drop the healthy ones instead of loading the whole
    # catalogue into Python.
    on_hand = func.coalesce(qty_sub.c.qty, 0)
    stmt = (
        select(Product.name, Product.sku, on_hand, Product.reorder_level)
        .outerjoin(qty_sub, qty_sub.c.product_id == Product.id)
        .where(
            Product.organization_id == org_id,
            Product.is_deleted.is_(False),
            or_(on_hand <= Product.reorder_level, on_hand <= 0),
        )
        .order_by(Product.name)
    )
    rows = []
    for name, sku, qty, reorder in db.execute(stmt).all():
        qty = _qty(qty)
        rows.append({
            "product": name,
            "sku": sku,
            "on_hand": qty,
            "reorder_level": _qty(reorder),
            "status": "Out of stock" if qty <= 0 else "Low stock",
        })
    return {
        "columns": [
            {"key": "product", "label": "Product"},
            {"key": "sku", "label": "SKU"},
            {"key": "on_hand", "label": "On hand", "num": True},
            {"key": "reorder_level", "label": "Reorder level", "num": True},
            {"key": "status", "label": "Status"},
        ],
        "rows": rows,
    }


def _alloc_sub():
    """Non-reversed khata receipts applied to invoices (so billed-on-khata survives later collections)."""
    return (
        select(
            CustomerPaymentAllocation.invoice_id.label("invoice_id"),
            func.coalesce(func.sum(CustomerPaymentAllocation.amount), 0).label("alloc"),
        )
        .join(CustomerPayment, CustomerPayment.id == CustomerPaymentAllocation.payment_id)
        .where(CustomerPayment.reversed_at.is_(None))
        .group_by(CustomerPaymentAllocation.invoice_id)
        .subquery()
    )


def _latest_bill_branch_subq(org_id):
    latest = (
        select(
            Invoice.customer_id.label("customer_id"),
            func.max(Invoice.id).label("invoice_id"),
        )
        .where(
            Invoice.organization_id == org_id,
            Invoice.status == InvoiceStatus.finalized,
            Invoice.customer_id.is_not(None),
        )
        .group_by(Invoice.customer_id)
        .subquery()
    )
    return (
        select(Invoice.customer_id.label("customer_id"), Invoice.branch_id.label("branch_id"))
        .join(latest, Invoice.id == latest.c.invoice_id)
        .subquery()
    )


def _khata_buckets(db, org_id, scope, start, end) -> list[dict]:
    """Opening / billed / collected / returned / closing by farmer and shop."""
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time())
    alloc = _alloc_sub()
    khata_expr = (
        Invoice.grand_total - Invoice.amount_paid + func.coalesce(alloc.c.alloc, 0)
    )
    billed_stmt = (
        select(
            Invoice.customer_id,
            Invoice.branch_id,
            func.coalesce(
                func.sum(case((Invoice.invoice_date < start, khata_expr), else_=0)), 0
            ),
            func.coalesce(
                func.sum(case((Invoice.invoice_date >= start, khata_expr), else_=0)), 0
            ),
            func.max(Invoice.invoice_date),
        )
        .select_from(Invoice)
        .outerjoin(alloc, alloc.c.invoice_id == Invoice.id)
        .where(
            Invoice.organization_id == org_id,
            Invoice.status == InvoiceStatus.finalized,
            Invoice.customer_id.is_not(None),
            Invoice.invoice_date <= end,
        )
        .group_by(Invoice.customer_id, Invoice.branch_id)
    )
    if scope is not None:
        billed_stmt = billed_stmt.where(Invoice.branch_id.in_(scope))

    inferred = _latest_bill_branch_subq(org_id)
    shop = func.coalesce(CustomerPayment.branch_id, inferred.c.branch_id)
    collected_stmt = (
        select(
            CustomerPayment.customer_id,
            shop,
            func.coalesce(
                func.sum(case((CustomerPayment.paid_at < start_dt, CustomerPayment.amount), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((CustomerPayment.paid_at >= start_dt, CustomerPayment.amount), else_=0)),
                0,
            ),
        )
        .select_from(CustomerPayment)
        .outerjoin(inferred, inferred.c.customer_id == CustomerPayment.customer_id)
        .where(
            CustomerPayment.organization_id == org_id,
            CustomerPayment.reversed_at.is_(None),
            CustomerPayment.paid_at < end_dt,
        )
        .group_by(CustomerPayment.customer_id, shop)
    )
    if scope is not None:
        collected_stmt = collected_stmt.where(shop.in_(scope))

    returned_stmt = (
        select(
            CreditNote.customer_id,
            CreditNote.branch_id,
            func.coalesce(
                func.sum(case((CreditNote.note_date < start, CreditNote.total), else_=0)), 0
            ),
            func.coalesce(
                func.sum(case((CreditNote.note_date >= start, CreditNote.total), else_=0)), 0
            ),
        )
        .where(
            CreditNote.organization_id == org_id,
            CreditNote.customer_id.is_not(None),
            CreditNote.note_date <= end,
        )
        .group_by(CreditNote.customer_id, CreditNote.branch_id)
    )
    if scope is not None:
        returned_stmt = returned_stmt.where(CreditNote.branch_id.in_(scope))

    buckets: dict[tuple[int, int], dict] = {}

    def bucket(cid, bid) -> dict:
        k = (int(cid), int(bid or 0))
        row = buckets.get(k)
        if row is None:
            row = {
                "customer_id": int(cid),
                "branch_id": int(bid or 0),
                "billed_before": 0.0,
                "billed": 0.0,
                "collected_before": 0.0,
                "collected": 0.0,
                "returned_before": 0.0,
                "returned": 0.0,
                "last_bill": None,
            }
            buckets[k] = row
        return row

    for cid, bid, before, during, last_bill in db.execute(billed_stmt).all():
        row = bucket(cid, bid)
        row["billed_before"] = _n(before)
        row["billed"] = _n(during)
        row["last_bill"] = last_bill

    for cid, bid, before, during in db.execute(collected_stmt).all():
        if cid is None:
            continue
        row = bucket(cid, bid)
        row["collected_before"] = _n(before)
        row["collected"] = _n(during)

    for cid, bid, before, during in db.execute(returned_stmt).all():
        if cid is None:
            continue
        row = bucket(cid, bid)
        row["returned_before"] = _n(before)
        row["returned"] = _n(during)

    cids = {r["customer_id"] for r in buckets.values()}
    bids = {r["branch_id"] for r in buckets.values() if r["branch_id"]}
    customers = {
        c.id: c for c in db.scalars(select(Customer).where(Customer.id.in_(cids))).all()
    } if cids else {}
    branches = {
        b.id: b.name for b in db.scalars(select(Branch).where(Branch.id.in_(bids))).all()
    } if bids else {}

    rows = []
    for r in buckets.values():
        c = customers.get(r["customer_id"])
        if c is None or c.is_deleted:
            continue
        opening = round(r["billed_before"] - r["collected_before"] - r["returned_before"], 2)
        closing = round(opening + r["billed"] - r["collected"] - r["returned"], 2)
        if opening == 0 and r["billed"] == 0 and r["collected"] == 0 and r["returned"] == 0 and closing == 0:
            continue
        last_bill = r["last_bill"]
        rows.append({
            "customer_id": r["customer_id"],
            "customer": c.name,
            "phone": c.phone or "—",
            "village": (c.village or "").strip() or "—",
            "branch": branches.get(r["branch_id"], "—"),
            "opening": opening,
            "billed": r["billed"],
            "collected": r["collected"],
            "returned": r["returned"],
            "outstanding": closing,
            "last_bill": last_bill.isoformat() if last_bill else "Never",
            "days_idle": (end - last_bill).days if last_bill else None,
        })
    rows.sort(key=lambda x: (-x["outstanding"], x["village"].lower(), x["customer"].lower()))
    return rows


def _customer_outstanding(db, org_id, scope, start, end) -> dict:
    data = _khata_buckets(db, org_id, scope, start, end)
    return {
        "columns": [
            {"key": "customer", "label": "Farmer"},
            {"key": "phone", "label": "Phone"},
            {"key": "village", "label": "Village"},
            {"key": "branch", "label": "Branch"},
            {"key": "opening", "label": "Opening", "num": True, "money": True},
            {"key": "billed", "label": "Billed", "num": True, "money": True},
            {"key": "collected", "label": "Collected", "num": True, "money": True},
            {"key": "returned", "label": "Returned", "num": True, "money": True},
            {"key": "outstanding", "label": "Closing", "num": True, "money": True},
            {"key": "last_bill", "label": "Last bill"},
        ],
        "rows": data,
        "summary": [
            {"label": "Farmers", "value": len(data)},
            {"label": "Billed", "value": round(sum(r["billed"] for r in data), 2), "money": True},
            {"label": "Collected", "value": round(sum(r["collected"] for r in data), 2), "money": True},
            {"label": "Closing", "value": round(sum(r["outstanding"] for r in data), 2), "money": True},
        ],
    }


def _khata_by_village(db, org_id, scope, start, end) -> dict:
    farmers = _khata_buckets(db, org_id, scope, start, end)
    by_village: dict[str, dict] = {}
    for r in farmers:
        village = r["village"]
        row = by_village.get(village)
        if row is None:
            row = {
                "village": village,
                "farmers": 0,
                "opening": 0.0,
                "billed": 0.0,
                "collected": 0.0,
                "returned": 0.0,
                "outstanding": 0.0,
            }
            by_village[village] = row
        row["farmers"] += 1
        row["opening"] = round(row["opening"] + r["opening"], 2)
        row["billed"] = round(row["billed"] + r["billed"], 2)
        row["collected"] = round(row["collected"] + r["collected"], 2)
        row["returned"] = round(row["returned"] + r["returned"], 2)
        row["outstanding"] = round(row["outstanding"] + r["outstanding"], 2)
    data = sorted(by_village.values(), key=lambda x: (-x["outstanding"], x["village"].lower()))
    return {
        "columns": [
            {"key": "village", "label": "Village"},
            {"key": "farmers", "label": "Farmers", "num": True},
            {"key": "opening", "label": "Opening", "num": True, "money": True},
            {"key": "billed", "label": "Billed", "num": True, "money": True},
            {"key": "collected", "label": "Collected", "num": True, "money": True},
            {"key": "returned", "label": "Returned", "num": True, "money": True},
            {"key": "outstanding", "label": "Closing", "num": True, "money": True},
        ],
        "rows": data,
        "summary": [
            {"label": "Villages", "value": len(data)},
            {"label": "Billed", "value": round(sum(r["billed"] for r in data), 2), "money": True},
            {"label": "Collected", "value": round(sum(r["collected"] for r in data), 2), "money": True},
            {"label": "Closing", "value": round(sum(r["outstanding"] for r in data), 2), "money": True},
        ],
    }


def _inactive_khata(db, org_id, scope, start, end) -> dict:
    """Khata farmers with no bill in the last 30 days (as of the report end date)."""
    days = 30
    cutoff = end - timedelta(days=days)
    last_sale = (
        select(
            Invoice.customer_id,
            func.max(Invoice.invoice_date).label("last_date"),
            func.count(Invoice.id).label("bills"),
        )
        .where(
            Invoice.organization_id == org_id,
            Invoice.status == InvoiceStatus.finalized,
            Invoice.customer_id.is_not(None),
        )
        .group_by(Invoice.customer_id)
    )
    if scope is not None:
        last_sale = last_sale.where(Invoice.branch_id.in_(scope))
    last_sale = last_sale.subquery()
    stmt = (
        select(Customer, last_sale.c.last_date, last_sale.c.bills)
        .outerjoin(last_sale, last_sale.c.customer_id == Customer.id)
        .where(
            Customer.organization_id == org_id,
            Customer.is_deleted.is_(False),
            Customer.outstanding_balance > 0,
            or_(last_sale.c.last_date.is_(None), last_sale.c.last_date <= cutoff),
        )
        .order_by(Customer.outstanding_balance.desc())
    )
    data = []
    for c, last_date, bills in db.execute(stmt).all():
        data.append({
            "customer": c.name,
            "phone": c.phone or "—",
            "village": c.village or "—",
            "outstanding": _n(c.outstanding_balance),
            "last_bill": last_date.isoformat() if last_date else "Never",
            "days_idle": (end - last_date).days if last_date else None,
            "bills": int(bills or 0),
        })
    return {
        "columns": [
            {"key": "customer", "label": "Farmer"},
            {"key": "phone", "label": "Phone"},
            {"key": "village", "label": "Village"},
            {"key": "outstanding", "label": "Outstanding", "num": True, "money": True},
            {"key": "last_bill", "label": "Last bill"},
            {"key": "days_idle", "label": "Days idle", "num": True},
            {"key": "bills", "label": "Lifetime bills", "num": True},
        ],
        "rows": data,
        "summary": [
            {"label": "Farmers to call", "value": len(data)},
            {"label": "Stuck khata", "value": round(sum(r["outstanding"] for r in data), 2), "money": True},
        ],
    }


def _supplier_outstanding(db, org_id, scope, start, end) -> dict:
    rows = accounting.vendor_payables(db, organization_id=org_id)
    data = [
        {
            "vendor": v.name,
            "gstin": v.gstin or "—",
            "phone": v.phone or "—",
            "outstanding": _n(v.outstanding_balance),
        }
        for v in rows
    ]
    return {
        "columns": [
            {"key": "vendor", "label": "Supplier"},
            {"key": "gstin", "label": "GSTIN"},
            {"key": "phone", "label": "Phone"},
            {"key": "outstanding", "label": "Payable", "num": True, "money": True},
        ],
        "rows": data,
        "summary": [{"label": "Payable", "value": round(sum(r["outstanding"] for r in data), 2), "money": True}],
    }


def _gst(db, org_id, scope, start, end) -> dict:
    rows = [
        {**slab, "taxable": slab.pop("taxable_value")}
        for slab in accounting.gst_slabs(
            db, organization_id=org_id, start=start, end=end, branch_ids=scope
        )
    ]
    return {
        "columns": [
            {"key": "gst_rate", "label": "GST %", "num": True},
            {"key": "taxable", "label": "Taxable value", "num": True, "money": True},
            {"key": "cgst", "label": "CGST", "num": True, "money": True},
            {"key": "sgst", "label": "SGST", "num": True, "money": True},
            {"key": "total_tax", "label": "Total tax", "num": True, "money": True},
        ],
        "rows": rows,
        "summary": [
            {"label": "Taxable", "value": round(sum(r["taxable"] for r in rows), 2), "money": True},
            {"label": "GST", "value": round(sum(r["total_tax"] for r in rows), 2), "money": True},
        ],
    }


def _payment_collection(db, org_id, scope, start, end) -> dict:
    inv_stmt = _inv_filter(
        select(Invoice.invoice_date, Invoice.invoice_no, Invoice.payment_mode, Invoice.amount_paid),
        org_id, scope, start, end,
    ).where(Invoice.amount_paid > 0).order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).limit(1500)
    rows = [
        {
            "date": d.isoformat(),
            "source": "Invoice",
            "ref": no,
            "mode": _enum(mode).upper(),
            "amount": _n(paid),
        }
        for d, no, mode, paid in db.execute(inv_stmt)
    ]
    pay_start = datetime.combine(start, datetime.min.time())
    pay_end = datetime.combine(end + timedelta(days=1), datetime.min.time())
    pay_stmt = select(CustomerPayment.paid_at, Customer.name, CustomerPayment.id, CustomerPayment.mode, CustomerPayment.amount).join(
        Customer, Customer.id == CustomerPayment.customer_id
    ).where(
        CustomerPayment.organization_id == org_id,
        CustomerPayment.paid_at >= pay_start,
        CustomerPayment.paid_at < pay_end,
        CustomerPayment.reversed_at.is_(None),
    ).order_by(CustomerPayment.paid_at.desc()).limit(1500)
    if scope is not None:
        pay_stmt = pay_stmt.where(
            (CustomerPayment.branch_id.in_(scope)) | (CustomerPayment.branch_id.is_(None))
        )
    for paid_at, name, pid, mode, amount in db.execute(pay_stmt):
        rows.append({
            "date": paid_at.date().isoformat(),
            "source": f"Khata · {name}",
            "ref": f"PMT-{pid}",
            "mode": (mode or "cash").upper(),
            "amount": _n(amount),
        })
    rows.sort(key=lambda r: r["date"], reverse=True)
    rows = rows[:2000]
    return {
        "columns": [
            {"key": "date", "label": "Date"},
            {"key": "source", "label": "Source"},
            {"key": "ref", "label": "Reference"},
            {"key": "mode", "label": "Mode"},
            {"key": "amount", "label": "Amount", "num": True, "money": True},
        ],
        "rows": rows,
        "summary": [{"label": "Collected", "value": round(sum(r["amount"] for r in rows), 2), "money": True}],
    }


def _batch_vendor_subq(org_id):
    """Attribute each batch to the vendor on its latest GRN line."""
    latest = (
        select(GRNItem.batch_id, func.max(GRNItem.id).label("grn_item_id"))
        .where(GRNItem.batch_id.is_not(None))
        .group_by(GRNItem.batch_id)
        .subquery()
    )
    return (
        select(
            latest.c.batch_id.label("batch_id"),
            GRN.vendor_id.label("vendor_id"),
            func.coalesce(Vendor.name, "Direct / unknown").label("vendor"),
        )
        .select_from(latest)
        .join(GRNItem, GRNItem.id == latest.c.grn_item_id)
        .join(GRN, GRN.id == GRNItem.grn_id)
        .outerjoin(Vendor, Vendor.id == GRN.vendor_id)
        .where(GRN.organization_id == org_id)
        .subquery()
    )


def _vendor_stock(db, org_id, scope, start, end) -> dict:
    """Received and sold in the period, leftover on the shelf now, by GRN vendor."""
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time())
    bv = _batch_vendor_subq(org_id)
    unknown = "Direct / unknown"

    rec_stmt = (
        select(
            GRN.vendor_id,
            func.coalesce(Vendor.name, unknown),
            GRNItem.product_id,
            GRN.branch_id,
            func.coalesce(func.sum(GRNItem.quantity), 0),
        )
        .select_from(GRNItem)
        .join(GRN, GRN.id == GRNItem.grn_id)
        .outerjoin(Vendor, Vendor.id == GRN.vendor_id)
        .where(
            GRN.organization_id == org_id,
            GRN.received_date >= start,
            GRN.received_date <= end,
        )
        .group_by(GRN.vendor_id, Vendor.name, GRNItem.product_id, GRN.branch_id)
    )
    if scope is not None:
        rec_stmt = rec_stmt.where(GRN.branch_id.in_(scope))

    sold_stmt = (
        select(
            bv.c.vendor_id,
            func.coalesce(bv.c.vendor, unknown),
            StockMovement.product_id,
            StockMovement.branch_id,
            StockMovement.movement_type,
            func.coalesce(func.sum(StockMovement.quantity), 0),
        )
        .select_from(StockMovement)
        .outerjoin(bv, bv.c.batch_id == StockMovement.batch_id)
        .where(
            StockMovement.organization_id == org_id,
            StockMovement.occurred_at >= start_dt,
            StockMovement.occurred_at < end_dt,
            StockMovement.movement_type.in_((MovementType.sale, MovementType.sale_return)),
        )
        .group_by(
            bv.c.vendor_id, bv.c.vendor, StockMovement.product_id,
            StockMovement.branch_id, StockMovement.movement_type,
        )
    )
    if scope is not None:
        sold_stmt = sold_stmt.where(StockMovement.branch_id.in_(scope))

    left_stmt = (
        select(
            bv.c.vendor_id,
            func.coalesce(bv.c.vendor, unknown),
            Stock.product_id,
            Stock.branch_id,
            func.coalesce(func.sum(Stock.quantity), 0),
            func.coalesce(func.sum(Stock.quantity * Batch.purchase_price), 0),
        )
        .select_from(Stock)
        .join(Batch, Batch.id == Stock.batch_id)
        .outerjoin(bv, bv.c.batch_id == Stock.batch_id)
        .where(Stock.organization_id == org_id)
        .group_by(bv.c.vendor_id, bv.c.vendor, Stock.product_id, Stock.branch_id)
    )
    if scope is not None:
        left_stmt = left_stmt.where(Stock.branch_id.in_(scope))

    buckets: dict[tuple, dict] = {}

    def bucket(vendor_id, vendor, product_id, branch_id) -> dict:
        k = (int(vendor_id or 0), str(vendor or unknown), int(product_id), int(branch_id))
        row = buckets.get(k)
        if row is None:
            row = {
                "vendor": vendor or unknown,
                "product_id": int(product_id),
                "branch_id": int(branch_id),
                "received": 0.0,
                "sold": 0.0,
                "left": 0.0,
                "value": 0.0,
            }
            buckets[k] = row
        return row

    for vendor_id, vendor, pid, bid, qty in db.execute(rec_stmt).all():
        bucket(vendor_id, vendor, pid, bid)["received"] = _qty(qty)

    for vendor_id, vendor, pid, bid, mtype, qty in db.execute(sold_stmt).all():
        row = bucket(vendor_id, vendor, pid, bid)
        q = _qty(qty)
        kind = _enum(mtype)
        if kind == MovementType.sale.value:
            row["sold"] = round(row["sold"] + (-q if q < 0 else 0.0), 3)
        elif kind == MovementType.sale_return.value:
            row["sold"] = round(row["sold"] - (q if q > 0 else 0.0), 3)

    for vendor_id, vendor, pid, bid, qty, value in db.execute(left_stmt).all():
        q = _qty(qty)
        if q == 0:
            continue
        row = bucket(vendor_id, vendor, pid, bid)
        row["left"] = q
        row["value"] = round(float(value or 0), 2)

    pids = {r["product_id"] for r in buckets.values()}
    bids = {r["branch_id"] for r in buckets.values()}
    products = {
        p.id: p for p in db.scalars(select(Product).where(Product.id.in_(pids))).all()
    } if pids else {}
    branches = {
        b.id: b.name for b in db.scalars(select(Branch).where(Branch.id.in_(bids))).all()
    } if bids else {}

    rows = []
    for r in buckets.values():
        p = products.get(r["product_id"])
        if p is None:
            continue
        if r["received"] == 0 and r["sold"] == 0 and r["left"] == 0:
            continue
        rows.append({
            "vendor": r["vendor"],
            "product": p.name,
            "sku": p.sku or "—",
            "branch": branches.get(r["branch_id"], "—"),
            "received": r["received"],
            "sold": r["sold"],
            "left": r["left"],
            "value": r["value"],
        })
    rows.sort(key=lambda x: (x["vendor"].lower(), x["product"].lower(), x["branch"]))
    return {
        "columns": [
            {"key": "vendor", "label": "Vendor"},
            {"key": "product", "label": "Product"},
            {"key": "sku", "label": "SKU"},
            {"key": "branch", "label": "Branch"},
            {"key": "received", "label": "Received", "num": True},
            {"key": "sold", "label": "Sold", "num": True},
            {"key": "left", "label": "Left", "num": True},
            {"key": "value", "label": "Left value", "num": True, "money": True},
        ],
        "rows": rows,
        "summary": [
            {"label": "Received", "value": round(sum(r["received"] for r in rows), 3)},
            {"label": "Sold", "value": round(sum(r["sold"] for r in rows), 3)},
            {"label": "Left", "value": round(sum(r["left"] for r in rows), 3)},
            {"label": "Left value", "value": round(sum(r["value"] for r in rows), 2), "money": True},
        ],
    }


def _field_visits(db, org_id, scope, start, end) -> dict:
    stmt = (
        select(FieldVisit, Branch.name, User.full_name)
        .join(Branch, Branch.id == FieldVisit.branch_id)
        .join(User, User.id == FieldVisit.visited_by_user_id)
        .where(
            FieldVisit.organization_id == org_id,
            FieldVisit.visit_date >= start,
            FieldVisit.visit_date <= end,
        )
        .order_by(FieldVisit.visit_date.desc(), FieldVisit.id.desc())
    )
    if scope is not None:
        stmt = stmt.where(FieldVisit.branch_id.in_(scope))
    rows = [
        {
            "visit_no": v.visit_no,
            "date": v.visit_date.isoformat(),
            "farmer": v.farmer_name,
            "phone": v.farmer_phone or "—",
            "village": v.village or "—",
            "staff": staff,
            "branch": branch,
            "status": _enum(v.status),
            "complaint": (v.complaint_notes or "—")[:120],
        }
        for v, branch, staff in db.execute(stmt).all()
    ]
    return {
        "columns": [
            {"key": "visit_no", "label": "Visit #"},
            {"key": "date", "label": "Date"},
            {"key": "farmer", "label": "Farmer"},
            {"key": "phone", "label": "Phone"},
            {"key": "village", "label": "Village"},
            {"key": "staff", "label": "Visited by"},
            {"key": "branch", "label": "Branch"},
            {"key": "status", "label": "Status"},
            {"key": "complaint", "label": "Complaint"},
        ],
        "rows": rows,
        "summary": [{"label": "Visits", "value": len(rows)}],
    }


def _product_margins(db, org_id, scope, start, end, *, lowest: bool) -> dict:
    stmt = (
        line_totals_stmt(Product.id, Product.name, Product.sku)
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .join(Product, Product.id == InvoiceItem.product_id)
    )
    stmt = _inv_filter(stmt, org_id, scope, start, end)
    rows = []
    for (_pid, name, sku), t in grouped_totals(db, stmt).items():
        profit = _n(t.taxable) - _n(t.cogs)
        margin = round(profit / _n(t.taxable) * 100, 1) if _n(t.taxable) else 0
        rows.append({
            "product": name,
            "sku": sku or "—",
            "qty": _qty(t.qty),
            "discount": _n(t.discount),
            "sales": _n(t.taxable),
            "cost": _n(t.cogs),
            "profit": round(profit, 2),
            "margin_pct": margin,
        })
    rows.sort(key=lambda r: r["profit"], reverse=not lowest)
    profit_sum = round(sum(r["profit"] for r in rows), 2)
    losers = sum(1 for r in rows if r["profit"] < 0)
    return {
        "columns": [
            {"key": "product", "label": "Product"},
            {"key": "sku", "label": "SKU"},
            {"key": "qty", "label": "Qty sold", "num": True},
            {"key": "discount", "label": "Discount", "num": True, "money": True},
            {"key": "sales", "label": "Sales (excl. GST)", "num": True, "money": True},
            {"key": "cost", "label": "Cost", "num": True, "money": True},
            {"key": "profit", "label": "Profit / (loss)", "num": True, "money": True},
            {"key": "margin_pct", "label": "Margin %", "num": True},
        ],
        "rows": rows,
        "summary": [
            {"label": "Profit", "value": profit_sum, "money": True},
            {"label": "Loss-making SKUs", "value": losers},
        ],
    }


def _product_profit(db, org_id, scope, start, end) -> dict:
    return _product_margins(db, org_id, scope, start, end, lowest=False)


def _product_loss(db, org_id, scope, start, end) -> dict:
    data = _product_margins(db, org_id, scope, start, end, lowest=True)
    data["rows"] = [r for r in data["rows"] if r["profit"] <= 0] or data["rows"][:25]
    data["summary"] = [{"label": "Profit / (loss)", "value": round(sum(r["profit"] for r in data["rows"]), 2), "money": True}]
    return data


def _farmer_margins(db, org_id, scope, start, end, *, lowest: bool) -> dict:
    stmt = (
        line_totals_stmt(Customer.id, Customer.name, Customer.village, Customer.phone)
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .join(Product, Product.id == InvoiceItem.product_id)
        .outerjoin(Customer, Customer.id == Invoice.customer_id)
    )
    stmt = _inv_filter(stmt, org_id, scope, start, end)
    # Bills are counted separately: the totals query also groups by product and
    # billed unit, so a COUNT DISTINCT there would repeat per line.
    bills_stmt = _inv_filter(
        select(Invoice.customer_id, func.count(func.distinct(Invoice.id)))
        .join(InvoiceItem, InvoiceItem.invoice_id == Invoice.id)
        .join(Product, Product.id == InvoiceItem.product_id),
        org_id, scope, start, end,
    ).group_by(Invoice.customer_id)
    bills_by_customer = {cid: int(n) for cid, n in db.execute(bills_stmt).all()}
    rows = []
    for (cid, name, village, phone), t in grouped_totals(db, stmt).items():
        profit = _n(t.taxable) - _n(t.cogs)
        rows.append({
            "farmer": name or "Walk-in",
            "village": village or "—",
            "phone": phone or "—",
            "bills": bills_by_customer.get(cid, 0),
            "sales": _n(t.taxable),
            "cost": _n(t.cogs),
            "profit": round(profit, 2),
        })
    rows.sort(key=lambda r: r["profit"], reverse=not lowest)
    return {
        "columns": [
            {"key": "farmer", "label": "Farmer"},
            {"key": "village", "label": "Village"},
            {"key": "phone", "label": "Phone"},
            {"key": "bills", "label": "Bills", "num": True},
            {"key": "sales", "label": "Sales (excl. GST)", "num": True, "money": True},
            {"key": "cost", "label": "Cost", "num": True, "money": True},
            {"key": "profit", "label": "Profit / (loss)", "num": True, "money": True},
        ],
        "rows": rows,
        "summary": [{"label": "Profit", "value": round(sum(r["profit"] for r in rows), 2), "money": True}],
    }


def _farmer_profit(db, org_id, scope, start, end) -> dict:
    return _farmer_margins(db, org_id, scope, start, end, lowest=False)


def _farmer_loss(db, org_id, scope, start, end) -> dict:
    data = _farmer_margins(db, org_id, scope, start, end, lowest=True)
    data["rows"] = [r for r in data["rows"] if r["profit"] <= 0] or data["rows"][:25]
    data["summary"] = [{"label": "Profit / (loss)", "value": round(sum(r["profit"] for r in data["rows"]), 2), "money": True}]
    return data


def _stock_reconcile(db, org_id, scope, start, end) -> dict:
    """Opening + inflows − outflows vs book qty left, plus any open count cases."""
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time())

    mov_base = select(
        StockMovement.product_id,
        StockMovement.branch_id,
        StockMovement.movement_type,
        func.coalesce(func.sum(StockMovement.quantity), 0),
    ).where(
        StockMovement.organization_id == org_id,
        StockMovement.occurred_at >= start_dt,
        StockMovement.occurred_at < end_dt,
    )
    if scope is not None:
        mov_base = mov_base.where(StockMovement.branch_id.in_(scope))
    mov_base = mov_base.group_by(
        StockMovement.product_id, StockMovement.branch_id, StockMovement.movement_type,
    )

    after_base = select(
        StockMovement.product_id,
        StockMovement.branch_id,
        func.coalesce(func.sum(StockMovement.quantity), 0),
    ).where(
        StockMovement.organization_id == org_id,
        StockMovement.occurred_at >= end_dt,
    )
    if scope is not None:
        after_base = after_base.where(StockMovement.branch_id.in_(scope))
    after_base = after_base.group_by(StockMovement.product_id, StockMovement.branch_id)

    stock_base = select(
        Stock.product_id,
        Stock.branch_id,
        func.coalesce(func.sum(Stock.quantity), 0),
    ).where(Stock.organization_id == org_id)
    if scope is not None:
        stock_base = stock_base.where(Stock.branch_id.in_(scope))
    stock_base = stock_base.group_by(Stock.product_id, Stock.branch_id)

    by_type: dict[tuple[int, int], dict[str, float]] = {}
    keys: set[tuple[int, int]] = set()

    def bucket(pid, bid) -> dict[str, float]:
        k = (int(pid), int(bid))
        keys.add(k)
        return by_type.setdefault(k, {})

    for pid, bid, mtype, qty in db.execute(mov_base).all():
        bucket(pid, bid)[_enum(mtype)] = _qty(qty)
    after: dict[tuple[int, int], float] = {}
    for pid, bid, qty in db.execute(after_base).all():
        k = (int(pid), int(bid))
        keys.add(k)
        after[k] = _qty(qty)
    on_hand_now: dict[tuple[int, int], float] = {}
    for pid, bid, qty in db.execute(stock_base).all():
        k = (int(pid), int(bid))
        if _qty(qty) == 0 and k not in keys:
            continue
        keys.add(k)
        on_hand_now[k] = _qty(qty)

    case_stmt = (
        select(StockDiscrepancy)
        .where(StockDiscrepancy.organization_id == org_id)
        .order_by(StockDiscrepancy.updated_at.desc(), StockDiscrepancy.id.desc())
    )
    if scope is not None:
        case_stmt = case_stmt.where(StockDiscrepancy.branch_id.in_(scope))
    latest_case: dict[tuple[int, int], StockDiscrepancy] = {}
    for c in db.scalars(case_stmt).all():
        k = (int(c.product_id), int(c.branch_id))
        keys.add(k)
        latest_case.setdefault(k, c)

    pids = {k[0] for k in keys}
    bids = {k[1] for k in keys}
    products = {
        p.id: p for p in db.scalars(select(Product).where(Product.id.in_(pids))).all()
    } if pids else {}
    branches = {
        b.id: b.name for b in db.scalars(select(Branch).where(Branch.id.in_(bids))).all()
    } if bids else {}

    def pos(v: float) -> float:
        return round(v if v > 0 else 0.0, 3)

    def neg(v: float) -> float:
        return round(-v if v < 0 else 0.0, 3)

    rows = []
    open_cases = 0
    ledger_mismatches = 0
    missing_bags = 0.0
    for pid, bid in sorted(keys, key=lambda k: ((products.get(k[0]).name if products.get(k[0]) else ""), k[1])):
        p = products.get(pid)
        if p is None:
            continue
        t = by_type.get((pid, bid), {})
        loaded = pos(t.get("grn", 0))
        sold = neg(t.get("sale", 0))
        sale_ret = pos(t.get("sale_return", 0))
        purch_ret = neg(t.get("purchase_return", 0))
        xfer_in = pos(t.get("transfer_in", 0))
        xfer_out = neg(t.get("transfer_out", 0))
        adj = round(t.get("adjustment", 0), 3)
        other = 0.0
        known = {
            "grn", "sale", "sale_return", "purchase_return",
            "transfer_in", "transfer_out", "adjustment",
        }
        for mt, q in t.items():
            if mt not in known:
                other += q
        other = round(other, 3)
        period_net = round(sum(t.values()), 3)
        book_now = on_hand_now.get((pid, bid), 0.0)
        book_end = round(book_now - after.get((pid, bid), 0.0), 3)
        opening = round(book_end - period_net, 3)
        expected = round(
            opening + loaded + sale_ret + xfer_in + adj + other - sold - purch_ret - xfer_out, 3
        )
        ledger_gap = round(book_end - expected, 3)
        case = latest_case.get((pid, bid))
        counted = _qty(case.counted_qty) if case else None
        gap = _qty(case.variance) if case else None  # counted - book at count time
        status = _enum(case.status) if case else ""
        if status in {StockDiscrepancyStatus.open.value, StockDiscrepancyStatus.investigating.value, "open", "investigating"}:
            open_cases += 1
            if gap is not None and gap < 0:
                missing_bags += -gap
        if abs(ledger_gap) >= 0.001:
            ledger_mismatches += 1
        rows.append({
            "product_id": pid,
            "branch_id": bid,
            "case_id": case.id if case else None,
            "product": p.name,
            "sku": p.sku or "—",
            "category": _enum(p.category).replace("_", " ").title(),
            "branch": branches.get(bid, "—"),
            "opening": opening,
            "loaded": loaded,
            "sold": sold,
            "sale_return": sale_ret,
            "purchase_return": purch_ret,
            "transfer_in": xfer_in,
            "transfer_out": xfer_out,
            "adjustment": adj,
            "expected": expected,
            "left": book_end,
            "ledger_gap": ledger_gap,
            "counted": counted,
            "gap": gap,
            "case_status": status or "—",
            "case_note": (case.note if case else None) or "—",
            "on_hand_now": book_now,
        })
    rows.sort(key=lambda r: (abs(r["ledger_gap"]) + abs(r["gap"] or 0), abs(r["left"])), reverse=True)
    return {
        "columns": [
            {"key": "product", "label": "Product"},
            {"key": "sku", "label": "SKU"},
            {"key": "category", "label": "Category"},
            {"key": "branch", "label": "Branch"},
            {"key": "counted", "label": "Counted", "num": True},
            {"key": "gap", "label": "Count gap", "num": True},
            {"key": "case_status", "label": "Case"},
            {"key": "opening", "label": "Opening", "num": True},
            {"key": "loaded", "label": "Loaded", "num": True},
            {"key": "sold", "label": "Sold", "num": True},
            {"key": "sale_return", "label": "Sale ret.", "num": True},
            {"key": "purchase_return", "label": "Purch. ret.", "num": True},
            {"key": "transfer_in", "label": "Xfer in", "num": True},
            {"key": "transfer_out", "label": "Xfer out", "num": True},
            {"key": "adjustment", "label": "Adjust", "num": True},
            {"key": "expected", "label": "Expected left", "num": True},
            {"key": "left", "label": "Left (book)", "num": True},
            {"key": "ledger_gap", "label": "Book gap", "num": True},
        ],
        "rows": rows,
        "summary": [
            {"label": "SKUs", "value": len(rows)},
            {"label": "Book mismatches", "value": ledger_mismatches},
            {"label": "Open cases", "value": open_cases},
            {"label": "Counted short (packs)", "value": round(missing_bags, 3)},
        ],
        "track": True,
    }
