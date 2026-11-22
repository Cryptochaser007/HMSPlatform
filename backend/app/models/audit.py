"""Immutable Audit Log model — append-only, no UPDATE or DELETE."""

from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.audit import AuditAction
from app.core.database import Base, TenantOwned


class AuditLog(TenantOwned, Base):
    __tablename__ = "audit_logs"

    user_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    action: Mapped[Any] = mapped_column(SAEnum(AuditAction, name="audit_action_enum"), nullable=False)
    entity_type: Mapped[Any] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    old_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Any] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Any] = mapped_column(String(500), nullable=True)
    session_id: Mapped[Any] = mapped_column(String(255), nullable=True)
    hash_chain: Mapped[Any] = mapped_column(String(64), nullable=False)  # SHA-256 of prev_hash + record

    # Override created_at to be truly immutable — use server default only
    # Do NOT allow Python-side updates

    # Relationships
    user = relationship("User", backref="audit_entries", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.entity_type} {self.entity_id}>"

