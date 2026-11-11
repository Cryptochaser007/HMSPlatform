"""Pharmacy service: drug management, inventory, dispensing."""

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pharmacy import Dispensing, Drug, DrugInventory
from app.models.clinical import PrescriptionItem, Prescription, PrescriptionStatus
from app.schemas.pharmacy import DispensingCreate, DrugCreate, DrugInventoryCreate, DrugUpdate


class PharmacyService:
    """Business logic for drug catalog, inventory, and dispensing."""

    # ── Drug catalog ────────────────────────────────────────────────────

    async def create_drug(self, db: AsyncSession, data: DrugCreate) -> Drug:
        drug = Drug(**data.model_dump())
        db.add(drug)
        await db.flush()
        await db.refresh(drug)
        return drug

    async def search_drugs(
        self,
        db: AsyncSession,
        name: Optional[str] = None,
        generic_name: Optional[str] = None,
        drug_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        query = select(Drug).where(Drug.is_deleted == False, Drug.is_active == True)  # noqa: E712
        if name:
            query = query.where(Drug.name.ilike(f"%{name}%"))
        if generic_name:
            query = query.where(Drug.generic_name.ilike(f"%{generic_name}%"))
        if drug_type:
            query = query.where(Drug.drug_type == drug_type)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        query = query.order_by(Drug.name).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        return {"items": list(result.scalars().all()), "total": total, "page": page, "page_size": page_size}

    async def update_drug(self, db: AsyncSession, drug_id: str, data: DrugUpdate) -> Drug:
        result = await db.execute(select(Drug).where(Drug.id == drug_id))
        drug = result.scalar_one_or_none()
        if drug is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drug not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(drug, field, value)
        await db.flush()
        await db.refresh(drug)
        return drug

    # ── Inventory ───────────────────────────────────────────────────────

    async def add_inventory(self, db: AsyncSession, data: DrugInventoryCreate) -> DrugInventory:
        inventory = DrugInventory(**data.model_dump())
        db.add(inventory)
        await db.flush()
        await db.refresh(inventory)
        return inventory

    async def get_stock_alerts(self, db: AsyncSession) -> list:
        """Drugs below reorder level."""
        result = await db.execute(
            select(DrugInventory, Drug)
            .join(Drug, DrugInventory.drug_id == Drug.id)
            .where(
                DrugInventory.quantity_in_stock <= DrugInventory.reorder_level,
                DrugInventory.is_deleted == False,  # noqa: E712
            )
        )
        alerts = []
        for inv, drug in result.all():
            alerts.append({
                "drug_id": drug.id,
                "drug_name": drug.name,
                "batch_number": inv.batch_number,
                "quantity_in_stock": inv.quantity_in_stock,
                "reorder_level": inv.reorder_level,
            })
        return alerts

    async def get_expiry_alerts(self, db: AsyncSession, days: int = 90) -> list:
        """Drugs expiring within N days."""
        threshold = date.today() + timedelta(days=days)
        result = await db.execute(
            select(DrugInventory, Drug)
            .join(Drug, DrugInventory.drug_id == Drug.id)
            .where(
                DrugInventory.expiry_date <= threshold,
                DrugInventory.quantity_in_stock > 0,
                DrugInventory.is_deleted == False,  # noqa: E712
            )
            .order_by(DrugInventory.expiry_date)
        )
        return [
            {
                "drug_id": drug.id,
                "drug_name": drug.name,
                "batch_number": inv.batch_number,
                "expiry_date": inv.expiry_date.isoformat(),
                "quantity_in_stock": inv.quantity_in_stock,
            }
            for inv, drug in result.all()
        ]

    # ── Dispensing ──────────────────────────────────────────────────────

    async def dispense_medication(
        self, db: AsyncSession, data: DispensingCreate, patient_id: str, user_id: str
    ) -> Dispensing:
        # Validate inventory
        inv_result = await db.execute(
            select(DrugInventory).where(DrugInventory.id == data.drug_inventory_id)
        )
        inventory = inv_result.scalar_one_or_none()
        if inventory is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory batch not found")
        if inventory.quantity_in_stock < data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {inventory.quantity_in_stock}",
            )
        if inventory.expiry_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot dispense expired medication",
            )

        # Deduct stock
        inventory.quantity_in_stock -= data.quantity

        dispensing = Dispensing(
            prescription_item_id=data.prescription_item_id,
            drug_inventory_id=data.drug_inventory_id,
            patient_id=patient_id,
            dispensed_by=user_id,
            quantity_dispensed=data.quantity,
            dispensed_at=datetime.now(timezone.utc),
            notes=data.notes,
        )
        db.add(dispensing)
        await db.flush()

        # Update prescription status
        presc_item = await db.execute(
            select(PrescriptionItem).where(PrescriptionItem.id == data.prescription_item_id)
        )
        item = presc_item.scalar_one_or_none()
        if item:
            prescription = await db.execute(
                select(Prescription).where(Prescription.id == item.prescription_id)
            )
            rx = prescription.scalar_one_or_none()
            if rx and rx.status == PrescriptionStatus.SIGNED:
                rx.status = PrescriptionStatus.DISPENSED

        await db.flush()
        await db.refresh(dispensing)
        return dispensing

    async def get_pending_prescriptions(self, db: AsyncSession) -> list:
        """Get signed prescriptions pending dispensing."""
        result = await db.execute(
            select(Prescription)
            .where(
                Prescription.status == PrescriptionStatus.SIGNED,
                Prescription.is_deleted == False,  # noqa: E712
            )
            .order_by(Prescription.created_at.asc())
        )
        return list(result.scalars().all())


pharmacy_service = PharmacyService()

