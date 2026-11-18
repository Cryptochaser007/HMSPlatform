"""
ABDMClient – Strategy/Adapter HTTP Client for ABDM v3 & v0.5 Gateway.

Strictly controlled by ``ABDM_ENV`` (MOCK | SANDBOX | PRODUCTION):
- ``MOCK``       -> ``MockABDMAdapter`` (zero outbound calls, deterministic responses)
- ``SANDBOX``    -> ``LiveABDMAdapter`` (official NHA Sandbox endpoints + OAuth2)
- ``PRODUCTION`` -> ``LiveABDMAdapter`` (official NHA Production endpoints + OAuth2)

Every outbound call attaches mandatory NHA headers:
  ``X-CM-ID``, ``REQUEST-ID``, ``TIMESTAMP``, ``Authorization: Bearer ...``
and records an immutable, PII-masked audit entry into ``abdm_transaction_logs``.
"""

from __future__ import annotations

import abc
import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from app.abdm.config import ABDMMode, ABDMSettings, get_abdm_settings
from app.core.wasa_security import compute_payload_sha256, mask_pii_dict

logger = logging.getLogger("abdm.client")


class ABDMError(Exception):
    """Exception raised for ABDM-specific API errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        http_status: Optional[int] = None,
        details: Optional[dict] = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.http_status = http_status
        self.details = details or {}
        super().__init__(self.message)


ABDM_ERROR_MESSAGES: dict[str, str] = {
    "ABDM-1001": "Invalid Aadhaar number",
    "ABDM-1002": "OTP expired or invalid",
    "ABDM-1003": "ABHA ID already exists for this Aadhaar",
    "ABDM-1004": "Patient not found",
    "ABDM-1005": "Consent request expired",
    "ABDM-1006": "Consent denied by patient",
    "ABDM-1007": "Invalid health information request",
    "ABDM-1008": "Facility not registered with ABDM",
    "ABDM-1009": "Professional not found in HPR",
    "ABDM-1010": "Session expired – re-authenticate",
    "ABDM-1011": "Rate limit exceeded",
    "ABDM-1012": "Gateway unavailable",
}


def utc_timestamp_iso() -> str:
    """Return NHA-compliant UTC ISO-8601 timestamp with millisecond precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# ---------------------------------------------------------------------------
# Strategy / Adapter Interface
# ---------------------------------------------------------------------------


class BaseABDMAdapter(abc.ABC):
    """Abstract adapter interface for ABDM Gateway & ABHA v3 communication."""

    def __init__(self, settings: ABDMSettings) -> None:
        self.settings = settings

    @abc.abstractmethod
    async def get_access_token(self) -> str:
        """Obtain (or return cached) OAuth2 bearer token."""

    @abc.abstractmethod
    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
        *,
        target: str = "gateway",
        sign: bool = False,
        require_auth: bool = True,
        request_id: Optional[str] = None,
    ) -> tuple[int, dict]:
        """Execute an ABDM call and return ``(http_status, response_dict)``."""

    async def close(self) -> None:
        """Release underlying HTTP resources."""


# ---------------------------------------------------------------------------
# Strategy 1: Deterministic MOCK Adapter (ABDM_ENV=MOCK)
# ---------------------------------------------------------------------------


