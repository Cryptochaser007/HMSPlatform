"""Quality & Accreditation models: QualityIndicator, QualityMeasurement, IncidentReport."""

import enum
from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime, Enum as SAEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


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


class QualityIndicator(Base):
    __tablename__ = "quality_indicators"

    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=False)  # Patient Safety, Clinical, Infection Control, etc.
    description = Column(Text, nullable=False)
    numerator_description = Column(Text, nullable=False)
    denominator_description = Column(Text, nullable=False)
    target_value = Column(Numeric(5, 2), nullable=False)
    unit = Column(String(20), nullable=False)  # %, count, rate
    frequency = Column(SAEnum(QualityFrequency, name="quality_frequency_enum"), nullable=False)
    is_nabh_mandatory = Column(Boolean, default=False, server_default="FALSE")
    is_active = Column(Boolean, default=True, server_default="TRUE")

    # Relationships
    measurements = relationship("QualityMeasurement", back_populates="indicator", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<QualityIndicator {self.code} - {self.name}>"


class QualityMeasurement(Base):
    __tablename__ = "quality_measurements"

    indicator_id = Column(UUID(as_uuid=False), ForeignKey("quality_indicators.id"), nullable=False, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    numerator_value = Column(Numeric(10, 2), nullable=False)
    denominator_value = Column(Numeric(10, 2), nullable=False)
    calculated_value = Column(Numeric(10, 2), nullable=False)
    recorded_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    indicator = relationship("QualityIndicator", back_populates="measurements")
    recorder = relationship("User", foreign_keys=[recorded_by], backref="quality_measurements")

    def __repr__(self) -> str:
        return f"<QualityMeasurement indicator={self.indicator_id} value={self.calculated_value}>"


class IncidentReport(Base):
    __tablename__ = "incident_reports"

    incident_number = Column(String(50), unique=True, nullable=False, index=True)
    incident_type = Column(SAEnum(IncidentType, name="incident_type_enum"), nullable=False)
    severity = Column(SAEnum(IncidentSeverity, name="incident_severity_enum"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(255), nullable=False)
    incident_date = Column(DateTime(timezone=True), nullable=False)
    reported_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    patient_id = Column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=True)
    root_cause = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    status = Column(
        SAEnum(IncidentStatus, name="incident_status_enum"),
        nullable=False,
        default=IncidentStatus.REPORTED,
    )
    closed_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    reporter = relationship("User", foreign_keys=[reported_by], backref="incidents_reported")
    patient = relationship("Patient", backref="incident_reports")
    closer = relationship("User", foreign_keys=[closed_by], backref="incidents_closed")

    def __repr__(self) -> str:
        return f"<IncidentReport {self.incident_number} severity={self.severity}>"

