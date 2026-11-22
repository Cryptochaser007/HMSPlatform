"""Pydantic v2 schemas for Clinical Notes, Prescriptions, and Vitals."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VitalsSchema(BaseModel):
    temperature: float | None = Field(None, ge=30.0, le=45.0, description="°C")
    bp_systolic: int | None = Field(None, ge=50, le=300)
    bp_diastolic: int | None = Field(None, ge=30, le=200)
    pulse: int | None = Field(None, ge=20, le=300, description="bpm")
    spo2: int | None = Field(None, ge=50, le=100, description="%")
    respiratory_rate: int | None = Field(None, ge=5, le=60, description="breaths/min")
    weight: float | None = Field(None, ge=0.5, le=500, description="kg")
    height: float | None = Field(None, ge=20, le=300, description="cm")
    bmi: float | None = None


class ClinicalNoteCreate(BaseModel):
    encounter_id: str
    note_type: str = Field("SOAP", pattern="^(SOAP|PROGRESS|DISCHARGE_SUMMARY|PROCEDURE|NURSING)$")
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None
    vitals: VitalsSchema | None = None
    icd_codes: list[str] | None = None


class ClinicalNoteUpdate(BaseModel):
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None
    vitals: VitalsSchema | None = None
    icd_codes: list[str] | None = None


class ClinicalNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    encounter_id: str
    author_id: str
    note_type: str
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None
    vitals: dict | None = None
    icd_codes: list[str] | None = None
    is_amendment: bool
    amended_from_id: str | None = None
    created_at: datetime


class PrescriptionItemCreate(BaseModel):
    drug_id: str | None = None
    drug_name: str
    dosage: str
    frequency: str
    route: str = "Oral"
    duration_days: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    instructions: str | None = None
    is_substitutable: bool = True


class PrescriptionCreate(BaseModel):
    encounter_id: str
    items: list[PrescriptionItemCreate] = Field(..., min_length=1)
    notes: str | None = None


class PrescriptionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    drug_id: str | None = None
    drug_name: str
    dosage: str
    frequency: str
    route: str
    duration_days: int
    quantity: int
    instructions: str | None = None
    is_substitutable: bool


class PrescriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    encounter_id: str
    doctor_id: str
    status: str
    notes: str | None = None
    items: list[PrescriptionItemResponse] = []
    created_at: datetime

