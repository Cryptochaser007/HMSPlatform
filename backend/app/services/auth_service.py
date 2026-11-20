"""Authentication service: login, token management, user registration."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import ROLE_PERMISSIONS, Permission, Role
from app.core.security import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    is_token_blacklisted,
    verify_password,
)
from app.models.user import User
from app.schemas.user import Token, UserCreate


class AuthService:
    """Handles authentication, token lifecycle, and user registration."""

    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> User:
        from app.core.redis_state import get_redis
        import time
        lock_key = f"auth:lockout:{email.strip().lower()}"
        redis_client = await get_redis()
        from app.core.config import get_settings
        if get_settings().ENVIRONMENT.lower() == "production" and redis_client.__class__.__name__ == "InMemoryRedisFallback":
            raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable")
        if int(await redis_client.get(lock_key) or 0) >= 5:
            raise HTTPException(status_code=401, detail="Invalid username and/or password")
        result = await db.execute(
            select(User).where(User.email == email, User.is_deleted == False)  # noqa: E712
        )
        user = result.scalar_one_or_none()
        if user is None or not verify_password(password, user.hashed_password):
            attempts = await redis_client.incr(lock_key)
            if attempts == 1:
                await redis_client.set(lock_key, attempts, ex=900)
            await redis_client.set(f"{lock_key}:last_failed", str(int(time.time())), ex=86400)
            if user is not None:
                has_failure_column = await db.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='last_failed_login')"
                ))
                if has_failure_column.scalar_one():
                    await db.execute(text(
                        "UPDATE users SET last_failed_login=:failed_at WHERE id=:uid"
                    ), {"failed_at": datetime.now(timezone.utc), "uid": str(user.id)})
                    await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username and/or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )
        user._previous_last_login = user.last_login
        user.last_login = datetime.now(timezone.utc)
        await redis_client.delete(lock_key)
        await db.flush()
        return user

    def create_tokens(self, user: User, session_id: Optional[str] = None) -> Token:
        import uuid
        session_id = session_id or str(uuid.uuid4())
        role = user.role if isinstance(user.role, str) else user.role.value
        role_enum = Role(role)
        permissions: List[str] = [p.value for p in ROLE_PERMISSIONS.get(role_enum, set())]
        access_token = create_access_token(
            subject=str(user.id),
            role=role,
            permissions=permissions,
            extra_claims={"sid": session_id},
        )
        refresh_token = create_refresh_token(subject=str(user.id), extra_claims={"sid": session_id})
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
        old_jti = payload.get("jti")
        if old_jti and await is_token_blacklisted(old_jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has already been rotated or revoked",
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
        # Rotate refresh token: revoke the consumed refresh token JTI immediately
        if old_jti:
            exp_ts = payload.get("exp")
            ttl = max(int(exp_ts - datetime.now(timezone.utc).timestamp()), 60) if isinstance(exp_ts, (int, float)) else 604800
            await blacklist_token(old_jti, expires_in=ttl)
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
        has_revocation_column = await db.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='tokens_valid_after')"))
        if has_revocation_column.scalar_one():
            await db.execute(text("UPDATE users SET tokens_valid_after=:revoked_at WHERE id=:uid"), {"revoked_at": datetime.now(timezone.utc), "uid": user_id})
        await db.flush()

    async def blacklist_token(self, jti: str, expires_in: int = 1800) -> None:
        await blacklist_token(jti, expires_in)


auth_service = AuthService()

