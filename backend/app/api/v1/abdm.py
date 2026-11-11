"""ABDM public API endpoints (ABHA registration, verification, HIU consent)."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.abdm.abha_service import abha_service
from app.abdm.hiu_service import ConsentRequest, hiu_service
from app.abdm.hpr_service import hpr_service
from app.core.database import get_db
from app.core.rbac import Permission
from app.core.security import get_current_user, require_permissions

router = APIRouter(prefix="/abdm", tags=["ABDM Public Integration"])


class AadhaarOTPRequest(BaseModel):
    aadhaar_number: str


class VerifyOTPRequest(BaseModel):
    txn_id: str
    otp: str


class MobileOTPRequest(BaseModel):
    mobile_number: str


@router.post("/abha/aadhaar/otp")
async def generate_aadhaar_otp(
    data: AadhaarOTPRequest,
) -> Dict[str, Any]:
    """Request OTP from UIDAI via ABDM for Aadhaar-based ABHA creation."""
    return await abha_service.generate_aadhaar_otp(data.aadhaar_number)


@router.post("/abha/aadhaar/verify")
async def verify_aadhaar_otp(
    data: VerifyOTPRequest,
) -> Dict[str, Any]:
    """Verify Aadhaar OTP to create / fetch ABHA ID profile."""
    return await abha_service.verify_aadhaar_otp(data.txn_id, data.otp)


@router.post("/abha/mobile/otp")
async def generate_mobile_otp(
    data: MobileOTPRequest,
) -> Dict[str, Any]:
    """Request OTP for mobile-based ABHA registration."""
    return await abha_service.generate_mobile_otp(data.mobile_number)


@router.post("/abha/mobile/verify")
async def verify_mobile_otp(
    data: VerifyOTPRequest,
) -> Dict[str, Any]:
    """Verify mobile OTP for ABHA creation."""
    return await abha_service.verify_mobile_otp(data.txn_id, data.otp)


@router.get("/abha/{abha_id}/profile")
async def get_abha_profile(
    abha_id: str,
) -> Dict[str, Any]:
    """Fetch ABHA demographic details from ABDM gateway."""
    profile = await abha_service.get_abha_profile(abha_id)
    return profile.model_dump()


@router.post(
    "/consent/request",
    dependencies=[Depends(require_permissions(Permission.ABDM_FETCH.value))],
)
async def request_patient_consent_hiu(
    data: ConsentRequest,
) -> Dict[str, Any]:
    """Initiate ABDM Consent Manager request to fetch past health records from other hospitals."""
    return await hiu_service.create_consent_request(data)


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

