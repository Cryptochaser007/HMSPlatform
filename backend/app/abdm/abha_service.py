"""
ABHAService – ABDM v3 Milestone 1 (M1) ABHA Creation, Verification & Scan-and-Share.

Supports:
- Aadhaar OTP enrolment & e-KYC verification (ABHA v3)
- Mobile OTP login & verification (ABHA v3)
- ABHA Address (@abdm / @sbx) search & profile fetch
- Persisting verified 14-digit ABHA Number, ABHA Address, KYC status & timestamp onto `patients`
- ABHA QR Scan & Share (`/v3/hip/patient-share`) instant OPD counter check-in queue
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.abdm.client import ABDMClient, ABDMError, utc_timestamp_iso
from app.abdm.config import ABDM_ENDPOINTS
from app.core.wasa_security import mask_identifier

logger = logging.getLogger("abdm.abha")

_RE_ABHA_NUM = re.compile(r"^\d{2}-?\d{4}-?\d{4}-?\d{4}$")
_RE_ABHA_ADDR = re.compile(r"^[a-zA-Z0-9._-]{3,64}@(abdm|sbx|ndhm)$", re.IGNORECASE)

# In-memory buffer for Scan & Share counter queue if DB migration 002 is not yet applied
_share_queue_memory: List[Dict[str, Any]] = []
_token_counter = 100


class ABHAProfile(BaseModel):
    """Represents a verified ABHA v3 Digital Health Account profile."""

    health_id: str = Field(..., description="ABHA address (e.g. user@sbx or user@abdm)")
    health_id_number: str = Field(
        ..., description="14-digit ABHA number (XX-XXXX-XXXX-XXXX)"
    )
    name: str = Field(..., description="Full name as on e-KYC")
    first_name: Optional[str] = Field(default=None)
    middle_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    gender: str = Field(..., description="M / F / O")
    year_of_birth: int = Field(..., ge=1900)
    month_of_birth: Optional[int] = Field(default=None, ge=1, le=12)
    day_of_birth: Optional[int] = Field(default=None, ge=1, le=31)
    address: Optional[str] = Field(default=None)
    district: Optional[str] = Field(default=None)
    state: Optional[str] = Field(default=None)
    pincode: Optional[str] = Field(default=None)
    mobile: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    profile_photo: Optional[str] = Field(default=None)
    kycVerified: bool = Field(default=False)
    kyc_status: str = Field(default="VERIFIED")
    abdm_mode: str = Field(default="MOCK")

    @property
    def date_of_birth(self) -> Optional[date]:
        if self.month_of_birth and self.day_of_birth:
            return date(self.year_of_birth, self.month_of_birth, self.day_of_birth)
        return None


class ABHAService:
    """Service layer for ABDM v3 M1 ABHA lifecycle and Scan & Share workflows."""

    def __init__(self, client: Optional[ABDMClient] = None) -> None:
        self._client = client or ABDMClient()

    # ------------------------------------------------------------------
    # M1: Aadhaar OTP flow (ABHA v3)
    # ------------------------------------------------------------------

    async def generate_aadhaar_otp(
        self, aadhaar_number: str, user_id: Optional[str] = None
    ) -> dict:
        aadhaar_clean = aadhaar_number.replace(" ", "").replace("-", "")
        if len(aadhaar_clean) != 12 or not aadhaar_clean.isdigit():
            raise ABDMError(
                message="Aadhaar number must be exactly 12 digits",
                error_code="VALIDATION",
                http_status=422,
            )

        logger.info(
            "ABHA v3 Aadhaar OTP request (masked=%s)",
            mask_identifier(aadhaar_clean, 4),
        )
        return await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["abha_aadhaar_generate_otp"],
            target="abha",
            data={
                "txnId": "",
                "scope": ["abha-enrol"],
                "loginHint": "aadhaar",
                "loginId": aadhaar_clean,
                "otpSystem": "aadhaar",
            },
            user_id=user_id,
        )

    async def verify_aadhaar_otp(
        self, txn_id: str, otp: str, mobile: Optional[str] = None, user_id: Optional[str] = None
    ) -> dict:
        otp_clean = otp.strip()
        if len(otp_clean) != 6 or not otp_clean.isdigit():
            raise ABDMError(
                message="OTP must be exactly 6 digits",
                error_code="VALIDATION",
                http_status=422,
            )
        logger.info("ABHA v3 Aadhaar OTP verify txnId=%s", txn_id)
        return await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["abha_aadhaar_verify_otp"],
            target="abha",
            data={
                "txnId": txn_id,
                "authData": {
                    "authMethods": ["otp"],
                    "otp": {
                        "txnId": txn_id,
                        "otpValue": otp_clean,
                        "mobile": mobile or "",
                    },
                },
                "consent": {"code": "abha-enrollment", "version": "1.4"},
            },
            user_id=user_id,
        )

    # ------------------------------------------------------------------
    # M1: Mobile OTP flow (ABHA v3)
    # ------------------------------------------------------------------

    async def generate_mobile_otp(
        self, mobile: str, user_id: Optional[str] = None
    ) -> dict:
        mobile_clean = mobile.replace(" ", "").replace("-", "").replace("+91", "")
        if len(mobile_clean) != 10 or not mobile_clean.isdigit():
            raise ABDMError(
                message="Mobile number must be exactly 10 digits",
                error_code="VALIDATION",
                http_status=422,
            )
        logger.info(
            "ABHA v3 Mobile OTP request (masked=%s)",
            mask_identifier(mobile_clean, 4),
        )
        return await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["abha_mobile_generate_otp"],
            target="abha",
            data={
                "scope": ["abha-login", "mobile-verify"],
                "loginHint": "mobile",
                "loginId": mobile_clean,
                "otpSystem": "abdm",
            },
            user_id=user_id,
        )

    async def verify_mobile_otp(
        self, txn_id: str, otp: str, user_id: Optional[str] = None
    ) -> dict:
        otp_clean = otp.strip()
        if len(otp_clean) != 6 or not otp_clean.isdigit():
            raise ABDMError(
                message="OTP must be exactly 6 digits",
                error_code="VALIDATION",
                http_status=422,
            )
        return await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["abha_mobile_verify_otp"],
            target="abha",
            data={
                "scope": ["abha-login", "mobile-verify"],
                "authData": {
                    "authMethods": ["otp"],
                    "otp": {"txnId": txn_id, "otpValue": otp_clean},
                },
            },
            user_id=user_id,
        )

    # ------------------------------------------------------------------
    # M1: ABHA Address Search & Profile Fetch
    # ------------------------------------------------------------------

    async def search_by_health_id(
        self, health_id: str, user_id: Optional[str] = None
    ) -> dict:
        cleaned = health_id.strip()
        if not (_RE_ABHA_NUM.match(cleaned) or _RE_ABHA_ADDR.match(cleaned)):
            raise ABDMError(
                message="Invalid ABHA format. Provide a 14-digit ABHA Number or handle ending in @abdm/@sbx",
                error_code="VALIDATION",
                http_status=422,
            )
        return await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["abha_address_search"],
            target="abha",
            data={"abhaAddress": cleaned, "healthId": cleaned},
            user_id=user_id,
        )

    async def get_abha_profile(
        self, abha_id: str, user_id: Optional[str] = None
    ) -> ABHAProfile:
        cleaned = abha_id.strip()
        result = await self._client._make_request(
            method="GET",
            endpoint=ABDM_ENDPOINTS["abha_profile"],
            target="abha",
            headers={"X-Health-Id": cleaned},
            user_id=user_id,
        )
        return self._parse_profile(result)

    # ------------------------------------------------------------------
    # M1: Persist Verified ABHA onto `patients` table
    # ------------------------------------------------------------------

    async def link_verified_abha_to_patient(
        self,
        db: AsyncSession,
        *,
        patient_id: str,
        abha_number: str,
        abha_address: str,
        kyc_status: str = "VERIFIED",
    ) -> Dict[str, Any]:
        """Store verified 14-digit ABHA number, ABHA address, KYC status & timestamp on Patient."""
        from app.models.patient import Patient

        res = await db.execute(
            select(Patient).where(Patient.id == patient_id, Patient.is_deleted == False)  # noqa: E712
        )
        patient = res.scalar_one_or_none()
        if not patient:
            raise ABDMError(
                message="Patient record not found",
                error_code="ABDM-1004",
                http_status=404,
            )

        now = datetime.now(timezone.utc)
        patient.abha_id = abha_number.strip()
        patient.abha_address = abha_address.strip().lower()
        patient.abha_kyc_status = kyc_status.upper()
        patient.abha_verified_at = now
        await db.flush()
        await db.refresh(patient)

        return {
            "patient_id": str(patient.id),
            "uhid": patient.registration_number,
            "abha_id": patient.abha_id,
            "abha_address": patient.abha_address,
            "abha_kyc_status": patient.abha_kyc_status,
            "abha_verified_at": now.isoformat(),
        }

    # ------------------------------------------------------------------
    # M1: ABHA QR Scan & Share Counter Check-in (`/v3/hip/patient-share`)
    # ------------------------------------------------------------------

    async def handle_patient_share(
        self, db: AsyncSession, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process incoming NHA ABHA QR Scan & Share webhook and issue instant OPD token."""
        global _token_counter
        _token_counter += 1

        req_id = payload.get("requestId") or str(uuid.uuid4())
        intent = payload.get("intent", {})
        meta_data = payload.get("metaData") or {}
        profile = payload.get("profile") or {}
        patient_data = profile.get("patient") or payload.get("patient") or {}

        abha_number = (
            patient_data.get("abhaNumber")
            or patient_data.get("healthIdNumber")
            or ""
        )
        abha_address = (
            patient_data.get("abhaAddress")
            or patient_data.get("healthId")
            or "unknown@sbx"
        )
        name = patient_data.get("name") or "ABHA Patient"
        gender = patient_data.get("gender") or "O"
        yob = patient_data.get("yearOfBirth")
        raw_mobile = None
        for ident in patient_data.get("identifiers", []):
            if str(ident.get("type", "")).upper() == "MOBILE":
                raw_mobile = ident.get("value")
        if not raw_mobile:
            raw_mobile = patient_data.get("phoneNumber") or patient_data.get("mobile")
        mobile_masked = mask_identifier(str(raw_mobile), 4) if raw_mobile else None

        hip_id = meta_data.get("hipId") or self._client.settings.hip_id
        counter_id = meta_data.get("context") or intent.get("type") or "OPD-COUNTER-01"
        token_number = f"TKN-{_token_counter}"
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=30)

        # Record inbound webhook in WASA transaction log
        await self._client.record_transaction(
            request_id=req_id,
            direction="INBOUND",
            http_method="POST",
            endpoint="/api/v1/abdm/v3/hip/patient-share",
            http_status=202,
            payload=payload,
        )

        # Match existing patient if already registered
        matched_patient_id: Optional[str] = None
        try:
            from app.models.patient import Patient

            if abha_number or abha_address:
                q = select(Patient).where(
                    (Patient.abha_id == abha_number) | (Patient.abha_address == abha_address)
                )
                found = (await db.execute(q)).scalar_one_or_none()
                if found:
                    matched_patient_id = str(found.id)
        except Exception:
            pass

        record_dict = {
            "id": str(uuid.uuid4()),
            "request_id": req_id,
            "hip_id": hip_id,
            "counter_id": counter_id,
            "token_number": token_number,
            "abha_number": abha_number,
            "abha_address": abha_address,
            "patient_name": name,
            "gender": gender,
            "year_of_birth": yob,
            "mobile_masked": mobile_masked,
            "patient_id": matched_patient_id,
            "status": "PENDING_CHECKIN",
            "expires_at": expires_at.isoformat(),
            "created_at": now.isoformat(),
        }

        try:
            from app.models.abdm import ABDMShareProfile

            share_row = ABDMShareProfile(
                request_id=req_id,
                hip_id=hip_id,
                counter_id=counter_id,
                token_number=token_number,
                abha_number=abha_number or None,
                abha_address=abha_address,
                patient_name=name,
                gender=gender,
                year_of_birth=int(yob) if yob else None,
                mobile_masked=mobile_masked,
                patient_id=matched_patient_id,
                status="PENDING_CHECKIN",
                expires_at=expires_at,
            )
            db.add(share_row)
            await db.flush()
            record_dict["id"] = str(share_row.id)
        except Exception as exc:
            logger.debug("Using in-memory Scan & Share queue fallback: %s", exc)
            _share_queue_memory.insert(0, record_dict)

        # Send async on-share acknowledgement back to NHA Gateway
        on_share_payload = {
            "requestId": str(uuid.uuid4()),
            "timestamp": utc_timestamp_iso(),
            "acknowledgement": {
                "status": "SUCCESS",
                "abhaAddress": abha_address,
                "profile": {
                    "context": counter_id,
                    "tokenNumber": token_number,
                    "expiry": "1800",
                },
            },
            "response": {"requestId": req_id},
        }
        try:
            await self._client._make_request(
                method="POST",
                endpoint=ABDM_ENDPOINTS["patient_share_on_share"],
                data=on_share_payload,
                correlation_id=req_id,
            )
        except Exception as exc:
            logger.warning("on-share callback dispatch warning: %s", exc)

        return {
            "status": "ACCEPTED",
            "token_number": token_number,
            "expires_in_seconds": 1800,
            "share_profile": record_dict,
        }

    async def list_share_queue(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """List recent ABHA QR Scan & Share counter check-in profiles."""
        try:
            from app.models.abdm import ABDMShareProfile

            res = await db.execute(
                select(ABDMShareProfile)
                .where(ABDMShareProfile.is_deleted == False)  # noqa: E712
                .order_by(desc(ABDMShareProfile.created_at))
                .limit(25)
            )
            rows = res.scalars().all()
            if rows:
                return [
                    {
                        "id": str(r.id),
                        "request_id": r.request_id,
                        "hip_id": r.hip_id,
                        "counter_id": r.counter_id,
                        "token_number": r.token_number,
                        "abha_number": r.abha_number,
                        "abha_address": r.abha_address,
                        "patient_name": r.patient_name,
                        "gender": r.gender,
                        "year_of_birth": r.year_of_birth,
                        "mobile_masked": r.mobile_masked,
                        "patient_id": str(r.patient_id) if r.patient_id else None,
                        "status": r.status,
                        "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                    for r in rows
                ]
        except Exception:
            pass
        return _share_queue_memory[:25]

    @staticmethod
    def _parse_profile(data: dict) -> ABHAProfile:
        phr_list = data.get("phrAddress")
        health_id = (
            data.get("healthId")
            or (phr_list[0] if isinstance(phr_list, list) and phr_list else None)
            or data.get("healthIdNumber")
            or data.get("ABHANumber")
            or ""
        )
        return ABHAProfile(
            health_id=health_id,
            health_id_number=data.get("healthIdNumber") or data.get("ABHANumber") or "",
            name=data.get("name", ""),
            first_name=data.get("firstName"),
            middle_name=data.get("middleName"),
            last_name=data.get("lastName"),
            gender=data.get("gender", "O"),
            year_of_birth=int(data.get("yearOfBirth", data.get("yob", 1990))),
            month_of_birth=data.get("monthOfBirth") or data.get("mob"),
            day_of_birth=data.get("dayOfBirth") or data.get("dob"),
            address=data.get("address"),
            district=data.get("districtName") or data.get("district"),
            state=data.get("stateName") or data.get("state"),
            pincode=data.get("pincode"),
            mobile=data.get("mobile"),
            email=data.get("email"),
            profile_photo=data.get("profilePhoto"),
            kycVerified=bool(data.get("kycVerified", True)),
            kyc_status=str(data.get("kycStatus", "VERIFIED")),
            abdm_mode=str(data.get("abdm_mode", "LIVE")),
        )


abha_service = ABHAService()
