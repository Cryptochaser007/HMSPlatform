"""Pydantic v2 schemas for Billing, Payments, and Receipts."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BillItemCreate(BaseModel):
    item_type: str
    description: str
    quantity: int = Field(1, ge=1)
    unit_price: Decimal = Field(..., ge=0)
    discount_percent: Decimal = Field(Decimal("0.00"), ge=0, le=100)
    tax_percent: Decimal = Field(Decimal("0.00"), ge=0, le=100)
    reference_id: str | None = None


class BillCreate(BaseModel):
    patient_id: str
    encounter_id: str | None = None
    bill_type: str
    items: list[BillItemCreate] = Field(..., min_length=1)
    notes: str | None = None
    discount_amount: Decimal = Field(Decimal("0.00"), ge=0)


class BillItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    item_type: str
    description: str
    quantity: int
    unit_price: Decimal
    discount_percent: Decimal
    tax_percent: Decimal
    total: Decimal


class BillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    bill_number: str
    encounter_id: str | None = None
    patient_id: str
    bill_type: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    payment_status: str
    notes: str | None = None
    items: list[BillItemResponse] = []
    created_at: datetime


class PaymentCreate(BaseModel):
    bill_id: str
    amount: Decimal = Field(..., gt=0)
    payment_method: str
    transaction_reference: str | None = None
    notes: str | None = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    bill_id: str
    amount: Decimal
    payment_method: str
    transaction_reference: str | None = None
    payment_date: datetime
    receipt_number: str
    notes: str | None = None


class BillSummary(BaseModel):
    total_bills: int
    total_amount: Decimal
    total_collected: Decimal
    total_pending: Decimal
    total_cancelled: Decimal
    period: str