class MockABDMAdapter(BaseABDMAdapter):
    """Zero-network deterministic ABDM v3/v0.5 mock adapter for dry-run & testing."""

    async def get_access_token(self) -> str:
        return "mock-abdm-v3-session-token"

    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
        *,
        target: str = "gateway",
        sign: bool = False,
        require_auth: bool = True,
        request_id: Optional[str] = None,
    ) -> tuple[int, dict]:
        data = data or {}
        headers = headers or {}
        req_id = request_id or str(uuid.uuid4())

        # 0. M1: NHA RSA Public Certificate (SANDBOX/PRODUCTION mode)
        if "public/certificate" in endpoint:
            return 200, {
                "publicKey": (
                    "-----BEGIN PUBLIC KEY-----\n"
                    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2a2rwplBQLzHPZe5TNJG\n"
                    "nI8M2PkFPNTa4WOEaOFOmRDMBQ7t3MRB3bFj29Ew8RxF5OgQG2Mg7kAhkKkD1+m\n"
                    "mock_key_data_for_testing_only_not_real_nha_key_do_not_use_production\n"
                    "-----END PUBLIC KEY-----"
                ),
                "abdm_mode": "MOCK",
            }

        # 0b. M1: ABHA Address Suggestions (CRT_ABHA_112)
        if "suggestions" in endpoint:
            cm_id = self.settings.x_cm_id
            return 200, {
                "txnId": data.get("txnId", "mock-txn"),
                "abhaAddressList": [
                    f"arun.kumar@{cm_id}",
                    f"arun.kumar99@{cm_id}",
                    f"arunkumar1991@{cm_id}",
                    f"arun.k.1991@{cm_id}",
                ],
                "abdm_mode": "MOCK",
            }

        # 0c. M1: ABHA Card (CRT_ABHA_114/209/308)
        if "abha-card" in endpoint or "abha_card" in endpoint:
            import base64 as _b64
            svg = (
                b'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">'
                b'<rect width="400" height="200" fill="#1a73e8"/>'
                b'<text x="20" y="40" fill="white" font-size="16">ABHA Card</text>'
                b'<text x="20" y="70" fill="white" font-size="12">91-4829-1029-4721</text>'
                b'<text x="20" y="95" fill="white" font-size="12">Arun Kumar | M | 1991</text>'
                b'<text x="20" y="120" fill="#ffeb3b" font-size="10">Sandbox Simulation</text>'
                b'</svg>'
            )
            return 200, {
                "cardImage": _b64.b64encode(svg).decode(),
                "mimeType": "image/svg+xml",
                "ABHANumber": "91-4829-1029-4721",
                "name": "Arun Kumar",
                "gender": "M",
                "yearOfBirth": 1991,
                "abdm_mode": "MOCK",
            }

        # 0d. M1: ABHA QR Code (CRT_ABHA_114)
        if "qrCode" in endpoint or "qr" in endpoint.lower():
            import base64 as _b64, json as _json
            qr_data = _json.dumps({
                "hidn": "91-4829-1029-4721",
                "hid": f"arun.kumar@{self.settings.x_cm_id}",
                "name": "Arun Kumar",
                "gender": "M",
                "dob": "1991-05-14",
                "address": "Bengaluru Urban, Karnataka",
            })
            return 200, {
                "qrData": _b64.b64encode(qr_data.encode()).decode(),
                "qrString": qr_data,
                "abdm_mode": "MOCK",
            }

        # 1. M1: Aadhaar OTP Request (v3)
        if "request/otp" in endpoint or "aadhaar/generateOtp" in endpoint:
            raw_id = str(data.get("loginId") or data.get("aadhaar") or "999988887777")
            last4 = raw_id[-4:] if len(raw_id) >= 4 else "7777"
            is_mobile = "mobile" in endpoint or len(raw_id) == 10
            return 200, {
                "txnId": f"abdm-v3-txn-{uuid.uuid4().hex[:10]}",
                "message": (
                    f"OTP sent to registered mobile ending in ...{last4}"
                    if is_mobile
                    else f"OTP sent to Aadhaar-linked mobile ending in ...{last4}"
                ),
                "mobileNumber": f"XXXXXX{last4}",
                "abdm_mode": "MOCK",
            }

        # 2a. M1: Demographic Enrolment (CRT_ABHA_301-309)
        if "enrol/byAadhaar" in endpoint:
            auth_data = data.get("authData", {})
            if "demographics" in auth_data.get("authMethods", []):
                demo = auth_data.get("demographics", {})
                name = demo.get("name", "Demo Patient")
                gender = demo.get("gender", "M")
                dob = demo.get("dateOfBirth", "1990-01-01")
                txn_id = data.get("txnId") or f"abdm-demo-txn-{uuid.uuid4().hex[:10]}"
                cm_id = self.settings.x_cm_id
                return 200, {
                    "txnId": txn_id,
                    "token": f"mock-abdm-v3-phr-token-{req_id[:8]}",
                    "ABHANumber": "91-4829-1029-4721",
                    "healthIdNumber": "91-4829-1029-4721",
                    "phrAddress": [f"demo.patient@{cm_id}"],
                    "healthId": f"demo.patient@{cm_id}",
                    "name": name,
                    "gender": gender,
                    "dateOfBirth": dob,
                    "mobile": demo.get("mobile", "9876543210"),
                    "address": demo.get("address", "Demo Address"),
                    "districtName": "Bengaluru Urban",
                    "stateName": "Karnataka",
                    "pincode": demo.get("pincode", "560038"),
                    "kycVerified": True,
                    "kycStatus": "VERIFIED",
                    "isNew": True,
                    "message": "ABHA created via demographic auth (Sandbox simulation)",
                    "abdm_mode": "MOCK",
                }

        # 2b. M1: Login OTP Verify (VRFY_ABHA_101/301/401 — returns ABHA list)
        if "login/verify" in endpoint:
            txn_id = data.get("txnId") or f"abdm-v3-login-txn-{uuid.uuid4().hex[:10]}"
            cm_id = self.settings.x_cm_id
            return 200, {
                "txnId": txn_id,
                "token": f"mock-abdm-v3-login-token-{req_id[:8]}",
                "ABHANumber": "91-4829-1029-4721",
                "healthIdNumber": "91-4829-1029-4721",
                "phrAddress": [f"arun.kumar@{cm_id}"],
                "healthId": f"arun.kumar@{cm_id}",
                "accounts": [
                    {
                        "ABHANumber": "91-4829-1029-4721",
                        "phrAddress": [f"arun.kumar@{cm_id}"],
                        "name": "Arun Kumar",
                        "gender": "M",
                        "yearOfBirth": 1991,
                        "mobile": "98XXXXX210",
                        "status": "ACTIVE",
                    }
                ],
                "name": "Arun Kumar",
                "gender": "M",
                "yearOfBirth": 1991,
                "kycVerified": True,
                "kycStatus": "VERIFIED",
                "message": "ABHA verified successfully (Sandbox simulation)",
                "abdm_mode": "MOCK",
            }

        # 2c. M1: Aadhaar / Mobile OTP Verify & Enrol (v3)
        if "enrol/byAadhaar" in endpoint or "aadhaar/verifyOtp" in endpoint:
            txn_id = data.get("txnId") or f"abdm-v3-txn-{uuid.uuid4().hex[:10]}"
            return 200, {
                "txnId": txn_id,
                "token": f"mock-abdm-v3-phr-token-{req_id[:8]}",
                "ABHANumber": "91-4829-1029-4721",
                "healthIdNumber": "91-4829-1029-4721",
                "phrAddress": [f"arun.kumar@{self.settings.x_cm_id}"],
                "healthId": f"arun.kumar@{self.settings.x_cm_id}",
                "name": "Arun Kumar",
                "firstName": "Arun",
                "lastName": "Kumar",
                "gender": "M",
                "yearOfBirth": 1991,
                "monthOfBirth": 5,
                "dayOfBirth": 14,
                "mobile": "9876543210",
                "address": "Flat 402, Shanti Vihar, Indiranagar",
                "districtName": "Bengaluru Urban",
                "stateName": "Karnataka",
                "pincode": "560038",
                "kycVerified": True,
                "kycStatus": "VERIFIED",
                "isNew": False,
                "message": "ABHA v3 e-KYC verified successfully (Sandbox simulation)",
                "abdm_mode": "MOCK",
            }

        # 3. M1: ABHA Address Search / Login
        if "abha/search" in endpoint or "searchByHealthId" in endpoint:
            query_id = str(data.get("abhaAddress") or data.get("healthId") or f"priya.sharma@{self.settings.x_cm_id}")
            is_num = query_id.replace("-", "").isdigit()
            abha_addr = query_id if not is_num else f"priya.sharma@{self.settings.x_cm_id}"
            abha_num = query_id if is_num else "91-7291-8840-2104"
            return 200, {
                "abhaAddress": abha_addr,
                "healthId": abha_addr,
                "ABHANumber": abha_num,
                "healthIdNumber": abha_num,
                "status": "ACTIVE",
                "authMethods": ["AADHAAR_OTP", "MOBILE_OTP", "PASSWORD"],
                "abdm_mode": "MOCK",
            }

        # 4. M1: ABHA Profile Retrieval
        if "profile/account" in endpoint or "account/profile" in endpoint:
            hid = headers.get("X-Health-Id") or f"priya.sharma@{self.settings.x_cm_id}"
            is_num = hid.replace("-", "").isdigit()
            return 200, {
                "healthId": hid if not is_num else f"priya.sharma@{self.settings.x_cm_id}",
                "healthIdNumber": hid if is_num else "91-7291-8840-2104",
                "name": "Priya Sharma",
                "firstName": "Priya",
                "lastName": "Sharma",
                "gender": "F",
                "yearOfBirth": 1994,
                "monthOfBirth": 11,
                "dayOfBirth": 28,
                "mobile": "9845102938",
                "email": "priya.sharma@example.com",
                "address": "45, Richmond Road, Shanthala Nagar",
                "districtName": "Bengaluru Urban",
                "stateName": "Karnataka",
                "pincode": "560025",
                "kycVerified": True,
                "abdm_mode": "MOCK",
            }

        # 5. HPR Doctor Verification
        if "doctors/verify" in endpoint:
            return 200, {
                "hpr_id": "DR-NMC-9201",
                "registration_number": data.get("registration_number", "KMC-49201"),
                "council": "National Medical Commission",
                "full_name": "Dr. Rajesh Varma",
                "is_verified": True,
                "specialization": "General Medicine",
                "abdm_mode": "MOCK",
            }

        # 6. M1/M2/M3 Async Gateway Acknowledgements (HTTP 202 Accepted per NHA spec)
        return 202, {
            "status": "ACCEPTED",
            "requestId": req_id,
            "timestamp": utc_timestamp_iso(),
            "x_cm_id": self.settings.x_cm_id,
            "abdm_mode": "MOCK",
        }


