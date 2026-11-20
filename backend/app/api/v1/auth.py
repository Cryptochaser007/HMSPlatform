"""Authentication, JWT tokens, and User lifecycle endpoints."""

from typing import Any, Dict
from datetime import datetime, timezone

import secrets
import hmac
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, audit_log, get_audit_logger
from app.core.database import get_db
from app.core.config import get_settings
from app.core.dependencies import RateLimiter
from app.core.rbac import Permission, Role
from app.core.security import decode_token, get_current_user, require_permissions, require_roles
from app.schemas.user import ChangePassword, Token, UserCreate, UserLogin, UserResponse
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def _activate_single_session(user_id: str, access_token: str) -> str:
    """Store the current session ID with a 15-minute idle sliding window."""
    from app.core.redis_state import get_redis
    payload = decode_token(access_token)
    sid = str(payload["sid"])
    redis_client = await get_redis()
    await redis_client.set(f"auth:session:{user_id}", sid, ex=900)
    return sid


@router.post(
    "/login",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
)
async def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Authenticate user with email and password, returning JWT access and refresh tokens."""
    user = await auth_service.authenticate_user(db, credentials.email, credentials.password)
    tokens = auth_service.create_tokens(user)
    await _activate_single_session(str(user.id), tokens.access_token)

    # Log successful login to immutable audit trail
    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=str(user.id),
        action=AuditAction.LOGIN,
        entity_type="User",
        entity_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    secure = request.url.scheme == "https" or get_settings().ENVIRONMENT.lower() == "production"
    response.set_cookie("access_token", tokens.access_token, httponly=True, secure=secure, samesite="strict", max_age=900, path="/")
    response.set_cookie("refresh_token", tokens.refresh_token, httponly=True, secure=secure, samesite="strict", max_age=604800, path="/api/v1/auth")
    response.set_cookie("csrf_token", secrets.token_urlsafe(32), httponly=False, secure=secure, samesite="strict", max_age=604800, path="/")
    from app.core.redis_state import get_redis
    failed_epoch = await (await get_redis()).get(f"auth:lockout:{credentials.email.strip().lower()}:last_failed")
    from sqlalchemy import text
    durable_failed = await db.execute(text("SELECT last_failed_login FROM users WHERE id=:uid"), {"uid": str(user.id)})
    last_failed = durable_failed.scalar_one_or_none()
    previous_login = getattr(user, "_previous_last_login", None)
    return {
        "authenticated": True,
        "last_successful_login": previous_login.isoformat() if previous_login else None,
        "last_failed_login": last_failed.isoformat() if last_failed else (datetime.fromtimestamp(int(failed_epoch), timezone.utc).isoformat() if failed_epoch else None),
    }


@router.post(
    "/refresh",
    dependencies=[Depends(RateLimiter(times=20, seconds=60))],
)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, bool]:
    """Exchange a valid refresh token for a new access token."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh session required")
    csrf_cookie = request.cookies.get("csrf_token", "")
    csrf_header = request.headers.get("X-CSRF-Token", "")
    if not csrf_cookie or not hmac.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
    try:
        refresh_claims = decode_token(token)
        from app.core.redis_state import get_redis
        sessions = await get_redis()
        active_sid = await sessions.get(f"auth:session:{refresh_claims.get('sub')}")
        if not refresh_claims.get("sid") or not active_sid or not hmac.compare_digest(str(active_sid), str(refresh_claims["sid"])):
            raise HTTPException(status_code=401, detail="Refresh session expired or replaced")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh session") from exc
    tokens = await auth_service.refresh_access_token(db, token)
    decoded = decode_token(tokens.access_token)
    await _activate_single_session(str(decoded["sub"]), tokens.access_token)
    secure = request.url.scheme == "https" or get_settings().ENVIRONMENT.lower() == "production"
    response.set_cookie("access_token", tokens.access_token, httponly=True, secure=secure, samesite="strict", max_age=900, path="/")
    response.set_cookie("refresh_token", tokens.refresh_token, httponly=True, secure=secure, samesite="strict", max_age=604800, path="/api/v1/auth")
    response.set_cookie("csrf_token", secrets.token_urlsafe(32), httponly=False, secure=secure, samesite="strict", max_age=604800, path="/")
    return {"authenticated": True}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Blacklist the active JWT access token."""
    jti = current_user.get("jti")
    if jti:
        await auth_service.blacklist_token(jti)
    from app.core.redis_state import get_redis
    await (await get_redis()).delete(f"auth:session:{current_user['user_id']}")
    refresh = request.cookies.get("refresh_token")
    if refresh:
        try:
            refresh_payload = decode_token(refresh)
        except Exception:
            refresh_payload = {}
        refresh_jti = refresh_payload.get("jti")
        expires = refresh_payload.get("exp")
        if refresh_payload.get("type") == "refresh" and refresh_jti:
            import time
            await auth_service.blacklist_token(refresh_jti, max(int(expires - time.time()), 60))

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.LOGOUT,
        entity_type="User",
        entity_id=current_user["user_id"],
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth")
    response.delete_cookie("csrf_token", path="/")
    return {"message": "Successfully logged out"}


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def signup(
    data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Public sign-up endpoint for new hospital staff accounts."""
    if data.role.upper() == Role.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot self-register as Super Administrator",
        )
    user = await auth_service.register_user(db, data)

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=str(user.id),
        action=AuditAction.CREATE,
        entity_type="User",
        entity_id=str(user.id),
        new_value={"email": user.email, "role": user.role, "registration_type": "public_signup"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return UserResponse.model_validate(user)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.USER_MANAGE.value))],
)
async def register_staff_user(
    data: UserCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register hospital staff account (Restricted to Hospital Administrators)."""
    user = await auth_service.register_user(db, data)

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.CREATE,
        entity_type="User",
        entity_id=str(user.id),
        new_value={"email": user.email, "role": user.role},
    )
    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> UserResponse:
    """Return profile and permissions of authenticated user."""
    db_user = current_user.get("db_user")
    if db_user:
        return UserResponse.model_validate(db_user)
    return UserResponse(
        id=current_user.get("user_id") or current_user.get("id", ""),
        email=current_user.get("email", "admin@hms.local"),
        name=current_user.get("name") or current_user.get("username", "Admin"),
        role=current_user.get("role") or (current_user.get("roles", ["SUPER_ADMIN"])[0]),
        is_active=True,
    )


@router.put("/change-password")
async def change_password(
    data: ChangePassword,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Update current user's password."""
    await auth_service.change_password(
        db, current_user["user_id"], data.old_password, data.new_password
    )
    return {"message": "Password updated successfully"}

