"""Pharmacy models: Drug, DrugInventory, Dispensing."""

import enum
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TenantOwned


class DrugType(str, enum.Enum):
    TABLET = "TABLET"
    CAPSULE = "CAPSULE"
    SYRUP = "SYRUP"
    INJECTION = "INJECTION"
    OINTMENT = "OINTMENT"
    DROPS = "DROPS"
    INHALER = "INHALER"
    PATCH = "PATCH"
    POWDER = "POWDER"
    GEL = "GEL"
    CREAM = "CREAM"
    OTHER = "OTHER"


class Drug(TenantOwned, Base):
    __tablename__ = "drugs"

    name: Mapped[Any] = mapped_column(String(255), nullable=False, index=True)
    generic_name: Mapped[Any] = mapped_column(String(255), nullable=False, index=True)
    brand_name: Mapped[Any] = mapped_column(String(255), nullable=True)
    drug_type: Mapped[Any] = mapped_column(SAEnum(DrugType, name="drug_type_enum"), nullable=False)
    strength: Mapped[Any] = mapped_column(String(50), nullable=False)
    manufacturer: Mapped[Any] = mapped_column(String(255), nullable=True)
    hsn_code: Mapped[Any] = mapped_column(String(20), nullable=True)
    schedule: Mapped[Any] = mapped_column(String(10), nullable=True)  # H, H1, X, etc.
    is_active: Mapped[Any] = mapped_column(Boolean, default=True, server_default="TRUE")

    # Relationships
    inventory = relationship("DrugInventory", back_populates="drug", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Drug {self.name} {self.strength}>"


class DrugInventory(TenantOwned, Base):
    __tablename__ = "drug_inventory"

    drug_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("drugs.id"), nullable=False, index=True)
    batch_number: Mapped[Any] = mapped_column(String(100), nullable=False)
    expiry_date: Mapped[Any] = mapped_column(Date, nullable=False)
    quantity_in_stock: Mapped[Any] = mapped_column(Integer, nullable=False, default=0)
    unit_price: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False)
    mrp: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False)
    gst_percentage: Mapped[Any] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("12.00"))
    reorder_level: Mapped[Any] = mapped_column(Integer, nullable=False, default=10)
    location: Mapped[Any] = mapped_column(String(100), nullable=True)  # store/shelf

    # Relationships
    drug = relationship("Drug", back_populates="inventory")

    def __repr__(self) -> str:
        return f"<DrugInventory drug_id={self.drug_id} batch={self.batch_number} qty={self.quantity_in_stock}>"


class Dispensing(TenantOwned, Base):
    __tablename__ = "dispensings"

    prescription_item_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("prescription_items.id"), nullable=False)
    drug_inventory_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("drug_inventory.id"), nullable=False)
    patient_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False)
    dispensed_by: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    quantity_dispensed: Mapped[Any] = mapped_column(Integer, nullable=False)
    dispensed_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[Any] = mapped_column(Text, nullable=True)

    # Relationships
    prescription_item = relationship("PrescriptionItem", backref="dispensings")
    drug_inventory = relationship("DrugInventory", backref="dispensings")
    patient = relationship("Patient", backref="dispensings")
    dispensed_by_user = relationship("User", backref="dispensings", foreign_keys=[dispensed_by])

    def __repr__(self) -> str:
        return f"<Dispensing {self.id} qty={self.quantity_dispensed}>"

