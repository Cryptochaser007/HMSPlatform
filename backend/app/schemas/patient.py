"""Pydantic v2 schemas for Patient Registration & Demographics."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: date
    gender: str = Field(..., pattern="^(MALE|FEMALE|OTHER|UNDISCLOSED)$")
    phone: str = Field(..., min_length=10, max_length=15)
    email: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = Field(None, pattern=r"^\d{6}$")
    blood_group: Optional[str] = Field(None, pattern=r"^(A|B|AB|O)[+-]$")
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    allergies: Optional[List[str]] = None


class PatientCreate(PatientBase):
    abha_id: Optional[str] = None
    aadhaar_number: Optional[str] = Field(None, min_length=12, max_length=12)


class PatientUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=255)
    last_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = None
    email: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    blood_group: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    allergies: Optional[List[str]] = None
    abha_id: Optional[str] = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    registration_number: str
    abha_id: Optional[str] = None
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    phone: str
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[List[str]] = None
    created_at: datetime


class PatientSearchParams(BaseModel):
    query: Optional[str] = None
    abha_id: Optional[str] = None
    phone: Optional[str] = None
    registration_number: Optional[str] = None


class PatientListResponse(BaseModel):
    items: List[PatientResponse]
    total: int
    page: int
    page_size: int

