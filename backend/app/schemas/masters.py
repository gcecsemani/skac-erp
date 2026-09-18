from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ProductCategory


# --- Branch ---
class BranchBase(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=200)
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    state_code: str | None = None
    pincode: str | None = None
    phone: str | None = None
    gstin: str | None = None
    fco_license_no: str | None = None
    fco_license_valid_to: date | None = None
    pesticide_license_no: str | None = None
    pesticide_license_valid_to: date | None = None
    seed_license_no: str | None = None
    seed_license_valid_to: date | None = None
    printer_name: str | None = None
    printer_type: str = "thermal"
    thermal_paper_mm: int = 80


class BranchCreate(BranchBase):
    @field_validator("code", "name")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("This field is required")
        return v

    @field_validator("gstin")
    @classmethod
    def _gstin(cls, v: str | None) -> str | None:
        if not v:
            return None
        v = v.strip().upper()
        if len(v) != 15:
            raise ValueError("GSTIN must be 15 characters")
        return v

    @field_validator("pincode")
    @classmethod
    def _pincode(cls, v: str | None) -> str | None:
        if not v:
            return None
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) != 6:
            raise ValueError("Pincode must be 6 digits")
        return digits

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if not v:
            return None
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) not in (10, 11, 12):
            raise ValueError("Enter a valid phone number")
        return digits


class BranchOut(BranchBase):
    id: int
    organization_id: int

    model_config = {"from_attributes": True}


# --- Product ---
class ProductUnitIn(BaseModel):
    unit: str
    factor_to_base: Decimal


class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    category: ProductCategory
    barcode: str | None = None
    brand: str | None = None
    manufacturer: str | None = None
    hsn_code: str | None = None
    gst_rate: Decimal = Field(default=Decimal("0"), ge=0, le=28)
    base_unit: str = "unit"
    mrp: Decimal = Field(default=Decimal("0"), ge=0)
    purchase_price: Decimal = Field(default=Decimal("0"), ge=0)
    sale_price: Decimal = Field(default=Decimal("0"), ge=0)
    reorder_level: Decimal = Field(default=Decimal("0"), ge=0)
    # category-specific
    npk_n: Decimal | None = None
    npk_p: Decimal | None = None
    npk_k: Decimal | None = None
    toxicity_class: str | None = None
    germination_pct: Decimal | None = None
    seed_lot: str | None = None
    sell_loose: bool | None = None
    pack_size: Decimal | None = Field(default=None, gt=0)


class ProductCreate(ProductBase):
    units: list[ProductUnitIn] = []


class ProductOut(ProductBase):
    id: int
    organization_id: int
    is_active: bool
    is_favorite: bool = False
    stock_qty: Decimal | None = None
    packing: str | None = None
    sale_unit: str = "pcs"
    pack_size: Decimal = Decimal("1")
    loose_unit: str | None = None
    allows_loose: bool = False

    model_config = {"from_attributes": True}


# --- Customer ---
class CustomerBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    phone: str | None = None
    aadhaar_no: str | None = None
    village: str | None = None
    district: str | None = None
    land_holding_acres: Decimal | None = None
    gstin: str | None = None
    credit_allowed: bool = False
    credit_limit: Decimal = Decimal("0")


class CustomerWrite(CustomerBase):
    phone: str = Field(min_length=8, max_length=20)
    village: str = Field(min_length=1, max_length=120)
    district: str = Field(min_length=1, max_length=120)


class CustomerCreate(CustomerWrite):
    pass


class CustomerOut(CustomerBase):
    id: int
    organization_id: int
    outstanding_balance: Decimal

    model_config = {"from_attributes": True}


# --- Batch / GRN (stock receipt) ---
class StockReceiptIn(BaseModel):
    branch_id: int
    product_id: int
    batch_no: str = Field(min_length=1, max_length=80)
    quantity: Decimal = Field(gt=0)
    mfg_date: date | None = None
    expiry_date: date | None = None
    purchase_price: Decimal = Field(default=Decimal("0"), ge=0)


class StockAdjustIn(BaseModel):
    """Take qty off an incorrect receive; optionally load it onto the right product/branch."""

    branch_id: int
    product_id: int
    batch_id: int
    quantity: Decimal = Field(gt=0)
    reason: str = Field(min_length=3, max_length=255)
    correct_branch_id: int | None = None
    correct_product_id: int | None = None
    correct_batch_no: str | None = Field(default=None, max_length=80)
    correct_mfg_date: date | None = None
    correct_expiry_date: date | None = None
    correct_purchase_price: Decimal | None = Field(default=None, ge=0)


class StockDiscrepancyIn(BaseModel):
    branch_id: int
    product_id: int
    counted_qty: Decimal = Field(ge=0)
    note: str = Field(min_length=3, max_length=255)
    count_date: date | None = None


class StockDiscrepancyResolveIn(BaseModel):
    resolution: str = Field(min_length=3, max_length=255)
