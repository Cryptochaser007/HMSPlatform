"""Billing models: Bill, BillItem, Payment."""

import enum
from decimal import Decimal

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class BillType(str, enum.Enum):
    OPD = "OPD"
    IPD = "IPD"
    PHARMACY = "PHARMACY"
    LAB = "LAB"
    RADIOLOGY = "RADIOLOGY"
    PROCEDURE = "PROCEDURE"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"


class BillItemType(str, enum.Enum):
    CONSULTATION = "CONSULTATION"
    PROCEDURE = "PROCEDURE"
    MEDICINE = "MEDICINE"
    LAB_TEST = "LAB_TEST"
    RADIOLOGY = "RADIOLOGY"
    BED_CHARGE = "BED_CHARGE"
    NURSING = "NURSING"
    OTHER = "OTHER"


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    CARD = "CARD"
    UPI = "UPI"
    NEFT = "NEFT"
    INSURANCE = "INSURANCE"
    CHEQUE = "CHEQUE"


class Bill(Base):
    __tablename__ = "bills"

    bill_number = Column(String(50), unique=True, nullable=False, index=True)
    encounter_id = Column(UUID(as_uuid=False), ForeignKey("encounters.id"), nullable=True)
    patient_id = Column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False, index=True)
    bill_type = Column(SAEnum(BillType, name="bill_type_enum"), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    discount_amount = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    tax_amount = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    total_amount = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    payment_status = Column(
        SAEnum(PaymentStatus, name="payment_status_enum"),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)

    # Relationships
    encounter = relationship("Encounter", back_populates="bills")
    patient = relationship("Patient", back_populates="bills")
    creator = relationship("User", foreign_keys=[created_by], backref="bills_created")
    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="bill", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Bill {self.bill_number} total={self.total_amount}>"


class BillItem(Base):
    __tablename__ = "bill_items"

    bill_id = Column(UUID(as_uuid=False), ForeignKey("bills.id"), nullable=False, index=True)
    item_type = Column(SAEnum(BillItemType, name="bill_item_type_enum"), nullable=False)
    description = Column(String(500), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount_percent = Column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    tax_percent = Column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    total = Column(Numeric(10, 2), nullable=False)
    reference_id = Column(UUID(as_uuid=False), nullable=True)  # FK to related entity

    # Relationships
    bill = relationship("Bill", back_populates="items")

    def __repr__(self) -> str:
        return f"<BillItem {self.description} total={self.total}>"


class Payment(Base):
    __tablename__ = "payments"

    bill_id = Column(UUID(as_uuid=False), ForeignKey("bills.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(SAEnum(PaymentMethod, name="payment_method_enum"), nullable=False)
    transaction_reference = Column(String(255), nullable=True)
    payment_date = Column(DateTime(timezone=True), nullable=False)
    received_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    receipt_number = Column(String(50), unique=True, nullable=False, index=True)
    notes = Column(Text, nullable=True)

    # Relationships
    bill = relationship("Bill", back_populates="payments")
    receiver = relationship("User", foreign_keys=[received_by], backref="payments_received")

    def __repr__(self) -> str:
        return f"<Payment {self.receipt_number} amount={self.amount}>"

