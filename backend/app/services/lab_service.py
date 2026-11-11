"""Laboratory service: orders, sample collection, results, verification."""

from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.laboratory import LabOrder, LabOrderStatus, LabResult, LabTest, ResultFlag
from app.schemas.laboratory import LabOrderCreate, LabResultCreate
from app.utils.helpers import generate_sample_id


class LabService:
    """Business logic for Lab Information System."""

    async def create_order(
        self, db: AsyncSession, data: LabOrderCreate, ordered_by: str
    ) -> LabOrder:
        # Verify test exists
        test_result = await db.execute(select(LabTest).where(LabTest.id == data.test_id))
        test = test_result.scalar_one_or_none()
        if test is None or not test.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab test not found or inactive")

        order = LabOrder(
            encounter_id=data.encounter_id,
            patient_id=data.patient_id,
            ordered_by=ordered_by,
            test_id=data.test_id,
            status=LabOrderStatus.ORDERED,
            priority=data.priority,
            clinical_notes=data.clinical_notes,
        )
        db.add(order)
        await db.flush()
        await db.refresh(order)
        return order

    async def collect_sample(
        self, db: AsyncSession, order_id: str, collector_id: str
    ) -> LabOrder:
        order = await self._get_order(db, order_id)
        if order.status != LabOrderStatus.ORDERED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot collect sample for order in status {order.status}",
            )
        order.status = LabOrderStatus.SAMPLE_COLLECTED
        order.sample_id = generate_sample_id()
        order.collected_at = datetime.now(timezone.utc)
        order.collected_by = collector_id
        await db.flush()
        return order

    async def enter_results(
        self, db: AsyncSession, data: LabResultCreate, performed_by: str
    ) -> List[LabResult]:
        order = await self._get_order(db, data.order_id)
        if order.status not in (LabOrderStatus.SAMPLE_COLLECTED, LabOrderStatus.IN_PROGRESS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sample must be collected before entering results",
            )

        # Get test reference ranges for abnormal flagging
        test_result = await db.execute(select(LabTest).where(LabTest.id == order.test_id))
        test = test_result.scalar_one_or_none()

        results = []
        for param in data.results:
            # Determine if abnormal
            is_abnormal, flag = self._check_abnormal(param.value, param.reference_range)

            result = LabResult(
                order_id=data.order_id,
                parameter_name=param.parameter_name,
                value=param.value,
                unit=param.unit,
                reference_range=param.reference_range,
                is_abnormal=is_abnormal,
                flag=flag,
                performed_by=performed_by,
            )
            db.add(result)
            results.append(result)

        order.status = LabOrderStatus.COMPLETED
        await db.flush()
        return results

    async def verify_results(
        self, db: AsyncSession, order_id: str, verifier_id: str, remarks: str = None
    ) -> List[LabResult]:
        order = await self._get_order(db, order_id)
        if order.status != LabOrderStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Results must be completed before verification",
            )

        result = await db.execute(
            select(LabResult).where(LabResult.order_id == order_id)
        )
        lab_results = list(result.scalars().all())

        now = datetime.now(timezone.utc)
        for lr in lab_results:
            lr.verified_by = verifier_id
            lr.verified_at = now
            if remarks:
                lr.remarks = remarks

        order.status = LabOrderStatus.VERIFIED
        await db.flush()
        return lab_results

    async def get_order_with_results(self, db: AsyncSession, order_id: str) -> dict:
        order = await self._get_order(db, order_id)
        results_q = await db.execute(
            select(LabResult)
            .where(LabResult.order_id == order_id)
            .order_by(LabResult.created_at)
        )
        results = list(results_q.scalars().all())
        return {"order": order, "results": results}

    async def list_orders(
        self, db: AsyncSession, page: int = 1, page_size: int = 20, status_filter: str = None
    ) -> dict:
        from sqlalchemy import func as sqlfunc

        query = select(LabOrder).where(LabOrder.is_deleted == False)  # noqa: E712
        if status_filter:
            query = query.where(LabOrder.status == status_filter)
        count_q = select(sqlfunc.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar() or 0
        query = query.order_by(LabOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list((await db.execute(query)).scalars().all())
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    # ── Helpers ─────────────────────────────────────────────────────────

    async def _get_order(self, db: AsyncSession, order_id: str) -> LabOrder:
        result = await db.execute(select(LabOrder).where(LabOrder.id == order_id))
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab order not found")
        return order

    @staticmethod
    def _check_abnormal(value: str, reference_range: str = None) -> tuple:
        """Simple numeric check against reference range 'min-max'."""
        if not reference_range:
            return False, None
        try:
            num_val = float(value)
            parts = reference_range.split("-")
            if len(parts) == 2:
                low, high = float(parts[0].strip()), float(parts[1].strip())
                if num_val < low:
                    flag = ResultFlag.CRITICAL if num_val < low * 0.7 else ResultFlag.LOW
                    return True, flag
                if num_val > high:
                    flag = ResultFlag.CRITICAL if num_val > high * 1.3 else ResultFlag.HIGH
                    return True, flag
            return False, ResultFlag.NORMAL
        except (ValueError, TypeError):
            return False, None


lab_service = LabService()

