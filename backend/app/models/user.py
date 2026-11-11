"""User model for authentication, RBAC, and staff management."""

from sqlalchemy import Boolean, Column, DateTime, Enum, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.encryption import EncryptedType
from app.core.rbac import Role


class User(Base):
    __tablename__ = "users"

    email: str = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password: str = Column(String(255), nullable=False)
    full_name: str = Column(String(255), nullable=False)
    role: str = Column(Enum(Role, name="user_role"), nullable=False)
    department: str = Column(String(100), nullable=True)
    registration_number: str = Column(String(100), nullable=True)  # Medical reg for doctors
    phone: str = Column(EncryptedType, nullable=True)
    is_active: bool = Column(Boolean, default=True, server_default="TRUE", nullable=False)
    is_verified: bool = Column(Boolean, default=False, server_default="FALSE", nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    encounters_as_doctor = relationship("Encounter", back_populates="doctor", foreign_keys="Encounter.doctor_id")
    clinical_notes = relationship("ClinicalNote", back_populates="author", foreign_keys="ClinicalNote.author_id")
    prescriptions = relationship("Prescription", back_populates="doctor", foreign_keys="Prescription.doctor_id")

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role}>"

