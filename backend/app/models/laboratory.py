"""Laboratory models: LabTest, LabOrder, LabResult."""

import enum
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TenantOwned


class LabOrderStatus(str, enum.Enum):
    ORDERED = "ORDERED"
    SAMPLE_COLLECTED = "SAMPLE_COLLECTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"
    CANCELLED = "CANCELLED"


class LabPriority(str, enum.Enum):
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    STAT = "STAT"


class ResultFlag(str, enum.Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class LabTest(TenantOwned, Base):
    __tablename__ = "lab_tests"

    name: Mapped[Any] = mapped_column(String(255), nullable=False)
    code: Mapped[Any] = mapped_column(String(50), unique=True, nullable=False, index=True)
    category: Mapped[Any] = mapped_column(String(100), nullable=False)  # Hematology, Biochemistry, etc.
    sample_type: Mapped[Any] = mapped_column(String(100), nullable=False)  # Blood, Urine, Stool, etc.
    description: Mapped[Any] = mapped_column(Text, nullable=True)
    reference_ranges: Mapped[Any] = mapped_column(JSONB, nullable=True)  # {"male": {"18-60": {"min": 4.5, "max": 5.5, "unit": "million/μL"}}}
    turnaround_hours: Mapped[Any] = mapped_column(Integer, default=24, nullable=False)
    price: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[Any] = mapped_column(Boolean, default=True, server_default="TRUE")

    # Relationships
    orders = relationship("LabOrder", back_populates="test", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<LabTest {self.code} - {self.name}>"


class LabOrder(TenantOwned, Base):
    __tablename__ = "lab_orders"

    encounter_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("encounters.id"), nullable=False, index=True)
    patient_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False, index=True)
    ordered_by: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    test_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("lab_tests.id"), nullable=False)
    status: Mapped[Any] = mapped_column(
        SAEnum(LabOrderStatus, name="lab_order_status_enum"),
        nullable=False,
        default=LabOrderStatus.ORDERED,
    )
    priority: Mapped[Any] = mapped_column(
        SAEnum(LabPriority, name="lab_priority_enum"),
        nullable=False,
        default=LabPriority.ROUTINE,
    )
    clinical_notes: Mapped[Any] = mapped_column(Text, nullable=True)
    sample_id: Mapped[Any] = mapped_column(String(50), nullable=True, unique=True)  # Barcode
    collected_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_by: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)

    # Relationships
    encounter = relationship("Encounter", back_populates="lab_orders")
    patient = relationship("Patient", back_populates="lab_orders")
    test = relationship("LabTest", back_populates="orders")
    ordering_doctor = relationship("User", foreign_keys=[ordered_by], backref="lab_orders_placed")
    collector = relationship("User", foreign_keys=[collected_by], backref="samples_collected")
    results = relationship("LabResult", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<LabOrder {self.id} status={self.status}>"


class LabResult(TenantOwned, Base):
    __tablename__ = "lab_results"

    order_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("lab_orders.id"), nullable=False, index=True)
    parameter_name: Mapped[Any] = mapped_column(String(255), nullable=False)
    value: Mapped[Any] = mapped_column(String(100), nullable=False)
    unit: Mapped[Any] = mapped_column(String(50), nullable=True)
    reference_range: Mapped[Any] = mapped_column(String(100), nullable=True)
    is_abnormal: Mapped[Any] = mapped_column(Boolean, default=False, server_default="FALSE")
    flag: Mapped[Any] = mapped_column(SAEnum(ResultFlag, name="result_flag_enum"), nullable=True)
    performed_by: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    verified_by: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)
    remarks: Mapped[Any] = mapped_column(Text, nullable=True)
    attachments: Mapped[Any] = mapped_column(JSONB, nullable=True)

    # Relationships
    order = relationship("LabOrder", back_populates="results")
    performer = relationship("User", foreign_keys=[performed_by], backref="lab_results_performed")
    verifier = relationship("User", foreign_keys=[verified_by], backref="lab_results_verified")

    def __repr__(self) -> str:
        return f"<LabResult {self.parameter_name}={self.value}>"

