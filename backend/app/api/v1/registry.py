"""HFR/HPR synchronization, referrals and payer/claim workflow endpoints."""
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.abdm.availability import require_abdm_enabled
from app.abdm.hfr_service import hfr_service
from app.abdm.hpr_service import hpr_service
from app.core.database import get_db
from app.core.encryption import encrypt_field
from app.core.rbac import Permission
from app.core.security import require_permissions
from app.models.registry import (
    HFRFacility,
    HPRPractitioner,
    InsuranceClaim,
    InsurancePolicy,
    Referral,
)

router = APIRouter(tags=["Registry, Referrals & Insurance"])


class ReferralCreate(BaseModel):
    patient_id: str
    encounter_id: str | None = None
    referral_type: str = "INTERNAL"
    source_department: str | None = None
    target_department: str | None = None
    target_facility_id: str | None = None
    practitioner_id: str | None = None
    reason: str = Field(..., min_length=2, max_length=4000)
    clinical_summary: dict[str, Any] = Field(default_factory=dict)


class PolicyCreate(BaseModel):
    patient_id: str
    payer_code: str | None = None
    payer_name: str
    policy_number: str | None = None
    member_id: str | None = None
    coverage: dict[str, Any] = Field(default_factory=dict)
    valid_from: date | None = None
    valid_to: date | None = None


class ClaimCreate(BaseModel):
    policy_id: str
    patient_id: str
    encounter_id: str | None = None
    claim_number: str | None = None
    preauth_reference: str | None = None
    requested_amount: Decimal = Field(ge=0)
    currency: str = "INR"
    nhcx_payload: dict[str, Any] = Field(default_factory=dict)


def _base(row) -> dict[str, Any]:
    return {"id": str(row.id), "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat()}


@router.post("/registry/hfr/sync", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_abdm_enabled), Depends(require_permissions(Permission.ADMIN_PANEL.value))])
async def sync_hfr_facility(facility_id: str = Query(..., min_length=2, max_length=100), db: AsyncSession = Depends(get_db)):
    profile = await hfr_service.get_facility_profile(facility_id)
    row = (await db.execute(select(HFRFacility).where(HFRFacility.hfr_id == facility_id))).scalar_one_or_none()
    if row is None:
        row = HFRFacility(hfr_id=facility_id, facility_name=profile.name)
        db.add(row)
    row.facility_name = profile.name
    row.facility_type = profile.facility_type
    row.address = {"address": profile.address, "ownership": profile.ownership, "specialities": profile.specialities, "services": profile.services}
    row.registry_status = "ACTIVE" if profile.is_active else "INACTIVE"
    row.synced_at = datetime.now(UTC)
    row.source_payload = profile.model_dump(mode="json")
    await db.flush()
    return {**_base(row), "hfr_id": row.hfr_id, "facility_name": row.facility_name, "registry_status": row.registry_status, "synced_at": row.synced_at.isoformat()}


@router.post("/registry/hpr/sync", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_abdm_enabled), Depends(require_permissions(Permission.USER_MANAGE.value))])
async def sync_hpr_practitioner(registration_number: str = Query(..., min_length=2, max_length=100), council: str = Query(..., min_length=2, max_length=150), db: AsyncSession = Depends(get_db)):
    profile = await hpr_service.verify_doctor(registration_number, council)
    row = (await db.execute(select(HPRPractitioner).where(HPRPractitioner.hpr_id == profile.hpr_id))).scalar_one_or_none()
    if row is None:
        row = HPRPractitioner(hpr_id=profile.hpr_id, practitioner_name=profile.name)
        db.add(row)
    row.practitioner_name = profile.name
    row.registration_number = profile.registration_number
    row.specialties = [profile.speciality]
    row.registry_status = "VERIFIED" if profile.is_verified else "UNVERIFIED"
    row.synced_at = datetime.now(UTC)
    row.source_payload = profile.model_dump(mode="json")
    await db.flush()
    return {**_base(row), "hpr_id": row.hpr_id, "practitioner_name": row.practitioner_name, "registry_status": row.registry_status}


@router.get("/referrals", dependencies=[Depends(require_permissions(Permission.PATIENT_READ.value))])
async def list_referrals(patient_id: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Referral).where(Referral.is_deleted == False).order_by(desc(Referral.created_at)).limit(100)
    if patient_id:
        query = query.where(Referral.patient_id == patient_id)
    rows = (await db.execute(query)).scalars().all()
    return {"items": [{**_base(r), "patient_id": str(r.patient_id), "encounter_id": str(r.encounter_id) if r.encounter_id else None, "referral_type": r.referral_type, "source_department": r.source_department, "target_department": r.target_department, "target_facility_id": str(r.target_facility_id) if r.target_facility_id else None, "practitioner_id": str(r.practitioner_id) if r.practitioner_id else None, "reason": r.reason, "clinical_summary": r.clinical_summary, "status": r.status, "abdm_request_id": r.abdm_request_id} for r in rows], "total": len(rows)}


