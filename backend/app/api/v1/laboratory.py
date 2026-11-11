"""Laboratory Information System (LIS) orders, sampling, and results endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, get_audit_logger
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.core.rbac import Permission
from app.core.security import get_current_user, require_permissions
from app.models.laboratory import LabTest
from app.schemas.laboratory import (
    LabOrderCreate,
    LabOrderResponse,
    LabResultCreate,
    LabResultResponse,
    LabResultVerify,
    LabTestCreate,
    LabTestResponse,
)
from app.services.lab_service import lab_service

router = APIRouter(prefix="/lab", tags=["Laboratory Information System (LIS)"])


@router.post(
    "/tests",
    response_model=LabTestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.LAB_RESULT_CREATE.value))],
)
async def create_lab_test(
    data: LabTestCreate,
    db: AsyncSession = Depends(get_db),
) -> LabTestResponse:
    """Add a diagnostic test profile to the laboratory catalog."""
    test = LabTest(**data.model_dump())
    db.add(test)
    await db.flush()
    await db.refresh(test)
    return LabTestResponse.model_validate(test)


@router.get(
    "/tests",
    response_model=List[LabTestResponse],
    dependencies=[Depends(require_permissions(Permission.LAB_ORDER_READ.value))],
)
async def list_lab_tests(
    db: AsyncSession = Depends(get_db),
) -> List[LabTestResponse]:
    """List all available laboratory test profiles with reference ranges."""
    res = await db.execute(select(LabTest).where(LabTest.is_deleted == False, LabTest.is_active == True))  # noqa: E712
    return [LabTestResponse.model_validate(t) for t in res.scalars().all()]


@router.post(
    "/orders",
    response_model=LabOrderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.LAB_ORDER_CREATE.value))],
)
async def order_lab_test(
    data: LabOrderCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabOrderResponse:
    """Doctor orders laboratory tests for a patient."""
    order = await lab_service.create_order(db, data, ordered_by=current_user["user_id"])

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.CREATE,
        entity_type="LabOrder",
        entity_id=str(order.id),
        new_value={"test_id": order.test_id, "priority": order.priority},
    )
    return LabOrderResponse.model_validate(order)


@router.put(
    "/orders/{order_id}/collect",
    response_model=LabOrderResponse,
    dependencies=[Depends(require_permissions(Permission.LAB_RESULT_CREATE.value))],
)
async def collect_sample(
    order_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LabOrderResponse:
    """Phlebotomist logs specimen collection and generates barcoded Sample ID."""
    order = await lab_service.collect_sample(db, order_id, collector_id=current_user["user_id"])
    return LabOrderResponse.model_validate(order)


@router.post(
    "/results",
    response_model=List[LabResultResponse],
    dependencies=[Depends(require_permissions(Permission.LAB_RESULT_CREATE.value))],
)
async def enter_lab_results(
    data: LabResultCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[LabResultResponse]:
    """Technician enters specimen assay values, with automatic abnormal range flagging."""
    results = await lab_service.enter_results(db, data, performed_by=current_user["user_id"])

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.CREATE,
        entity_type="LabResult",
        entity_id=data.order_id,
        new_value={"param_count": len(results)},
    )
    return [LabResultResponse.model_validate(r) for r in results]


@router.put(
    "/orders/{order_id}/verify",
    response_model=List[LabResultResponse],
    dependencies=[Depends(require_permissions(Permission.LAB_RESULT_VERIFY.value))],
)
async def verify_lab_results(
    order_id: str,
    body: LabResultVerify,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[LabResultResponse]:
    """Pathologist verifies and signs lab results for reporting."""
    results = await lab_service.verify_results(
        db, order_id, verifier_id=current_user["user_id"], remarks=body.remarks
    )
    return [LabResultResponse.model_validate(r) for r in results]


@router.get(
    "/orders/{order_id}/report",
    dependencies=[Depends(require_permissions(Permission.LAB_ORDER_READ.value))],
)
async def get_lab_report(
    order_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Generate printable diagnostic laboratory report."""
    data = await lab_service.get_order_with_results(db, order_id)
    return {
        "order": LabOrderResponse.model_validate(data["order"]),
        "results": [LabResultResponse.model_validate(r) for r in data["results"]],
    }

