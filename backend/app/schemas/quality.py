"""Pydantic v2 schemas for Quality Indicators, Measurements, and Incidents."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class QualityIndicatorCreate(BaseModel):
    name: str
    code: str
    category: str
    description: str
    numerator_description: str
    denominator_description: str
    target_value: Decimal
    unit: str
    frequency: str
    is_nabh_mandatory: bool = False


class QualityIndicatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    code: str
    category: str
    description: str
    numerator_description: str
    denominator_description: str
    target_value: Decimal
    unit: str
    frequency: str
    is_nabh_mandatory: bool
    is_active: bool


class QualityMeasurementCreate(BaseModel):
    indicator_id: str
    period_start: date
    period_end: date
    numerator_value: Decimal = Field(..., ge=0)
    denominator_value: Decimal = Field(..., gt=0)
    notes: str | None = None


class QualityMeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    indicator_id: str
    period_start: date
    period_end: date
    numerator_value: Decimal
    denominator_value: Decimal
    calculated_value: Decimal
    recorded_by: str
    notes: str | None = None
    created_at: datetime


class IncidentReportCreate(BaseModel):
    incident_type: str
    severity: str
    title: str
    description: str
    location: str
    incident_date: datetime
    patient_id: str | None = None


class IncidentReportUpdate(BaseModel):
    root_cause: str | None = None
    corrective_action: str | None = None
    status: str | None = None


class IncidentReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    incident_number: str
    incident_type: str
    severity: str
    title: str
    description: str
    location: str
    incident_date: datetime
    reported_by: str
    patient_id: str | None = None
    root_cause: str | None = None
    corrective_action: str | None = None
    status: str
    closed_by: str | None = None
    closed_at: datetime | None = None
    created_at: datetime


class NABHDashboard(BaseModel):
    total_indicators: int
    compliant: int
    non_compliant: int
    compliance_rate: float
    indicators: list[dict]

