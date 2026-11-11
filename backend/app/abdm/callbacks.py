"""ABDM Gateway webhook callbacks receiver."""

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

router = APIRouter(prefix="/v0.5", tags=["ABDM Gateway Callbacks"])


class CallbackAck(BaseModel):
    status: str = "ACK"
    timestamp: str


@router.post("/patients/on-discover", response_model=CallbackAck)
async def on_discover_callback(
    request: Request,
    body: Dict[str, Any],
    authorization: str = Header(None),
) -> CallbackAck:
    """Callback triggered after patient discovery query."""
    return CallbackAck(timestamp=datetime.now(timezone.utc).isoformat())


@router.post("/links/link/on-init", response_model=CallbackAck)
async def on_link_init_callback(
    body: Dict[str, Any],
) -> CallbackAck:
    """Callback triggered after link authentication initiation."""
    return CallbackAck(timestamp=datetime.now(timezone.utc).isoformat())


@router.post("/links/link/on-confirm", response_model=CallbackAck)
async def on_link_confirm_callback(
    body: Dict[str, Any],
) -> CallbackAck:
    """Callback triggered after link token confirmation."""
    return CallbackAck(timestamp=datetime.now(timezone.utc).isoformat())


@router.post("/consent-requests/on-notify", response_model=CallbackAck)
async def on_consent_notify_callback(
    body: Dict[str, Any],
) -> CallbackAck:
    """Consent notification: patient granted, denied or revoked consent."""
    return CallbackAck(timestamp=datetime.now(timezone.utc).isoformat())


@router.post("/health-information/request", response_model=CallbackAck)
async def on_health_information_request(
    body: Dict[str, Any],
) -> CallbackAck:
    """Gateway requests health records transfer to HIU."""
    return CallbackAck(timestamp=datetime.now(timezone.utc).isoformat())


@router.post("/health-information/transfer", response_model=CallbackAck)
async def on_health_information_transfer(
    body: Dict[str, Any],
) -> CallbackAck:
    """Data push receiver: receives encrypted FHIR bundles from external HIP."""
    return CallbackAck(timestamp=datetime.now(timezone.utc).isoformat())

