"""Enumerations shared across domain models."""
from __future__ import annotations

import enum


class ProductCategory(str, enum.Enum):
    fertilizer = "fertilizer"
    pesticide = "pesticide"
    seed = "seed"


class MovementType(str, enum.Enum):
    grn = "grn"                 # goods received (purchase)
    sale = "sale"               # sold to customer
    sale_return = "sale_return"
    purchase_return = "purchase_return"
    transfer_out = "transfer_out"
    transfer_in = "transfer_in"
    adjustment = "adjustment"   # stock-take correction


class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    finalized = "finalized"     # immutable once finalized
    cancelled = "cancelled"     # only via credit note flow


class PaymentMode(str, enum.Enum):
    cash = "cash"
    credit = "credit"
    upi = "upi"
    card = "card"


class TaxType(str, enum.Enum):
    intra = "intra"  # CGST + SGST
    inter = "inter"  # IGST


class PurchaseOrderStatus(str, enum.Enum):
    draft = "draft"
    placed = "placed"
    partially_received = "partially_received"
    received = "received"
    cancelled = "cancelled"


class TransferStatus(str, enum.Enum):
    requested = "requested"
    approved = "approved"
    dispatched = "dispatched"
    received = "received"
    rejected = "rejected"


class DocumentStatus(str, enum.Enum):
    draft = "draft"
    finalized = "finalized"
    cancelled = "cancelled"


class AccountType(str, enum.Enum):
    asset = "asset"
    liability = "liability"
    income = "income"
    expense = "expense"
    equity = "equity"
