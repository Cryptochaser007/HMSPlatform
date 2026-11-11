"""Pharmacy models: Drug, DrugInventory, Dispensing."""

import enum
from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


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


class Drug(Base):
    __tablename__ = "drugs"

    name = Column(String(255), nullable=False, index=True)
    generic_name = Column(String(255), nullable=False, index=True)
    brand_name = Column(String(255), nullable=True)
    drug_type = Column(SAEnum(DrugType, name="drug_type_enum"), nullable=False)
    strength = Column(String(50), nullable=False)
    manufacturer = Column(String(255), nullable=True)
    hsn_code = Column(String(20), nullable=True)
    schedule = Column(String(10), nullable=True)  # H, H1, X, etc.
    is_active = Column(Boolean, default=True, server_default="TRUE")

    # Relationships
    inventory = relationship("DrugInventory", back_populates="drug", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Drug {self.name} {self.strength}>"


class DrugInventory(Base):
    __tablename__ = "drug_inventory"

    drug_id = Column(UUID(as_uuid=False), ForeignKey("drugs.id"), nullable=False, index=True)
    batch_number = Column(String(100), nullable=False)
    expiry_date = Column(Date, nullable=False)
    quantity_in_stock = Column(Integer, nullable=False, default=0)
    unit_price = Column(Numeric(10, 2), nullable=False)
    mrp = Column(Numeric(10, 2), nullable=False)
    gst_percentage = Column(Numeric(5, 2), nullable=False, default=Decimal("12.00"))
    reorder_level = Column(Integer, nullable=False, default=10)
    location = Column(String(100), nullable=True)  # store/shelf

    # Relationships
    drug = relationship("Drug", back_populates="inventory")

    def __repr__(self) -> str:
        return f"<DrugInventory drug_id={self.drug_id} batch={self.batch_number} qty={self.quantity_in_stock}>"


class Dispensing(Base):
    __tablename__ = "dispensings"

    prescription_item_id = Column(UUID(as_uuid=False), ForeignKey("prescription_items.id"), nullable=False)
    drug_inventory_id = Column(UUID(as_uuid=False), ForeignKey("drug_inventory.id"), nullable=False)
    patient_id = Column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False)
    dispensed_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    quantity_dispensed = Column(Integer, nullable=False)
    dispensed_at = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    prescription_item = relationship("PrescriptionItem", backref="dispensings")
    drug_inventory = relationship("DrugInventory", backref="dispensings")
    patient = relationship("Patient", backref="dispensings")
    dispensed_by_user = relationship("User", backref="dispensings", foreign_keys=[dispensed_by])

    def __repr__(self) -> str:
        return f"<Dispensing {self.id} qty={self.quantity_dispensed}>"

