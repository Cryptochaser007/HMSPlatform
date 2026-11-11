"""Pydantic v2 schemas for Pharmacy, Drug Inventory, and Dispensing."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DrugCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    generic_name: str
    brand_name: Optional[str] = None
    drug_type: str
    strength: str
    manufacturer: Optional[str] = None
    hsn_code: Optional[str] = None
    schedule: Optional[str] = None


class DrugUpdate(BaseModel):
    name: Optional[str] = None
    generic_name: Optional[str] = None
    brand_name: Optional[str] = None
    drug_type: Optional[str] = None
    strength: Optional[str] = None
    manufacturer: Optional[str] = None
    is_active: Optional[bool] = None


class DrugResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    generic_name: str
    brand_name: Optional[str] = None
    drug_type: str
    strength: str
    manufacturer: Optional[str] = None
    hsn_code: Optional[str] = None
    schedule: Optional[str] = None
    is_active: bool
    created_at: datetime


class DrugInventoryCreate(BaseModel):
    drug_id: str
    batch_number: str
    expiry_date: date
    quantity_in_stock: int = Field(..., ge=0)
    unit_price: Decimal = Field(..., ge=0)
    mrp: Decimal = Field(..., ge=0)
    gst_percentage: Decimal = Field(default=Decimal("12.00"), ge=0, le=100)
    reorder_level: int = Field(default=10, ge=0)
    location: Optional[str] = None


class DrugInventoryUpdate(BaseModel):
    quantity_in_stock: Optional[int] = None
    unit_price: Optional[Decimal] = None
    mrp: Optional[Decimal] = None
    reorder_level: Optional[int] = None
    location: Optional[str] = None


class DrugInventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    drug_id: str
    batch_number: str
    expiry_date: date
    quantity_in_stock: int
    unit_price: Decimal
    mrp: Decimal
    gst_percentage: Decimal
    reorder_level: int
    location: Optional[str] = None
    created_at: datetime


class DispensingCreate(BaseModel):
    prescription_item_id: str
    drug_inventory_id: str
    quantity: int = Field(..., ge=1)
    notes: Optional[str] = None


class DispensingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    prescription_item_id: str
    drug_inventory_id: str
    patient_id: str
    dispensed_by: str
    quantity_dispensed: int
    dispensed_at: datetime
    notes: Optional[str] = None


class StockAlertResponse(BaseModel):
    drug_id: str
    drug_name: str
    batch_number: str
    quantity_in_stock: int
    reorder_level: int


class DrugSearchParams(BaseModel):
    name: Optional[str] = None
    generic_name: Optional[str] = None
    drug_type: Optional[str] = None