@router.post("/referrals", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permissions(Permission.PATIENT_CREATE.value))])
async def create_referral(data: ReferralCreate, db: AsyncSession = Depends(get_db)):
    row = Referral(**data.model_dump())
    db.add(row)
    await db.flush()
    return {**_base(row), "patient_id": str(row.patient_id), "referral_type": row.referral_type, "status": row.status}


@router.patch("/referrals/{referral_id}/status", dependencies=[Depends(require_permissions(Permission.PATIENT_UPDATE.value))])
async def update_referral_status(referral_id: str, new_status: str = Query(..., pattern="^(DRAFT|SENT|ACCEPTED|DECLINED|COMPLETED|CANCELLED)$"), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Referral).where(Referral.id == referral_id, Referral.is_deleted == False))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Referral not found")
    row.status = new_status
    row.responded_at = datetime.now(UTC) if new_status in {"ACCEPTED", "DECLINED", "COMPLETED"} else row.responded_at
    await db.flush()
    return {"id": str(row.id), "status": row.status}


@router.get("/insurance/policies", dependencies=[Depends(require_permissions(Permission.BILLING_READ.value))])
async def list_policies(patient_id: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(InsurancePolicy).where(InsurancePolicy.is_deleted == False).order_by(desc(InsurancePolicy.created_at)).limit(100)
    if patient_id:
        q = q.where(InsurancePolicy.patient_id == patient_id)
    rows = (await db.execute(q)).scalars().all()
    return {"items": [{**_base(r), "patient_id": str(r.patient_id), "payer_code": r.payer_code, "payer_name": r.payer_name, "coverage": r.coverage, "valid_from": r.valid_from.isoformat() if r.valid_from else None, "valid_to": r.valid_to.isoformat() if r.valid_to else None, "status": r.status} for r in rows], "total": len(rows)}


@router.post("/insurance/policies", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permissions(Permission.BILLING_CREATE.value))])
async def create_policy(data: PolicyCreate, db: AsyncSession = Depends(get_db)):
    values = data.model_dump(exclude={"policy_number", "member_id"})
    row = InsurancePolicy(**values, policy_number_encrypted=encrypt_field(data.policy_number) if data.policy_number else None, member_id_encrypted=encrypt_field(data.member_id) if data.member_id else None)
    db.add(row)
    await db.flush()
    return {**_base(row), "patient_id": str(row.patient_id), "payer_name": row.payer_name, "status": row.status}


@router.get("/insurance/claims", dependencies=[Depends(require_permissions(Permission.BILLING_READ.value))])
async def list_claims(patient_id: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(InsuranceClaim).where(InsuranceClaim.is_deleted == False).order_by(desc(InsuranceClaim.created_at)).limit(100)
    if patient_id:
        q = q.where(InsuranceClaim.patient_id == patient_id)
    rows = (await db.execute(q)).scalars().all()
    return {"items": [{**_base(r), "policy_id": str(r.policy_id), "patient_id": str(r.patient_id), "encounter_id": str(r.encounter_id) if r.encounter_id else None, "claim_number": r.claim_number, "preauth_reference": r.preauth_reference, "lifecycle_status": r.lifecycle_status, "requested_amount": str(r.requested_amount), "approved_amount": str(r.approved_amount) if r.approved_amount is not None else None, "currency": r.currency, "nhcx_payload": r.nhcx_payload} for r in rows], "total": len(rows)}


@router.post("/insurance/claims", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permissions(Permission.BILLING_CREATE.value))])
async def create_claim(data: ClaimCreate, db: AsyncSession = Depends(get_db)):
    row = InsuranceClaim(**data.model_dump(mode="python"))
    db.add(row)
    await db.flush()
    return {**_base(row), "claim_number": row.claim_number, "lifecycle_status": row.lifecycle_status, "requested_amount": str(row.requested_amount), "currency": row.currency}


@router.patch("/insurance/claims/{claim_id}/status", dependencies=[Depends(require_permissions(Permission.BILLING_UPDATE.value))])
async def update_claim_status(claim_id: str, new_status: str = Query(..., pattern="^(DRAFT|PREAUTH_PENDING|PREAUTH_APPROVED|SUBMITTED|ADJUDICATED|REJECTED|PAID|CANCELLED)$"), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(InsuranceClaim).where(InsuranceClaim.id == claim_id, InsuranceClaim.is_deleted == False))).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Insurance claim not found")
    row.lifecycle_status = new_status
    if new_status in {"ADJUDICATED", "REJECTED", "PAID"}:
        row.adjudicated_at = datetime.now(UTC)
    await db.flush()
    return {"id": str(row.id), "lifecycle_status": row.lifecycle_status}
