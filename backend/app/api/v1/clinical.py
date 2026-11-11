"""Electronic Medical Records (EMR): SOAP notes, vitals, prescriptions."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, get_audit_logger
from app.core.database import get_db
from app.core.rbac import Permission
from app.core.security import get_current_user, require_permissions
from app.schemas.clinical import (
    ClinicalNoteCreate,
    ClinicalNoteResponse,
    ClinicalNoteUpdate,
    PrescriptionCreate,
    PrescriptionResponse,
)
from app.services.clinical_service import clinical_service

router = APIRouter(prefix="/clinical", tags=["Electronic Medical Records (EMR)"])


@router.post(
    "/notes",
    response_model=ClinicalNoteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.EMR_CREATE.value))],
)
async def create_clinical_note(
    data: ClinicalNoteCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClinicalNoteResponse:
    """Record clinical consultation note (SOAP, progress note, or procedure)."""
    note = await clinical_service.create_clinical_note(
        db, data, author_id=current_user["user_id"]
    )

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.CREATE,
        entity_type="ClinicalNote",
        entity_id=str(note.id),
        new_value={"type": note.note_type, "encounter_id": note.encounter_id},
    )
    return ClinicalNoteResponse.model_validate(note)


@router.get(
    "/notes/{encounter_id}",
    response_model=List[ClinicalNoteResponse],
    dependencies=[Depends(require_permissions(Permission.EMR_READ.value))],
)
async def get_encounter_notes(
    encounter_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[ClinicalNoteResponse]:
    """Retrieve all clinical notes and history recorded under an encounter."""
    notes = await clinical_service.get_notes_for_encounter(db, encounter_id)
    return [ClinicalNoteResponse.model_validate(n) for n in notes]


@router.put(
    "/notes/{note_id}/amend",
    response_model=ClinicalNoteResponse,
    dependencies=[Depends(require_permissions(Permission.EMR_UPDATE.value))],
)
async def amend_clinical_note(
    note_id: str,
    data: ClinicalNoteUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClinicalNoteResponse:
    """Create an amendment note linked to original (enforces immutable medical records)."""
    amendment = await clinical_service.amend_note(
        db, note_id, data, author_id=current_user["user_id"]
    )

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.UPDATE,
        entity_type="ClinicalNote",
        entity_id=str(amendment.id),
        new_value={"amended_from_id": note_id},
    )
    return ClinicalNoteResponse.model_validate(amendment)


@router.post(
    "/prescriptions",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.PRESCRIPTION_CREATE.value))],
)
async def create_prescription(
    data: PrescriptionCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrescriptionResponse:
    """Create a digital prescription with medication dosages and schedules."""
    prescription = await clinical_service.create_prescription(
        db, data, doctor_id=current_user["user_id"]
    )

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.CREATE,
        entity_type="Prescription",
        entity_id=str(prescription.id),
        new_value={"item_count": len(prescription.items)},
    )
    return PrescriptionResponse.model_validate(prescription)


@router.get(
    "/prescriptions/{encounter_id}",
    response_model=List[PrescriptionResponse],
    dependencies=[Depends(require_permissions(Permission.PRESCRIPTION_READ.value))],
)
async def get_encounter_prescriptions(
    encounter_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[PrescriptionResponse]:
    """Get all prescriptions issued during an encounter."""
    prescriptions = await clinical_service.get_prescriptions_for_encounter(db, encounter_id)
    return [PrescriptionResponse.model_validate(p) for p in prescriptions]


@router.put(
    "/prescriptions/{prescription_id}/sign",
    response_model=PrescriptionResponse,
    dependencies=[Depends(require_permissions(Permission.PRESCRIPTION_CREATE.value))],
)
async def sign_prescription(
    prescription_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrescriptionResponse:
    """Doctor digitally signs the prescription to authorize pharmacy dispensing."""
    prescription = await clinical_service.sign_prescription(
        db, prescription_id, doctor_id=current_user["user_id"]
    )

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.UPDATE,
        entity_type="Prescription",
        entity_id=prescription_id,
        new_value={"status": "SIGNED"},
    )
    return PrescriptionResponse.model_validate(prescription)


@router.get(
    "/patient/{patient_id}/timeline",
    dependencies=[Depends(require_permissions(Permission.EMR_READ.value))],
)
async def get_patient_clinical_timeline(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve unified historical clinical timeline for the patient."""
    timeline = await clinical_service.get_patient_history(db, patient_id)
    return {
        "encounter_count": len(timeline["encounters"]),
        "note_count": len(timeline["clinical_notes"]),
        "prescription_count": len(timeline["prescriptions"]),
    }

