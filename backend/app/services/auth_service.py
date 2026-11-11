"""Authentication service: login, token management, user registration."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import ROLE_PERMISSIONS, Permission, Role
from app.core.security import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import Token, UserCreate


class AuthService:
    """Handles authentication, token lifecycle, and user registration."""

    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> User:
        result = await db.execute(
            select(User).where(User.email == email, User.is_deleted == False)  # noqa: E712
        )
        user = result.scalar_one_or_none()
        if user is None or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )
        user.last_login = datetime.now(timezone.utc)
        await db.flush()
        return user

    def create_tokens(self, user: User) -> Token:
        role = user.role if isinstance(user.role, str) else user.role.value
        role_enum = Role(role)
        permissions: List[str] = [p.value for p in ROLE_PERMISSIONS.get(role_enum, set())]
        access_token = create_access_token(
            subject=str(user.id),
            role=role,
            permissions=permissions,
        )
        refresh_token = create_refresh_token(subject=str(user.id))
        return Token(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(self, db: AsyncSession, refresh_token: str) -> Token:
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is not a refresh token",
            )
        user_id = payload.get("sub")
        result = await db.execute(
            select(User).where(User.id == user_id, User.is_deleted == False)  # noqa: E712
        )
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        return self.create_tokens(user)

    async def register_user(self, db: AsyncSession, data: UserCreate) -> User:
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
            department=data.department,
            registration_number=data.registration_number,
            phone=data.phone,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    async def change_password(
        self, db: AsyncSession, user_id: str, old_password: str, new_password: str
    ) -> None:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not verify_password(old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )
        user.hashed_password = hash_password(new_password)
        await db.flush()

    async def blacklist_token(self, jti: str, expires_in: int = 1800) -> None:
        await blacklist_token(jti, expires_in)


auth_service = AuthService()

