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
import json
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.abdm.client import ABDMClient, ABDMError, utc_timestamp_iso
from app.abdm.config import ABDM_ENDPOINTS, ABDMMode
from app.core.wasa_security import mask_identifier

logger = logging.getLogger("abdm.abha")

_RE_ABHA_NUM = re.compile(r"^\d{2}-?\d{4}-?\d{4}-?\d{4}$")
_RE_ABHA_ADDR = re.compile(r"^[a-zA-Z0-9._-]{3,64}@(abdm|sbx|ndhm)$", re.IGNORECASE)

# In-memory buffer for Scan & Share counter queue if DB migration 002 is not yet applied
_SHARE_QUEUE_KEY = "abdm:share:queue"


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
        login_id_val = aadhaar_clean
        if self._client.mode != ABDMMode.MOCK:
            try:
                cert = await self.get_nha_public_certificate()
                login_id_val = self.encrypt_with_nha_rsa_oaep(aadhaar_clean, cert)
            except Exception as exc:
                logger.warning("Could not encrypt Aadhaar with NHA cert: %s", exc)

        return await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["abha_aadhaar_generate_otp"],
            target="abha",
            data={
                "txnId": "",
                "scope": ["abha-enrol"],
                "loginHint": "aadhaar",
                "loginId": login_id_val,
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
        otp_val = otp_clean
        if self._client.mode != ABDMMode.MOCK:
            try:
                cert = await self.get_nha_public_certificate()
                otp_val = self.encrypt_with_nha_rsa_oaep(otp_clean, cert)
            except Exception as exc:
                logger.warning("Could not encrypt OTP with NHA cert: %s", exc)

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
                        "otpValue": otp_val,
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
        from app.core.redis_state import get_redis
        day_key = datetime.now(timezone.utc).strftime("%Y%m%d")
        token_number = f"TKN-{await (await get_redis()).incr(f'abdm:share:token:{day_key}') }"
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
            try:
                await db.rollback()
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
            try:
                await db.rollback()
            except Exception:
                pass
            # Redis fallback is shared across workers; protect the patient profile at rest.
            from app.core.encryption import encrypt_field
            queue = await get_redis()
            await queue.lpush(_SHARE_QUEUE_KEY, encrypt_field(json.dumps(record_dict, separators=(",", ":"))))
            await queue.ltrim(_SHARE_QUEUE_KEY, 0, 499)

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
        from app.core.redis_state import get_redis
        from app.core.encryption import decrypt_field
        queue = await get_redis()
        values = await queue.lrange(_SHARE_QUEUE_KEY, 0, 24)
        return [json.loads(decrypt_field(value)) for value in values]

    # ------------------------------------------------------------------
    # M1: RSA-OAEP NHA Public Certificate Fetching & Encryption (SANDBOX mode)
    # ------------------------------------------------------------------

    async def get_nha_public_certificate(self) -> str:
        """Fetch NHA RSA public certificate for SANDBOX/PRODUCTION Aadhaar/OTP encryption.

        Endpoint: GET /profile/public/certificate
        Cached in memory for 23 hours.
        Returns PEM-encoded public key string.
        """
        import time as _time

        now = _time.time()
        cached = getattr(self, "_nha_cert_cache", None)
        cached_at = getattr(self, "_nha_cert_cached_at", 0.0)
        if cached and (now - cached_at) < 82800:
            return cached

        logger.info("Fetching NHA RSA public certificate for OTP encryption")
        result = await self._client._make_request(
            method="GET",
            endpoint=ABDM_ENDPOINTS.get("abha_public_cert", "/profile/public/certificate"),
            target="abha",
        )
        cert = result.get("publicKey") or result.get("certificate") or result.get("cert") or ""
        if not cert:
            raise ABDMError(
                message="NHA public certificate response missing publicKey field",
                error_code="ABDM-CERT",
                http_status=502,
            )
        self._nha_cert_cache = cert
        self._nha_cert_cached_at = now
        return cert

    @staticmethod
    def encrypt_with_nha_rsa_oaep(plaintext: str, public_key_pem: str) -> str:
        """Encrypt plaintext using NHA's RSA public key with OAEP-SHA1 padding.

        Required by ABDM v3 for encrypting Aadhaar number and OTP values
        before sending to NHA endpoints in SANDBOX/PRODUCTION mode.
        Returns base64-encoded ciphertext string.
        """
        try:
            import base64
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

            public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
            ciphertext = public_key.encrypt(
                plaintext.encode("utf-8"),
                asym_padding.OAEP(
                    mgf=asym_padding.MGF1(algorithm=hashes.SHA1()),  # noqa: S303
                    algorithm=hashes.SHA1(),  # noqa: S303
                    label=None,
                ),
            )
            return base64.b64encode(ciphertext).decode("utf-8")
        except ImportError as exc:
            raise ABDMError(
                message="cryptography library required for SANDBOX mode RSA encryption",
                error_code="ABDM-DEPS",
                http_status=500,
            ) from exc
        except Exception as exc:
            raise ABDMError(
                message=f"RSA-OAEP encryption failed: {exc}",
                error_code="ABDM-ENCRYPT",
                http_status=500,
            ) from exc

    # ------------------------------------------------------------------
    # M1: Resend OTP (CRT_ABHA_106 / VRFY_ABHA_305 / VRFY_ABHA_405)
    # ------------------------------------------------------------------

    async def resend_otp(
        self, txn_id: str, otp_system: str = "aadhaar", user_id: Optional[str] = None
    ) -> dict:
        """Resend OTP for existing transaction (max 2 times per NHA spec).

        CRT_ABHA_106: Resend OTP button activatable max 2 times after 60 seconds.
        """
        logger.info("ABHA v3 Resend OTP txnId=%s system=%s", txn_id, otp_system)
        return await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS.get("abha_resend_otp", "/enrollment/request/otp"),
            target="abha",
            data={
                "txnId": txn_id,
                "scope": ["abha-enrol"] if otp_system == "aadhaar" else ["abha-login", "mobile-verify"],
                "loginHint": "aadhaar" if otp_system == "aadhaar" else "mobile",
                "otpSystem": otp_system,
            },
            user_id=user_id,
        )

    # ------------------------------------------------------------------
    # M1: Demographic Auth (CRT_ABHA_301–309)
    # ------------------------------------------------------------------

    async def enrol_by_demographic(
        self,
        *,
        aadhaar_number: str,
        name: str,
        date_of_birth: str,
        gender: str,
        mobile: str,
        state_code: Optional[str] = None,
        district_code: Optional[str] = None,
        address: Optional[str] = None,
        pincode: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Create ABHA via Aadhaar demographic authentication (no OTP)."""
        aadhaar_clean = aadhaar_number.replace(" ", "").replace("-", "")
        if len(aadhaar_clean) != 12 or not aadhaar_clean.isdigit():
            raise ABDMError(
                message="Aadhaar number must be exactly 12 digits",
                error_code="VALIDATION",
                http_status=422,
            )

        gender_upper = gender.strip().upper()
        if gender_upper not in ("M", "F", "O"):
            raise ABDMError(
                message="Gender must be M, F, or O",
                error_code="VALIDATION",
                http_status=422,
            )

        try:
            from datetime import date

            dob_parts = date_of_birth.split("-")
            if len(dob_parts) != 3:
                raise ValueError("bad format")
            date(int(dob_parts[0]), int(dob_parts[1]), int(dob_parts[2]))
        except (ValueError, IndexError) as exc:
            raise ABDMError(
                message="date_of_birth must be in YYYY-MM-DD format",
                error_code="VALIDATION",
                http_status=422,
            ) from exc

        logger.info(
            "ABHA v3 Demographic enrolment (aadhaar_masked=%s)",
            mask_identifier(aadhaar_clean, 4),
        )

        return await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS.get("abha_demographic_enrol", "/enrollment/enrol/byAadhaar"),
            target="abha",
            data={
                "txnId": "",
                "scope": ["abha-enrol"],
                "authData": {
                    "authMethods": ["demographics"],
                    "demographics": {
                        "aadhaarNumber": aadhaar_clean,
                        "name": name.strip(),
                        "gender": gender_upper,
                        "dateOfBirth": date_of_birth,
                        "mobile": mobile.replace(" ", "").replace("-", "").replace("+91", ""),
                        **({"stateCode": state_code} if state_code else {}),
                        **({"districtCode": district_code} if district_code else {}),
                        **({"address": address} if address else {}),
                        **({"pincode": pincode} if pincode else {}),
                    },
                },
                "consent": {"code": "abha-enrollment", "version": "1.4"},
            },
            user_id=user_id,
        )

    # ------------------------------------------------------------------
    # M1: Communication Mobile Login (VRFY_ABHA_301–305)
    # ------------------------------------------------------------------

    async def login_by_communication_mobile(
        self, mobile: str, user_id: Optional[str] = None
    ) -> dict:
        """Initiate ABHA retrieval/login using communication mobile number."""
        mobile_clean = mobile.replace(" ", "").replace("-", "").replace("+91", "")
        if len(mobile_clean) != 10 or not mobile_clean.isdigit():
            raise ABDMError(
                message="Mobile number must be exactly 10 digits",
                error_code="VALIDATION",
                http_status=422,
            )

        logger.info(
            "ABHA v3 Communication Mobile login OTP (masked=%s)",
            mask_identifier(mobile_clean, 4),
        )
        return await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS.get("abha_login_request_otp", "/profile/login/request/otp"),
            target="abha",
            data={
                "scope": ["abha-login"],
                "loginHint": "mobile",
                "loginId": mobile_clean,
                "otpSystem": "abdm",
            },
            user_id=user_id,
        )

    async def verify_communication_mobile_otp(
        self, txn_id: str, otp: str, user_id: Optional[str] = None
    ) -> dict:
        """Verify OTP for communication mobile login and return matching ABHA list."""
        otp_clean = otp.strip()
        if len(otp_clean) != 6 or not otp_clean.isdigit():
            raise ABDMError(
                message="OTP must be exactly 6 digits",
                error_code="VALIDATION",
                http_status=422,
            )
        return await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS.get("abha_login_verify_otp", "/profile/login/verify"),
            target="abha",
            data={
                "scope": ["abha-login"],
                "authData": {
                    "authMethods": ["otp"],
                    "otp": {"txnId": txn_id, "otpValue": otp_clean},
                },
            },
            user_id=user_id,
        )

    # ------------------------------------------------------------------
    # M1: ABHA Login by Aadhaar OTP (VRFY_ABHA_101/401)
    # ------------------------------------------------------------------

    async def login_by_aadhaar_otp(
        self, aadhaar_number: str, user_id: Optional[str] = None
    ) -> dict:
        """Initiate ABHA verification/login using Aadhaar OTP."""
        aadhaar_clean = aadhaar_number.replace(" ", "").replace("-", "")
        if len(aadhaar_clean) != 12 or not aadhaar_clean.isdigit():
            raise ABDMError(
                message="Aadhaar number must be exactly 12 digits",
                error_code="VALIDATION",
                http_status=422,
            )
        logger.info(
            "ABHA v3 Aadhaar login OTP request (masked=%s)",
            mask_identifier(aadhaar_clean, 4),
        )
        return await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS.get("abha_login_request_otp", "/profile/login/request/otp"),
            target="abha",
            data={
                "scope": ["abha-login"],
                "loginHint": "aadhaar",
                "loginId": aadhaar_clean,
                "otpSystem": "aadhaar",
            },
            user_id=user_id,
        )

    async def verify_aadhaar_login_otp(
        self, txn_id: str, otp: str, user_id: Optional[str] = None
    ) -> dict:
        """Verify Aadhaar OTP for ABHA login and return ABHA profile."""
        otp_clean = otp.strip()
        if len(otp_clean) != 6 or not otp_clean.isdigit():
            raise ABDMError(
                message="OTP must be exactly 6 digits",
                error_code="VALIDATION",
                http_status=422,
            )
        return await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS.get("abha_login_verify_otp", "/profile/login/verify"),
            target="abha",
            data={
                "scope": ["abha-login"],
                "authData": {
                    "authMethods": ["otp"],
                    "otp": {"txnId": txn_id, "otpValue": otp_clean},
                },
            },
            user_id=user_id,
        )

    # ------------------------------------------------------------------
    # M1: ABHA Card Data Fetch (CRT_ABHA_114/209/308)
    # ------------------------------------------------------------------

    async def get_abha_card(
        self, abha_token: str, user_id: Optional[str] = None
    ) -> dict:
        """Fetch ABHA card data including QR code and demographics."""
        return await self._client._make_request(
            method="GET",
            endpoint=ABDM_ENDPOINTS.get("abha_card", "/profile/account/abha-card"),
            target="abha",
            headers={"X-Token": f"Bearer {abha_token}"},
            user_id=user_id,
        )

    async def get_abha_qr(
        self, abha_token: str, user_id: Optional[str] = None
    ) -> dict:
        """Fetch ABHA QR code for display on registration counter."""
        return await self._client._make_request(
            method="GET",
            endpoint=ABDM_ENDPOINTS.get("abha_qr", "/profile/account/qrCode"),
            target="abha",
            headers={"X-Token": f"Bearer {abha_token}"},
            user_id=user_id,
        )

    # ------------------------------------------------------------------
    # M1: ABHA Address Suggestions (CRT_ABHA_112)
    # ------------------------------------------------------------------

    async def get_abha_address_suggestions(
        self, txn_id: str, user_id: Optional[str] = None
    ) -> dict:
        """Get at least 3 ABHA address suggestions after OTP verification."""
        return await self._client._make_request(
            method="GET",
            endpoint=ABDM_ENDPOINTS.get("abha_address_suggestions", "/enrollment/enrol/suggestions"),
            target="abha",
            headers={"txnId": txn_id},
            user_id=user_id,
        )

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
