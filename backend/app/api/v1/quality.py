"""Quality & Accreditation (NABH) indicators and incident reporting endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, get_audit_logger
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.core.rbac import Permission
from app.core.security import get_current_user, require_permissions
from app.schemas.quality import (
    IncidentReportCreate,
    IncidentReportResponse,
    IncidentReportUpdate,
    NABHDashboard,
    QualityIndicatorCreate,
    QualityIndicatorResponse,
    QualityMeasurementCreate,
    QualityMeasurementResponse,
)
from app.services.quality_service import quality_service

router = APIRouter(prefix="/quality", tags=["Quality & NABH Accreditation"])


@router.post(
    "/indicators",
    response_model=QualityIndicatorResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.QUALITY_MANAGE.value))],
)
async def create_quality_indicator(
    data: QualityIndicatorCreate,
    db: AsyncSession = Depends(get_db),
) -> QualityIndicatorResponse:
    """Define a NABH quality indicator (e.g. Surgical site infections, Med errors, Patient falls)."""
    indicator = await quality_service.create_indicator(db, data)
    return QualityIndicatorResponse.model_validate(indicator)


@router.get(
    "/indicators",
    response_model=List[QualityIndicatorResponse],
    dependencies=[Depends(require_permissions(Permission.QUALITY_READ.value))],
)
async def list_quality_indicators(
    db: AsyncSession = Depends(get_db),
) -> List[QualityIndicatorResponse]:
    """List configured hospital clinical quality & patient safety indicators."""
    indicators = await quality_service.list_indicators(db)
    return [QualityIndicatorResponse.model_validate(i) for i in indicators]


@router.post(
    "/measurements",
    response_model=QualityMeasurementResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.QUALITY_MANAGE.value))],
)
async def record_indicator_measurement(
    data: QualityMeasurementCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QualityMeasurementResponse:
    """Log periodic numerator/denominator metrics for indicator calculation."""
    meas = await quality_service.record_measurement(
        db, data, recorded_by=current_user["user_id"]
    )
    return QualityMeasurementResponse.model_validate(meas)


@router.get(
    "/dashboard",
    response_model=NABHDashboard,
    dependencies=[Depends(require_permissions(Permission.QUALITY_READ.value))],
)
async def get_nabh_compliance_dashboard(
    db: AsyncSession = Depends(get_db),
) -> NABHDashboard:
    """Consolidated NABH accreditation performance dashboard with compliance rates."""
    data = await quality_service.get_nabh_dashboard(db)
    return NABHDashboard(**data)


@router.post(
    "/incidents",
    response_model=IncidentReportResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.INCIDENT_CREATE.value))],
)
async def report_incident(
    data: IncidentReportCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncidentReportResponse:
    """Report clinical incident, sentinel event, medication error, or near miss."""
    incident = await quality_service.create_incident(
        db, data, reported_by=current_user["user_id"]
    )

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.CREATE,
        entity_type="IncidentReport",
        entity_id=str(incident.id),
        new_value={"number": incident.incident_number, "severity": incident.severity},
    )
    return IncidentReportResponse.model_validate(incident)


@router.get(
    "/incidents",
    dependencies=[Depends(require_permissions(Permission.QUALITY_READ.value))],
)
async def list_incident_reports(
    status_filter: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Review hospital incident register."""
    res = await quality_service.list_incidents(
        db, page=pagination.page, page_size=pagination.page_size, status_filter=status_filter
    )
    return {
        "items": [IncidentReportResponse.model_validate(i) for i in res["items"]],
        "total": res["total"],
        "page": res["page"],
        "page_size": res["page_size"],
    }


@router.put(
    "/incidents/{incident_id}",
    response_model=IncidentReportResponse,
    dependencies=[Depends(require_permissions(Permission.INCIDENT_MANAGE.value))],
)
async def update_incident_investigation(
    incident_id: str,
    data: IncidentReportUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncidentReportResponse:
    """Document root cause analysis (RCA), corrective actions (CAPA), and closure."""
    incident = await quality_service.update_incident(
        db, incident_id, data, user_id=current_user["user_id"]
    )
    return IncidentReportResponse.model_validate(incident)

