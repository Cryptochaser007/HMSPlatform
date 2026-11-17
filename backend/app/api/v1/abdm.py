"""ABDM v3 API Endpoints (M1 ABHA, M2 HIP linking, M3 HIU Consent & Longitudinal Records, WASA Audit)."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.abdm.abha_service import abha_service
from app.abdm.client import ABDMError
from app.abdm.config import get_abdm_settings
from app.abdm.hiu_service import ConsentRequest, hiu_service
from app.abdm.hpr_service import hpr_service
from app.core.database import get_db
from app.core.dependencies import RateLimiter
from app.core.rbac import Permission
from app.core.security import get_current_user, require_permissions

router = APIRouter(prefix="/abdm", tags=["ABDM v3 Integration (M1 / M2 / M3)"])

_RE_DANGEROUS = re.compile(r"[<>\"';`]")


class AadhaarOTPRequest(BaseModel):
    aadhaar_number: str = Field(..., min_length=12, max_length=16)

    @field_validator("aadhaar_number")
    @classmethod
    def check_digits(cls, v: str) -> str:
        cleaned = v.replace(" ", "").replace("-", "")
        if not cleaned.isdigit() or len(cleaned) != 12:
            raise ValueError("Aadhaar number must be exactly 12 digits")
        return cleaned


class VerifyOTPRequest(BaseModel):
    txn_id: str = Field(..., min_length=4, max_length=120)
    otp: str = Field(..., min_length=6, max_length=6)
    mobile: Optional[str] = Field(default=None, max_length=15)

    @field_validator("otp")
    @classmethod
    def check_otp(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP must contain 6 digits only")
        return v


class MobileOTPRequest(BaseModel):
    mobile_number: str = Field(..., min_length=10, max_length=15)

    @field_validator("mobile_number")
    @classmethod
    def check_mobile(cls, v: str) -> str:
        cleaned = v.replace(" ", "").replace("-", "").replace("+91", "")
        if not cleaned.isdigit() or len(cleaned) != 10:
            raise ValueError("Mobile number must be exactly 10 digits")
        return cleaned


class AbhaSearchRequest(BaseModel):
    abha_id: str = Field(..., min_length=4, max_length=100)

    @field_validator("abha_id")
    @classmethod
    def check_safe(cls, v: str) -> str:
        if _RE_DANGEROUS.search(v):
            raise ValueError("Invalid characters in ABHA identifier")
        return v.strip()


class LinkPatientAbhaRequest(BaseModel):
    patient_id: str = Field(..., min_length=8, max_length=64)
    abha_number: str = Field(..., min_length=14, max_length=20)
    abha_address: str = Field(..., min_length=4, max_length=255)
    kyc_status: str = Field(default="VERIFIED", max_length=30)


class HIUFetchRequest(BaseModel):
    consent_artefact_id: str = Field(..., min_length=4, max_length=120)


# =============================================================================
# Status & Diagnostics (Zero Secrets)
# =============================================================================


@router.get("/status")
async def get_abdm_status() -> Dict[str, Any]:
    """Return active ABDM adapter mode (MOCK | SANDBOX | PRODUCTION) and safe gateway metadata."""
    return get_abdm_settings().public_status()


# =============================================================================
# Milestone 1 (M1): ABHA v3 Creation, Login & Verification
# =============================================================================


@router.post(
    "/abha/aadhaar/otp",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def generate_aadhaar_otp(
    data: AadhaarOTPRequest,
) -> Dict[str, Any]:
    """Request OTP from UIDAI via ABDM v3 for Aadhaar-based ABHA creation."""
    try:
        return await abha_service.generate_aadhaar_otp(data.aadhaar_number)
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


@router.post(
    "/abha/aadhaar/verify",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
)
async def verify_aadhaar_otp(
    data: VerifyOTPRequest,
) -> Dict[str, Any]:
    """Verify Aadhaar OTP to create / fetch ABHA v3 e-KYC profile."""
    try:
        return await abha_service.verify_aadhaar_otp(data.txn_id, data.otp, mobile=data.mobile)
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


@router.post(
    "/abha/mobile/otp",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def generate_mobile_otp(
    data: MobileOTPRequest,
) -> Dict[str, Any]:
    """Request OTP for ABDM v3 mobile-based ABHA login / registration."""
    try:
        return await abha_service.generate_mobile_otp(data.mobile_number)
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


@router.post(
    "/abha/mobile/verify",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
)
async def verify_mobile_otp(
    data: VerifyOTPRequest,
) -> Dict[str, Any]:
    """Verify ABDM v3 mobile OTP."""
    try:
        return await abha_service.verify_mobile_otp(data.txn_id, data.otp)
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


@router.post(
    "/abha/address/search",
    dependencies=[Depends(RateLimiter(times=20, seconds=60))],
)
async def search_abha_address(
    data: AbhaSearchRequest,
) -> Dict[str, Any]:
    """Search / verify ABHA Address (@abdm / @sbx) or 14-digit ABHA Number via ABDM v3."""
    try:
        return await abha_service.search_by_health_id(data.abha_id)
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


@router.get(
    "/abha/{abha_id}/profile",
    dependencies=[Depends(RateLimiter(times=20, seconds=60))],
)
async def get_abha_profile(
    abha_id: str,
) -> Dict[str, Any]:
    """Fetch ABHA v3 demographic details from ABDM gateway."""
    if _RE_DANGEROUS.search(abha_id):
        raise HTTPException(status_code=422, detail="Invalid ABHA identifier format")
    try:
        profile = await abha_service.get_abha_profile(abha_id)
        return profile.model_dump()
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


@router.post(
    "/abha/link-patient",
    dependencies=[Depends(require_permissions(Permission.ABDM_LINK.value))],
)
async def link_verified_abha_to_patient(
    data: LinkPatientAbhaRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Persist verified 14-digit ABHA Number, ABHA Address, KYC status & timestamp on Patient."""
    try:
        return await abha_service.link_verified_abha_to_patient(
            db,
            patient_id=data.patient_id,
            abha_number=data.abha_number,
            abha_address=data.abha_address,
            kyc_status=data.kyc_status,
        )
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


