from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import InvoiceStatus, PaymentMode, TaxType


class InvoiceLineIn(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0)
    unit: str | None = None


class InvoiceCreate(BaseModel):
    branch_id: int
    customer_id: int | None = None
    payment_mode: PaymentMode = PaymentMode.cash
    tax_type: TaxType = TaxType.intra
    invoice_date: date | None = None
    amount_paid: Decimal = Field(default=Decimal("0"), ge=0)
    client_uuid: str | None = None
    lines: list[InvoiceLineIn] = Field(min_length=1)


class InvoiceItemOut(BaseModel):
    product_id: int
    product_name: str
    hsn_code: str | None
    batch_no: str | None
    mfg_date: date | None
    expiry_date: date | None
    unit: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal
    gst_rate: Decimal
    taxable_value: Decimal
    tax_amount: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class InvoiceOut(BaseModel):
    id: int
    organization_id: int
    branch_id: int
    branch_name: str | None = None
    branch_code: str | None = None
    branch_phone: str | None = None
    branch_gstin: str | None = None
    branch_address: str | None = None
    branch_fco_license: str | None = None
    branch_pesticide_license: str | None = None
    branch_seed_license: str | None = None
    organization_name: str | None = None
    thermal_paper_mm: int = 80
    printer_name: str | None = None
    printer_type: str | None = None
    customer_id: int | None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_village: str | None = None
    client_uuid: str | None
    invoice_no: str | None
    invoice_date: date
    status: InvoiceStatus
    tax_type: TaxType
    payment_mode: PaymentMode
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    grand_total: Decimal
    amount_paid: Decimal
    finalized_at: datetime | None
    items: list[InvoiceItemOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SyncInvoicesRequest(BaseModel):
    """Offline outbox: a batch of client-generated invoices to reconcile."""

    invoices: list[InvoiceCreate]


class AskRequest(BaseModel):
    question: str
    branch_id: int | None = None


class ReportColumn(BaseModel):
    key: str
    label: str
    money: bool = False
    num: bool = False


class ReportPayload(BaseModel):
    title: str
    columns: list[ReportColumn]
    rows: list[dict[str, Any]]
    row_count: int = 0


class AskResponse(BaseModel):
    question: str
    tool: str
    arguments: dict
    data: dict
    answer: str
    report: ReportPayload | None = None
