"""Pydantic v2 schemas for Ward, Bed, and Admission management."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class WardCreate(BaseModel):
    name: str
    ward_type: str
    floor: int
    total_beds: int = Field(..., ge=1)
    department: str | None = None


class WardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    ward_type: str
    floor: int
    total_beds: int
    department: str | None = None
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
    expected_discharge: date | None = None


class DischargeCreate(BaseModel):
    discharge_type: str
    discharge_summary: str | None = None


class AdmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    encounter_id: str
    patient_id: str
    bed_id: str
    admitted_by: str
    admission_date: datetime
    expected_discharge: date | None = None
    actual_discharge: datetime | None = None
    discharge_type: str | None = None
    status: str
    created_at: datetime


class BedOccupancyDashboard(BaseModel):
    total_beds: int
    occupied: int
    available: int
    maintenance: int
    reserved: int
    occupancy_rate: float
    by_ward_type: list[dict]

