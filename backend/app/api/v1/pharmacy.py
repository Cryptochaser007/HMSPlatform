"""Pharmacy, Drug Inventory, and Dispensing endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditAction, get_audit_logger
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.core.rbac import Permission
from app.core.security import get_current_user, require_permissions
from app.schemas.clinical import PrescriptionResponse
from app.schemas.pharmacy import (
    DispensingCreate,
    DispensingResponse,
    DrugCreate,
    DrugInventoryCreate,
    DrugInventoryResponse,
    DrugResponse,
    DrugUpdate,
    StockAlertResponse,
)
from app.services.pharmacy_service import pharmacy_service

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy & Inventory"])


@router.post(
    "/drugs",
    response_model=DrugResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.PHARMACY_MANAGE.value))],
)
async def add_drug(
    data: DrugCreate,
    db: AsyncSession = Depends(get_db),
) -> DrugResponse:
    """Add a new drug to the hospital master formulary."""
    drug = await pharmacy_service.create_drug(db, data)
    return DrugResponse.model_validate(drug)


@router.get(
    "/drugs",
    dependencies=[Depends(require_permissions(Permission.DRUG_INVENTORY_READ.value))],
)
async def search_drugs(
    name: Optional[str] = Query(None),
    generic_name: Optional[str] = Query(None),
    drug_type: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Search medications by brand name, generic name, or dosage form."""
    res = await pharmacy_service.search_drugs(
        db,
        name=name,
        generic_name=generic_name,
        drug_type=drug_type,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return {
        "items": [DrugResponse.model_validate(d) for d in res["items"]],
        "total": res["total"],
        "page": res["page"],
        "page_size": res["page_size"],
    }


@router.post(
    "/inventory",
    response_model=DrugInventoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.DRUG_INVENTORY_MANAGE.value))],
)
async def add_inventory_batch(
    data: DrugInventoryCreate,
    db: AsyncSession = Depends(get_db),
) -> DrugInventoryResponse:
    """Receive and record a new drug inventory batch with expiry and pricing."""
    inv = await pharmacy_service.add_inventory(db, data)
    return DrugInventoryResponse.model_validate(inv)


@router.post(
    "/dispense",
    response_model=DispensingResponse,
    dependencies=[Depends(require_permissions(Permission.PRESCRIPTION_DISPENSE.value))],
)
async def dispense_medication(
    data: DispensingCreate,
    patient_id: str = Query(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DispensingResponse:
    """Dispense medication against prescription, deducting inventory."""
    dispensing = await pharmacy_service.dispense_medication(
        db, data, patient_id=patient_id, user_id=current_user["user_id"]
    )

    logger = await get_audit_logger()
    await logger.log(
        db,
        user_id=current_user["user_id"],
        action=AuditAction.CREATE,
        entity_type="Dispensing",
        entity_id=str(dispensing.id),
        new_value={"qty": dispensing.quantity_dispensed, "batch_id": str(dispensing.drug_inventory_id)},
    )
    return DispensingResponse.model_validate(dispensing)


@router.get(
    "/pending",
    response_model=List[PrescriptionResponse],
    dependencies=[Depends(require_permissions(Permission.PRESCRIPTION_READ.value))],
)
async def get_pending_prescriptions(
    db: AsyncSession = Depends(get_db),
) -> List[PrescriptionResponse]:
    """List signed prescriptions waiting for pharmacy fulfillment."""
    prescriptions = await pharmacy_service.get_pending_prescriptions(db)
    return [PrescriptionResponse.model_validate(p) for p in prescriptions]


@router.get(
    "/alerts/stock",
    response_model=List[StockAlertResponse],
    dependencies=[Depends(require_permissions(Permission.DRUG_INVENTORY_READ.value))],
)
async def get_stock_alerts(
    db: AsyncSession = Depends(get_db),
) -> List[StockAlertResponse]:
    """Alerts for medications that have fallen below their reorder threshold."""
    alerts = await pharmacy_service.get_stock_alerts(db)
    return [StockAlertResponse(**a) for a in alerts]


@router.get(
    "/alerts/expiry",
    dependencies=[Depends(require_permissions(Permission.DRUG_INVENTORY_READ.value))],
)
async def get_expiry_alerts(
    days: int = Query(90, description="Days to expiry"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Alerts for drug batches expiring within the specified window (default 90 days)."""
    return await pharmacy_service.get_expiry_alerts(db, days=days)

