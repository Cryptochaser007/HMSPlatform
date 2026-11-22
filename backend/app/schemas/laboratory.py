"""Pydantic v2 schemas for Laboratory Information System."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class LabTestCreate(BaseModel):
    name: str
    code: str
    category: str
    sample_type: str
    description: str | None = None
    reference_ranges: dict | None = None
    turnaround_hours: int = 24
    price: Decimal = Field(..., ge=0)


class LabTestUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    reference_ranges: dict | None = None
    turnaround_hours: int | None = None
    price: Decimal | None = None
    is_active: bool | None = None


class LabTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    code: str
    category: str
    sample_type: str
    description: str | None = None
    reference_ranges: dict | None = None
    turnaround_hours: int
    price: Decimal
    is_active: bool


class LabOrderCreate(BaseModel):
    encounter_id: str
    patient_id: str
    test_id: str
    priority: str = Field("ROUTINE", pattern="^(ROUTINE|URGENT|STAT)$")
    clinical_notes: str | None = None


class LabOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    encounter_id: str
    patient_id: str
    ordered_by: str
    test_id: str
    status: str
    priority: str
    clinical_notes: str | None = None
    sample_id: str | None = None
    collected_at: datetime | None = None
    created_at: datetime


class LabResultParam(BaseModel):
    parameter_name: str
    value: str
    unit: str | None = None
    reference_range: str | None = None


class LabResultCreate(BaseModel):
    order_id: str
    results: list[LabResultParam] = Field(..., min_length=1)


class LabResultVerify(BaseModel):
    remarks: str | None = None


class LabResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    order_id: str
    parameter_name: str
    value: str
    unit: str | None = None
    reference_range: str | None = None
    is_abnormal: bool
    flag: str | None = None
    verified_by: str | None = None
    verified_at: datetime | None = None
    remarks: str | None = None

