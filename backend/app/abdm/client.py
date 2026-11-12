"""
ABDMClient – async HTTP client for communicating with the ABDM Gateway.

Handles OAuth2 token management with caching, automatic retry with
exponential backoff, request/response logging, and ABDM-specific
error translation.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
from typing import Any, Optional

import httpx

from app.abdm.config import ABDMSettings

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


# Maps ABDM error codes to human-friendly messages
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


class ABDMClient:
    """
    Async HTTP client for the ABDM Gateway.

    Usage::

        settings = ABDMSettings()
        client = ABDMClient(settings)
        token = await client.get_access_token()
        data = await client._make_request("GET", "/v1/account/profile")
    """

    MAX_RETRIES = 3
    BACKOFF_BASE = 1.0  # seconds
    TOKEN_EXPIRY_BUFFER = 300  # refresh 5 min before actual expiry

    def __init__(self, settings: Optional[ABDMSettings] = None) -> None:
        self.settings = settings or ABDMSettings()
        self._http = httpx.AsyncClient(
            base_url=self.settings.gateway_url,
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
        # Token cache
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0  # epoch seconds

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Gracefully close the underlying HTTP client."""
        await self._http.aclose()

    async def __aenter__(self) -> "ABDMClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # OAuth2 token management
    # ------------------------------------------------------------------

    async def get_access_token(self) -> str:
        """
        Obtain a valid ABDM access token.

        Tokens are cached and reused until 5 minutes before their expiry.
        Uses the OAuth2 *client_credentials* grant against the ABDM sessions
        endpoint.

        Returns:
            A bearer access token string.

        Raises:
            ABDMError: If the token request fails.
        """
        now = time.time()
        if self._access_token and now < self._token_expires_at:
            logger.debug("Using cached ABDM access token")
            return self._access_token

        if not self.settings.client_id or self.settings.client_id in ("sandbox_client_id", "test", "dummy"):
            logger.info("Using simulated sandbox ABDM access token")
            self._access_token = "mock-abdm-access-token"
            self._token_expires_at = now + 3600
            return self._access_token

        logger.info("Requesting new ABDM access token")
        payload = {
            "clientId": self.settings.client_id,
            "clientSecret": self.settings.client_secret,
        }

        try:
            response = await self._http.post(
                self.settings.token_url,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            self._access_token = data["accessToken"]
            expires_in: int = data.get("expiresIn", 1800)
            self._token_expires_at = now + expires_in - self.TOKEN_EXPIRY_BUFFER

            logger.info(
                "ABDM access token acquired, expires in %d s (buffer %d s)",
                expires_in,
                self.TOKEN_EXPIRY_BUFFER,
            )
            return self._access_token

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Token request failed: HTTP %d – %s",
                exc.response.status_code,
                exc.response.text,
            )
            raise ABDMError(
                message="Failed to obtain ABDM access token",
                http_status=exc.response.status_code,
                details={"response": exc.response.text},
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Token request network error: %s", exc)
            raise ABDMError(
                message=f"Network error while obtaining ABDM token: {exc}",
            ) from exc

    # ------------------------------------------------------------------
    # Request signing (optional HMAC-based request integrity)
    # ------------------------------------------------------------------

    def _sign_request(self, body: str) -> str:
        """
        Generate an HMAC-SHA256 signature for request body integrity.

        The ABDM gateway may optionally require request signing for certain
        endpoints. The signature is computed using the client secret as key.

        Args:
            body: JSON-serialised request body.

        Returns:
            Hex-encoded HMAC-SHA256 signature.
        """
        key = self.settings.client_secret.encode("utf-8")
        sig = hmac.new(key, body.encode("utf-8"), hashlib.sha256).hexdigest()
        return sig

    # ------------------------------------------------------------------
    # Core request helper
    # ------------------------------------------------------------------

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
        *,
        sign: bool = False,
        require_auth: bool = True,
    ) -> dict:
        """
        Execute an HTTP request against the ABDM Gateway with automatic
        retry, logging, and error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: Relative endpoint path or absolute URL.
            data: Optional JSON-serialisable request body.
            headers: Optional extra headers.
            sign: If ``True``, attach an HMAC signature header.
            require_auth: If ``True`` (default), attach a bearer token.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            ABDMError: On ABDM-specific or HTTP errors after retries.
        """
        request_headers: dict[str, str] = {}
        if require_auth:
            token = await self.get_access_token()
            request_headers["Authorization"] = f"Bearer {token}"
        if self.settings.hip_id:
            request_headers["X-HIP-ID"] = self.settings.hip_id
        if self.settings.hiu_id:
            request_headers["X-HIU-ID"] = self.settings.hiu_id
        if headers:
            request_headers.update(headers)

        import json as _json

        body_str = _json.dumps(data) if data else ""
        if sign and body_str:
            request_headers["X-ABDM-Signature"] = self._sign_request(body_str)

        # In sandbox mode without production credentials, return simulated response
        if not self.settings.client_id or self.settings.client_id in ("sandbox_client_id", "test", "dummy"):
            return self._mock_response(endpoint, data, headers)

        last_exc: Optional[Exception] = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.debug(
                    "ABDM request attempt %d/%d: %s %s",
                    attempt,
                    self.MAX_RETRIES,
                    method.upper(),
                    endpoint,
                )
                if data:
                    logger.debug("Request body: %s", body_str[:2000])

                response = await self._http.request(
                    method=method.upper(),
                    url=endpoint,
                    json=data,
                    headers=request_headers,
                )

                logger.debug(
                    "ABDM response %d: %s",
                    response.status_code,
                    response.text[:2000],
                )

                response.raise_for_status()
                return response.json() if response.text.strip() else {}

            except httpx.HTTPStatusError as exc:
                last_exc = exc
                status = exc.response.status_code

                # Parse ABDM error body
                try:
                    err_body = exc.response.json()
                except Exception:
                    err_body = {"message": exc.response.text}

                abdm_code = err_body.get("code") or err_body.get("error", {}).get(
                    "code"
                )
                abdm_msg = (
                    ABDM_ERROR_MESSAGES.get(abdm_code, "")
                    or err_body.get("message")
                    or err_body.get("error", {}).get("message", "Unknown error")
                )

                logger.warning(
                    "ABDM error (attempt %d/%d) HTTP %d – [%s] %s",
                    attempt,
                    self.MAX_RETRIES,
                    status,
                    abdm_code,
                    abdm_msg,
                )

                # Don't retry on 4xx client errors (except 429 rate limit)
                if 400 <= status < 500 and status != 429:
                    raise ABDMError(
                        message=abdm_msg,
                        error_code=abdm_code,
                        http_status=status,
                        details=err_body,
                    ) from exc

                # 401 – token may have expired; invalidate cache
                if status == 401:
                    self._access_token = None
                    self._token_expires_at = 0.0

            except httpx.RequestError as exc:
                last_exc = exc
                logger.warning(
                    "ABDM network error (attempt %d/%d): %s",
                    attempt,
                    self.MAX_RETRIES,
                    exc,
                )

            # Exponential backoff before next retry
            if attempt < self.MAX_RETRIES:
                backoff = self.BACKOFF_BASE * (2 ** (attempt - 1))
                logger.debug("Backing off %.1f s before retry", backoff)
                await asyncio.sleep(backoff)

        # Fallback to sandbox simulation if live ABDM server is unreachable
        if self.settings.environment.value == "sandbox":
            logger.warning(
                "ABDM live call failed (%s); falling back to simulated sandbox response",
                last_exc,
            )
            return self._mock_response(endpoint, data, headers)

        # All retries exhausted
        raise ABDMError(
            message=f"ABDM request failed after {self.MAX_RETRIES} attempts: {last_exc}",
            http_status=getattr(last_exc, "response", None)
            and getattr(last_exc.response, "status_code", None),  # type: ignore[union-attr]
        )

    def _mock_response(
        self, endpoint: str, data: Optional[dict] = None, headers: Optional[dict] = None
    ) -> dict:
        """Provide realistic sandbox mock responses for ABDM endpoints when live credentials are not active."""
        data = data or {}
        headers = headers or {}

        # 1. Aadhaar OTP generation
        if "aadhaar/generateOtp" in endpoint:
            aadhaar = str(data.get("aadhaar", "999988887777"))
            last4 = aadhaar[-4:] if len(aadhaar) >= 4 else "7777"
            return {
                "txnId": f"txn-{int(time.time())}-{last4}",
                "message": f"OTP successfully sent to mobile linked with Aadhaar ending in ...{last4}",
                "mobileNumber": f"XXXXXX{last4}",
            }

        # 2. Aadhaar OTP verification
        if "aadhaar/verifyOtp" in endpoint:
            txn_id = data.get("txnId", f"txn-{int(time.time())}")
            return {
                "txnId": txn_id,
                "token": f"mock-abdm-preverified-token-{int(time.time())}",
                "healthIdNumber": "91-4829-1029-4721",
                "healthId": "arun.kumar@abdm",
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
                "isNew": False,
                "message": "Aadhaar verified successfully",
            }

        # 3. Aadhaar creation with pre-verified
        if "createHealthIdWithPreVerified" in endpoint or "createHealthId" in endpoint:
            preferred = data.get("healthId", "user@abdm")
            return {
                "healthIdNumber": "91-4829-1029-4721",
                "healthId": preferred,
                "name": data.get("name", "Arun Kumar"),
                "gender": data.get("gender", "M"),
                "yearOfBirth": data.get("yearOfBirth", 1991),
                "monthOfBirth": data.get("monthOfBirth", 5),
                "dayOfBirth": data.get("dayOfBirth", 14),
                "mobile": data.get("mobile", "9876543210"),
                "address": data.get("address", "Flat 402, Shanti Vihar"),
                "districtName": data.get("district", "Bengaluru Urban"),
                "stateName": data.get("state", "Karnataka"),
                "pincode": data.get("pincode", "560038"),
                "kycVerified": True,
            }

        # 4. Mobile OTP generation & verification
        if "mobile/generateOtp" in endpoint:
            return {
                "txnId": f"mob-txn-{int(time.time())}",
                "message": "OTP sent to registered mobile number",
            }
        if "mobile/verifyOtp" in endpoint:
            return {
                "txnId": data.get("txnId", f"mob-txn-{int(time.time())}"),
                "token": f"mock-mob-token-{int(time.time())}",
                "message": "Mobile OTP verified successfully",
            }

        # 5. ABHA Profile retrieval
        if "account/profile" in endpoint:
            health_id = headers.get("X-Health-Id") or "arun.kumar@abdm"
            is_num = health_id.replace("-", "").isdigit()
            return {
                "healthId": health_id if not is_num else "patient.verified@abdm",
                "healthIdNumber": health_id if is_num else "91-7291-8840-2104",
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
            }

        # 6. ABHA search
        if "searchByHealthId" in endpoint:
            hid = data.get("healthId", "user@abdm")
            return {
                "healthId": hid,
                "status": "ACTIVE",
                "authMethods": ["AADHAAR_OTP", "MOBILE_OTP", "DEMOGRAPHICS"],
            }

        # 7. Doctor HPR verification
        if "doctors/verify" in endpoint or "hpr" in endpoint:
            return {
                "hpr_id": "DR-NMC-9201",
                "registration_number": data.get("registration_number", "KMC-49201"),
                "council": "National Medical Commission",
                "full_name": "Dr. Rajesh Varma",
                "is_verified": True,
                "specialization": "General Medicine",
            }

        return {"status": "SUCCESS", "message": "Operation completed in ABDM sandbox mode"}
