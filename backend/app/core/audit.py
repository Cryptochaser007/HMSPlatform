"""
Immutable, append-only audit logging with SHA-256 hash chain for
tamper detection.
"""

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db


class AuditAction(str, PyEnum):
    """Enumeration of auditable actions."""

    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"
    PRINT = "PRINT"
    CONSENT_GRANTED = "CONSENT_GRANTED"
    CONSENT_REVOKED = "CONSENT_REVOKED"


def _compute_hash(prev_hash: str, record_data: str) -> str:
    """Compute SHA-256 hash chaining: hash(prev_hash + record_data)."""
    payload = f"{prev_hash}{record_data}".encode()
    return hashlib.sha256(payload).hexdigest()


def _json_default(obj: Any) -> Any:
    """JSON serializer fallback for objects not natively serializable."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, PyEnum):
        return obj.value
    if hasattr(obj, "__str__"):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _safe_json(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, default=_json_default, sort_keys=True)


class AuditLogger:
    """Creates immutable audit log entries with hash-chain integrity."""

    async def _get_last_hash(self, db: AsyncSession) -> str:
        """Return the hash_chain value of the most recent audit entry."""
        # Lazy import to avoid circular deps
        from app.models.audit import AuditLog

        result = await db.execute(
            select(AuditLog.hash_chain)
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
        last_hash = result.scalar_one_or_none()
        return last_hash or "GENESIS"

    async def log(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[str] = None,
        action: AuditAction,
        entity_type: str,
        entity_id: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Persist a new audit log entry. Returns the new entry ID."""
        from app.models.audit import AuditLog

        entry_id = str(uuid4())
        now = datetime.now(timezone.utc)

        # Build the canonical string for hashing
        record_data = _safe_json(
            {
                "id": entry_id,
                "user_id": user_id,
                "action": action.value,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "old_value": old_value,
                "new_value": new_value,
                "created_at": now.isoformat(),
            }
        )

        prev_hash = await self._get_last_hash(db)
        chain_hash = _compute_hash(prev_hash, record_data or "")

        entry = AuditLog(
            id=entry_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            hash_chain=chain_hash,
            created_at=now,
        )
        db.add(entry)
        await db.flush()
        return entry_id

    async def log_clinical_change(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        entity_type: str,
        entity_id: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> str:
        """Convenience wrapper for clinical-record modifications.

        Captures *which field* changed, making clinical audit trails
        granular and traceable.
        """
        return await self.log(
            db,
            user_id=user_id,
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value={"field": field_name, "value": old_value},
            new_value={"field": field_name, "value": new_value},
            ip_address=ip_address,
            user_agent=user_agent,
        )


# Module-level singleton
audit_logger = AuditLogger()


async def get_audit_logger() -> AuditLogger:
    """FastAPI dependency that returns the audit logger singleton."""
    return audit_logger


def audit_log(
    action: AuditAction,
    entity_type: str,
):
    """Decorator / dependency factory that auto-captures audit events.

    Usage as a dependency::

        @router.post("/patients")
        async def create_patient(
            ...,
            _audit=Depends(audit_log(AuditAction.CREATE, "Patient")),
        ):
            ...
    """

    async def _dependency(
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> Callable:
        """Return a callable that the endpoint can invoke to write the
        audit entry after it has the entity data."""

        async def _write(
            entity_id: str,
            old_value: Optional[Dict[str, Any]] = None,
            new_value: Optional[Dict[str, Any]] = None,
            user_id: Optional[str] = None,
        ) -> str:
            return await audit_logger.log(
                db,
                user_id=user_id or getattr(request.state, "user_id", None),
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                old_value=old_value,
                new_value=new_value,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                session_id=request.headers.get("x-session-id"),
            )

        return _write

    return _dependency
