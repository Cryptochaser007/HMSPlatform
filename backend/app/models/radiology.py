"""Radiology models: RadiologyOrder, RadiologyReport."""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Modality(str, enum.Enum):
    XRAY = "XRAY"
    CT = "CT"
    MRI = "MRI"
    ULTRASOUND = "ULTRASOUND"
    MAMMOGRAPHY = "MAMMOGRAPHY"
    FLUOROSCOPY = "FLUOROSCOPY"
    PET = "PET"


class RadiologyOrderStatus(str, enum.Enum):
    ORDERED = "ORDERED"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REPORTED = "REPORTED"
    VERIFIED = "VERIFIED"
    CANCELLED = "CANCELLED"


class RadiologyPriority(str, enum.Enum):
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    STAT = "STAT"


class RadiologyOrder(Base):
    __tablename__ = "radiology_orders"

    encounter_id = Column(UUID(as_uuid=False), ForeignKey("encounters.id"), nullable=False, index=True)
    patient_id = Column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False, index=True)
    ordered_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    modality = Column(SAEnum(Modality, name="modality_enum"), nullable=False)
    body_part = Column(String(200), nullable=False)
    study_description = Column(Text, nullable=True)
    status = Column(
        SAEnum(RadiologyOrderStatus, name="radiology_order_status_enum"),
        nullable=False,
        default=RadiologyOrderStatus.ORDERED,
    )
    priority = Column(
        SAEnum(RadiologyPriority, name="radiology_priority_enum"),
        nullable=False,
        default=RadiologyPriority.ROUTINE,
    )
    clinical_indication = Column(Text, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    orthanc_study_id = Column(String(255), nullable=True)
    dicom_study_uid = Column(String(255), nullable=True)
    accession_number = Column(String(50), unique=True, nullable=True)

    # Relationships
    encounter = relationship("Encounter", back_populates="radiology_orders")
    patient = relationship("Patient", back_populates="radiology_orders")
    ordering_doctor = relationship("User", foreign_keys=[ordered_by], backref="radiology_orders_placed")
    report = relationship("RadiologyReport", back_populates="order", uselist=False)

    def __repr__(self) -> str:
        return f"<RadiologyOrder {self.modality} {self.body_part}>"


class RadiologyReport(Base):
    __tablename__ = "radiology_reports"

    order_id = Column(UUID(as_uuid=False), ForeignKey("radiology_orders.id"), nullable=False, unique=True)
    radiologist_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    findings = Column(Text, nullable=False)
    impression = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=True)
    is_critical = Column(Boolean, default=False, server_default="FALSE")
    reported_at = Column(DateTime(timezone=True), nullable=False)
    verified_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    template_used = Column(String(100), nullable=True)

    # Relationships
    order = relationship("RadiologyOrder", back_populates="report")
    radiologist = relationship("User", foreign_keys=[radiologist_id], backref="radiology_reports_authored")
    verifier = relationship("User", foreign_keys=[verified_by], backref="radiology_reports_verified")

    def __repr__(self) -> str:
        return f"<RadiologyReport order_id={self.order_id}>"

