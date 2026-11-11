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

        # All retries exhausted
        raise ABDMError(
            message=f"ABDM request failed after {self.MAX_RETRIES} attempts: {last_exc}",
            http_status=getattr(last_exc, "response", None)
            and getattr(last_exc.response, "status_code", None),  # type: ignore[union-attr]
        )
