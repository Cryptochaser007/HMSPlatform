"""
CERT-In WASA & NDHM HDMP Security Controls.

Provides:
- HTTP Security Headers Middleware (HSTS, CSP, X-Frame-Options, nosniff, Cache-Control)
- PII & Secret Masking utilities for application logs and API responses
- Logging filter preventing accidental leakage of Aadhaar, ABHA, mobile, OTP, or tokens
- Canonical SHA-256 payload hashing for immutable ABDM transaction evidence
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Sensitive keys whose values must ALWAYS be fully redacted in logs / audit summaries
REDACTED_KEYS = frozenset(
    {
        "password",
        "old_password",
        "new_password",
        "hashed_password",
        "secret",
        "clientsecret",
        "client_secret",
        "accesstoken",
        "access_token",
        "refreshtoken",
        "refresh_token",
        "authorization",
        "x-token",
        "privatekey",
        "private_key",
        "otp",
        "token",
        "aadhaar",
        "aadhaar_number",
    }
)

# Keys whose values should retain only the last 4 characters for non-sensitive correlation
PARTIAL_MASK_KEYS = frozenset(
    {
        "mobile",
        "mobile_number",
        "phone",
        "emergency_contact_phone",
        "abha_id",
        "healthidnumber",
        "health_id_number",
        "abha_number",
    }
)

_RE_AADHAAR = re.compile(r"\b(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})\b")
_RE_ABHA_NUM = re.compile(r"\b(\d{2})-?(\d{4})-?(\d{4})-?(\d{4})\b")
_RE_INDIAN_MOBILE = re.compile(r"(?<!\d)(\+91[\s-]?)?([6-9]\d{5})(\d{4})(?!\d)")
_RE_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)


def mask_identifier(value: str, keep_last: int = 4) -> str:
    """Mask an identifier string while optionally retaining the last N characters."""
    cleaned = str(value).strip()
    if len(cleaned) <= keep_last:
        return "****"
    return ("X" * (len(cleaned) - keep_last)) + cleaned[-keep_last:]


def mask_pii_text(text: str) -> str:
    """Redact Aadhaar, ABHA numbers, mobile numbers, and Bearer tokens from free text."""
    if not text:
        return text
    masked = _RE_BEARER.sub(r"\1[REDACTED]", text)
    masked = _RE_ABHA_NUM.sub(r"XX-XXXX-XXXX-\4", masked)
    masked = _RE_AADHAAR.sub(r"XXXX-XXXX-\3", masked)
    masked = _RE_INDIAN_MOBILE.sub(r"\1XXXXXX\3", masked)
    return masked


def mask_pii_dict(obj: Any, _depth: int = 0) -> Any:
    """Recursively redact secrets and mask PII inside dicts/lists for safe logging."""
    if _depth > 8:
        return "[TRUNCATED]"
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            key_norm = str(k).lower()
            if key_norm in REDACTED_KEYS:
                out[k] = "[REDACTED]"
            elif key_norm in PARTIAL_MASK_KEYS and isinstance(v, (str, int)):
                out[k] = mask_identifier(str(v), keep_last=4)
            else:
                out[k] = mask_pii_dict(v, _depth + 1)
        return out
    if isinstance(obj, list):
        return [mask_pii_dict(item, _depth + 1) for item in obj[:50]]
    if isinstance(obj, str):
        return mask_pii_text(obj)
    return obj


def compute_payload_sha256(payload: Any) -> str:
    """Return a canonical SHA-256 hex digest of a payload for WASA/NHA audit evidence."""
    if payload is None:
        raw = b""
    elif isinstance(payload, bytes):
        raw = payload
    elif isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class PIIMaskingLogFilter(logging.Filter):
    """Logging filter that strips PII and credentials from log messages and args."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_pii_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = mask_pii_dict(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    mask_pii_text(a) if isinstance(a, str) else a for a in record.args
                )
        return True


def install_pii_log_filter() -> None:
    """Attach PIIMaskingLogFilter to root and key application loggers."""
    flt = PIIMaskingLogFilter()
    for logger_name in ("", "uvicorn", "uvicorn.access", "uvicorn.error", "abdm", "abdm.client", "abdm.abha", "abdm.hip", "abdm.hiu"):
        lg = logging.getLogger(logger_name)
        if not any(isinstance(f, PIIMaskingLogFilter) for f in lg.filters):
            lg.addFilter(flt)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces CERT-In WASA Safe-to-Host HTTP security headers on every response."""

    STRICT_CSP = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    DOCS_CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://fastapi.tiangolo.com; "
        "frame-ancestors 'none'"
    )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"

        path = request.url.path
        if path.startswith("/docs") or path.startswith("/redoc"):
            response.headers["Content-Security-Policy"] = self.DOCS_CSP
        else:
            response.headers["Content-Security-Policy"] = self.STRICT_CSP

        if path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        # Remove server fingerprinting header if present
        if "server" in response.headers:
            del response.headers["server"]

        return response

