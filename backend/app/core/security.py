"""
Security utilities: password hashing, JWT creation / verification,
token blacklisting (Redis), and FastAPI auth dependencies.
"""

import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
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


# ── Token blacklist (Redis) ─────────────────────────────────────────────

_redis_pool: Optional[aioredis.Redis] = None


async def _get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_pool


async def blacklist_token(jti: str, expires_in: int) -> None:
    """Add a JTI to the Redis blacklist until its natural expiry."""
    r = await _get_redis()
    await r.setex(f"bl:{jti}", expires_in, "1")


async def is_token_blacklisted(jti: str) -> bool:
    """Return True if the JTI has been blacklisted."""
    try:
        r = await _get_redis()
        return await r.exists(f"bl:{jti}") > 0
    except Exception:
        return False


# ── FastAPI dependencies ────────────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Extract and validate the JWT from the Authorization header.

    Returns a dict with the decoded claims plus a ``db_user`` key
    containing the SQLAlchemy User instance.
    """
    # Extract and clean token (handles accidental 'Bearer ' prefix, quotes, or whitespace from Swagger UI)
    raw_token = credentials.credentials.strip()
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
        except Exception:
            pass  # If Redis is unavailable, proceed without blacklist validation

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
