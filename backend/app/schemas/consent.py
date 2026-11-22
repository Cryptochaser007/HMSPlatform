"""Pydantic v2 schemas for Consent management (DPDP Act)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConsentCreate(BaseModel):
    consent_type: str
    purpose: str
    data_categories: list[str] | None = None
    granted_to: str = "Self Hospital"
    expires_at: datetime | None = None


class ConsentRevoke(BaseModel):
    reason: str


class ConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    patient_id: str
    consent_type: str
    purpose: str
    data_categories: list[str] | None = None
    granted_to: str
    status: str
    granted_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    revoked_reason: str | None = None
    consent_artifact_id: str | None = None


class ConsentListResponse(BaseModel):
    items: list[ConsentResponse]
    total: int
    page: int
    page_size: int

