"""Ward management, Bed allocations, and IPD Inpatient Admissions."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, get_audit_logger
from app.core.database import get_db
from app.core.rbac import Permission
from app.core.security import get_current_user, require_permissions
from app.schemas.ward import (
    AdmissionCreate,
    AdmissionResponse,
    BedOccupancyDashboard,
    BedResponse,
    BedStatusUpdate,
    DischargeCreate,
    WardCreate,
    WardResponse,
)
from app.services.ward_service import ward_service

router = APIRouter(prefix="/wards", tags=["Ward & Bed Management"])


@router.post(
    "/",
    response_model=WardResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.WARD_MANAGE.value))],
)
async def create_ward(
    data: WardCreate,
    db: AsyncSession = Depends(get_db),
) -> WardResponse:
    """Create a new hospital ward (ICU, General, Private) and initialize beds."""
    ward = await ward_service.create_ward(db, data)
    return WardResponse.model_validate(ward)


@router.get(
    "/",
    response_model=List[WardResponse],
    dependencies=[Depends(require_permissions(Permission.ADMISSION_READ.value))],
)
async def list_wards(
    db: AsyncSession = Depends(get_db),
) -> List[WardResponse]:
    """List all hospital wards."""
    wards = await ward_service.list_wards(db)
    return [WardResponse.model_validate(w) for w in wards]


@router.put(
    "/beds/{bed_id}/status",
    response_model=BedResponse,
    dependencies=[Depends(require_permissions(Permission.BED_MANAGE.value))],
)
async def update_bed_status(
    bed_id: str,
    body: BedStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> BedResponse:
    """Update bed status (AVAILABLE, MAINTENANCE, OCCUPIED)."""
    bed = await ward_service.update_bed_status(db, bed_id, body.status)
    return BedResponse.model_validate(bed)


@router.post(
    "/admissions",
    response_model=AdmissionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.ADMISSION_CREATE.value))],
)
async def admit_patient(
    data: AdmissionCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdmissionResponse:
    """Admit patient to an inpatient bed (IPD intake)."""
    admission = await ward_service.admit_patient(
        db, data, admitted_by=current_user["user_id"]
    )

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.CREATE,
        entity_type="Admission",
        entity_id=str(admission.id),
        new_value={"bed_id": str(admission.bed_id), "patient_id": str(admission.patient_id)},
    )
    return AdmissionResponse.model_validate(admission)


@router.put(
    "/admissions/{admission_id}/transfer",
    response_model=AdmissionResponse,
    dependencies=[Depends(require_permissions(Permission.ADMISSION_UPDATE.value))],
)
async def transfer_bed(
    admission_id: str,
    new_bed_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> AdmissionResponse:
    """Transfer admitted patient to another bed / ward."""
    admission = await ward_service.transfer_bed(db, admission_id, new_bed_id)
    return AdmissionResponse.model_validate(admission)


@router.post(
    "/admissions/{admission_id}/discharge",
    response_model=AdmissionResponse,
    dependencies=[Depends(require_permissions(Permission.ADMISSION_UPDATE.value))],
)
async def discharge_patient(
    admission_id: str,
    data: DischargeCreate,
    db: AsyncSession = Depends(get_db),
) -> AdmissionResponse:
    """Discharge inpatient, releasing occupied bed."""
    admission = await ward_service.discharge_patient(db, admission_id, data)
    return AdmissionResponse.model_validate(admission)


@router.get(
    "/occupancy",
    response_model=BedOccupancyDashboard,
    dependencies=[Depends(require_permissions(Permission.ADMISSION_READ.value))],
)
async def get_bed_occupancy_dashboard(
    db: AsyncSession = Depends(get_db),
) -> BedOccupancyDashboard:
    """Live hospital bed census and occupancy rates by ward."""
    dashboard = await ward_service.get_bed_occupancy(db)
    return BedOccupancyDashboard(**dashboard)

