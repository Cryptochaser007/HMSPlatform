"""Authentication, JWT tokens, and User lifecycle endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, audit_log, get_audit_logger
from app.core.database import get_db
from app.core.rbac import Permission, Role
from app.core.security import get_current_user, require_permissions, require_roles
from app.schemas.user import ChangePassword, Token, UserCreate, UserLogin, UserResponse
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Authenticate user with email and password, returning JWT access and refresh tokens."""
    user = await auth_service.authenticate_user(db, credentials.email, credentials.password)
    tokens = auth_service.create_tokens(user)

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
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Exchange a valid refresh token for a new access token."""
    return await auth_service.refresh_access_token(db, refresh_token)


@router.post("/logout")
async def logout(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Blacklist the active JWT access token."""
    jti = current_user.get("jti")
    if jti:
        await auth_service.blacklist_token(jti)

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
    return {"message": "Successfully logged out"}


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
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
    return UserResponse.model_validate(current_user["db_user"])


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

