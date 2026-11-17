"""
ABDM v3 & v0.5 Async Webhook Callback Routers (M1 Scan & Share, M2 HIP, M3 HIU).

Mounted under `/api/v1/abdm` in `app.api.v1.router`.
Implements all mandatory NHA Sandbox Exit webhook receivers with HTTP 202 Accepted
acknowledgements, NHA signature verification, and WASA immutable transaction logging.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.abdm.abha_service import abha_service
from app.abdm.client import ABDMError, utc_timestamp_iso
from app.abdm.hip_service import hip_service
from app.abdm.hiu_service import hiu_service
from app.core.database import get_db
from app.core.dependencies import RateLimiter
from app.core.rbac import Permission
from app.core.security import get_current_user, require_permissions

router = APIRouter(tags=["ABDM v3/v0.5 Webhooks (M1/M2/M3)"])


class CallbackAck(BaseModel):
    status: str = "ACCEPTED"
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class HIPAddContextsRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=100)
    abha_address: str = Field(..., min_length=4, max_length=255)
    care_contexts: List[Dict[str, str]] = Field(..., min_length=1)


# =============================================================================
# M1: ABHA QR Scan & Share Counter Check-In
# =============================================================================


@router.post(
    "/v3/hip/patient-share",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(RateLimiter(times=60, seconds=60))],
)
async def v3_hip_patient_share(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """M1 ABHA QR Scan & Share webhook receiver for instant OPD counter check-in."""
    try:
        return await abha_service.handle_patient_share(db, body)
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


@router.get(
    "/v3/hip/patient-share/queue",
    dependencies=[Depends(require_permissions(Permission.PATIENT_READ.value))],
)
async def get_patient_share_queue(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Fetch live ABHA QR Scan & Share OPD check-in queue."""
    items = await abha_service.list_share_queue(db)
    return {"items": items, "total": len(items)}


# =============================================================================
# M2: HIP Care Context Discovery & Linking
# =============================================================================


