"""Pydantic v2 schemas for Quality Indicators, Measurements, and Incidents."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

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
    notes: Optional[str] = None


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
    notes: Optional[str] = None
    created_at: datetime


class IncidentReportCreate(BaseModel):
    incident_type: str
    severity: str
    title: str
    description: str
    location: str
    incident_date: datetime
    patient_id: Optional[str] = None


class IncidentReportUpdate(BaseModel):
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    status: Optional[str] = None


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
    patient_id: Optional[str] = None
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    status: str
    closed_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    created_at: datetime


class NABHDashboard(BaseModel):
    total_indicators: int
    compliant: int
    non_compliant: int
    compliance_rate: float
    indicators: List[dict]

