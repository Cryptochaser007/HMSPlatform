"""Billing models: Bill, BillItem, Payment."""

import enum
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TenantOwned


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


class Bill(TenantOwned, Base):
    __tablename__ = "bills"

    bill_number: Mapped[Any] = mapped_column(String(50), unique=True, nullable=False, index=True)
    encounter_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("encounters.id"), nullable=True)
    patient_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False, index=True)
    bill_type: Mapped[Any] = mapped_column(SAEnum(BillType, name="bill_type_enum"), nullable=False)
    subtotal: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    discount_amount: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    tax_amount: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    total_amount: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    payment_status: Mapped[Any] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status_enum"),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    notes: Mapped[Any] = mapped_column(Text, nullable=True)
    created_by: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)

    # Relationships
    encounter = relationship("Encounter", back_populates="bills")
    patient = relationship("Patient", back_populates="bills")
    creator = relationship("User", foreign_keys=[created_by], backref="bills_created")
    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="bill", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Bill {self.bill_number} total={self.total_amount}>"


class BillItem(TenantOwned, Base):
    __tablename__ = "bill_items"

    bill_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("bills.id"), nullable=False, index=True)
    item_type: Mapped[Any] = mapped_column(SAEnum(BillItemType, name="bill_item_type_enum"), nullable=False)
    description: Mapped[Any] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Any] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False)
    discount_percent: Mapped[Any] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    tax_percent: Mapped[Any] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    total: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False)
    reference_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), nullable=True)  # FK to related entity

    # Relationships
    bill = relationship("Bill", back_populates="items")

    def __repr__(self) -> str:
        return f"<BillItem {self.description} total={self.total}>"


class Payment(TenantOwned, Base):
    __tablename__ = "payments"

    bill_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("bills.id"), nullable=False, index=True)
    amount: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[Any] = mapped_column(SAEnum(PaymentMethod, name="payment_method_enum"), nullable=False)
    transaction_reference: Mapped[Any] = mapped_column(String(255), nullable=True)
    payment_date: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
    received_by: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    receipt_number: Mapped[Any] = mapped_column(String(50), unique=True, nullable=False, index=True)
    notes: Mapped[Any] = mapped_column(Text, nullable=True)

    # Relationships
    bill = relationship("Bill", back_populates="payments")
    receiver = relationship("User", foreign_keys=[received_by], backref="payments_received")

    def __repr__(self) -> str:
        return f"<Payment {self.receipt_number} amount={self.amount}>"

