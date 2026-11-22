"""
Security utilities: password hashing, JWT creation / verification,
token blacklisting (Redis), and FastAPI auth dependencies.
"""

import hmac
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db

settings = get_settings()

# ── Password hashing ────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify *plain_password* against *hashed_password*."""
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
        return False


# ── JWT helpers ──────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    role: str,
    permissions: list[str],
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a short-lived access JWT."""
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "permissions": permissions,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
        "jti": str(uuid4()),
        "type": "access",
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a long-lived refresh JWT."""
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": subject,
        "exp": now + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
        "iat": now,
        "jti": str(uuid4()),
        "type": "refresh",
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT, returning its claims dict.

    Raises ``JWTError`` on any validation failure.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


logger = logging.getLogger(__name__)

# ── Token blacklist (Redis + in-memory fallback) ─────────────────────────

_redis_pool: aioredis.Redis | None = None
_memory_blacklist: set[str] = set()


async def _get_redis() -> aioredis.Redis | None:
    global _redis_pool
    if _redis_pool is not None:
        try:
            await _redis_pool.ping()
            return _redis_pool
        except Exception:
            logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
            _redis_pool = None

    redis_url = getattr(settings, "REDIS_URL", "")
    if not redis_url or (os.environ.get("VERCEL") and "localhost" in redis_url):
        return None

    try:
        client = aioredis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
        )
        await client.ping()
        _redis_pool = client
        return _redis_pool
    except Exception:
        logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
        return None


async def security_redis():
    """Shared authentication state must remain available across workers."""
    r = await _get_redis()
    if r is None:
        raise HTTPException(status_code=503, detail="Authentication state service unavailable")
    return r


async def blacklist_token(jti: str, expires_in: int = 3600) -> None:
    try:
        await (await security_redis()).setex(f"bl:{jti}", max(expires_in, 1), "1")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Authentication state service unavailable") from exc


async def is_token_blacklisted(jti: str) -> bool:
    try:
        return bool(await (await security_redis()).exists(f"bl:{jti}"))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Authentication state service unavailable") from exc


async def validate_session(payload: dict, touch: bool = True) -> None:
    if not payload.get("sid") or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Session expired")
    try:
        r = await security_redis()
        # Compare and touch atomically so an old session cannot extend a replacement.
        script = """
        if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
        if ARGV[2] == '1' then redis.call('EXPIRE', KEYS[1], 900) end
        return 1
        """
        valid = await r.eval(script, 1, f"auth:session:{payload['sub']}",
                             str(payload["sid"]), "1" if touch else "0")
        if not valid:
            raise HTTPException(status_code=401, detail="Session expired or replaced")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Authentication state service unavailable") from exc


# ── FastAPI dependencies ────────────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Extract and validate the JWT from the Authorization header.

    Returns a dict with the decoded claims plus a ``db_user`` key
    containing the SQLAlchemy User instance.
    """
    # Extract and clean token (handles accidental 'Bearer ' prefix, quotes, or whitespace from Swagger UI)
    cookie_auth = credentials is None
    raw_token = (credentials.credentials if credentials else request.cookies.get("access_token", "")).strip()
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if cookie_auth and request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("x-csrf-token")
        if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")
    if raw_token.startswith("Bearer "):
        raw_token = raw_token[7:].strip()
    token = raw_token.strip("\"'")

    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {exc!s}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type; expected access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # A revocation-store failure must stop authenticated requests.
    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked/logged out",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject (user_id)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Lazy import to avoid circular dependency at module level
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this token does not exist",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active or getattr(user, "is_deleted", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated or has been deleted",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await validate_session(payload)
    hospital_id = str(user.hospital_id) if user.hospital_id else None
    if hospital_id != payload.get("hospital_id") or user.role != payload.get("role"):
        raise HTTPException(status_code=401, detail="Account membership changed; sign in again")
    from app.models.tenant import Hospital
    hospital = (await db.execute(select(Hospital).where(Hospital.id == hospital_id))).scalar_one_or_none()
    if hospital is None or not hospital.is_active or hospital.is_deleted:
        raise HTTPException(status_code=401, detail="Hospital account is inactive")
    revoked_after = (await db.execute(text(
        "SELECT tokens_valid_after FROM users WHERE id=:uid"
    ), {"uid": user_id})).scalar_one_or_none()
    issued_at = payload.get("iat")
    if revoked_after and issued_at and datetime.fromtimestamp(float(issued_at), UTC) <= revoked_after:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    from app.core.tenant_context import current_hospital
    current_hospital.set({"hospital_id": hospital_id, "abdm_env": hospital.abdm_env,
                          "hip_id": hospital.hip_id, "hiu_id": hospital.hiu_id,
                          "hfr_facility_id": hospital.hfr_facility_id})

    return {
        "user_id": user_id,
        "role": payload.get("role"),
        "permissions": payload.get("permissions", []),
        "jti": jti,
        "db_user": user,
        "hospital_id": hospital_id,
    }


def require_roles(*allowed_roles: str):
    """Dependency factory – ensures the authenticated user has one of the
    listed roles."""

    async def _checker(
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role privileges",
            )
        return current_user

    return _checker


def require_permissions(*required_permissions: str):
    """Dependency factory – ensures the authenticated user has **all** of
    the listed permissions."""

    async def _checker(
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        user_permissions: set[str] = set(current_user.get("permissions", []))
        missing = set(required_permissions) - user_permissions
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(sorted(missing))}",
            )
        return current_user

    return _checker
