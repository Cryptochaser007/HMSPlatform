"""Patient model with encrypted PII fields and ABDM linkage."""

import enum
from typing import Any

from sqlalchemy import Date, DateTime, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TenantOwned
from app.core.encryption import EncryptedType


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    UNDISCLOSED = "UNDISCLOSED"


class Patient(TenantOwned, Base):
    __tablename__ = "patients"

    # ABDM fields
    abha_id: Mapped[Any] = mapped_column(String(50), unique=True, nullable=True, index=True)
    abha_address: Mapped[Any] = mapped_column(String(255), nullable=True, index=True)
    abha_kyc_status: Mapped[Any] = mapped_column(String(30), nullable=False, default="UNVERIFIED")
    abha_verified_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)

    # PII — encrypted at rest
    first_name: Mapped[Any] = mapped_column(EncryptedType, nullable=False)
    last_name: Mapped[Any] = mapped_column(EncryptedType, nullable=False)
    date_of_birth: Mapped[Any] = mapped_column(Date, nullable=False)
    gender: Mapped[Any] = mapped_column(SAEnum(Gender, name="gender_enum"), nullable=False)
    phone: Mapped[Any] = mapped_column(EncryptedType, nullable=False)
    email: Mapped[Any] = mapped_column(EncryptedType, nullable=True)
    address_line1: Mapped[Any] = mapped_column(EncryptedType, nullable=True)
    address_line2: Mapped[Any] = mapped_column(String(255), nullable=True)
    city: Mapped[Any] = mapped_column(String(100), nullable=True)
    state: Mapped[Any] = mapped_column(String(100), nullable=True)
    pincode: Mapped[Any] = mapped_column(String(10), nullable=True)

    # Aadhaar — never store raw, only HMAC hash
    aadhaar_hash: Mapped[Any] = mapped_column(String(64), nullable=True)

    # Clinical
    blood_group: Mapped[Any] = mapped_column(String(10), nullable=True)
    allergies: Mapped[Any] = mapped_column(JSONB, nullable=True)

    # Emergency contact
    emergency_contact_name: Mapped[Any] = mapped_column(String(255), nullable=True)
    emergency_contact_phone: Mapped[Any] = mapped_column(EncryptedType, nullable=True)

    # Photo
    photo_url: Mapped[Any] = mapped_column(String(500), nullable=True)

    # Unique Hospital ID — auto-generated
    registration_number: Mapped[Any] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # HMAC hash for searching encrypted name
    name_search_hash: Mapped[Any] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    encounters = relationship("Encounter", back_populates="patient", lazy="dynamic")
    consents = relationship("Consent", back_populates="patient", lazy="dynamic")
    bills = relationship("Bill", back_populates="patient", lazy="dynamic")
    admissions = relationship("Admission", back_populates="patient", lazy="dynamic")
    lab_orders = relationship("LabOrder", back_populates="patient", lazy="dynamic")
    radiology_orders = relationship("RadiologyOrder", back_populates="patient", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Patient UHID={self.registration_number}>"

