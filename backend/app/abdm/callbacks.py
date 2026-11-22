"""
ABDM v3 & v0.5 Async Webhook Callback Routers (M1 Scan & Share, M2 HIP, M3 HIU).

Mounted under `/api/v1/abdm` in `app.api.v1.router`.
Implements all mandatory NHA Sandbox Exit webhook receivers with HTTP 202 Accepted
acknowledgements, NHA signature verification, and WASA immutable transaction logging.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
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
_gateway_callback_client = None


async def verify_gateway_callback_request(request: Request) -> None:
    """Require allowlisted source IP and an NHA-signed bearer JWT in live modes."""
    from app.abdm.config import ABDMMode, get_abdm_settings
    config = get_abdm_settings()
    if config.abdm_env == ABDMMode.MOCK:
        return
    path = request.url.path
    # Staff-initiated linking endpoints use normal HMS auth and are not gateway callbacks.
    if (path.endswith(("/hip/link/token", "/hip/link/carecontext", "/patient-share/queue", "/links/context/add"))):
        return
    client_ip = request.client.host if request.client else ""
    allowed = {part.strip() for part in config.abdm_gateway_allowed_ips.split(",") if part.strip()}
    if client_ip not in allowed:
        raise HTTPException(status_code=403, detail="ABDM gateway source IP is not allowed")
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="ABDM gateway callback token required")
    global _gateway_callback_client
    if _gateway_callback_client is None:
        from app.abdm.client import ABDMClient
        _gateway_callback_client = ABDMClient(config)
    await _gateway_callback_client._adapter.verify_gateway_jwt(authorization[7:].strip())


def idempotent_webhook(fn):
    """Make gateway retries safe across processes; Redis failure returns 503 for retry."""
    @wraps(fn)
    async def wrapped(*args, **kwargs):
        body = kwargs.get("body")
        if body is None:
            body = next((arg for arg in args if isinstance(arg, dict)), {})
        request_id = str(body.get("requestId") or body.get("request_id") or body.get("transactionId") or body.get("transaction_id") or "")
        if not request_id:
            return await fn(*args, **kwargs)
        from app.core.redis_state import acquire_idempotency, get_redis
        try:
            acquired = await acquire_idempotency(request_id)
        except Exception:
            logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
            acquired = True
        if not acquired:
            return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"status": "ACCEPTED", "timestamp": utc_timestamp_iso(), "details": {"duplicate": True}})
        try:
            result = await fn(*args, **kwargs)
            try:
                redis_client = await get_redis()
                await redis_client.set(f"abdm:idem:{request_id}", "done", ex=86400)
            except Exception:
                logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
            return result
        except Exception:
            try:
                redis_client = await get_redis()
                await redis_client.delete(f"abdm:idem:{request_id}")
            except Exception:
                logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
            raise
    return wrapped


class CallbackAck(BaseModel):
    status: str = "ACCEPTED"
    timestamp: str
    details: dict[str, Any] | None = None


class HIPAddContextsRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=100)
    abha_address: str = Field(..., min_length=4, max_length=255)
    care_contexts: list[dict[str, str]] = Field(..., min_length=1)


class HIPLinkTokenRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, max_length=100)
    abha_address: str = Field(..., min_length=4, max_length=255)


# =============================================================================
# M1: ABHA QR Scan & Share Counter Check-In
# =============================================================================


@router.post(
    "/v3/hip/patient-share",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(RateLimiter(times=60, seconds=60))],
)
@idempotent_webhook
async def v3_hip_patient_share(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
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
) -> dict[str, Any]:
    """Fetch live ABHA QR Scan & Share OPD check-in queue."""
    items = await abha_service.list_share_queue(db)
    return {"items": items, "total": len(items)}


# =============================================================================
# M2: HIP Care Context Discovery & Linking
# =============================================================================


@router.post("/v3/hip/patient/care-context/discover", status_code=status.HTTP_202_ACCEPTED)
@router.post("/v0.5/care-contexts/discover", status_code=status.HTTP_202_ACCEPTED)
@idempotent_webhook
async def hip_care_contexts_discover(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> CallbackAck:
    """M2 HIP Discovery webhook: matches local patient and dispatches on-discover."""
    result = await hip_service.on_discover(db, body)
    return CallbackAck(timestamp=utc_timestamp_iso(), details=result)


@router.post("/v3/hip/patient/care-context/on-discover", response_model=CallbackAck)
@router.post("/v0.5/care-contexts/on-discover", response_model=CallbackAck)
@router.post("/v0.5/patients/on-discover", response_model=CallbackAck)
@idempotent_webhook
async def on_discover_callback(body: dict[str, Any]) -> CallbackAck:
    """Gateway acknowledgement for on-discover."""
    return CallbackAck(timestamp=utc_timestamp_iso())


@router.post("/v3/hip/link/care-context/init", status_code=status.HTTP_202_ACCEPTED)
@router.post("/v0.5/links/link/init", status_code=status.HTTP_202_ACCEPTED)
@idempotent_webhook
async def hip_link_init(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> CallbackAck:
    """M2 HIP Link Init webhook: issues link reference & OTP, dispatches on-init."""
    result = await hip_service.on_link_init(db, body)
    return CallbackAck(timestamp=utc_timestamp_iso(), details=result)


@router.post("/v3/hip/link/care-context/on-init", response_model=CallbackAck)
@router.post("/v0.5/links/link/on-init", response_model=CallbackAck)
@idempotent_webhook
async def on_link_init_callback(body: dict[str, Any]) -> CallbackAck:
    """Gateway acknowledgement for on-init."""
    return CallbackAck(timestamp=utc_timestamp_iso())


@router.post("/v3/hip/link/care-context/confirm", status_code=status.HTTP_202_ACCEPTED)
@router.post("/v0.5/links/link/confirm", status_code=status.HTTP_202_ACCEPTED)
@idempotent_webhook
async def hip_link_confirm(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> CallbackAck:
    """M2 HIP Link Confirm webhook: verifies OTP and marks care contexts LINKED."""
    result = await hip_service.on_link_confirm(db, body)
    return CallbackAck(timestamp=utc_timestamp_iso(), details=result)


@router.post("/v3/hip/link/care-context/on-confirm", response_model=CallbackAck)
@router.post("/v0.5/links/link/on-confirm", response_model=CallbackAck)
@idempotent_webhook
async def on_link_confirm_callback(body: dict[str, Any]) -> CallbackAck:
    """Gateway acknowledgement for on-confirm."""
    return CallbackAck(timestamp=utc_timestamp_iso())


@router.post(
    "/v0.5/links/context/add",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permissions(Permission.ABDM_LINK.value))],
)
async def hip_initiated_context_add(
    data: HIPAddContextsRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
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


@router.post("/v3/hip/link/token", dependencies=[Depends(require_permissions(Permission.ABDM_LINK.value))])
async def hip_link_token_request(
    data: HIPLinkTokenRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return await hip_service.generate_link_token(
            patient_id=data.patient_id, abha_address=data.abha_address, user_id=current_user["user_id"]
        )
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


@router.post("/v3/hip/link/carecontext", dependencies=[Depends(require_permissions(Permission.ABDM_LINK.value))])
async def hip_link_care_context_v3(
    data: HIPAddContextsRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from app.core.redis_state import get_redis
    token = await (await get_redis()).get(f"abdm:hip:link-token:{data.patient_id}")
    if not token:
        raise HTTPException(status_code=409, detail="ABDM link token is pending; retry after token callback")
    try:
        result = await hip_service.hip_add_care_contexts(
            db, patient_id=data.patient_id, abha_address=data.abha_address,
            care_contexts=data.care_contexts, link_access_token=token,
            user_id=current_user["user_id"],
        )
        await (await get_redis()).delete(f"abdm:hip:link-token:{data.patient_id}")
        return result
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


@router.post("/v3/hip/token/on-generate-token", response_model=CallbackAck)
@idempotent_webhook
async def hip_token_generated(body: dict[str, Any]) -> CallbackAck:
    """Cache HIP linkToken delivered asynchronously by the gateway."""
    patient = body.get("patient") or body.get("link") or {}
    reference = patient.get("referenceNumber") or body.get("referenceNumber")
    link_token = body.get("linkToken") or (body.get("token") or {}).get("linkToken")
    from app.core.redis_state import get_redis
    redis_client = await get_redis()
    if not reference:
        request_id = body.get("requestId") or body.get("transactionId")
        if request_id:
            reference = await redis_client.get(f"abdm:hip:link-token-request:{request_id}")
    if reference and link_token:
        await redis_client.set(f"abdm:hip:link-token:{reference}", link_token, ex=1800)
    return CallbackAck(timestamp=utc_timestamp_iso(), details={"linkTokenCached": bool(link_token)})


@router.post("/v3/link/on_carecontext", response_model=CallbackAck)
@idempotent_webhook
async def hip_care_context_linked(body: dict[str, Any]) -> CallbackAck:
    """Acknowledge the gateway response for HIP initiated care-context linking."""
    return CallbackAck(timestamp=utc_timestamp_iso(), details={"requestId": body.get("requestId")})


# =============================================================================
# M2: HIP Consent Notification & Encrypted Health Information Push
# =============================================================================


@router.post("/v3/consent/request/hip/notify", status_code=status.HTTP_202_ACCEPTED)
@router.post("/v0.5/consents/hip/notify", status_code=status.HTTP_202_ACCEPTED)
@idempotent_webhook
async def hip_consent_notify(
    request: Request,
    body: dict[str, Any],
    x_abdm_signature: str | None = Header(None, alias="X-ABDM-Signature"),
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
@idempotent_webhook
async def hip_consent_on_notify_callback(body: dict[str, Any]) -> CallbackAck:
    """Gateway acknowledgement for consent on-notify."""
    return CallbackAck(timestamp=utc_timestamp_iso())


@router.post("/v3/hip/health-information/request", status_code=status.HTTP_202_ACCEPTED)
@router.post("/v0.5/health-information/hip/request", status_code=status.HTTP_202_ACCEPTED)
@router.post("/v0.5/health-information/request", status_code=status.HTTP_202_ACCEPTED)
@idempotent_webhook
async def hip_health_information_request(
    body: dict[str, Any],
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
@idempotent_webhook
async def hip_health_info_ack(body: dict[str, Any]) -> CallbackAck:
    """Gateway acknowledgement for on-request / delivery notify."""
    return CallbackAck(timestamp=utc_timestamp_iso())


# =============================================================================
# M3: HIU Consent Callback & Decrypted Data Push Receiver
# =============================================================================


@router.post("/v3/hiu/consent/request/notify", status_code=status.HTTP_202_ACCEPTED)
@router.post("/v0.5/consents/hiu/notify", status_code=status.HTTP_202_ACCEPTED)
@idempotent_webhook
async def hiu_consent_notify(
    request: Request,
    body: dict[str, Any],
    x_abdm_signature: str | None = Header(None, alias="X-ABDM-Signature"),
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


@router.post("/v3/hiu/consent/on-fetch", response_model=CallbackAck)
@idempotent_webhook
async def hiu_consent_on_fetch(body: dict[str, Any], db: AsyncSession = Depends(get_db)) -> CallbackAck:
    """Persist signed consent artefacts returned by the v3 Consent Manager fetch."""
    request_block = body.get("consentRequest") or body
    request_id = request_block.get("consentRequestId") or body.get("consentRequestId")
    artefacts = body.get("consentArtefacts") or body.get("consents") or []
    if request_id:
        try:
            from sqlalchemy import select

            from app.models.abdm import ABDMConsentArtefact
            row = (await db.execute(select(ABDMConsentArtefact).where(
                ABDMConsentArtefact.consent_request_id == request_id
            ))).scalar_one_or_none()
            if row:
                row.artefact_payload = {"signed_artefacts": artefacts, "fetch_response": body}
                if artefacts and isinstance(artefacts[0], dict):
                    row.signature = str(artefacts[0].get("signature") or "")
                await db.flush()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Unable to persist signed consent artefact") from exc
    return CallbackAck(timestamp=utc_timestamp_iso(), details={"consentRequestId": request_id, "stored": bool(artefacts)})


@router.post("/v3/health-information/transfer", response_model=CallbackAck, status_code=status.HTTP_202_ACCEPTED)
@router.post("/v0.5/health-information/transfer", response_model=CallbackAck, status_code=status.HTTP_202_ACCEPTED)
@idempotent_webhook
async def hiu_health_information_transfer(
    body: dict[str, Any],
) -> CallbackAck:
    """M3 HIU Data Push Receiver: decrypts incoming Fidelius-encrypted FHIR R4 bundles."""
    try:
        result = await hiu_service.on_health_information_transfer(body)
        return CallbackAck(timestamp=utc_timestamp_iso(), details=result)
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)
