"""Patient model with encrypted PII fields and ABDM linkage."""

from sqlalchemy import Column, Date, Enum as SAEnum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.encryption import EncryptedType

import enum


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    UNDISCLOSED = "UNDISCLOSED"


class Patient(Base):
    __tablename__ = "patients"

    # ABDM fields
    abha_id = Column(String(50), unique=True, nullable=True, index=True)
    abha_address = Column(String(255), nullable=True)

    # PII — encrypted at rest
    first_name = Column(EncryptedType, nullable=False)
    last_name = Column(EncryptedType, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(SAEnum(Gender, name="gender_enum"), nullable=False)
    phone = Column(EncryptedType, nullable=False)
    email = Column(EncryptedType, nullable=True)
    address_line1 = Column(EncryptedType, nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)

    # Aadhaar — never store raw, only HMAC hash
    aadhaar_hash = Column(String(64), nullable=True)

    # Clinical
    blood_group = Column(String(10), nullable=True)
    allergies = Column(JSONB, nullable=True)

    # Emergency contact
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(EncryptedType, nullable=True)

    # Photo
    photo_url = Column(String(500), nullable=True)

    # Unique Hospital ID — auto-generated
    registration_number = Column(String(50), unique=True, nullable=False, index=True)

    # HMAC hash for searching encrypted name
    name_search_hash = Column(String(64), nullable=True, index=True)

    # Relationships
    encounters = relationship("Encounter", back_populates="patient", lazy="dynamic")
    consents = relationship("Consent", back_populates="patient", lazy="dynamic")
    bills = relationship("Bill", back_populates="patient", lazy="dynamic")
    admissions = relationship("Admission", back_populates="patient", lazy="dynamic")
    lab_orders = relationship("LabOrder", back_populates="patient", lazy="dynamic")
    radiology_orders = relationship("RadiologyOrder", back_populates="patient", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Patient UHID={self.registration_number}>"