# =============================================================================
# Milestone 3 (M3): HIU Consent Initiation & Longitudinal Health Record Viewer
# =============================================================================


@router.post(
    "/consent/request",
    dependencies=[Depends(require_permissions(Permission.ABDM_FETCH.value))],
)
@router.post(
    "/hiu/consent/request",
    dependencies=[Depends(require_permissions(Permission.ABDM_FETCH.value))],
)
async def request_patient_consent_hiu(
    data: ConsentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Initiate ABDM Consent Manager request to fetch longitudinal health records."""
    db_user = current_user.get("db_user")
    try:
        return await hiu_service.create_consent_request(
            db,
            data,
            requester_name=getattr(db_user, "full_name", "Consulting Physician"),
            requester_reg=getattr(db_user, "registration_number", None) or "NMC-2018-94021",
            user_id=current_user["user_id"],
        )
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


@router.get(
    "/hiu/consents",
    dependencies=[Depends(require_permissions(Permission.ABDM_FETCH.value))],
)
async def list_hiu_consents(
    patient_abha: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """List HIU consent artefacts and statuses for clinical review."""
    items = await hiu_service.list_consents(db, patient_abha=patient_abha)
    return {"items": items, "total": len(items)}


@router.post(
    "/hiu/health-info/fetch",
    dependencies=[Depends(require_permissions(Permission.ABDM_FETCH.value))],
)
async def fetch_hiu_health_info(
    data: HIUFetchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Request health info using Fidelius Curve25519 keypair and decrypt incoming FHIR R4 bundles."""
    try:
        return await hiu_service.fetch_health_info(
            db, data.consent_artefact_id, user_id=current_user["user_id"]
        )
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 400, detail=exc.message)


@router.get(
    "/hiu/records/{patient_abha}",
    dependencies=[Depends(require_permissions(Permission.ABDM_FETCH.value))],
)
async def get_hiu_longitudinal_records(
    patient_abha: str,
) -> Dict[str, Any]:
    """Return decrypted FHIR R4 Longitudinal Health Record timeline for the Doctor EMR."""
    if _RE_DANGEROUS.search(patient_abha):
        raise HTTPException(status_code=422, detail="Invalid ABHA address")
    items = hiu_service.get_longitudinal_records(patient_abha)
    return {"patient_abha": patient_abha, "items": items, "total": len(items)}


# =============================================================================
# WASA & NHA Functional Evidence: Immutable ABDM Transaction Audit Logs
# =============================================================================


@router.get(
    "/transactions",
    dependencies=[Depends(require_permissions(Permission.AUDIT_READ.value))],
)
async def list_abdm_transaction_logs(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve immutable, PII-masked ABDM API transaction logs for WASA / NHA Exit audits."""
    try:
        from app.models.abdm import ABDMTransactionLog

        res = await db.execute(
            select(ABDMTransactionLog)
            .order_by(desc(ABDMTransactionLog.created_at))
            .limit(limit)
        )
        rows = res.scalars().all()
        items = [
            {
                "id": str(r.id),
                "request_id": r.request_id,
                "correlation_id": r.correlation_id,
                "direction": r.direction,
                "abdm_env": r.abdm_env,
                "x_cm_id": r.x_cm_id,
                "http_method": r.http_method,
                "endpoint": r.endpoint,
                "http_status": r.http_status,
                "payload_sha256": r.payload_sha256,
                "masked_summary": r.masked_summary,
                "error_code": r.error_code,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
        return {"items": items, "total": len(items)}
    except Exception:
        return {"items": [], "total": 0, "note": "Run migrations/002_abdm_v3_exit_compliance.sql to persist logs"}


@router.get(
    "/hpr/verify",
    dependencies=[Depends(require_permissions(Permission.USER_MANAGE.value))],
)
async def verify_doctor_hpr(
    registration_number: str = Query(...),
    council: str = Query("National Medical Commission"),
) -> Dict[str, Any]:
    """Verify doctor credentials against National Healthcare Professional Registry."""
    profile = await hpr_service.verify_doctor(registration_number, council)
    return profile.model_dump()
