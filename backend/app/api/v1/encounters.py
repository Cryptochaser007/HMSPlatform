"""OPD and IPD Encounter management and clinic queue endpoints."""

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, get_audit_logger
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.core.rbac import Permission
from app.core.security import get_current_user, require_permissions
from app.schemas.encounter import (
    AppointmentSlot,
    EncounterCreate,
    EncounterListResponse,
    EncounterResponse,
    EncounterUpdate,
    QueueResponse,
)
from app.services.encounter_service import encounter_service

router = APIRouter(prefix="/encounters", tags=["OPD & IPD Encounters"])


@router.post(
    "/",
    response_model=EncounterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.ENCOUNTER_CREATE.value))],
)
async def create_encounter(
    data: EncounterCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EncounterResponse:
    """Create a new encounter (OPD walk-in, IPD intake, or booked appointment)."""
    encounter = await encounter_service.create_encounter(db, data)

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.CREATE,
        entity_type="Encounter",
        entity_id=str(encounter.id),
        new_value={"type": encounter.encounter_type, "token": encounter.token_number},
    )
    return EncounterResponse.model_validate(encounter)


@router.get(
    "/",
    response_model=EncounterListResponse,
    dependencies=[Depends(require_permissions(Permission.ENCOUNTER_READ.value))],
)
async def list_encounters(
    department: Optional[str] = Query(None),
    doctor_id: Optional[str] = Query(None),
    encounter_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    target_date: Optional[date] = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> EncounterListResponse:
    """List encounters filtered by department, doctor, status, or date."""
    res = await encounter_service.list_encounters(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        department=department,
        doctor_id=doctor_id,
        encounter_type=encounter_type,
        status_filter=status_filter,
        date_filter=target_date,
    )
    return EncounterListResponse(
        items=[EncounterResponse.model_validate(e) for e in res["items"]],
        total=res["total"],
        page=res["page"],
        page_size=res["page_size"],
    )


@router.get(
    "/{encounter_id}",
    response_model=EncounterResponse,
    dependencies=[Depends(require_permissions(Permission.ENCOUNTER_READ.value))],
)
async def get_encounter(
    encounter_id: str,
    db: AsyncSession = Depends(get_db),
) -> EncounterResponse:
    """Get single encounter details."""
    encounter = await encounter_service.get_encounter(db, encounter_id)
    return EncounterResponse.model_validate(encounter)


@router.put(
    "/{encounter_id}",
    response_model=EncounterResponse,
    dependencies=[Depends(require_permissions(Permission.ENCOUNTER_UPDATE.value))],
)
async def update_encounter(
    encounter_id: str,
    data: EncounterUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EncounterResponse:
    """Update encounter notes, room assignment, or follow-up date."""
    encounter = await encounter_service.update_encounter(db, encounter_id, data)
    return EncounterResponse.model_validate(encounter)


@router.post(
    "/{encounter_id}/check-in",
    response_model=EncounterResponse,
    dependencies=[Depends(require_permissions(Permission.ENCOUNTER_UPDATE.value))],
)
async def check_in_patient(
    encounter_id: str,
    db: AsyncSession = Depends(get_db),
) -> EncounterResponse:
    """Check in patient on arrival and allocate sequential OPD token."""
    encounter = await encounter_service.check_in(db, encounter_id)
    return EncounterResponse.model_validate(encounter)


@router.post(
    "/{encounter_id}/start",
    response_model=EncounterResponse,
    dependencies=[Depends(require_permissions(Permission.ENCOUNTER_UPDATE.value))],
)
async def start_consultation(
    encounter_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EncounterResponse:
    """Doctor marks encounter as IN_PROGRESS when starting patient examination."""
    encounter = await encounter_service.start_consultation(
        db, encounter_id, current_user["user_id"]
    )
    return EncounterResponse.model_validate(encounter)


@router.post(
    "/{encounter_id}/complete",
    response_model=EncounterResponse,
    dependencies=[Depends(require_permissions(Permission.ENCOUNTER_UPDATE.value))],
)
async def complete_consultation(
    encounter_id: str,
    db: AsyncSession = Depends(get_db),
) -> EncounterResponse:
    """Conclude encounter and mark status COMPLETED."""
    encounter = await encounter_service.complete_encounter(db, encounter_id)
    return EncounterResponse.model_validate(encounter)


@router.get(
    "/queue/{department}",
    response_model=List[QueueResponse],
    dependencies=[Depends(require_permissions(Permission.ENCOUNTER_READ.value))],
)
async def get_opd_queue(
    department: str,
    db: AsyncSession = Depends(get_db),
) -> List[QueueResponse]:
    """Get active live queue tokens and estimated wait times for a department."""
    queue = await encounter_service.get_queue(db, department)
    return [QueueResponse(**item) for item in queue]


@router.get(
    "/appointments/slots",
    response_model=AppointmentSlot,
)
async def get_available_appointment_slots(
    doctor_id: str = Query(...),
    target_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
) -> AppointmentSlot:
    """Find doctor's available 30-minute booking slots on a selected date."""
    slots = await encounter_service.get_appointment_slots(db, doctor_id, target_date)
    return AppointmentSlot(**slots)

