"""Radiology service: orders, PACS integration, and diagnostic reports."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.radiology import RadiologyOrder, RadiologyOrderStatus, RadiologyReport
from app.schemas.radiology import RadiologyOrderCreate, RadiologyOrderUpdate, RadiologyReportCreate
from app.utils.helpers import generate_accession_number


class RadiologyService:
    """Business logic for radiology orders, reports, and PACS viewer linkage."""

    async def create_order(
        self, db: AsyncSession, data: RadiologyOrderCreate, ordered_by: str
    ) -> RadiologyOrder:
        accession_no = generate_accession_number()
        order = RadiologyOrder(
            encounter_id=data.encounter_id,
            patient_id=data.patient_id,
            ordered_by=ordered_by,
            modality=data.modality,
            body_part=data.body_part,
            study_description=data.study_description,
            status=RadiologyOrderStatus.ORDERED,
            priority=data.priority,
            clinical_indication=data.clinical_indication,
            scheduled_at=data.scheduled_at,
            accession_number=accession_no,
        )
        db.add(order)
        await db.flush()
        await db.refresh(order)
        return order

    async def get_order(self, db: AsyncSession, order_id: str) -> RadiologyOrder:
        result = await db.execute(
            select(RadiologyOrder)
            .options(selectinload(RadiologyOrder.report))
            .where(RadiologyOrder.id == order_id, RadiologyOrder.is_deleted == False)  # noqa: E712
        )
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Radiology order not found")
        return order

    async def list_orders(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        modality: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> dict:
        query = select(RadiologyOrder).where(RadiologyOrder.is_deleted == False)  # noqa: E712
        if modality:
            query = query.where(RadiologyOrder.modality == modality)
        if status_filter:
            query = query.where(RadiologyOrder.status == status_filter)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        query = query.order_by(RadiologyOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list((await db.execute(query)).scalars().all())
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def update_order_status(
        self, db: AsyncSession, order_id: str, data: RadiologyOrderUpdate
    ) -> RadiologyOrder:
        order = await self.get_order(db, order_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(order, field, value)
        order.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(order)
        return order

    async def create_report(
        self, db: AsyncSession, data: RadiologyReportCreate, radiologist_id: str
    ) -> RadiologyReport:
        order = await self.get_order(db, data.order_id)
        if order.report:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Report already exists for this radiology order",
            )
        report = RadiologyReport(
            order_id=data.order_id,
            radiologist_id=radiologist_id,
            findings=data.findings,
            impression=data.impression,
            recommendation=data.recommendation,
            is_critical=data.is_critical,
            reported_at=datetime.now(timezone.utc),
            template_used=data.template_used,
        )
        db.add(report)
        order.status = RadiologyOrderStatus.REPORTED
        await db.flush()
        await db.refresh(report)
        return report

    async def verify_report(
        self, db: AsyncSession, report_id: str, verifier_id: str
    ) -> RadiologyReport:
        result = await db.execute(select(RadiologyReport).where(RadiologyReport.id == report_id))
        report = result.scalar_one_or_none()
        if report is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        report.verified_by = verifier_id
        report.verified_at = datetime.now(timezone.utc)

        # Update order status to VERIFIED
        order = await self.get_order(db, report.order_id)
        order.status = RadiologyOrderStatus.VERIFIED
        await db.flush()
        return report

    def get_viewer_url(self, study_id: str) -> dict:
        """Return OHIF PACS web viewer embedded URL for DICOM study."""
        # Standard Orthanc / OHIF Web viewer URL format
        viewer_url = f"http://localhost:8042/ohif/viewer?StudyInstanceUIDs={study_id}"
        return {
            "study_id": study_id,
            "viewer_url": viewer_url,
            "protocol": "DICOMweb",
        }


radiology_service = RadiologyService()

