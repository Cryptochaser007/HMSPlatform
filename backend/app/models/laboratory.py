"""Laboratory models: LabTest, LabOrder, LabResult."""

import enum
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


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


class LabTest(Base):
    __tablename__ = "lab_tests"

    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=False)  # Hematology, Biochemistry, etc.
    sample_type = Column(String(100), nullable=False)  # Blood, Urine, Stool, etc.
    description = Column(Text, nullable=True)
    reference_ranges = Column(JSONB, nullable=True)  # {"male": {"18-60": {"min": 4.5, "max": 5.5, "unit": "million/μL"}}}
    turnaround_hours = Column(Integer, default=24, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True, server_default="TRUE")

    # Relationships
    orders = relationship("LabOrder", back_populates="test", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<LabTest {self.code} - {self.name}>"


class LabOrder(Base):
    __tablename__ = "lab_orders"

    encounter_id = Column(UUID(as_uuid=False), ForeignKey("encounters.id"), nullable=False, index=True)
    patient_id = Column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False, index=True)
    ordered_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    test_id = Column(UUID(as_uuid=False), ForeignKey("lab_tests.id"), nullable=False)
    status = Column(
        SAEnum(LabOrderStatus, name="lab_order_status_enum"),
        nullable=False,
        default=LabOrderStatus.ORDERED,
    )
    priority = Column(
        SAEnum(LabPriority, name="lab_priority_enum"),
        nullable=False,
        default=LabPriority.ROUTINE,
    )
    clinical_notes = Column(Text, nullable=True)
    sample_id = Column(String(50), nullable=True, unique=True)  # Barcode
    collected_at = Column(DateTime(timezone=True), nullable=True)
    collected_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)

    # Relationships
    encounter = relationship("Encounter", back_populates="lab_orders")
    patient = relationship("Patient", back_populates="lab_orders")
    test = relationship("LabTest", back_populates="orders")
    ordering_doctor = relationship("User", foreign_keys=[ordered_by], backref="lab_orders_placed")
    collector = relationship("User", foreign_keys=[collected_by], backref="samples_collected")
    results = relationship("LabResult", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<LabOrder {self.id} status={self.status}>"


class LabResult(Base):
    __tablename__ = "lab_results"

    order_id = Column(UUID(as_uuid=False), ForeignKey("lab_orders.id"), nullable=False, index=True)
    parameter_name = Column(String(255), nullable=False)
    value = Column(String(100), nullable=False)
    unit = Column(String(50), nullable=True)
    reference_range = Column(String(100), nullable=True)
    is_abnormal = Column(Boolean, default=False, server_default="FALSE")
    flag = Column(SAEnum(ResultFlag, name="result_flag_enum"), nullable=True)
    performed_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    verified_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    remarks = Column(Text, nullable=True)
    attachments = Column(JSONB, nullable=True)

    # Relationships
    order = relationship("LabOrder", back_populates="results")
    performer = relationship("User", foreign_keys=[performed_by], backref="lab_results_performed")
    verifier = relationship("User", foreign_keys=[verified_by], backref="lab_results_verified")

    def __repr__(self) -> str:
        return f"<LabResult {self.parameter_name}={self.value}>"