# ---------------------------------------------------------------------------
# Strategy 2: Official Live NHA Adapter (ABDM_ENV=SANDBOX | PRODUCTION)
# ---------------------------------------------------------------------------


class LiveABDMAdapter(BaseABDMAdapter):
    """Official HTTP client for NHA ABDM Sandbox and Production APIs."""

    MAX_RETRIES = 3
    BACKOFF_BASE = 1.0
    TOKEN_EXPIRY_BUFFER = 300

    def __init__(self, settings: ABDMSettings) -> None:
        super().__init__(settings)
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,
                read=float(self.settings.request_timeout),
                write=10.0,
                pool=10.0,
            ),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._token_lock = asyncio.Lock()

    async def close(self) -> None:
        await self._http.aclose()

    def _sign_request(self, body: str) -> str:
        key = self.settings.client_secret.encode("utf-8")
        return hmac.new(key, body.encode("utf-8"), hashlib.sha256).hexdigest()

    async def get_access_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._token_expires_at:
            return self._access_token

        async with self._token_lock:
            now = time.time()
            if self._access_token and now < self._token_expires_at:
                return self._access_token

            if not self.settings.client_id or not self.settings.client_secret:
                raise ABDMError(
                    message=(
                        f"ABDM_ENV={self.settings.abdm_env.value} requires "
                        "ABDM_CLIENT_ID and ABDM_CLIENT_SECRET environment variables"
                    ),
                    error_code="ABDM-CONFIG",
                    http_status=503,
                )

            req_id = str(uuid.uuid4())
            ts = utc_timestamp_iso()
            payload = {
                "clientId": self.settings.client_id,
                "clientSecret": self.settings.client_secret,
                "grantType": "client_credentials",
            }
            headers = {
                "REQUEST-ID": req_id,
                "TIMESTAMP": ts,
                "X-CM-ID": self.settings.x_cm_id,
            }

            try:
                response = await self._http.post(
                    self.settings.token_url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                body = response.json()
                token = body.get("accessToken") or body.get("access_token")
                if not token:
                    raise ABDMError(
                        message="ABDM session response missing accessToken",
                        http_status=502,
                    )
                expires_in = int(body.get("expiresIn") or body.get("expires_in") or 1200)
                self._access_token = token
                self._token_expires_at = now + max(expires_in - self.TOKEN_EXPIRY_BUFFER, 60)
                logger.info(
                    "ABDM OAuth2 session token refreshed (env=%s, ttl=%ds)",
                    self.settings.abdm_env.value,
                    expires_in,
                )
                return self._access_token
            except httpx.HTTPStatusError as exc:
                raise ABDMError(
                    message="Failed to obtain ABDM OAuth2 session token",
                    http_status=exc.response.status_code,
                ) from exc
            except httpx.RequestError as exc:
                raise ABDMError(
                    message=f"Network error contacting ABDM session gateway: {exc}",
                    http_status=503,
                ) from exc

    def _resolve_url(self, endpoint: str, target: str) -> str:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        base = self.settings.abha_url if target == "abha" else self.settings.gateway_url
        return f"{base.rstrip('/')}/{endpoint.lstrip('/')}"

    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
        *,
        target: str = "gateway",
        sign: bool = False,
        require_auth: bool = True,
        request_id: Optional[str] = None,
    ) -> tuple[int, dict]:
        req_id = request_id or str(uuid.uuid4())
        ts = utc_timestamp_iso()
        url = self._resolve_url(endpoint, target)

        req_headers: dict[str, str] = {
            "X-CM-ID": self.settings.x_cm_id,
            "REQUEST-ID": req_id,
            "TIMESTAMP": ts,
        }
        if self.settings.hip_id:
            req_headers["X-HIP-ID"] = self.settings.hip_id
        if self.settings.hiu_id:
            req_headers["X-HIU-ID"] = self.settings.hiu_id
        if self.settings.bridge_id:
            req_headers["X-BRIDGE-ID"] = self.settings.bridge_id
        if headers:
            req_headers.update(headers)

        body_str = json.dumps(data) if data else ""
        if sign and body_str:
            req_headers["X-ABDM-Signature"] = self._sign_request(body_str)

        last_exc: Optional[Exception] = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                if require_auth:
                    token = await self.get_access_token()
                    req_headers["Authorization"] = f"Bearer {token}"

                response = await self._http.request(
                    method=method.upper(),
                    url=url,
                    json=data,
                    headers=req_headers,
                )
                response.raise_for_status()
                parsed = response.json() if response.text.strip() else {"status": "ACCEPTED"}
                return response.status_code, parsed

            except httpx.HTTPStatusError as exc:
                last_exc = exc
                sc = exc.response.status_code
                if sc == 401:
                    self._access_token = None
                    self._token_expires_at = 0.0
                    if attempt < self.MAX_RETRIES:
                        continue
                try:
                    err_body = exc.response.json()
                except Exception:
                    err_body = {"message": exc.response.text[:300]}

                abdm_code = err_body.get("code") or err_body.get("error", {}).get("code")
                abdm_msg = (
                    ABDM_ERROR_MESSAGES.get(abdm_code, "")
                    or err_body.get("message")
                    or err_body.get("error", {}).get("message", "ABDM Gateway Error")
                )
                if 400 <= sc < 500 and sc != 429:
                    raise ABDMError(
                        message=abdm_msg,
                        error_code=abdm_code,
                        http_status=sc,
                        details=mask_pii_dict(err_body),
                    ) from exc

            except httpx.RequestError as exc:
                last_exc = exc

            if attempt < self.MAX_RETRIES:
                await asyncio.sleep(self.BACKOFF_BASE * (2 ** (attempt - 1)))

        raise ABDMError(
            message=f"ABDM request failed after {self.MAX_RETRIES} attempts",
            error_code="ABDM-1012",
            http_status=502,
            details={"reason": str(last_exc)[:200] if last_exc else "unknown"},
        )


