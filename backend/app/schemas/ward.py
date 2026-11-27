"""Pydantic v2 schemas for Ward, Bed, and Admission management."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.ward import WardType


class WardCreate(BaseModel):
    name: str
    ward_type: str
    floor: int
    total_beds: int = Field(..., ge=1)
    department: str | None = None


class SetupWard(WardCreate):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    ward_type: WardType
    floor: int = Field(ge=-10, le=100)
    total_beds: int = Field(ge=1, le=500)
    department: str | None = Field(default=None, max_length=100)


class WardSetupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["INPATIENT", "OPD_ONLY"]
    wards: list[SetupWard] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_inventory(self) -> "WardSetupRequest":
        if self.mode == "OPD_ONLY" and self.wards:
            raise ValueError("An OPD-only clinic cannot include inpatient wards")
        if self.mode == "INPATIENT" and not self.wards:
            raise ValueError("Add at least one ward")
        if len({ward.name.casefold() for ward in self.wards}) != len(self.wards):
            raise ValueError("Ward names must be distinct")
        if sum(ward.total_beds for ward in self.wards) > 1000:
            raise ValueError("Setup supports at most 1000 beds")
        return self


class WardSetupStatus(BaseModel):
    status: Literal["pending", "skipped", "configured"]


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


class BedInventoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    bed_number: str
    status: str


class WardInventory(BaseModel):
    id: str
    name: str
    ward_type: str
    floor: int
    beds: list[BedInventoryItem]


class BedOccupancyDashboard(BaseModel):
    total_beds: int
    occupied: int
    available: int
    maintenance: int
    reserved: int
    occupancy_rate: float
    by_ward_type: list[dict]
    wards: list[WardInventory]

