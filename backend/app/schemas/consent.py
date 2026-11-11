"""Pydantic v2 schemas for Consent management (DPDP Act)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ConsentCreate(BaseModel):
    consent_type: str
    purpose: str
    data_categories: Optional[List[str]] = None
    granted_to: str = "Self Hospital"
    expires_at: Optional[datetime] = None


class ConsentRevoke(BaseModel):
    reason: str


class ConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    patient_id: str
    consent_type: str
    purpose: str
    data_categories: Optional[List[str]] = None
    granted_to: str
    status: str
    granted_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None
    consent_artifact_id: Optional[str] = None


class ConsentListResponse(BaseModel):
    items: List[ConsentResponse]
    total: int
    page: int
    page_size: int

