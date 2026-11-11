"""Radiology Information System and PACS / OHIF integration endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, get_audit_logger
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.core.rbac import Permission
from app.core.security import get_current_user, require_permissions
from app.schemas.radiology import (
    RadiologyOrderCreate,
    RadiologyOrderResponse,
    RadiologyOrderUpdate,
    RadiologyReportCreate,
    RadiologyReportResponse,
)
from app.services.radiology_service import radiology_service

router = APIRouter(prefix="/radiology", tags=["Radiology (PACS)"])


@router.post(
    "/orders",
    response_model=RadiologyOrderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.RADIOLOGY_ORDER_CREATE.value))],
)
async def create_radiology_order(
    data: RadiologyOrderCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RadiologyOrderResponse:
    """Order radiology examination (X-Ray, CT, MRI, Ultrasound) with Accession Number."""
    order = await radiology_service.create_order(
        db, data, ordered_by=current_user["user_id"]
    )

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.CREATE,
        entity_type="RadiologyOrder",
        entity_id=str(order.id),
        new_value={"modality": order.modality, "body_part": order.body_part},
    )
    return RadiologyOrderResponse.model_validate(order)


@router.get(
    "/orders",
    dependencies=[Depends(require_permissions(Permission.RADIOLOGY_VIEW.value))],
)
async def list_radiology_orders(
    modality: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """List radiology imaging worklist."""
    res = await radiology_service.list_orders(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        modality=modality,
        status_filter=status_filter,
    )
    return {
        "items": [RadiologyOrderResponse.model_validate(o) for o in res["items"]],
        "total": res["total"],
        "page": res["page"],
        "page_size": res["page_size"],
    }


@router.put(
    "/orders/{order_id}/status",
    response_model=RadiologyOrderResponse,
    dependencies=[Depends(require_permissions(Permission.RADIOLOGY_UPLOAD.value))],
)
async def update_radiology_status(
    order_id: str,
    data: RadiologyOrderUpdate,
    db: AsyncSession = Depends(get_db),
) -> RadiologyOrderResponse:
    """Link PACS DICOM study UID or update examination execution status."""
    order = await radiology_service.update_order_status(db, order_id, data)
    return RadiologyOrderResponse.model_validate(order)


@router.post(
    "/reports",
    response_model=RadiologyReportResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.RADIOLOGY_REPORT.value))],
)
async def create_radiology_report(
    data: RadiologyReportCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RadiologyReportResponse:
    """Radiologist drafts diagnostic study interpretation."""
    report = await radiology_service.create_report(
        db, data, radiologist_id=current_user["user_id"]
    )
    return RadiologyReportResponse.model_validate(report)


@router.put(
    "/reports/{report_id}/verify",
    response_model=RadiologyReportResponse,
    dependencies=[Depends(require_permissions(Permission.RADIOLOGY_REPORT.value))],
)
async def verify_radiology_report(
    report_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RadiologyReportResponse:
    """Consultant Radiologist signs and verifies diagnostic imaging report."""
    report = await radiology_service.verify_report(
        db, report_id, verifier_id=current_user["user_id"]
    )
    return RadiologyReportResponse.model_validate(report)


@router.get(
    "/viewer/{study_id}",
    dependencies=[Depends(require_permissions(Permission.RADIOLOGY_VIEW.value))],
)
async def get_pacs_viewer_link(
    study_id: str,
) -> Dict[str, str]:
    """Generate OHIF DICOM Web viewer URL for deep-linking images in patient chart."""
    return radiology_service.get_viewer_url(study_id)

