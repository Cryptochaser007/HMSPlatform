"""Clinical models: ClinicalNote, Prescription, PrescriptionItem."""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class NoteType(str, enum.Enum):
    SOAP = "SOAP"
    PROGRESS = "PROGRESS"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    PROCEDURE = "PROCEDURE"
    NURSING = "NURSING"


class PrescriptionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SIGNED = "SIGNED"
    DISPENSED = "DISPENSED"
    PARTIALLY_DISPENSED = "PARTIALLY_DISPENSED"
    CANCELLED = "CANCELLED"


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    encounter_id = Column(UUID(as_uuid=False), ForeignKey("encounters.id"), nullable=False, index=True)
    author_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    note_type = Column(SAEnum(NoteType, name="note_type_enum"), nullable=False, default=NoteType.SOAP)
    subjective = Column(Text, nullable=True)
    objective = Column(Text, nullable=True)
    assessment = Column(Text, nullable=True)
    plan = Column(Text, nullable=True)
    vitals = Column(JSONB, nullable=True)  # {temp, bp_systolic, bp_diastolic, pulse, spo2, resp_rate, weight, height, bmi}
    icd_codes = Column(JSONB, nullable=True)  # ["I10", "E11.9"]
    attachments = Column(JSONB, nullable=True)
    is_amendment = Column(Boolean, default=False, server_default="FALSE")
    amended_from_id = Column(UUID(as_uuid=False), ForeignKey("clinical_notes.id"), nullable=True)
    digital_signature = Column(String(512), nullable=True)

    # Relationships
    encounter = relationship("Encounter", back_populates="clinical_notes")
    author = relationship("User", back_populates="clinical_notes", foreign_keys=[author_id])
    amendments = relationship("ClinicalNote", backref="amended_from", remote_side="ClinicalNote.id")

    def __repr__(self) -> str:
        return f"<ClinicalNote {self.id} type={self.note_type}>"


class Prescription(Base):
    __tablename__ = "prescriptions"

    encounter_id = Column(UUID(as_uuid=False), ForeignKey("encounters.id"), nullable=False, index=True)
    doctor_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    status = Column(
        SAEnum(PrescriptionStatus, name="prescription_status_enum"),
        nullable=False,
        default=PrescriptionStatus.DRAFT,
    )
    notes = Column(Text, nullable=True)

    # Relationships
    encounter = relationship("Encounter", back_populates="prescriptions")
    doctor = relationship("User", back_populates="prescriptions", foreign_keys=[doctor_id])
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Prescription {self.id} status={self.status}>"


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    prescription_id = Column(UUID(as_uuid=False), ForeignKey("prescriptions.id"), nullable=False, index=True)
    drug_id = Column(UUID(as_uuid=False), ForeignKey("drugs.id"), nullable=True)
    drug_name = Column(String(255), nullable=False)  # Denormalized for display
    dosage = Column(String(100), nullable=False)  # e.g., "500mg"
    frequency = Column(String(100), nullable=False)  # e.g., "TID", "BD"
    route = Column(String(50), nullable=False, default="Oral")  # Oral, IV, IM, SC, etc.
    duration_days = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    instructions = Column(Text, nullable=True)
    is_substitutable = Column(Boolean, default=True, server_default="TRUE")

    # Relationships
    prescription = relationship("Prescription", back_populates="items")
    drug = relationship("Drug", backref="prescription_items")

    def __repr__(self) -> str:
        return f"<PrescriptionItem {self.drug_name} {self.dosage}>"

