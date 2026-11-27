"""Explicit opt-in for ABDM operations, independent of the gateway mode."""

from fastapi import HTTPException, status

from app.core.config import get_settings


def require_abdm_enabled() -> None:
    if not get_settings().ABDM_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ABHA integration is unavailable in this environment.",
        )
