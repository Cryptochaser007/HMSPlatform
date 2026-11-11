"""Pydantic v2 schemas for Ward, Bed, and Admission management."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WardCreate(BaseModel):
    name: str
    ward_type: str
    floor: int
    total_beds: int = Field(..., ge=1)
    department: Optional[str] = None


class WardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    ward_type: str
    floor: int
    total_beds: int
    department: Optional[str] = None
    is_active: bool
    created_at: datetime


class BedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    ward_id: str
    bed_number: str
    status: str
    bed_type: str
    daily_charge: Decimal


class BedStatusUpdate(BaseModel):
    status: str


class AdmissionCreate(BaseModel):
    encounter_id: str
    patient_id: str
    bed_id: str
    expected_discharge: Optional[date] = None


class DischargeCreate(BaseModel):
    discharge_type: str
    discharge_summary: Optional[str] = None


class AdmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    encounter_id: str
    patient_id: str
    bed_id: str
    admitted_by: str
    admission_date: datetime
    expected_discharge: Optional[date] = None
    actual_discharge: Optional[datetime] = None
    discharge_type: Optional[str] = None
    status: str
    created_at: datetime


class BedOccupancyDashboard(BaseModel):
    total_beds: int
    occupied: int
    available: int
    maintenance: int
    reserved: int
    occupancy_rate: float
    by_ward_type: List[dict]

