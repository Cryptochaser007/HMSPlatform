"""Encounter model covering OPD, IPD, and Emergency visits."""

import enum

from sqlalchemy import Column, Date, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


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


class Encounter(Base):
    __tablename__ = "encounters"

    patient_id = Column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    encounter_type = Column(SAEnum(EncounterType, name="encounter_type_enum"), nullable=False)
    status = Column(
        SAEnum(EncounterStatus, name="encounter_status_enum"),
        nullable=False,
        default=EncounterStatus.SCHEDULED,
    )
    token_number = Column(Integer, nullable=True)
    appointment_time = Column(DateTime(timezone=True), nullable=True)
    check_in_time = Column(DateTime(timezone=True), nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    department = Column(String(100), nullable=False)
    room_number = Column(String(20), nullable=True)
    chief_complaint = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    follow_up_date = Column(Date, nullable=True)
    priority = Column(
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

