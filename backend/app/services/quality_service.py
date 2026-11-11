"""Quality, NABH compliance indicators, and clinical incident reporting."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality import (
    IncidentReport,
    IncidentSeverity,
    IncidentStatus,
    IncidentType,
    QualityIndicator,
    QualityMeasurement,
)
from app.schemas.quality import (
    IncidentReportCreate,
    IncidentReportUpdate,
    QualityIndicatorCreate,
    QualityMeasurementCreate,
)
from app.utils.helpers import generate_incident_number


class QualityService:
    """Business logic for NABH quality indicators, measurements, and incident reporting."""

    # ── Quality Indicators ──────────────────────────────────────────────

    async def create_indicator(self, db: AsyncSession, data: QualityIndicatorCreate) -> QualityIndicator:
        indicator = QualityIndicator(**data.model_dump())
        db.add(indicator)
        await db.flush()
        await db.refresh(indicator)
        return indicator

    async def list_indicators(self, db: AsyncSession) -> List[QualityIndicator]:
        result = await db.execute(
            select(QualityIndicator).where(QualityIndicator.is_deleted == False, QualityIndicator.is_active == True)  # noqa: E712
        )
        return list(result.scalars().all())

    async def record_measurement(
        self, db: AsyncSession, data: QualityMeasurementCreate, recorded_by: str
    ) -> QualityMeasurement:
        num = Decimal(str(data.numerator_value))
        den = Decimal(str(data.denominator_value))
        calculated = (num / den) * Decimal("100.00") if den > Decimal("0") else Decimal("0.00")

        measurement = QualityMeasurement(
            indicator_id=data.indicator_id,
            period_start=data.period_start,
            period_end=data.period_end,
            numerator_value=num,
            denominator_value=den,
            calculated_value=round(calculated, 2),
            recorded_by=recorded_by,
            notes=data.notes,
        )
        db.add(measurement)
        await db.flush()
        await db.refresh(measurement)
        return measurement

    async def get_nabh_dashboard(self, db: AsyncSession) -> dict:
        indicators = await self.list_indicators(db)

        indicator_summaries = []
        compliant_count = 0

        for ind in indicators:
            latest_meas_res = await db.execute(
                select(QualityMeasurement)
                .where(QualityMeasurement.indicator_id == ind.id)
                .order_by(QualityMeasurement.period_end.desc())
                .limit(1)
            )
            latest_meas = latest_meas_res.scalar_one_or_none()
            current_val = latest_meas.calculated_value if latest_meas else Decimal("0.00")
            target = Decimal(str(ind.target_value))

            is_compliant = current_val <= target
            if is_compliant:
                compliant_count += 1

            indicator_summaries.append({
                "id": str(ind.id),
                "name": ind.name,
                "code": ind.code,
                "category": ind.category,
                "target_value": float(target),
                "current_value": float(current_val),
                "unit": ind.unit,
                "is_compliant": is_compliant,
                "is_nabh_mandatory": ind.is_nabh_mandatory,
            })

        total = len(indicators)
        compliance_rate = (compliant_count / total * 100.0) if total > 0 else 100.0

        return {
            "total_indicators": total,
            "compliant": compliant_count,
            "non_compliant": total - compliant_count,
            "compliance_rate": round(compliance_rate, 2),
            "indicators": indicator_summaries,
        }

    # ── Incident Reporting ──────────────────────────────────────────────

    async def create_incident(
        self, db: AsyncSession, data: IncidentReportCreate, reported_by: str
    ) -> IncidentReport:
        inc_number = generate_incident_number()
        incident = IncidentReport(
            incident_number=inc_number,
            incident_type=IncidentType(data.incident_type),
            severity=IncidentSeverity(data.severity),
            title=data.title,
            description=data.description,
            location=data.location,
            incident_date=data.incident_date,
            reported_by=reported_by,
            patient_id=data.patient_id,
            status=IncidentStatus.REPORTED,
        )
        db.add(incident)
        await db.flush()
        await db.refresh(incident)
        return incident

    async def list_incidents(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
    ) -> dict:
        query = select(IncidentReport).where(IncidentReport.is_deleted == False)  # noqa: E712
        if status_filter:
            query = query.where(IncidentReport.status == status_filter)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        query = query.order_by(IncidentReport.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list((await db.execute(query)).scalars().all())
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def update_incident(
        self, db: AsyncSession, incident_id: str, data: IncidentReportUpdate, user_id: str
    ) -> IncidentReport:
        result = await db.execute(select(IncidentReport).where(IncidentReport.id == incident_id))
        incident = result.scalar_one_or_none()
        if incident is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident report not found")

        if data.root_cause:
            incident.root_cause = data.root_cause
        if data.corrective_action:
            incident.corrective_action = data.corrective_action
        if data.status:
            incident.status = IncidentStatus(data.status)
            if data.status == IncidentStatus.CLOSED:
                incident.closed_by = user_id
                incident.closed_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(incident)
        return incident


quality_service = QualityService()

