"""ABDM v3 API Endpoints (M1 ABHA, M2 HIP linking, M3 HIU Consent & Longitudinal Records, WASA Audit)."""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.abdm.abha_service import abha_service
from app.abdm.client import ABDMError
from app.abdm.config import get_abdm_settings
from app.abdm.hiu_service import ConsentRequest, hiu_service
from app.abdm.hpr_service import hpr_service
from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import RateLimiter
from app.core.rbac import Permission
from app.core.security import get_current_user, require_permissions

public_router = APIRouter(tags=["ABDM status"])
router = APIRouter(prefix="/abdm", tags=["ABDM v3 Integration (M1 / M2 / M3)"],
                   dependencies=[Depends(get_current_user)])

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
    mobile: str | None = Field(default=None, max_length=15)

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


class AbhaAddressEnrollRequest(BaseModel):
    txn_id: str = Field(..., min_length=4, max_length=120)
    abha_address: str = Field(..., min_length=4, max_length=255)


# =============================================================================
# Status & Diagnostics (Zero Secrets)
# =============================================================================


@public_router.get("/abdm/status")
async def get_abdm_status() -> dict[str, Any]:
    """Return active ABDM adapter mode (MOCK | SANDBOX | PRODUCTION) and safe gateway metadata."""
    return {**get_abdm_settings().public_status(), "integration_enabled": get_settings().ABDM_ENABLED}


# =============================================================================
# Milestone 1 (M1): ABHA v3 Creation, Login & Verification
# =============================================================================


