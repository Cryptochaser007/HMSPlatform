"""Pydantic v2 schemas for Encounters (OPD/IPD workflow)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class EncounterCreate(BaseModel):
    patient_id: str
    doctor_id: str
    encounter_type: str = Field(..., pattern="^(OPD|IPD|EMERGENCY)$")
    department: str
    appointment_time: datetime | None = None
    chief_complaint: str | None = None
    priority: str = Field("NORMAL", pattern="^(NORMAL|URGENT|EMERGENCY)$")


class EncounterUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    room_number: str | None = None
    follow_up_date: date | None = None
    chief_complaint: str | None = None


class EncounterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    patient_id: str
    doctor_id: str
    encounter_type: str
    status: str
    token_number: int | None = None
    appointment_time: datetime | None = None
    check_in_time: datetime | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    department: str
    room_number: str | None = None
    chief_complaint: str | None = None
    notes: str | None = None
    follow_up_date: date | None = None
    priority: str
    created_at: datetime


class QueueResponse(BaseModel):
    token_number: int
    patient_name: str
    patient_id: str
    doctor_name: str
    department: str
    status: str
    check_in_time: datetime | None = None
    estimated_wait_minutes: int | None = None


class AppointmentSlot(BaseModel):
    doctor_id: str
    doctor_name: str
    date: date
    available_slots: list[str]  # ["09:00", "09:30", "10:00", ...]


class EncounterListResponse(BaseModel):
    items: list[EncounterResponse]
    total: int
    page: int
    page_size: int

