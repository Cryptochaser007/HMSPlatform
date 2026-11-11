"""Pydantic v2 schemas for Laboratory Information System."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class LabTestCreate(BaseModel):
    name: str
    code: str
    category: str
    sample_type: str
    description: Optional[str] = None
    reference_ranges: Optional[dict] = None
    turnaround_hours: int = 24
    price: Decimal = Field(..., ge=0)


class LabTestUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    reference_ranges: Optional[dict] = None
    turnaround_hours: Optional[int] = None
    price: Optional[Decimal] = None
    is_active: Optional[bool] = None


class LabTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    code: str
    category: str
    sample_type: str
    description: Optional[str] = None
    reference_ranges: Optional[dict] = None
    turnaround_hours: int
    price: Decimal
    is_active: bool


class LabOrderCreate(BaseModel):
    encounter_id: str
    patient_id: str
    test_id: str
    priority: str = Field("ROUTINE", pattern="^(ROUTINE|URGENT|STAT)$")
    clinical_notes: Optional[str] = None


class LabOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    encounter_id: str
    patient_id: str
    ordered_by: str
    test_id: str
    status: str
    priority: str
    clinical_notes: Optional[str] = None
    sample_id: Optional[str] = None
    collected_at: Optional[datetime] = None
    created_at: datetime


class LabResultParam(BaseModel):
    parameter_name: str
    value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None


class LabResultCreate(BaseModel):
    order_id: str
    results: List[LabResultParam] = Field(..., min_length=1)


class LabResultVerify(BaseModel):
    remarks: Optional[str] = None


class LabResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    order_id: str
    parameter_name: str
    value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    is_abnormal: bool
    flag: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    remarks: Optional[str] = None