@router.post(
    "/abha/aadhaar/otp",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def generate_aadhaar_otp(
    data: AadhaarOTPRequest,
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
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
    patient_abha: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List HIU consent artefacts and statuses for clinical review."""
    items = await hiu_service.list_consents(db, patient_abha=patient_abha)
    return {"items": items, "total": len(items)}


@router.post(
    "/hiu/health-info/fetch",
    dependencies=[Depends(require_permissions(Permission.ABDM_FETCH.value))],
)
async def fetch_hiu_health_info(
    data: HIUFetchRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
        logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
        return {"items": [], "total": 0, "note": "Run migrations/002_abdm_v3_exit_compliance.sql to persist logs"}


@router.get(
    "/hpr/verify",
    dependencies=[Depends(require_permissions(Permission.USER_MANAGE.value))],
)
async def verify_doctor_hpr(
    registration_number: str = Query(...),
    council: str = Query("National Medical Commission"),
) -> dict[str, Any]:
    """Verify doctor credentials against National Healthcare Professional Registry."""
    profile = await hpr_service.verify_doctor(registration_number, council)
    return profile.model_dump()


# ─── M1: Resend OTP (CRT_ABHA_106 / VRFY_ABHA_305 / VRFY_ABHA_405) ───────────


class ResendOTPRequest(BaseModel):
    txn_id: str = Field(..., min_length=4, max_length=120)
    otp_system: str = Field(default="aadhaar", pattern="^(aadhaar|abdm|mobile)$")


@router.post(
    "/abha/resend-otp",
    summary="CRT_ABHA_106 / VRFY_ABHA_305 / VRFY_ABHA_405 — Resend OTP",
    dependencies=[Depends(RateLimiter(times=3, seconds=180))],
)
async def resend_abha_otp(
    body: ResendOTPRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        result = await abha_service.resend_otp(
            txn_id=body.txn_id,
            otp_system=body.otp_system,
            user_id=str(current_user.get("id")),
        )
        return result
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 502, detail=exc.message) from exc


# ─── M1: Demographic Enrolment (CRT_ABHA_301–309) ────────────────────────────


class DemographicEnrolRequest(BaseModel):
    aadhaar_number: str = Field(..., min_length=12, max_length=16)
    name: str = Field(..., min_length=2, max_length=120)
    date_of_birth: str = Field(..., description="YYYY-MM-DD format", pattern=r"^\d{4}-\d{2}-\d{2}$")
    gender: str = Field(..., pattern="^[MFO]$")
    mobile: str = Field(..., min_length=10, max_length=15)
    state_code: str | None = Field(default=None, max_length=10)
    district_code: str | None = Field(default=None, max_length=10)
    address: str | None = Field(default=None, max_length=500)
    pincode: str | None = Field(default=None, max_length=10)
    consent_given: bool = Field(..., description="CRT_ABHA_302: User consent must be collected before enrolment")

    @field_validator("aadhaar_number")
    @classmethod
    def check_aadhaar(cls, v: str) -> str:
        cleaned = v.replace(" ", "").replace("-", "")
        if not cleaned.isdigit() or len(cleaned) != 12:
            raise ValueError("Aadhaar number must be exactly 12 digits")
        return cleaned

    @field_validator("consent_given")
    @classmethod
    def check_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("CRT_ABHA_302: User consent is mandatory before ABHA enrolment")
        return v


@router.post(
    "/abha/enrol/demographic",
    summary="CRT_ABHA_301–309 — Create ABHA via Aadhaar Demographic Authentication",
    dependencies=[Depends(RateLimiter(times=5, seconds=300))],
)
async def enrol_abha_by_demographic(
    body: DemographicEnrolRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create ABHA via demographic data (name, DOB, gender matched against Aadhaar)."""
    try:
        result = await abha_service.enrol_by_demographic(
            aadhaar_number=body.aadhaar_number,
            name=body.name,
            date_of_birth=body.date_of_birth,
            gender=body.gender,
            mobile=body.mobile,
            state_code=body.state_code,
            district_code=body.district_code,
            address=body.address,
            pincode=body.pincode,
            user_id=str(current_user.get("id")),
        )
        return result
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 502, detail=exc.message) from exc


# ─── M1: Communication Mobile Login (VRFY_ABHA_301–305) ──────────────────────


class CommunicationMobileLoginRequest(BaseModel):
    mobile: str = Field(..., min_length=10, max_length=15)

    @field_validator("mobile")
    @classmethod
    def check_mobile(cls, v: str) -> str:
        cleaned = v.replace(" ", "").replace("-", "").replace("+91", "")
        if not cleaned.isdigit() or len(cleaned) != 10:
            raise ValueError("Mobile number must be exactly 10 digits")
        return cleaned


@router.post(
    "/abha/login/mobile",
    summary="VRFY_ABHA_301 — Fetch ABHA using Communication Mobile OTP",
    dependencies=[Depends(RateLimiter(times=5, seconds=300))],
)
async def login_abha_by_mobile(
    body: CommunicationMobileLoginRequest,
    current_user: dict = Depends(get_current_user),
):
    """VRFY_ABHA_301: Request OTP for ABHA retrieval using communication mobile number."""
    try:
        result = await abha_service.login_by_communication_mobile(
            mobile=body.mobile,
            user_id=str(current_user.get("id")),
        )
        return result
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 502, detail=exc.message) from exc


@router.post(
    "/abha/login/mobile/verify",
    summary="VRFY_ABHA_302–304 — Verify Mobile OTP and retrieve ABHA list",
    dependencies=[Depends(RateLimiter(times=5, seconds=300))],
)
async def verify_abha_mobile_login(
    body: VerifyOTPRequest,
    current_user: dict = Depends(get_current_user),
):
    """VRFY_ABHA_302–304: Verify OTP and get list of ABHA Numbers linked to mobile."""
    try:
        result = await abha_service.verify_communication_mobile_otp(
            txn_id=body.txn_id,
            otp=body.otp,
            user_id=str(current_user.get("id")),
        )
        return result
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 502, detail=exc.message) from exc


# ─── M1: Aadhaar Login OTP (VRFY_ABHA_101/401) ───────────────────────────────


