"""Radiology models: RadiologyOrder, RadiologyReport."""

import enum
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TenantOwned


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


class RadiologyOrder(TenantOwned, Base):
    __tablename__ = "radiology_orders"

    encounter_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("encounters.id"), nullable=False, index=True)
    patient_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False, index=True)
    ordered_by: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    modality: Mapped[Any] = mapped_column(SAEnum(Modality, name="modality_enum"), nullable=False)
    body_part: Mapped[Any] = mapped_column(String(200), nullable=False)
    study_description: Mapped[Any] = mapped_column(Text, nullable=True)
    status: Mapped[Any] = mapped_column(
        SAEnum(RadiologyOrderStatus, name="radiology_order_status_enum"),
        nullable=False,
        default=RadiologyOrderStatus.ORDERED,
    )
    priority: Mapped[Any] = mapped_column(
        SAEnum(RadiologyPriority, name="radiology_priority_enum"),
        nullable=False,
        default=RadiologyPriority.ROUTINE,
    )
    clinical_indication: Mapped[Any] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)
    orthanc_study_id: Mapped[Any] = mapped_column(String(255), nullable=True)
    dicom_study_uid: Mapped[Any] = mapped_column(String(255), nullable=True)
    accession_number: Mapped[Any] = mapped_column(String(50), unique=True, nullable=True)

    # Relationships
    encounter = relationship("Encounter", back_populates="radiology_orders")
    patient = relationship("Patient", back_populates="radiology_orders")
    ordering_doctor = relationship("User", foreign_keys=[ordered_by], backref="radiology_orders_placed")
    report = relationship("RadiologyReport", back_populates="order", uselist=False)

    def __repr__(self) -> str:
        return f"<RadiologyOrder {self.modality} {self.body_part}>"


class RadiologyReport(TenantOwned, Base):
    __tablename__ = "radiology_reports"

    order_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("radiology_orders.id"), nullable=False, unique=True)
    radiologist_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    findings: Mapped[Any] = mapped_column(Text, nullable=False)
    impression: Mapped[Any] = mapped_column(Text, nullable=False)
    recommendation: Mapped[Any] = mapped_column(Text, nullable=True)
    is_critical: Mapped[Any] = mapped_column(Boolean, default=False, server_default="FALSE")
    reported_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_by: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)
    template_used: Mapped[Any] = mapped_column(String(100), nullable=True)

    # Relationships
    order = relationship("RadiologyOrder", back_populates="report")
    radiologist = relationship("User", foreign_keys=[radiologist_id], backref="radiology_reports_authored")
    verifier = relationship("User", foreign_keys=[verified_by], backref="radiology_reports_verified")

    def __repr__(self) -> str:
        return f"<RadiologyReport order_id={self.order_id}>"

