"""Tenant (Hospital) multi-tenant organization model."""
from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Hospital(Base):
    """Hospital tenant entity for multi-tenant isolation and RLS."""

    __tablename__ = "hospitals"

    name = Column(String(255), nullable=False)
    code = Column(String(80), unique=True, nullable=False, index=True)
    hfr_id = Column(String(100), nullable=True, index=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    state = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