@router.post(
    "/abha/login/aadhaar",
    summary="VRFY_ABHA_101/401 — Initiate ABHA Verification via Aadhaar OTP",
    dependencies=[Depends(RateLimiter(times=5, seconds=300))],
)
async def login_abha_by_aadhaar(
    body: AadhaarOTPRequest,
    current_user: dict = Depends(get_current_user),
):
    """VRFY_ABHA_101/401: Request Aadhaar OTP for ABHA number verification/retrieval."""
    try:
        result = await abha_service.login_by_aadhaar_otp(
            aadhaar_number=body.aadhaar_number,
            user_id=str(current_user.get("id")),
        )
        return result
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 502, detail=exc.message) from exc


@router.post(
    "/abha/login/aadhaar/verify",
    summary="VRFY_ABHA_101/401 — Verify Aadhaar OTP for ABHA login",
    dependencies=[Depends(RateLimiter(times=5, seconds=300))],
)
async def verify_abha_aadhaar_login(
    body: VerifyOTPRequest,
    current_user: dict = Depends(get_current_user),
):
    """VRFY_ABHA_101/401: Verify Aadhaar OTP and retrieve ABHA profile."""
    try:
        result = await abha_service.verify_aadhaar_login_otp(
            txn_id=body.txn_id,
            otp=body.otp,
            user_id=str(current_user.get("id")),
        )
        return result
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 502, detail=exc.message) from exc


# ─── M1: ABHA Card & QR (CRT_ABHA_114/209/308) ───────────────────────────────


class AbhaCardRequest(BaseModel):
    abha_token: str = Field(
        ...,
        min_length=4,
        max_length=1024,
        description="X-Token from ABHA enrolment/login response",
    )


@router.post("/abha/card", summary="CRT_ABHA_114/209/308 — Fetch ABHA Card (image + demographics)")
async def get_abha_card_data(
    body: AbhaCardRequest,
    current_user: dict = Depends(get_current_user),
):
    """CRT_ABHA_114: Returns ABHA card with ABHA number, name, DOB, gender, QR code."""
    try:
        result = await abha_service.get_abha_card(
            abha_token=body.abha_token,
            user_id=str(current_user.get("id")),
        )
        return result
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 502, detail=exc.message) from exc


@router.post("/abha/qr", summary="CRT_ABHA_114 — Fetch ABHA QR Code")
async def get_abha_qr_code(
    body: AbhaCardRequest,
    current_user: dict = Depends(get_current_user),
):
    """CRT_ABHA_114: Returns ABHA QR code for printing on registration counter."""
    try:
        result = await abha_service.get_abha_qr(
            abha_token=body.abha_token,
            user_id=str(current_user.get("id")),
        )
        return result
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 502, detail=exc.message) from exc


# ─── M1: ABHA Address Suggestions (CRT_ABHA_112) ─────────────────────────────


@router.get(
    "/abha/suggestions",
    summary="CRT_ABHA_112 — Get ABHA Address Suggestions (3+ options)",
)
async def get_abha_address_suggestions(
    txn_id: str = Query(..., min_length=4, max_length=120),
    current_user: dict = Depends(get_current_user),
):
    """CRT_ABHA_112: Returns at least 3 available ABHA address suggestions for user selection."""
    try:
        result = await abha_service.get_abha_address_suggestions(
            txn_id=txn_id,
            user_id=str(current_user.get("id")),
        )
        return result
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 502, detail=exc.message) from exc


@router.post("/abha/address/enrol", dependencies=[Depends(RateLimiter(times=5, seconds=300))])
async def enrol_abha_address(
    data: AbhaAddressEnrollRequest,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Select and enrol an ABHA address suggested for the active transaction."""
    try:
        return await abha_service.enrol_abha_address(
            data.txn_id, data.abha_address, user_id=str(current_user["user_id"])
        )
    except ABDMError as exc:
        raise HTTPException(status_code=exc.http_status or 502, detail=exc.message) from exc
