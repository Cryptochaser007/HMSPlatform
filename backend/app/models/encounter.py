"""Encounter model covering OPD, IPD, and Emergency visits."""

import enum
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TenantOwned


class EncounterType(str, enum.Enum):
    OPD = "OPD"
    IPD = "IPD"
    EMERGENCY = "EMERGENCY"


class EncounterStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    CHECKED_IN = "CHECKED_IN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ADMITTED = "ADMITTED"
    DISCHARGED = "DISCHARGED"


class EncounterPriority(str, enum.Enum):
    NORMAL = "NORMAL"
    URGENT = "URGENT"
    EMERGENCY = "EMERGENCY"


class Encounter(TenantOwned, Base):
    __tablename__ = "encounters"

    patient_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    encounter_type: Mapped[Any] = mapped_column(SAEnum(EncounterType, name="encounter_type_enum"), nullable=False)
    status: Mapped[Any] = mapped_column(
        SAEnum(EncounterStatus, name="encounter_status_enum"),
        nullable=False,
        default=EncounterStatus.SCHEDULED,
    )
    token_number: Mapped[Any] = mapped_column(Integer, nullable=True)
    appointment_time: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)
    check_in_time: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)
    start_time: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)
    department: Mapped[Any] = mapped_column(String(100), nullable=False)
    room_number: Mapped[Any] = mapped_column(String(20), nullable=True)
    chief_complaint: Mapped[Any] = mapped_column(Text, nullable=True)
    notes: Mapped[Any] = mapped_column(Text, nullable=True)
    follow_up_date: Mapped[Any] = mapped_column(Date, nullable=True)
    priority: Mapped[Any] = mapped_column(
        SAEnum(EncounterPriority, name="encounter_priority_enum"),
        nullable=False,
        default=EncounterPriority.NORMAL,
    )

    # Relationships
    patient = relationship("Patient", back_populates="encounters")
    doctor = relationship("User", back_populates="encounters_as_doctor", foreign_keys=[doctor_id])
    clinical_notes = relationship("ClinicalNote", back_populates="encounter", lazy="dynamic")
    prescriptions = relationship("Prescription", back_populates="encounter", lazy="dynamic")
    lab_orders = relationship("LabOrder", back_populates="encounter", lazy="dynamic")
    radiology_orders = relationship("RadiologyOrder", back_populates="encounter", lazy="dynamic")
    bills = relationship("Bill", back_populates="encounter", lazy="dynamic")
    admission = relationship("Admission", back_populates="encounter", uselist=False)

    def __repr__(self) -> str:
        return f"<Encounter {self.id} type={self.encounter_type} status={self.status}>"

