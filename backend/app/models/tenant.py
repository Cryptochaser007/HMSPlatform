"""Hospital tenants and their starter departments."""
from typing import Any

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Hospital(Base):
    __tablename__ = "hospitals"

    name: Mapped[Any] = mapped_column(String(255), nullable=False)
    code: Mapped[Any] = mapped_column(String(80), unique=True)
    slug: Mapped[Any] = mapped_column(String(80), unique=True, nullable=False)
    hfr_facility_id: Mapped[Any] = mapped_column(String(100))
    hip_id: Mapped[Any] = mapped_column(String(100))
    hiu_id: Mapped[Any] = mapped_column(String(100))
    abdm_env: Mapped[Any] = mapped_column(String(20), nullable=False, default="MOCK")
    subscription_tier: Mapped[Any] = mapped_column(String(30), nullable=False, default="TRIAL")
    is_active: Mapped[Any] = mapped_column(Boolean, nullable=False, default=True)
    ward_setup_skipped: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("hospital_id", "name"),)

    hospital_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("hospitals.id"), nullable=False,
                         server_default=text("hms_current_hospital_id()"))
    name: Mapped[Any] = mapped_column(String(100), nullable=False)
