"""Pydantic v2 schemas for Patient Registration & Demographics."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: date
    gender: str = Field(..., pattern="^(MALE|FEMALE|OTHER|UNDISCLOSED)$")
    phone: str = Field(..., min_length=10, max_length=15)
    email: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = Field(None, pattern=r"^\d{6}$")
    blood_group: str | None = Field(None, pattern=r"^(A|B|AB|O)[+-]$")
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    allergies: list[str] | None = None


class PatientCreate(PatientBase):
    abha_id: str | None = None
    abha_address: str | None = None
    aadhaar_number: str | None = Field(None, min_length=12, max_length=12)


class PatientUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=255)
    last_name: str | None = Field(None, min_length=1, max_length=255)
    phone: str | None = None
    email: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    blood_group: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    allergies: list[str] | None = None
    abha_id: str | None = None
    abha_address: str | None = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    registration_number: str
    abha_id: str | None = None
    abha_address: str | None = None
    abha_kyc_status: str | None = "UNVERIFIED"
    abha_verified_at: datetime | None = None
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    phone: str
    email: str | None = None
    city: str | None = None
    state: str | None = None
    blood_group: str | None = None
    allergies: list[str] | None = None
    created_at: datetime


class PatientSearchParams(BaseModel):
    query: str | None = None
    abha_id: str | None = None
    phone: str | None = None
    registration_number: str | None = None


class PatientListResponse(BaseModel):
    items: list[PatientResponse]
    total: int
    page: int
    page_size: int

