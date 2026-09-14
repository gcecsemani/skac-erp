"""Double-entry accounting: default chart of accounts + auto-posting + reports."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.accounting import JournalEntry, JournalLine, LedgerAccount
from app.models.enums import AccountType

# code -> (name, type)
DEFAULT_ACCOUNTS: dict[str, tuple[str, AccountType]] = {
    "1000": ("Cash", AccountType.asset),
    "1010": ("Bank", AccountType.asset),
    "1200": ("Accounts Receivable (Debtors)", AccountType.asset),
    "1300": ("Inventory", AccountType.asset),
    "1310": ("GST Input Credit", AccountType.asset),
    "2000": ("Accounts Payable (Creditors)", AccountType.liability),
    "2100": ("GST Payable", AccountType.liability),
    "3000": ("Sales", AccountType.income),
    "4000": ("Purchases / COGS", AccountType.expense),
    "4100": ("Transport Charges", AccountType.expense),
    "4200": ("Salaries & Wages", AccountType.expense),
    "4300": ("Rent", AccountType.expense),
    "4400": ("Electricity & Utilities", AccountType.expense),
    "4500": ("Other Operating Expenses", AccountType.expense),
    "5000": ("Owner Capital", AccountType.equity),
}

EXPENSE_CATEGORY_ACCOUNTS: dict[str, str] = {
    "transport": "4100",
    "salary": "4200",
    "rent": "4300",
    "electricity": "4400",
    "packing": "4500",
    "maintenance": "4500",
    "other": "4500",
}


def ensure_accounts(db: Session, organization_id: int) -> dict[str, LedgerAccount]:
    existing = {
        a.code: a
        for a in db.scalars(
            select(LedgerAccount).where(LedgerAccount.organization_id == organization_id)
        ).all()
    }
    created = False
    for code, (name, atype) in DEFAULT_ACCOUNTS.items():
        if code not in existing:
            acc = LedgerAccount(
                organization_id=organization_id, code=code, name=name,
                type=atype, is_system=True,
            )
            db.add(acc)
            existing[code] = acc
            created = True
    if created:
        db.flush()
    return existing


def post_entry(
    db: Session,
    *,
    organization_id: int,
    branch_id: int | None,
    entry_date: date,
    narration: str,
    ref_type: str,
    ref_id: int | None,
    lines: list[tuple[str, Decimal, Decimal]],  # (account_code, debit, credit)
) -> JournalEntry:
    accounts = ensure_accounts(db, organization_id)
    entry = JournalEntry(
        organization_id=organization_id, branch_id=branch_id, entry_date=entry_date,
        narration=narration, ref_type=ref_type, ref_id=ref_id,
    )
    db.add(entry)
    db.flush()
    for code, debit, credit in lines:
        acc = accounts[code]
        db.add(
            JournalLine(
                entry_id=entry.id, account_id=acc.id,
                debit=Decimal(debit), credit=Decimal(credit),
            )
        )
    return entry


# --- Posting rules for source documents ---
def post_sale(db, *, organization_id, branch_id, entry_date, invoice_id,
              taxable, tax, grand_total, amount_paid) -> None:
    paid = Decimal(amount_paid)
    on_credit = Decimal(grand_total) - paid
    lines = []
    if paid > 0:
        lines.append(("1000", paid, Decimal("0")))          # Dr Cash
    if on_credit > 0:
        lines.append(("1200", on_credit, Decimal("0")))     # Dr Debtors
    lines.append(("3000", Decimal("0"), Decimal(taxable)))  # Cr Sales
    if Decimal(tax) > 0:
        lines.append(("2100", Decimal("0"), Decimal(tax)))  # Cr GST Payable
    post_entry(db, organization_id=organization_id, branch_id=branch_id,
               entry_date=entry_date, narration="Sales invoice",
               ref_type="invoice", ref_id=invoice_id, lines=lines)


def post_purchase(db, *, organization_id, branch_id, entry_date, grn_id, total_value) -> None:
    post_entry(db, organization_id=organization_id, branch_id=branch_id,
               entry_date=entry_date, narration="Goods received (GRN)",
               ref_type="grn", ref_id=grn_id,
               lines=[("1300", Decimal(total_value), Decimal("0")),   # Dr Inventory
                      ("2000", Decimal("0"), Decimal(total_value))])  # Cr Creditors


def post_customer_receipt(db, *, organization_id, branch_id, entry_date, payment_id, amount, mode) -> None:
    cash_acc = "1010" if mode in ("bank", "upi", "card") else "1000"
    post_entry(db, organization_id=organization_id, branch_id=branch_id,
               entry_date=entry_date, narration="Customer receipt (khata collection)",
               ref_type="customer_payment", ref_id=payment_id,
               lines=[(cash_acc, Decimal(amount), Decimal("0")),   # Dr Cash/Bank
                      ("1200", Decimal("0"), Decimal(amount))])    # Cr Debtors


def post_vendor_payment(db, *, organization_id, branch_id, entry_date, payment_id, amount, mode) -> None:
    cash_acc = "1010" if mode in ("bank", "upi", "card") else "1000"
    post_entry(db, organization_id=organization_id, branch_id=branch_id,
               entry_date=entry_date, narration="Vendor payment",
               ref_type="vendor_payment", ref_id=payment_id,
               lines=[("2000", Decimal(amount), Decimal("0")),       # Dr Creditors
                      (cash_acc, Decimal("0"), Decimal(amount))])    # Cr Cash/Bank


def expense_account_for(db: Session, organization_id: int, category: str) -> str:
    from app.models.config import KIND_EXPENSE, ConfigItem
    row = db.scalar(select(ConfigItem).where(
        ConfigItem.organization_id == organization_id,
        ConfigItem.kind == KIND_EXPENSE,
        ConfigItem.code == category,
        ConfigItem.is_deleted.is_(False),
    ))
    if row:
        acc = (row.extra or {}).get("account")
        if acc:
            return str(acc)
    return EXPENSE_CATEGORY_ACCOUNTS.get(category, "4500")


def post_expense(db, *, organization_id, branch_id, entry_date, expense_id, amount, mode,
                 category: str, payee: str | None = None) -> None:
    cash_acc = "1010" if mode in ("bank", "upi", "card") else "1000"
    exp_acc = expense_account_for(db, organization_id, category)
    who = f" to {payee}" if payee else ""
    post_entry(
        db, organization_id=organization_id, branch_id=branch_id,
        entry_date=entry_date, narration=f"{category.replace('_', ' ').title()} expense{who}",
        ref_type="expense", ref_id=expense_id,
        lines=[(exp_acc, Decimal(amount), Decimal("0")),     # Dr expense
               (cash_acc, Decimal("0"), Decimal(amount))],   # Cr Cash/Bank
    )


def post_purchase_return(db, *, organization_id, branch_id, entry_date, purchase_return_id,
                         total_value) -> None:
    post_entry(
        db, organization_id=organization_id, branch_id=branch_id,
        entry_date=entry_date, narration="Purchase return (debit note)",
        ref_type="purchase_return", ref_id=purchase_return_id,
        lines=[("2000", Decimal(total_value), Decimal("0")),   # Dr Creditors
               ("1300", Decimal("0"), Decimal(total_value))],  # Cr Inventory
    )


def post_credit_note(db, *, organization_id, branch_id, entry_date, credit_note_id,
                     taxable, tax, total) -> None:
    lines = [("3000", Decimal(taxable), Decimal("0"))]              # Dr Sales (reverse)
    if Decimal(tax) > 0:
        lines.append(("2100", Decimal(tax), Decimal("0")))         # Dr GST Payable
    lines.append(("1200", Decimal("0"), Decimal(total)))           # Cr Debtors
    post_entry(db, organization_id=organization_id, branch_id=branch_id,
               entry_date=entry_date, narration="Sales return (credit note)",
               ref_type="credit_note", ref_id=credit_note_id, lines=lines)


# --- Reports ---
def daybook(db: Session, *, organization_id: int, start: date, end: date,
            branch_ids: list[int] | None, limit: int = 400) -> list[dict]:
    stmt = (
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines).joinedload(JournalLine.account))
        .where(
            JournalEntry.organization_id == organization_id,
            JournalEntry.entry_date >= start, JournalEntry.entry_date <= end,
        )
        .order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc())
        .limit(limit)
    )
    if branch_ids is not None:
        stmt = stmt.where(JournalEntry.branch_id.in_(branch_ids))
    out = []
    for e in db.scalars(stmt).unique().all():
        out.append({
            "id": e.id, "date": e.entry_date.isoformat(), "narration": e.narration,
            "ref_type": e.ref_type, "ref_id": e.ref_id,
            "lines": [
                {"account": l.account.name, "code": l.account.code,
                 "debit": float(l.debit), "credit": float(l.credit)}
                for l in e.lines
            ],
        })
    return out


def profit_and_loss(db: Session, *, organization_id: int, start: date, end: date,
                    branch_ids: list[int] | None) -> dict:
    def total_for(atype: AccountType) -> Decimal:
        stmt = (
            select(
                func.coalesce(func.sum(JournalLine.credit), 0),
                func.coalesce(func.sum(JournalLine.debit), 0),
            )
            .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
            .join(LedgerAccount, LedgerAccount.id == JournalLine.account_id)
            .where(
                JournalEntry.organization_id == organization_id,
                JournalEntry.entry_date >= start, JournalEntry.entry_date <= end,
                LedgerAccount.type == atype,
            )
        )
        if branch_ids is not None:
            stmt = stmt.where(JournalEntry.branch_id.in_(branch_ids))
        cr, dr = db.execute(stmt).one()
        return Decimal(cr), Decimal(dr)

    inc_cr, inc_dr = total_for(AccountType.income)
    exp_cr, exp_dr = total_for(AccountType.expense)
    income = inc_cr - inc_dr           # income normal balance is credit
    expense = exp_dr - exp_cr          # expense normal balance is debit
    return {
        "income": float(income),
        "expense": float(expense),
        "net_profit": float(income - expense),
        "start": start.isoformat(), "end": end.isoformat(),
    }
