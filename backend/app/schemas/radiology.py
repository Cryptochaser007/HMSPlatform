"""Pydantic v2 schemas for Radiology orders and reports."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RadiologyOrderCreate(BaseModel):
    encounter_id: str
    patient_id: str
    modality: str
    body_part: str
    study_description: Optional[str] = None
    priority: str = "ROUTINE"
    clinical_indication: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class RadiologyOrderUpdate(BaseModel):
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    orthanc_study_id: Optional[str] = None
    dicom_study_uid: Optional[str] = None


class RadiologyOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    encounter_id: str
    patient_id: str
    ordered_by: str
    modality: str
    body_part: str
    study_description: Optional[str] = None
    status: str
    priority: str
    clinical_indication: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    accession_number: Optional[str] = None
    created_at: datetime


class RadiologyReportCreate(BaseModel):
    order_id: str
    findings: str
    impression: str
    recommendation: Optional[str] = None
    is_critical: bool = False
    template_used: Optional[str] = None


class RadiologyReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    order_id: str
    radiologist_id: str
    findings: str
    impression: str
    recommendation: Optional[str] = None
    is_critical: bool
    reported_at: datetime
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None

