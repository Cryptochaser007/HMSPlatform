"""Pydantic v2 schemas for Billing, Payments, and Receipts."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BillItemCreate(BaseModel):
    item_type: str
    description: str
    quantity: int = Field(1, ge=1)
    unit_price: Decimal = Field(..., ge=0)
    discount_percent: Decimal = Field(Decimal("0.00"), ge=0, le=100)
    tax_percent: Decimal = Field(Decimal("0.00"), ge=0, le=100)
    reference_id: Optional[str] = None


class BillCreate(BaseModel):
    patient_id: str
    encounter_id: Optional[str] = None
    bill_type: str
    items: List[BillItemCreate] = Field(..., min_length=1)
    notes: Optional[str] = None
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
    encounter_id: Optional[str] = None
    patient_id: str
    bill_type: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    payment_status: str
    notes: Optional[str] = None
    items: List[BillItemResponse] = []
    created_at: datetime


class PaymentCreate(BaseModel):
    bill_id: str
    amount: Decimal = Field(..., gt=0)
    payment_method: str
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    bill_id: str
    amount: Decimal
    payment_method: str
    transaction_reference: Optional[str] = None
    payment_date: datetime
    receipt_number: str
    notes: Optional[str] = None


class BillSummary(BaseModel):
    total_bills: int
    total_amount: Decimal
    total_collected: Decimal
    total_pending: Decimal
    total_cancelled: Decimal
    period: str

