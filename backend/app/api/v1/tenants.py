"""Atomic self-service trial hospital onboarding."""
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, get_audit_logger
from app.core.database import get_db
from app.core.dependencies import RateLimiter
from app.core.security import hash_password
from app.models.tenant import Department, Hospital
from app.models.user import User

router = APIRouter(prefix="/tenants", tags=["Hospital onboarding"])


class HospitalSignup(BaseModel):
    hospital_name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    admin_name: str = Field(min_length=2, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8, max_length=72)


@router.post("/register", status_code=201,
             dependencies=[Depends(RateLimiter(times=5, seconds=300))])
async def register_hospital(data: HospitalSignup, db: AsyncSession = Depends(get_db)) -> dict:
    hospital_id = str(uuid4())
    admin_id = str(uuid4())
    try:
        # Start tenant context before the first write. RLS also protects RETURNING.
        await db.execute(text(
            "SELECT set_config('app.current_hospital_id', :hid, true), "
            "set_config('app.hospital_id', :hid, true), "
            "set_config('app.is_superadmin', 'false', true)"
        ), {"hid": hospital_id})
        hospital = Hospital(id=hospital_id, name=data.hospital_name, slug=data.slug,
                            code=data.slug, abdm_env="MOCK", subscription_tier="TRIAL")
        db.add(hospital)
        await db.flush()
        admin = User(id=admin_id, email=str(data.admin_email).lower(),
                     full_name=data.admin_name, hashed_password=hash_password(data.admin_password),
                     role="HOSPITAL_ADMIN", department="OPD", hospital_id=hospital_id)
        db.add(admin)
        db.add(Department(hospital_id=hospital_id, name="OPD"))
        await db.flush()
        # Stable clinical definitions with codes scoped by hospital.
        for code, name, description in [
            ("NABH-WAIT", "OPD wait time compliance", "OPD visits served within 30 minutes"),
            ("NABH-HYGIENE", "Hand hygiene compliance", "Observed hand hygiene opportunities completed"),
        ]:
            await db.execute(text(
                "INSERT INTO quality_indicators "
                "(name,code,category,description,numerator_description,denominator_description,"
                "target_value,unit,frequency,is_nabh_mandatory,is_active) "
                "VALUES (:name,:code,'Patient Safety',:description,'Compliant events',"
                "'Observed events',95,'%', 'MONTHLY',true,true)"
            ), {"code": code, "name": name, "description": description})
        await (await get_audit_logger()).log(
            db, user_id=admin_id, action=AuditAction.CREATE, entity_type="Hospital",
            entity_id=hospital_id, new_value={"slug": data.slug, "abdm_env": "MOCK"},
        )
        # Return success only after all provisioning work is durable.
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise HTTPException(status_code=409, detail="Hospital slug or administrator email already registered") from exc
        raise
    return {"hospital_id": hospital_id, "admin_id": admin_id, "abdm_env": "MOCK",
            "subscription_tier": "TRIAL", "message": "Hospital registered. Sign in with your administrator account."}
