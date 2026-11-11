"""Patient Registration & Demographics endpoints with DPDP compliance."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, get_audit_logger
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.core.rbac import Permission, Role
from app.core.security import get_current_user, require_permissions
from app.models.consent import Consent, ConsentStatus, ConsentType
from app.models.patient import Patient
from app.schemas.consent import ConsentCreate, ConsentResponse
from app.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientSearchParams,
    PatientUpdate,
)
from app.services.patient_service import patient_service

router = APIRouter(prefix="/patients", tags=["Patient Registration & Demographics"])


@router.post(
    "/",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.PATIENT_CREATE.value))],
)
async def register_patient(
    data: PatientCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PatientResponse:
    """Register a new patient with auto-generated UHID, encryption for PII, and ABHA ID."""
    patient = await patient_service.register_patient(db, data)

    # Immutable audit logging
    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.CREATE,
        entity_type="Patient",
        entity_id=str(patient.id),
        new_value={"uhid": patient.registration_number, "abha_id": patient.abha_id},
    )
    return PatientResponse.model_validate(patient)


@router.get(
    "/",
    response_model=PatientListResponse,
    dependencies=[Depends(require_permissions(Permission.PATIENT_READ.value))],
)
async def list_patients(
    query: Optional[str] = Query(None, description="Search name, phone, or UHID"),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> PatientListResponse:
    """Search and paginate registered patients."""
    search_params = PatientSearchParams(query=query)
    res = await patient_service.search_patients(
        db, search_params, page=pagination.page, page_size=pagination.page_size
    )
    return PatientListResponse(
        items=[PatientResponse.model_validate(p) for p in res["items"]],
        total=res["total"],
        page=res["page"],
        page_size=res["page_size"],
    )


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    dependencies=[Depends(require_permissions(Permission.PATIENT_READ.value))],
)
async def get_patient_by_id(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
) -> PatientResponse:
    """Fetch patient profile with decrypted PII for authorized clinical roles."""
    patient = await patient_service.get_patient(db, patient_id)
    return PatientResponse.model_validate(patient)


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    dependencies=[Depends(require_permissions(Permission.PATIENT_UPDATE.value))],
)
async def update_patient(
    patient_id: str,
    data: PatientUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PatientResponse:
    """Update patient demographic details with audit capture."""
    patient = await patient_service.update_patient(db, patient_id, data)

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.UPDATE,
        entity_type="Patient",
        entity_id=patient_id,
        new_value=data.model_dump(exclude_unset=True),
    )
    return PatientResponse.model_validate(patient)


@router.delete(
    "/{patient_id}",
    dependencies=[Depends(require_permissions(Permission.PATIENT_DELETE.value))],
)
async def delete_patient_dpdp(
    patient_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Execute DPDP Act Right-to-Erasure (anonymization and soft delete)."""
    await patient_service.soft_delete_patient(db, patient_id)

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.DELETE,
        entity_type="Patient",
        entity_id=patient_id,
        new_value={"reason": "DPDP Right to Erasure requested"},
    )
    return {"message": "Patient record anonymized and removed under DPDP compliance"}


# ── DPDP Consent Management ──────────────────────────────────────────────────


@router.post(
    "/{patient_id}/consents",
    response_model=ConsentResponse,
    dependencies=[Depends(require_permissions(Permission.CONSENT_MANAGE.value))],
)
async def record_patient_consent(
    patient_id: str,
    data: ConsentCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsentResponse:
    """Record signed consent artifact for patient data processing / ABDM linking."""
    consent = Consent(
        patient_id=patient_id,
        consent_type=ConsentType(data.consent_type),
        purpose=data.purpose,
        data_categories=data.data_categories or ["demographics", "clinical"],
        granted_to=data.granted_to,
        status=ConsentStatus.GRANTED,
        granted_at=datetime.now(timezone.utc),
        expires_at=data.expires_at,
    )
    db.add(consent)
    await db.flush()
    await db.refresh(consent)

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.CONSENT_GRANTED,
        entity_type="Consent",
        entity_id=str(consent.id),
        new_value={"consent_type": consent.consent_type, "patient_id": patient_id},
    )
    return ConsentResponse.model_validate(consent)


@router.get(
    "/{patient_id}/consents",
    response_model=List[ConsentResponse],
    dependencies=[Depends(require_permissions(Permission.CONSENT_READ.value))],
)
async def list_patient_consents(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[ConsentResponse]:
    """List historical consents recorded for the patient."""
    res = await db.execute(select(Consent).where(Consent.patient_id == patient_id))
    consents = list(res.scalars().all())
    return [ConsentResponse.model_validate(c) for c in consents]

