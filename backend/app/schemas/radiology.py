"""Pydantic v2 schemas for Radiology orders and reports."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RadiologyOrderCreate(BaseModel):
    encounter_id: str
    patient_id: str
    modality: str
    body_part: str
    study_description: str | None = None
    priority: str = "ROUTINE"
    clinical_indication: str | None = None
    scheduled_at: datetime | None = None


class RadiologyOrderUpdate(BaseModel):
    status: str | None = None
    scheduled_at: datetime | None = None
    orthanc_study_id: str | None = None
    dicom_study_uid: str | None = None


class RadiologyOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    encounter_id: str
    patient_id: str
    ordered_by: str
    modality: str
    body_part: str
    study_description: str | None = None
    status: str
    priority: str
    clinical_indication: str | None = None
    scheduled_at: datetime | None = None
    accession_number: str | None = None
    created_at: datetime


class RadiologyReportCreate(BaseModel):
    order_id: str
    findings: str
    impression: str
    recommendation: str | None = None
    is_critical: bool = False
    template_used: str | None = None


class RadiologyReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    order_id: str
    radiologist_id: str
    findings: str
    impression: str
    recommendation: str | None = None
    is_critical: bool
    reported_at: datetime
    verified_by: str | None = None
    verified_at: datetime | None = None

