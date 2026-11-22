"""
Security utilities: password hashing, JWT creation / verification,
token blacklisting (Redis), and FastAPI auth dependencies.
"""

import logging
import os
import bcrypt
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

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
        return False


# ── JWT helpers ──────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    role: str,
    permissions: List[str],
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a short-lived access JWT."""
    now = datetime.now(timezone.utc)
    claims: Dict[str, Any] = {
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
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a long-lived refresh JWT."""
    now = datetime.now(timezone.utc)
    claims: Dict[str, Any] = {
        "sub": subject,
        "exp": now + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
        "iat": now,
        "jti": str(uuid4()),
        "type": "refresh",
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT, returning its claims dict.

    Raises ``JWTError`` on any validation failure.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


logger = logging.getLogger(__name__)

# ── Token blacklist (Redis + in-memory fallback) ─────────────────────────

_redis_pool: Optional[aioredis.Redis] = None
_memory_blacklist: Set[str] = set()


async def _get_redis() -> Optional[aioredis.Redis]:
    global _redis_pool
    if _redis_pool is not None:
        try:
            await _redis_pool.ping()
            return _redis_pool
        except Exception:
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
        return None


async def blacklist_token(jti: str, expires_in: int = 3600) -> None:
    """Add a JTI to the shared Redis blacklist until its natural expiry."""
    _memory_blacklist.add(jti)
    try:
        r = await _get_redis()
        if r is not None:
            await r.setex(f"bl:{jti}", max(expires_in, 60), "1")
    except Exception as exc:
        logger.debug("Failed to set blacklist token in Redis: %s", exc)


async def is_token_blacklisted(jti: str) -> bool:
    """Return True if the JTI has been blacklisted."""
    if jti in _memory_blacklist:
        return True
    try:
        r = await _get_redis()
        if r is not None:
            return bool(await r.exists(f"bl:{jti}"))
    except Exception as exc:
        logger.debug("Redis token blacklist check skipped: %s", exc)
    return False


# ── FastAPI dependencies ────────────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
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
            detail=f"Could not validate credentials: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type; expected access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check blacklist (safe against Redis connection issues)
    jti = payload.get("jti")
    if jti:
        try:
            if await is_token_blacklisted(jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked/logged out",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.debug("Blacklist check skipped due to Redis error: %s", exc)

    user_id: Optional[str] = payload.get("sub")
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

    # Single active session per account with a 15-minute sliding idle TTL.
    # Session state is shared in Redis (with in-memory fallback for serverless deployments).
    session_id = payload.get("sid")
    if session_id:
        from app.core.redis_state import get_redis
        try:
            session_store = await get_redis()
            active_session = await session_store.get(f"auth:session:{user_id}")
            if active_session and not hmac.compare_digest(str(active_session), str(session_id)):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or replaced")
            await session_store.expire(f"auth:session:{user_id}", 900)
        except HTTPException:
            raise
        except Exception as exc:
            logger.debug("Session store check skipped: %s", exc)

    issued_at = payload.get("iat")
    # Read additive migration fields without selecting them in the ORM model,
    # so pre-003 databases continue to authenticate during rolling deployment.
    columns = (await db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name IN ('hospital_id','tokens_valid_after')"))).scalars().all()
    if "hospital_id" in columns:
        hospital_id = (await db.execute(text("SELECT hospital_id FROM users WHERE id=:uid"), {"uid": user_id})).scalar_one_or_none()
        if hospital_id:
            await db.execute(text("SELECT set_config('app.hospital_id', :hospital_id, true)"), {"hospital_id": str(hospital_id)})
    revoked_after = None
    if "tokens_valid_after" in columns:
        revoked_after = (await db.execute(text("SELECT tokens_valid_after FROM users WHERE id=:uid"), {"uid": user_id})).scalar_one_or_none()
    if revoked_after and issued_at and datetime.fromtimestamp(float(issued_at), timezone.utc) <= revoked_after:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    return {
        "user_id": user_id,
        "role": payload.get("role"),
        "permissions": payload.get("permissions", []),
        "jti": jti,
        "db_user": user,
    }


def require_roles(*allowed_roles: str):
    """Dependency factory – ensures the authenticated user has one of the
    listed roles."""

    async def _checker(
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
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
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        user_permissions: Set[str] = set(current_user.get("permissions", []))
        missing = set(required_permissions) - user_permissions
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(sorted(missing))}",
            )
        return current_user

    return _checker
