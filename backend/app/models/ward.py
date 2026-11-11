"""Ward, Bed, and Admission models for IPD management."""

import enum
from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class WardType(str, enum.Enum):
    GENERAL = "GENERAL"
    SEMI_PRIVATE = "SEMI_PRIVATE"
    PRIVATE = "PRIVATE"
    ICU = "ICU"
    NICU = "NICU"
    PICU = "PICU"
    ISOLATION = "ISOLATION"
    EMERGENCY = "EMERGENCY"


class BedStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"
    RESERVED = "RESERVED"


class BedType(str, enum.Enum):
    REGULAR = "REGULAR"
    ELECTRIC = "ELECTRIC"
    ICU = "ICU"
    VENTILATOR = "VENTILATOR"
    CRADLE = "CRADLE"


class DischargeType(str, enum.Enum):
    NORMAL = "NORMAL"
    AGAINST_ADVICE = "AGAINST_ADVICE"
    ABSCONDED = "ABSCONDED"
    DEATH = "DEATH"
    TRANSFER = "TRANSFER"


class AdmissionStatus(str, enum.Enum):
    ADMITTED = "ADMITTED"
    DISCHARGED = "DISCHARGED"
    TRANSFERRED = "TRANSFERRED"


class Ward(Base):
    __tablename__ = "wards"

    name = Column(String(100), nullable=False)
    ward_type = Column(SAEnum(WardType, name="ward_type_enum"), nullable=False)
    floor = Column(Integer, nullable=False)
    total_beds = Column(Integer, nullable=False)
    department = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, server_default="TRUE")

    # Relationships
    beds = relationship("Bed", back_populates="ward", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Ward {self.name} type={self.ward_type}>"


class Bed(Base):
    __tablename__ = "beds"

    ward_id = Column(UUID(as_uuid=False), ForeignKey("wards.id"), nullable=False, index=True)
    bed_number = Column(String(20), nullable=False)
    status = Column(
        SAEnum(BedStatus, name="bed_status_enum"),
        nullable=False,
        default=BedStatus.AVAILABLE,
    )
    bed_type = Column(SAEnum(BedType, name="bed_type_enum"), nullable=False, default=BedType.REGULAR)
    daily_charge = Column(Numeric(10, 2), nullable=False, default=Decimal("500.00"))

    # Relationships
    ward = relationship("Ward", back_populates="beds")
    admissions = relationship("Admission", back_populates="bed")

    def __repr__(self) -> str:
        return f"<Bed {self.bed_number} status={self.status}>"


class Admission(Base):
    __tablename__ = "admissions"

    encounter_id = Column(UUID(as_uuid=False), ForeignKey("encounters.id"), nullable=False, index=True)
    patient_id = Column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False, index=True)
    bed_id = Column(UUID(as_uuid=False), ForeignKey("beds.id"), nullable=False)
    admitted_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    admission_date = Column(DateTime(timezone=True), nullable=False)
    expected_discharge = Column(Date, nullable=True)
    actual_discharge = Column(DateTime(timezone=True), nullable=True)
    discharge_type = Column(SAEnum(DischargeType, name="discharge_type_enum"), nullable=True)
    discharge_summary_id = Column(UUID(as_uuid=False), ForeignKey("clinical_notes.id"), nullable=True)
    status = Column(
        SAEnum(AdmissionStatus, name="admission_status_enum"),
        nullable=False,
        default=AdmissionStatus.ADMITTED,
    )

    # Relationships
    encounter = relationship("Encounter", back_populates="admission")
    patient = relationship("Patient", back_populates="admissions")
    bed = relationship("Bed", back_populates="admissions")
    admitting_user = relationship("User", foreign_keys=[admitted_by], backref="admissions_created")
    discharge_summary = relationship("ClinicalNote", foreign_keys=[discharge_summary_id])

    def __repr__(self) -> str:
        return f"<Admission patient={self.patient_id} status={self.status}>"

