"""Authentication service: login, token management, user registration."""

import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import ROLE_PERMISSIONS, Role
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
        from app.core.security import security_redis
        email = email.strip().lower()
        redis_client = await security_redis()
        lock_key = f"auth:fail:{email}"
        if int(await redis_client.get(lock_key) or 0) >= 5:
            raise HTTPException(status_code=401, detail="Invalid username and/or password")
        await db.execute(text(
            "SELECT set_config('app.login_email', :email, true), "
            "set_config('app.is_superadmin', 'false', true)"
        ), {"email": email})
        result = await db.execute(select(User).where(User.email == email, User.is_deleted.is_(False)))
        user = result.scalar_one_or_none()
        await db.execute(text("SELECT set_config('app.login_email', '', true)"))
        valid = user is not None and verify_password(password, user.hashed_password) and user.is_active
        if not valid:
            # Increment and assign the lockout window in one operation.
            await redis_client.eval("""
                local n = redis.call('INCR', KEYS[1])
                if n == 1 then redis.call('EXPIRE', KEYS[1], 900) end
                return n
            """, 1, lock_key)
            await redis_client.set(f"{lock_key}:last_failed", datetime.now(UTC).isoformat(), ex=86400)
            raise HTTPException(status_code=401, detail="Invalid username and/or password")
        assert user is not None
        await db.execute(text(
            "SELECT set_config('app.current_hospital_id', :hid, true), "
            "set_config('app.hospital_id', :hid, true)"
        ), {"hid": str(user.hospital_id)})
        from app.models.tenant import Hospital
        hospital = (await db.execute(select(Hospital).where(Hospital.id == user.hospital_id))).scalar_one_or_none()
        if hospital is None or not hospital.is_active or hospital.is_deleted:
            raise HTTPException(status_code=401, detail="Invalid username and/or password")
        assert user is not None
        db.info["previous_last_login"] = user.last_login
        user.last_login = datetime.now(UTC)
        await redis_client.delete(lock_key)
        await db.flush()
        return user

    def create_tokens(self, user: User, session_id: str | None = None) -> Token:
        import uuid
        session_id = session_id or str(uuid.uuid4())
        role = user.role if isinstance(user.role, str) else user.role.value
        role_enum = Role(role)
        permissions: list[str] = [p.value for p in ROLE_PERMISSIONS.get(role_enum, set())]
        access_token = create_access_token(
            subject=str(user.id),
            role=role,
            permissions=permissions,
            extra_claims={"sid": session_id, "hospital_id": str(user.hospital_id)},
        )
        refresh_token = create_refresh_token(subject=str(user.id), extra_claims={"sid": session_id})
        return Token(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(self, db: AsyncSession, refresh_token: str) -> Token:
        try:
            payload = decode_token(refresh_token)
        except Exception:
            logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
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
        from app.core.security import validate_session
        await validate_session(payload)
        user_id = payload.get("sub")
        await db.execute(text("SELECT set_config('app.current_hospital_id', :hid, true)"),
                         {"hid": str(payload.get("hospital_id", ""))})
        result = await db.execute(
            select(User).where(User.id == user_id, User.is_deleted == False)
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
            ttl = max(int(exp_ts - datetime.now(UTC).timestamp()), 60) if isinstance(exp_ts, (int, float)) else 604800
            await blacklist_token(old_jti, expires_in=ttl)
        return self.create_tokens(user)

    async def register_user(self, db: AsyncSession, data: UserCreate) -> User:
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        if data.role == Role.SUPER_ADMIN.value:
            raise HTTPException(status_code=403, detail="Super administrator provisioning requires a system operator")
        user = User(
            email=data.email.strip().lower(),
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
            await db.execute(text("UPDATE users SET tokens_valid_after=:revoked_at WHERE id=:uid"), {"revoked_at": datetime.now(UTC), "uid": user_id})
        await db.flush()

    async def blacklist_token(self, jti: str, expires_in: int = 1800) -> None:
        await blacklist_token(jti, expires_in)


auth_service = AuthService()

