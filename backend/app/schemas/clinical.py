"""Pydantic v2 schemas for Clinical Notes, Prescriptions, and Vitals."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class VitalsSchema(BaseModel):
    temperature: Optional[float] = Field(None, ge=30.0, le=45.0, description="°C")
    bp_systolic: Optional[int] = Field(None, ge=50, le=300)
    bp_diastolic: Optional[int] = Field(None, ge=30, le=200)
    pulse: Optional[int] = Field(None, ge=20, le=300, description="bpm")
    spo2: Optional[int] = Field(None, ge=50, le=100, description="%")
    respiratory_rate: Optional[int] = Field(None, ge=5, le=60, description="breaths/min")
    weight: Optional[float] = Field(None, ge=0.5, le=500, description="kg")
    height: Optional[float] = Field(None, ge=20, le=300, description="cm")
    bmi: Optional[float] = None


class ClinicalNoteCreate(BaseModel):
    encounter_id: str
    note_type: str = Field("SOAP", pattern="^(SOAP|PROGRESS|DISCHARGE_SUMMARY|PROCEDURE|NURSING)$")
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    vitals: Optional[VitalsSchema] = None
    icd_codes: Optional[List[str]] = None


class ClinicalNoteUpdate(BaseModel):
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    vitals: Optional[VitalsSchema] = None
    icd_codes: Optional[List[str]] = None


class ClinicalNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    encounter_id: str
    author_id: str
    note_type: str
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    vitals: Optional[dict] = None
    icd_codes: Optional[List[str]] = None
    is_amendment: bool
    amended_from_id: Optional[str] = None
    created_at: datetime


class PrescriptionItemCreate(BaseModel):
    drug_id: Optional[str] = None
    drug_name: str
    dosage: str
    frequency: str
    route: str = "Oral"
    duration_days: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    instructions: Optional[str] = None
    is_substitutable: bool = True


class PrescriptionCreate(BaseModel):
    encounter_id: str
    items: List[PrescriptionItemCreate] = Field(..., min_length=1)
    notes: Optional[str] = None


class PrescriptionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    drug_id: Optional[str] = None
    drug_name: str
    dosage: str
    frequency: str
    route: str
    duration_days: int
    quantity: int
    instructions: Optional[str] = None
    is_substitutable: bool


class PrescriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    encounter_id: str
    doctor_id: str
    status: str
    notes: Optional[str] = None
    items: List[PrescriptionItemResponse] = []
    created_at: datetime

