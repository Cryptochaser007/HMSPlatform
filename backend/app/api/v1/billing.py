"""Billing, Invoicing, and Payment Collection endpoints."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, get_audit_logger
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.core.rbac import Permission
from app.core.security import get_current_user, require_permissions
from app.schemas.billing import (
    BillCreate,
    BillResponse,
    BillSummary,
    PaymentCreate,
    PaymentResponse,
)
from app.services.billing_service import billing_service

router = APIRouter(prefix="/billing", tags=["Billing & Payments"])


@router.post(
    "/bills",
    response_model=BillResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.BILLING_CREATE.value))],
)
async def generate_bill(
    data: BillCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BillResponse:
    """Generate itemized patient invoice (OPD consultation, procedures, bed charges)."""
    bill = await billing_service.create_bill(
        db, data, created_by=current_user["user_id"]
    )

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.CREATE,
        entity_type="Bill",
        entity_id=str(bill.id),
        new_value={"bill_number": bill.bill_number, "total": float(bill.total_amount)},
    )
    return BillResponse.model_validate(bill)


@router.get(
    "/bills",
    dependencies=[Depends(require_permissions(Permission.BILLING_READ.value))],
)
async def list_bills(
    patient_id: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Search and paginate billing records."""
    res = await billing_service.list_bills(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        patient_id=patient_id,
        payment_status=payment_status,
    )
    return {
        "items": [BillResponse.model_validate(b) for b in res["items"]],
        "total": res["total"],
        "page": res["page"],
        "page_size": res["page_size"],
    }


@router.get(
    "/bills/{bill_id}",
    response_model=BillResponse,
    dependencies=[Depends(require_permissions(Permission.BILLING_READ.value))],
)
async def get_bill_details(
    bill_id: str,
    db: AsyncSession = Depends(get_db),
) -> BillResponse:
    """Get full bill details with itemized charges and payments."""
    bill = await billing_service.get_bill(db, bill_id)
    return BillResponse.model_validate(bill)


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.PAYMENT_RECEIVE.value))],
)
async def record_payment(
    data: PaymentCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """Record payment received (Cash, Card, UPI, Insurance) and issue money receipt."""
    payment = await billing_service.record_payment(
        db, data, received_by=current_user["user_id"]
    )

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.CREATE,
        entity_type="Payment",
        entity_id=str(payment.id),
        new_value={"receipt": payment.receipt_number, "amount": float(payment.amount)},
    )
    return PaymentResponse.model_validate(payment)


@router.post(
    "/bills/{bill_id}/cancel",
    response_model=BillResponse,
    dependencies=[Depends(require_permissions(Permission.BILLING_UPDATE.value))],
)
async def cancel_bill(
    bill_id: str,
    db: AsyncSession = Depends(get_db),
) -> BillResponse:
    """Cancel unpaid bill with audit record."""
    bill = await billing_service.cancel_bill(db, bill_id)
    return BillResponse.model_validate(bill)


@router.get(
    "/summary",
    response_model=BillSummary,
    dependencies=[Depends(require_permissions(Permission.BILLING_READ.value))],
)
async def get_financial_summary(
    period: str = Query("today", description="today / monthly"),
    db: AsyncSession = Depends(get_db),
) -> BillSummary:
    """Hospital revenue collections and outstanding receivables dashboard."""
    summary = await billing_service.get_billing_summary(db, period=period)
    return BillSummary(**summary)

