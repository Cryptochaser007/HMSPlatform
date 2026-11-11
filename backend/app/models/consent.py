"""Consent model for DPDP Act compliance."""

import enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


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


class Consent(Base):
    __tablename__ = "consents"

    patient_id = Column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False, index=True)
    consent_type = Column(SAEnum(ConsentType, name="consent_type_enum"), nullable=False)
    purpose = Column(Text, nullable=False)
    data_categories = Column(JSONB, nullable=True)  # ["demographics", "clinical", "billing"]
    granted_to = Column(String(255), nullable=False)  # Entity name / HIP ID
    status = Column(
        SAEnum(ConsentStatus, name="consent_status_enum"),
        nullable=False,
        default=ConsentStatus.GRANTED,
    )
    granted_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(Text, nullable=True)
    consent_artifact_id = Column(String(255), nullable=True)  # ABDM consent artifact
    digital_signature = Column(String(512), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="consents")

    def __repr__(self) -> str:
        return f"<Consent patient={self.patient_id} type={self.consent_type} status={self.status}>"

