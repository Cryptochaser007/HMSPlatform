"""Tenant (Hospital) onboarding and multi-tenancy management endpoints."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, get_audit_logger
from app.core.database import get_db
from app.core.dependencies import RateLimiter
from app.core.rbac import Role
from app.core.security import get_current_user, hash_password
from app.models.tenant import Hospital
from app.models.user import User

router = APIRouter(prefix="/tenants", tags=["Multi-Tenant Management"])


class TenantRegisterRequest(BaseModel):
    hospital_name: str = Field(..., min_length=2, max_length=255, description="Full registered hospital facility name")
    hospital_code: str = Field(..., min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9_\-]+$", description="Unique facility identifier slug")
    admin_name: str = Field(..., min_length=2, max_length=120)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8, max_length=128)
    hfr_id: Optional[str] = Field(None, max_length=100, description="ABDM National Health Facility Registry (HFR) ID")
    contact_phone: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)


class TenantResponse(BaseModel):
    hospital_id: str
    hospital_name: str
    hospital_code: str
    hfr_id: Optional[str] = None
    admin_email: str
    admin_id: str
    message: str = "Tenant registered successfully"


@router.post(
    "/register",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(times=10, seconds=300))],
)
async def register_tenant(
    data: TenantRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Register a new hospital tenant with an administrator account for Stage 2 cloud deployment."""
    # Check if hospital code already exists
    existing_hosp = await db.execute(select(Hospital).where(Hospital.code == data.hospital_code.lower()))
    if existing_hosp.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Hospital code '{data.hospital_code}' is already registered",
        )

    # Check if admin email already exists
    existing_user = await db.execute(select(User).where(User.email == data.admin_email.lower()))
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{data.admin_email}' is already registered",
        )

    # Create Hospital tenant
    hospital = Hospital(
        name=data.hospital_name,
        code=data.hospital_code.lower(),
        hfr_id=data.hfr_id,
        contact_email=str(data.admin_email),
        contact_phone=data.contact_phone,
        city=data.city,
        state=data.state,
        is_active=True,
    )
    db.add(hospital)
    await db.flush()

    # Create Hospital Admin user
    admin_user = User(
        email=str(data.admin_email).lower(),
        hashed_password=hash_password(data.admin_password),
        name=data.admin_name,
        role=Role.HOSPITAL_ADMIN.value,
        is_active=True,
        hospital_id=hospital.id,
    )
    db.add(admin_user)
    await db.flush()

    # Set PostgreSQL RLS context for the new tenant
    try:
        await db.execute(
            text("SELECT set_config('app.hospital_id', :hid, true)"),
            {"hid": str(hospital.id)},
        )
    except Exception:
        pass

    # Audit log
    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=str(admin_user.id),
        action=AuditAction.CREATE,
        entity_type="Hospital",
        entity_id=str(hospital.id),
        new_value={"name": hospital.name, "code": hospital.code, "admin": admin_user.email},
    )

    return TenantResponse(
        hospital_id=str(hospital.id),
        hospital_name=hospital.name,
        hospital_code=hospital.code,
        hfr_id=hospital.hfr_id,
        admin_email=admin_user.email,
        admin_id=str(admin_user.id),
        message="Hospital tenant registered successfully with admin privileges",
    )


@router.get("/list", response_model=List[Dict[str, Any]])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List registered hospital facilities."""
    result = await db.execute(select(Hospital).where(Hospital.is_active == True).limit(50))
    hospitals = result.scalars().all()
    return [
        {
            "id": str(h.id),
            "name": h.name,
            "code": h.code,
            "hfr_id": h.hfr_id,
            "city": h.city,
            "state": h.state,
        }
        for h in hospitals
    ]
