"""Clinical models: ClinicalNote, Prescription, PrescriptionItem."""

import enum
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TenantOwned


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


class ClinicalNote(TenantOwned, Base):
    __tablename__ = "clinical_notes"

    encounter_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("encounters.id"), nullable=False, index=True)
    author_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    note_type: Mapped[Any] = mapped_column(SAEnum(NoteType, name="note_type_enum"), nullable=False, default=NoteType.SOAP)
    subjective: Mapped[Any] = mapped_column(Text, nullable=True)
    objective: Mapped[Any] = mapped_column(Text, nullable=True)
    assessment: Mapped[Any] = mapped_column(Text, nullable=True)
    plan: Mapped[Any] = mapped_column(Text, nullable=True)
    vitals: Mapped[Any] = mapped_column(JSONB, nullable=True)  # {temp, bp_systolic, bp_diastolic, pulse, spo2, resp_rate, weight, height, bmi}
    icd_codes: Mapped[Any] = mapped_column(JSONB, nullable=True)  # ["I10", "E11.9"]
    attachments: Mapped[Any] = mapped_column(JSONB, nullable=True)
    is_amendment: Mapped[Any] = mapped_column(Boolean, default=False, server_default="FALSE")
    amended_from_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("clinical_notes.id"), nullable=True)
    digital_signature: Mapped[Any] = mapped_column(String(512), nullable=True)

    # Relationships
    encounter = relationship("Encounter", back_populates="clinical_notes")
    author = relationship("User", back_populates="clinical_notes", foreign_keys=[author_id])
    amendments = relationship("ClinicalNote", backref="amended_from", remote_side="ClinicalNote.id")

    def __repr__(self) -> str:
        return f"<ClinicalNote {self.id} type={self.note_type}>"


class Prescription(TenantOwned, Base):
    __tablename__ = "prescriptions"

    encounter_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("encounters.id"), nullable=False, index=True)
    doctor_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    status: Mapped[Any] = mapped_column(
        SAEnum(PrescriptionStatus, name="prescription_status_enum"),
        nullable=False,
        default=PrescriptionStatus.DRAFT,
    )
    notes: Mapped[Any] = mapped_column(Text, nullable=True)

    # Relationships
    encounter = relationship("Encounter", back_populates="prescriptions")
    doctor = relationship("User", back_populates="prescriptions", foreign_keys=[doctor_id])
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Prescription {self.id} status={self.status}>"


class PrescriptionItem(TenantOwned, Base):
    __tablename__ = "prescription_items"

    prescription_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("prescriptions.id"), nullable=False, index=True)
    drug_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("drugs.id"), nullable=True)
    drug_name: Mapped[Any] = mapped_column(String(255), nullable=False)  # Denormalized for display
    dosage: Mapped[Any] = mapped_column(String(100), nullable=False)  # e.g., "500mg"
    frequency: Mapped[Any] = mapped_column(String(100), nullable=False)  # e.g., "TID", "BD"
    route: Mapped[Any] = mapped_column(String(50), nullable=False, default="Oral")  # Oral, IV, IM, SC, etc.
    duration_days: Mapped[Any] = mapped_column(Integer, nullable=False)
    quantity: Mapped[Any] = mapped_column(Integer, nullable=False)
    instructions: Mapped[Any] = mapped_column(Text, nullable=True)
    is_substitutable: Mapped[Any] = mapped_column(Boolean, default=True, server_default="TRUE")

    # Relationships
    prescription = relationship("Prescription", back_populates="items")
    drug = relationship("Drug", backref="prescription_items")

    def __repr__(self) -> str:
        return f"<PrescriptionItem {self.drug_name} {self.dosage}>"