# ---------------------------------------------------------------------------
# Public Client Facade with Immutable WASA Transaction Logging
# ---------------------------------------------------------------------------


class ABDMClient:
    """Facade selecting MOCK vs LIVE adapter from ``ABDM_ENV`` and auditing all calls."""

    def __init__(self, settings: Optional[ABDMSettings] = None) -> None:
        self.settings = settings or get_abdm_settings()
        self._adapter: BaseABDMAdapter = (
            MockABDMAdapter(self.settings)
            if self.settings.abdm_env == ABDMMode.MOCK
            else LiveABDMAdapter(self.settings)
        )

    @property
    def mode(self) -> ABDMMode:
        return self.settings.abdm_env

    async def close(self) -> None:
        await self._adapter.close()

    async def __aenter__(self) -> "ABDMClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def get_access_token(self) -> str:
        return await self._adapter.get_access_token()

    async def record_transaction(
        self,
        *,
        request_id: str,
        direction: str,
        http_method: str,
        endpoint: str,
        http_status: Optional[int],
        payload: Any,
        correlation_id: Optional[str] = None,
        error_code: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Persist an immutable, PII-masked entry into ``abdm_transaction_logs``."""
        try:
            from app.core.database import async_session_factory
            from app.models.abdm import ABDMTransactionLog

            entry = ABDMTransactionLog(
                request_id=request_id,
                correlation_id=correlation_id,
                direction=direction,
                abdm_env=self.settings.abdm_env.value,
                x_cm_id=self.settings.x_cm_id,
                http_method=http_method.upper(),
                endpoint=endpoint[:500],
                http_status=http_status,
                payload_sha256=compute_payload_sha256(payload),
                masked_summary=mask_pii_dict(payload) if isinstance(payload, dict) else {},
                error_code=error_code,
                user_id=user_id,
            )
            async with async_session_factory() as session:
                session.add(entry)
                await session.commit()
        except Exception as exc:
            # Never break clinical/ABDM flow if transaction log table isn't migrated yet
            logger.debug("ABDM transaction log skipped: %s", exc)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
        *,
        target: str = "gateway",
        sign: bool = False,
        require_auth: bool = True,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Execute an outbound ABDM API call with full WASA transaction auditing."""
        req_id = (data or {}).get("requestId") or str(uuid.uuid4())
        http_status: Optional[int] = None
        err_code: Optional[str] = None

        try:
            http_status, response = await self._adapter.request(
                method=method,
                endpoint=endpoint,
                data=data,
                headers=headers,
                target=target,
                sign=sign,
                require_auth=require_auth,
                request_id=req_id,
            )
            await self.record_transaction(
                request_id=req_id,
                correlation_id=correlation_id,
                direction="OUTBOUND",
                http_method=method,
                endpoint=endpoint,
                http_status=http_status,
                payload={"request": data or {}, "response_status": http_status},
                user_id=user_id,
            )
            return response
        except ABDMError as exc:
            http_status = exc.http_status
            err_code = exc.error_code
            await self.record_transaction(
                request_id=req_id,
                correlation_id=correlation_id,
                direction="OUTBOUND",
                http_method=method,
                endpoint=endpoint,
                http_status=http_status,
                payload={"request": data or {}, "error": exc.message},
                error_code=err_code,
                user_id=user_id,
            )
            raise
