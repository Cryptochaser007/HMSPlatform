"""Quality & Accreditation models: QualityIndicator, QualityMeasurement, IncidentReport."""

import enum
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TenantOwned


class QualityFrequency(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


class IncidentType(str, enum.Enum):
    PATIENT_SAFETY = "PATIENT_SAFETY"
    MEDICATION_ERROR = "MEDICATION_ERROR"
    FALL = "FALL"
    INFECTION = "INFECTION"
    EQUIPMENT = "EQUIPMENT"
    NEAR_MISS = "NEAR_MISS"
    NEEDLE_STICK = "NEEDLE_STICK"
    OTHER = "OTHER"


class IncidentSeverity(str, enum.Enum):
    NEAR_MISS = "NEAR_MISS"
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"
    SENTINEL = "SENTINEL"


class IncidentStatus(str, enum.Enum):
    REPORTED = "REPORTED"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    ACTION_TAKEN = "ACTION_TAKEN"
    CLOSED = "CLOSED"


class QualityIndicator(TenantOwned, Base):
    __tablename__ = "quality_indicators"
    __table_args__ = (UniqueConstraint("hospital_id", "code"),)

    name: Mapped[Any] = mapped_column(String(255), nullable=False)
    code: Mapped[Any] = mapped_column(String(50), nullable=False, index=True)
    category: Mapped[Any] = mapped_column(String(100), nullable=False)  # Patient Safety, Clinical, Infection Control, etc.
    description: Mapped[Any] = mapped_column(Text, nullable=False)
    numerator_description: Mapped[Any] = mapped_column(Text, nullable=False)
    denominator_description: Mapped[Any] = mapped_column(Text, nullable=False)
    target_value: Mapped[Any] = mapped_column(Numeric(5, 2), nullable=False)
    unit: Mapped[Any] = mapped_column(String(20), nullable=False)  # %, count, rate
    frequency: Mapped[Any] = mapped_column(SAEnum(QualityFrequency, name="quality_frequency_enum"), nullable=False)
    is_nabh_mandatory: Mapped[Any] = mapped_column(Boolean, default=False, server_default="FALSE")
    is_active: Mapped[Any] = mapped_column(Boolean, default=True, server_default="TRUE")

    # Relationships
    measurements = relationship("QualityMeasurement", back_populates="indicator", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<QualityIndicator {self.code} - {self.name}>"


class QualityMeasurement(TenantOwned, Base):
    __tablename__ = "quality_measurements"

    indicator_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("quality_indicators.id"), nullable=False, index=True)
    period_start: Mapped[Any] = mapped_column(Date, nullable=False)
    period_end: Mapped[Any] = mapped_column(Date, nullable=False)
    numerator_value: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False)
    denominator_value: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False)
    calculated_value: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False)
    recorded_by: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    notes: Mapped[Any] = mapped_column(Text, nullable=True)

    # Relationships
    indicator = relationship("QualityIndicator", back_populates="measurements")
    recorder = relationship("User", foreign_keys=[recorded_by], backref="quality_measurements")

    def __repr__(self) -> str:
        return f"<QualityMeasurement indicator={self.indicator_id} value={self.calculated_value}>"


class IncidentReport(TenantOwned, Base):
    __tablename__ = "incident_reports"

    incident_number: Mapped[Any] = mapped_column(String(50), unique=True, nullable=False, index=True)
    incident_type: Mapped[Any] = mapped_column(SAEnum(IncidentType, name="incident_type_enum"), nullable=False)
    severity: Mapped[Any] = mapped_column(SAEnum(IncidentSeverity, name="incident_severity_enum"), nullable=False)
    title: Mapped[Any] = mapped_column(String(500), nullable=False)
    description: Mapped[Any] = mapped_column(Text, nullable=False)
    location: Mapped[Any] = mapped_column(String(255), nullable=False)
    incident_date: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
    reported_by: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    patient_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=True)
    root_cause: Mapped[Any] = mapped_column(Text, nullable=True)
    corrective_action: Mapped[Any] = mapped_column(Text, nullable=True)
    status: Mapped[Any] = mapped_column(
        SAEnum(IncidentStatus, name="incident_status_enum"),
        nullable=False,
        default=IncidentStatus.REPORTED,
    )
    closed_by: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    reporter = relationship("User", foreign_keys=[reported_by], backref="incidents_reported")
    patient = relationship("Patient", backref="incident_reports")
    closer = relationship("User", foreign_keys=[closed_by], backref="incidents_closed")

    def __repr__(self) -> str:
        return f"<IncidentReport {self.incident_number} severity={self.severity}>"