@router.post("/v0.5/care-contexts/discover", status_code=status.HTTP_202_ACCEPTED)
async def hip_care_contexts_discover(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> CallbackAck:
    """M2 HIP Discovery webhook: matches local patient and dispatches on-discover."""
    result = await hip_service.on_discover(db, body)
    return CallbackAck(timestamp=utc_timestamp_iso(), details=result)


@router.post("/v0.5/care-contexts/on-discover", response_model=CallbackAck)
@router.post("/v0.5/patients/on-discover", response_model=CallbackAck)
async def on_discover_callback(body: Dict[str, Any]) -> CallbackAck:
    """Gateway acknowledgement for on-discover."""
    return CallbackAck(timestamp=utc_timestamp_iso())


@router.post("/v0.5/links/link/init", status_code=status.HTTP_202_ACCEPTED)
async def hip_link_init(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> CallbackAck:
    """M2 HIP Link Init webhook: issues link reference & OTP, dispatches on-init."""
    result = await hip_service.on_link_init(db, body)
    return CallbackAck(timestamp=utc_timestamp_iso(), details=result)


@router.post("/v0.5/links/link/on-init", response_model=CallbackAck)
async def on_link_init_callback(body: Dict[str, Any]) -> CallbackAck:
    """Gateway acknowledgement for on-init."""
    return CallbackAck(timestamp=utc_timestamp_iso())


@router.post("/v0.5/links/link/confirm", status_code=status.HTTP_202_ACCEPTED)
async def hip_link_confirm(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> CallbackAck:
    """M2 HIP Link Confirm webhook: verifies OTP and marks care contexts LINKED."""
    result = await hip_service.on_link_confirm(db, body)
    return CallbackAck(timestamp=utc_timestamp_iso(), details=result)


@router.post("/v0.5/links/link/on-confirm", response_model=CallbackAck)
async def on_link_confirm_callback(body: Dict[str, Any]) -> CallbackAck:
    """Gateway acknowledgement for on-confirm."""
    return CallbackAck(timestamp=utc_timestamp_iso())


@router.post(
    "/v0.5/links/context/add",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permissions(Permission.ABDM_LINK.value))],
)
async def hip_initiated_context_add(
    data: HIPAddContextsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """M2 HIP-initiated linking: push new encounter care contexts to patient's ABHA."""
    try:
        return await hip_service.hip_add_care_contexts(
            db,
            patient_id=data.patient_id,
            abha_address=data.abha_address,
            care_contexts=data.care_contexts,
            user_id=current_user["user_id"],
        )
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


# =============================================================================
# M2: HIP Consent Notification & Encrypted Health Information Push
# =============================================================================


@router.post("/v0.5/consents/hip/notify", status_code=status.HTTP_202_ACCEPTED)
async def hip_consent_notify(
    request: Request,
    body: Dict[str, Any],
    x_abdm_signature: Optional[str] = Header(None, alias="X-ABDM-Signature"),
    db: AsyncSession = Depends(get_db),
) -> CallbackAck:
    """M2 HIP Consent Notification webhook with signature check and immutable artefact storage."""
    raw_body = await request.body()
    try:
        result = await hip_service.on_consent_notify(
            db, body, raw_body=raw_body, signature_header=x_abdm_signature
        )
        return CallbackAck(timestamp=utc_timestamp_iso(), details=result)
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


@router.post("/v0.5/consents/hip/on-notify", response_model=CallbackAck)
@router.post("/v0.5/consent-requests/on-notify", response_model=CallbackAck)
async def hip_consent_on_notify_callback(body: Dict[str, Any]) -> CallbackAck:
    """Gateway acknowledgement for consent on-notify."""
    return CallbackAck(timestamp=utc_timestamp_iso())


@router.post("/v0.5/health-information/hip/request", status_code=status.HTTP_202_ACCEPTED)
@router.post("/v0.5/health-information/request", status_code=status.HTTP_202_ACCEPTED)
async def hip_health_information_request(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> CallbackAck:
    """M2 HIP Health Info Request: builds FHIR R4 bundles, encrypts via Fidelius, pushes to HIU."""
    try:
        result = await hip_service.on_data_request(db, body)
        return CallbackAck(timestamp=utc_timestamp_iso(), details=result)
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


@router.post("/v0.5/health-information/hip/on-request", response_model=CallbackAck)
@router.post("/v0.5/health-information/notify", response_model=CallbackAck)
async def hip_health_info_ack(body: Dict[str, Any]) -> CallbackAck:
    """Gateway acknowledgement for on-request / delivery notify."""
    return CallbackAck(timestamp=utc_timestamp_iso())


# =============================================================================
# M3: HIU Consent Callback & Decrypted Data Push Receiver
# =============================================================================


@router.post("/v0.5/consents/hiu/notify", status_code=status.HTTP_202_ACCEPTED)
async def hiu_consent_notify(
    request: Request,
    body: Dict[str, Any],
    x_abdm_signature: Optional[str] = Header(None, alias="X-ABDM-Signature"),
    db: AsyncSession = Depends(get_db),
) -> CallbackAck:
    """M3 HIU Consent Approval/Denial/Revocation webhook from Consent Manager."""
    raw_body = await request.body()
    try:
        result = await hiu_service.on_consent_hiu_notify(
            db, body, raw_body=raw_body, signature_header=x_abdm_signature
        )
        return CallbackAck(timestamp=utc_timestamp_iso(), details=result)
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


@router.post("/v0.5/health-information/transfer", response_model=CallbackAck)
async def hiu_health_information_transfer(
    body: Dict[str, Any],
) -> CallbackAck:
    """M3 HIU Data Push Receiver: decrypts incoming Fidelius-encrypted FHIR R4 bundles."""
    try:
        result = await hiu_service.on_health_information_transfer(body)
        return CallbackAck(timestamp=utc_timestamp_iso(), details=result)
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)
