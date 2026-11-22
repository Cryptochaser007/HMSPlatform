"""Request-local hospital settings, reset with the database dependency."""
from contextvars import ContextVar
from typing import Any

current_hospital: ContextVar[dict[str, Any] | None] = ContextVar("current_hospital", default=None)


def tenant_cache_key(key: str) -> str:
    """Unresolved callbacks never share caches with an authenticated hospital."""
    hospital = current_hospital.get()
    hospital_id = hospital["hospital_id"] if hospital else "unassigned"
    return f"hospital:{hospital_id}:{key}"
