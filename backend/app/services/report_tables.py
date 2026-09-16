"""Tabular operational reports returned as columns + rows for the UI/export."""
from __future__ import annotations

from calendar import month_name
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer, CustomerPayment
from app.models.enums import InvoiceStatus, MovementType
from app.models.expense import Expense
from app.models.field_visit import FieldVisit
from app.models.inventory import Batch, Stock, StockMovement
from app.models.organization import Branch
from app.models.product import Product
from app.models.purchase import GRN, GRNItem
from app.models.sales import Invoice, InvoiceItem
from app.models.user import User
from app.models.vendor import Vendor

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
    {"key": "customer_outstanding", "label": "Khata outstanding", "group": "collections", "needs_dates": False,
     "blurb": "Everyone who still owes the shop. Call the top of this list first."},
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
    {"key": "expiry", "label": "Expiry risk", "group": "stock", "needs_dates": False,
     "blurb": "Batches expiring in 60 days. Sell, return, or write off before they become unsaleable."},
    {"key": "low_stock", "label": "Reorder", "group": "stock", "needs_dates": False,
     "blurb": "Out of stock or below reorder level. These are lost sales if a farmer walks in tomorrow."},
    {"key": "gst", "label": "GST", "group": "accounts", "needs_dates": True,
     "blurb": "Taxable value and tax by slab. Hand this to your CA for the return."},
    {"key": "profit_loss", "label": "Profit & loss", "group": "accounts", "needs_dates": True,
     "blurb": "Sales minus GST, product cost, and expenses. The number that says whether the shop made money."},
    # Kept for AI / old links; not shown on the Reports screen.
    {"key": "category_sales", "label": "Category sales", "needs_dates": True, "nav": False},
    {"key": "stock_movement", "label": "Stock movement", "needs_dates": True, "nav": False},
    {"key": "vendor_stock", "label": "Vendor-wise stock", "needs_dates": True, "nav": False},
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
        "supplier_outstanding": _supplier_outstanding,
        "gst": _gst,
        "payment_collection": _payment_collection,
        "vendor_stock": _vendor_stock,
        "field_visits": _field_visits,
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
        select(
            InvoiceItem.product_id,
            InvoiceItem.product_name,
            Product.category,
            func.coalesce(func.sum(InvoiceItem.quantity), 0),
            func.coalesce(func.sum(InvoiceItem.taxable_value), 0),
            func.coalesce(func.sum(InvoiceItem.tax_amount), 0),
            func.coalesce(func.sum(InvoiceItem.line_total), 0),
        )
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .outerjoin(Product, Product.id == InvoiceItem.product_id)
    )
    stmt = _inv_filter(stmt, org_id, scope, start, end)
    stmt = stmt.group_by(InvoiceItem.product_id, InvoiceItem.product_name, Product.category).order_by(
        func.sum(InvoiceItem.line_total).desc()
    )
    rows = [
        {
            "product": name,
            "category": _enum(cat).replace("_", " ").title() if cat else "—",
            "qty": _qty(qty),
            "taxable": _n(taxable),
            "tax": _n(tax),
            "amount": _n(total),
        }
        for _pid, name, cat, qty, taxable, tax, total in db.execute(stmt).all()
    ]
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
        select(
            Product.category,
            func.coalesce(func.sum(InvoiceItem.quantity), 0),
            func.coalesce(func.sum(InvoiceItem.taxable_value), 0),
            func.coalesce(func.sum(InvoiceItem.line_total), 0),
        )
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .join(Product, Product.id == InvoiceItem.product_id)
    )
    stmt = _inv_filter(stmt, org_id, scope, start, end)
    stmt = stmt.group_by(Product.category)
    rows = [
        {
            "category": _enum(cat).replace("_", " ").title(),
            "qty": _qty(qty),
            "taxable": _n(taxable),
            "amount": _n(total),
        }
        for cat, qty, taxable, total in db.execute(stmt).all()
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
            func.coalesce(func.sum(Invoice.grand_total), 0),
            func.coalesce(func.sum(Invoice.tax_total), 0),
            func.coalesce(func.sum(Invoice.discount_total), 0),
        ),
        org_id, scope, start, end,
    )
    sales, tax, discount = db.execute(sales_stmt).one()
    cogs_stmt = (
        select(func.coalesce(func.sum(InvoiceItem.quantity * Product.purchase_price), 0))
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .join(Product, Product.id == InvoiceItem.product_id)
    )
    cogs_stmt = _inv_filter(cogs_stmt, org_id, scope, start, end)
    cogs = db.scalar(cogs_stmt) or 0
    exp_stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.organization_id == org_id,
        Expense.expense_date >= start,
        Expense.expense_date <= end,
    )
    if scope is not None:
        exp_stmt = exp_stmt.where(Expense.branch_id.in_(scope))
    expenses = db.scalar(exp_stmt) or 0
    net_sales = _n(sales) - _n(tax)
    gross = net_sales - _n(cogs)
    net = gross - _n(expenses)
    rows = [
        {"line": "Gross sales (incl. GST)", "amount": _n(sales)},
        {"line": "GST collected", "amount": _n(tax)},
        {"line": "Discounts", "amount": _n(discount)},
        {"line": "Net sales (excl. GST)", "amount": round(net_sales, 2)},
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
    qty_stmt = select(Stock.product_id, func.coalesce(func.sum(Stock.quantity), 0)).where(
        Stock.organization_id == org_id
    )
    if scope is not None:
        qty_stmt = qty_stmt.where(Stock.branch_id.in_(scope))
    qty_stmt = qty_stmt.group_by(Stock.product_id)
    qty_map = {pid: _qty(q) for pid, q in db.execute(qty_stmt).all()}
    products = db.scalars(select(Product).where(
        Product.organization_id == org_id, Product.is_deleted.is_(False)
    ).order_by(Product.name)).all()
    rows = []
    for p in products:
        qty = qty_map.get(p.id, 0.0)
        reorder = _qty(p.reorder_level)
        if qty > reorder and qty > 0:
            continue
        status = "Out of stock" if qty <= 0 else "Low stock"
        rows.append({
            "product": p.name,
            "sku": p.sku,
            "on_hand": qty,
            "reorder_level": reorder,
            "status": status,
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


def _customer_outstanding(db, org_id, scope, start, end) -> dict:
    last_sale = (
        select(
            Invoice.customer_id,
            func.max(Invoice.invoice_date).label("last_date"),
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
    rows = db.execute(
        select(Customer, last_sale.c.last_date)
        .outerjoin(last_sale, last_sale.c.customer_id == Customer.id)
        .where(
            Customer.organization_id == org_id,
            Customer.is_deleted.is_(False),
            Customer.outstanding_balance > 0,
        )
        .order_by(Customer.outstanding_balance.desc())
    ).all()
    today = date.today()
    data = []
    for c, last_date in rows:
        data.append({
            "customer": c.name,
            "phone": c.phone or "—",
            "village": c.village or "—",
            "outstanding": _n(c.outstanding_balance),
            "last_bill": last_date.isoformat() if last_date else "Never",
            "days_idle": (today - last_date).days if last_date else None,
        })
    return {
        "columns": [
            {"key": "customer", "label": "Farmer"},
            {"key": "phone", "label": "Phone"},
            {"key": "village", "label": "Village"},
            {"key": "outstanding", "label": "Outstanding", "num": True, "money": True},
            {"key": "last_bill", "label": "Last bill"},
            {"key": "days_idle", "label": "Days since bill", "num": True},
        ],
        "rows": data,
        "summary": [
            {"label": "Farmers", "value": len(data)},
            {"label": "Receivable", "value": round(sum(r["outstanding"] for r in data), 2), "money": True},
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
    rows = db.scalars(select(Vendor).where(
        Vendor.organization_id == org_id,
        Vendor.is_deleted.is_(False),
        Vendor.outstanding_balance > 0,
    ).order_by(Vendor.outstanding_balance.desc())).all()
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
    stmt = (
        select(
            InvoiceItem.gst_rate,
            func.coalesce(func.sum(InvoiceItem.taxable_value), 0),
            func.coalesce(func.sum(InvoiceItem.tax_amount), 0),
        )
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
    )
    stmt = _inv_filter(stmt, org_id, scope, start, end).group_by(InvoiceItem.gst_rate)
    rows = []
    for rate, taxable, tax in db.execute(stmt).all():
        tax_f = _n(tax)
        rows.append({
            "gst_rate": _n(rate),
            "taxable": _n(taxable),
            "cgst": round(tax_f / 2, 2),
            "sgst": round(tax_f / 2, 2),
            "total_tax": tax_f,
        })
    rows.sort(key=lambda r: r["gst_rate"])
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


def _vendor_stock(db, org_id, scope, start, end) -> dict:
    latest = (
        select(GRNItem.batch_id, func.max(GRNItem.id).label("grn_item_id"))
        .where(GRNItem.batch_id.is_not(None))
        .group_by(GRNItem.batch_id)
        .subquery()
    )
    stmt = (
        select(
            Vendor.name, Product.name, Product.sku, Batch.batch_no, Branch.name,
            Stock.quantity, Batch.purchase_price, Batch.expiry_date,
        )
        .select_from(Stock)
        .join(Product, Product.id == Stock.product_id)
        .join(Batch, Batch.id == Stock.batch_id)
        .join(Branch, Branch.id == Stock.branch_id)
        .outerjoin(latest, latest.c.batch_id == Stock.batch_id)
        .outerjoin(GRNItem, GRNItem.id == latest.c.grn_item_id)
        .outerjoin(GRN, GRN.id == GRNItem.grn_id)
        .outerjoin(Vendor, Vendor.id == GRN.vendor_id)
        .where(Stock.organization_id == org_id, Stock.quantity > 0)
        .order_by(Vendor.name.asc(), Product.name.asc())
    )
    if scope is not None:
        stmt = stmt.where(Stock.branch_id.in_(scope))
    rows = []
    total = 0.0
    for vendor, product, sku, batch, branch, qty, cost, expiry in db.execute(stmt).all():
        value = _qty(qty) * _n(cost)
        total += value
        rows.append({
            "vendor": vendor or "Direct / unknown",
            "product": product,
            "sku": sku,
            "batch": batch,
            "expiry": expiry.isoformat() if expiry else "—",
            "branch": branch,
            "qty": _qty(qty),
            "value": round(value, 2),
        })
    return {
        "columns": [
            {"key": "vendor", "label": "Vendor"},
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
        select(
            Product.name, Product.sku,
            func.coalesce(func.sum(InvoiceItem.quantity), 0),
            func.coalesce(func.sum(InvoiceItem.taxable_value), 0),
            func.coalesce(func.sum(InvoiceItem.quantity * Product.purchase_price), 0),
        )
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .join(Product, Product.id == InvoiceItem.product_id)
    )
    stmt = _inv_filter(stmt, org_id, scope, start, end)
    stmt = stmt.group_by(Product.id, Product.name, Product.sku)
    rows = []
    for name, sku, qty, taxable, cogs in db.execute(stmt).all():
        profit = _n(taxable) - _n(cogs)
        margin = round(profit / _n(taxable) * 100, 1) if _n(taxable) else 0
        rows.append({
            "product": name,
            "sku": sku or "—",
            "qty": _qty(qty),
            "sales": _n(taxable),
            "cost": _n(cogs),
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
        select(
            Customer.id, Customer.name, Customer.village, Customer.phone,
            func.coalesce(func.sum(InvoiceItem.taxable_value), 0),
            func.coalesce(func.sum(InvoiceItem.quantity * Product.purchase_price), 0),
            func.count(func.distinct(Invoice.id)),
        )
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .join(Product, Product.id == InvoiceItem.product_id)
        .outerjoin(Customer, Customer.id == Invoice.customer_id)
    )
    stmt = _inv_filter(stmt, org_id, scope, start, end)
    stmt = stmt.group_by(Customer.id, Customer.name, Customer.village, Customer.phone)
    rows = []
    for cid, name, village, phone, taxable, cogs, bills in db.execute(stmt).all():
        profit = _n(taxable) - _n(cogs)
        rows.append({
            "farmer": name or "Walk-in",
            "village": village or "—",
            "phone": phone or "—",
            "bills": int(bills),
            "sales": _n(taxable),
            "cost": _n(cogs),
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
