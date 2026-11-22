"""User model for authentication, RBAC, and staff management."""

from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.encryption import EncryptedType
from app.core.rbac import Role


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum(Role, name="user_role_enum"), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    registration_number: Mapped[str] = mapped_column(String(100), nullable=True)  # Medical reg for doctors
    phone: Mapped[str] = mapped_column(EncryptedType, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="TRUE", nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="FALSE", nullable=False)
    last_login: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)
    hospital_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("hospitals.id"), nullable=False,
                         server_default=text("hms_current_hospital_id()"))

    # Relationships
    encounters_as_doctor = relationship("Encounter", back_populates="doctor", foreign_keys="Encounter.doctor_id")
    clinical_notes = relationship("ClinicalNote", back_populates="author", foreign_keys="ClinicalNote.author_id")
    prescriptions = relationship("Prescription", back_populates="doctor", foreign_keys="Prescription.doctor_id")

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role}>"

