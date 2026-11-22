"""Ward, Bed, and Admission models for IPD management."""

import enum
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TenantOwned


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


class Ward(TenantOwned, Base):
    __tablename__ = "wards"

    name: Mapped[Any] = mapped_column(String(100), nullable=False)
    ward_type: Mapped[Any] = mapped_column(SAEnum(WardType, name="ward_type_enum"), nullable=False)
    floor: Mapped[Any] = mapped_column(Integer, nullable=False)
    total_beds: Mapped[Any] = mapped_column(Integer, nullable=False)
    department: Mapped[Any] = mapped_column(String(100), nullable=True)
    is_active: Mapped[Any] = mapped_column(Boolean, default=True, server_default="TRUE")

    # Relationships
    beds = relationship("Bed", back_populates="ward", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Ward {self.name} type={self.ward_type}>"


class Bed(TenantOwned, Base):
    __tablename__ = "beds"

    ward_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("wards.id"), nullable=False, index=True)
    bed_number: Mapped[Any] = mapped_column(String(20), nullable=False)
    status: Mapped[Any] = mapped_column(
        SAEnum(BedStatus, name="bed_status_enum"),
        nullable=False,
        default=BedStatus.AVAILABLE,
    )
    bed_type: Mapped[Any] = mapped_column(SAEnum(BedType, name="bed_type_enum"), nullable=False, default=BedType.REGULAR)
    daily_charge: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("500.00"))

    # Relationships
    ward = relationship("Ward", back_populates="beds")
    admissions = relationship("Admission", back_populates="bed")

    def __repr__(self) -> str:
        return f"<Bed {self.bed_number} status={self.status}>"


class Admission(TenantOwned, Base):
    __tablename__ = "admissions"

    encounter_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("encounters.id"), nullable=False, index=True)
    patient_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False, index=True)
    bed_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("beds.id"), nullable=False)
    admitted_by: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    admission_date: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_discharge: Mapped[Any] = mapped_column(Date, nullable=True)
    actual_discharge: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)
    discharge_type: Mapped[Any] = mapped_column(SAEnum(DischargeType, name="discharge_type_enum"), nullable=True)
    discharge_summary_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("clinical_notes.id"), nullable=True)
    status: Mapped[Any] = mapped_column(
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

