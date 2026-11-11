"""Immutable Audit Log model — append-only, no UPDATE or DELETE."""

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.audit import AuditAction
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    action = Column(SAEnum(AuditAction, name="audit_action_enum"), nullable=False)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=False), nullable=True, index=True)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(255), nullable=True)
    hash_chain = Column(String(64), nullable=False)  # SHA-256 of prev_hash + record

    # Override created_at to be truly immutable — use server default only
    # Do NOT allow Python-side updates

    # Relationships
    user = relationship("User", backref="audit_entries", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.entity_type} {self.entity_id}>"

