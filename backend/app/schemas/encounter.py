"""Pydantic v2 schemas for Encounters (OPD/IPD workflow)."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EncounterCreate(BaseModel):
    patient_id: str
    doctor_id: str
    encounter_type: str = Field(..., pattern="^(OPD|IPD|EMERGENCY)$")
    department: str
    appointment_time: Optional[datetime] = None
    chief_complaint: Optional[str] = None
    priority: str = Field("NORMAL", pattern="^(NORMAL|URGENT|EMERGENCY)$")


class EncounterUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    room_number: Optional[str] = None
    follow_up_date: Optional[date] = None
    chief_complaint: Optional[str] = None


class EncounterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    patient_id: str
    doctor_id: str
    encounter_type: str
    status: str
    token_number: Optional[int] = None
    appointment_time: Optional[datetime] = None
    check_in_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    department: str
    room_number: Optional[str] = None
    chief_complaint: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[date] = None
    priority: str
    created_at: datetime


class QueueResponse(BaseModel):
    token_number: int
    patient_name: str
    patient_id: str
    doctor_name: str
    department: str
    status: str
    check_in_time: Optional[datetime] = None
    estimated_wait_minutes: Optional[int] = None


class AppointmentSlot(BaseModel):
    doctor_id: str
    doctor_name: str
    date: date
    available_slots: List[str]  # ["09:00", "09:30", "10:00", ...]


class EncounterListResponse(BaseModel):
    items: List[EncounterResponse]
    total: int
    page: int
    page_size: int

