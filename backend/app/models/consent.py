"""Consent model for DPDP Act compliance."""

import enum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TenantOwned


class ConsentType(str, enum.Enum):
    TREATMENT = "TREATMENT"
    DATA_PROCESSING = "DATA_PROCESSING"
    DATA_SHARING = "DATA_SHARING"
    RESEARCH = "RESEARCH"
    ABDM_LINKING = "ABDM_LINKING"


class ConsentStatus(str, enum.Enum):
    GRANTED = "GRANTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class Consent(TenantOwned, Base):
    __tablename__ = "consents"

    patient_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False, index=True)
    consent_type: Mapped[Any] = mapped_column(SAEnum(ConsentType, name="consent_type_enum"), nullable=False)
    purpose: Mapped[Any] = mapped_column(Text, nullable=False)
    data_categories: Mapped[Any] = mapped_column(JSONB, nullable=True)  # ["demographics", "clinical", "billing"]
    granted_to: Mapped[Any] = mapped_column(String(255), nullable=False)  # Entity name / HIP ID
    status: Mapped[Any] = mapped_column(
        SAEnum(ConsentStatus, name="consent_status_enum"),
        nullable=False,
        default=ConsentStatus.GRANTED,
    )
    granted_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[Any] = mapped_column(Text, nullable=True)
    consent_artifact_id: Mapped[Any] = mapped_column(String(255), nullable=True)  # ABDM consent artifact
    digital_signature: Mapped[Any] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[Any] = mapped_column(String(45), nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="consents")

    def __repr__(self) -> str:
        return f"<Consent patient={self.patient_id} type={self.consent_type} status={self.status}>"

