"""Ward, Bed and IPD Admission service."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.encounter import Encounter, EncounterStatus
from app.models.ward import Admission, AdmissionStatus, Bed, BedStatus, DischargeType, Ward
from app.schemas.ward import AdmissionCreate, DischargeCreate, WardCreate


class WardService:
    """Business logic for ward bed allocation, IPD admissions, and discharges."""

    async def create_ward(self, db: AsyncSession, data: WardCreate) -> Ward:
        ward = Ward(
            name=data.name,
            ward_type=data.ward_type,
            floor=data.floor,
            total_beds=data.total_beds,
            department=data.department,
        )
        db.add(ward)
        await db.flush()

        # Automatically create initial available beds
        for i in range(1, data.total_beds + 1):
            bed = Bed(
                ward_id=ward.id,
                bed_number=f"{data.name[:3].upper()}-{data.floor}{i:02d}",
                status=BedStatus.AVAILABLE,
            )
            db.add(bed)

        await db.flush()
        await db.refresh(ward)
        return ward

    async def list_wards(self, db: AsyncSession) -> List[Ward]:
        result = await db.execute(
            select(Ward).options(selectinload(Ward.beds)).where(Ward.is_deleted == False)  # noqa: E712
        )
        return list(result.scalars().all())

    async def update_bed_status(self, db: AsyncSession, bed_id: str, new_status: str) -> Bed:
        result = await db.execute(select(Bed).where(Bed.id == bed_id))
        bed = result.scalar_one_or_none()
        if bed is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
        bed.status = BedStatus(new_status)
        await db.flush()
        await db.refresh(bed)
        return bed

    async def admit_patient(
        self, db: AsyncSession, data: AdmissionCreate, admitted_by: str
    ) -> Admission:
        # Check bed availability
        bed_res = await db.execute(select(Bed).where(Bed.id == data.bed_id))
        bed = bed_res.scalar_one_or_none()
        if bed is None or bed.status != BedStatus.AVAILABLE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected bed is not available")

        # Create admission
        admission = Admission(
            encounter_id=data.encounter_id,
            patient_id=data.patient_id,
            bed_id=data.bed_id,
            admitted_by=admitted_by,
            admission_date=datetime.now(timezone.utc),
            expected_discharge=data.expected_discharge,
            status=AdmissionStatus.ADMITTED,
        )
        db.add(admission)

        # Update bed status to OCCUPIED
        bed.status = BedStatus.OCCUPIED

        # Update encounter status to ADMITTED
        enc_res = await db.execute(select(Encounter).where(Encounter.id == data.encounter_id))
        encounter = enc_res.scalar_one_or_none()
        if encounter:
            encounter.status = EncounterStatus.ADMITTED

        await db.flush()
        await db.refresh(admission)
        return admission

    async def transfer_bed(
        self, db: AsyncSession, admission_id: str, new_bed_id: str
    ) -> Admission:
        result = await db.execute(select(Admission).where(Admission.id == admission_id))
        admission = result.scalar_one_or_none()
        if admission is None or admission.status != AdmissionStatus.ADMITTED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active admission not found")

        new_bed_res = await db.execute(select(Bed).where(Bed.id == new_bed_id))
        new_bed = new_bed_res.scalar_one_or_none()
        if new_bed is None or new_bed.status != BedStatus.AVAILABLE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target bed is not available")

        # Free old bed
        old_bed_res = await db.execute(select(Bed).where(Bed.id == admission.bed_id))
        old_bed = old_bed_res.scalar_one_or_none()
        if old_bed:
            old_bed.status = BedStatus.AVAILABLE

        # Occupy new bed
        new_bed.status = BedStatus.OCCUPIED
        admission.bed_id = new_bed_id
        await db.flush()
        return admission

    async def discharge_patient(
        self, db: AsyncSession, admission_id: str, data: DischargeCreate
    ) -> Admission:
        result = await db.execute(select(Admission).where(Admission.id == admission_id))
        admission = result.scalar_one_or_none()
        if admission is None or admission.status != AdmissionStatus.ADMITTED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active admission not found")

        admission.status = AdmissionStatus.DISCHARGED
        admission.actual_discharge = datetime.now(timezone.utc)
        admission.discharge_type = DischargeType(data.discharge_type)

        # Free bed
        bed_res = await db.execute(select(Bed).where(Bed.id == admission.bed_id))
        bed = bed_res.scalar_one_or_none()
        if bed:
            bed.status = BedStatus.AVAILABLE

        # Update encounter
        enc_res = await db.execute(select(Encounter).where(Encounter.id == admission.encounter_id))
        encounter = enc_res.scalar_one_or_none()
        if encounter:
            encounter.status = EncounterStatus.DISCHARGED
            encounter.end_time = datetime.now(timezone.utc)

        await db.flush()
        return admission

    async def get_bed_occupancy(self, db: AsyncSession) -> dict:
        total_beds_res = await db.execute(select(func.count(Bed.id)))
        total_beds = total_beds_res.scalar() or 0

        occupied_res = await db.execute(select(func.count(Bed.id)).where(Bed.status == BedStatus.OCCUPIED))
        occupied = occupied_res.scalar() or 0

        available_res = await db.execute(select(func.count(Bed.id)).where(Bed.status == BedStatus.AVAILABLE))
        available = available_res.scalar() or 0

        maintenance_res = await db.execute(select(func.count(Bed.id)).where(Bed.status == BedStatus.MAINTENANCE))
        maintenance = maintenance_res.scalar() or 0

        reserved_res = await db.execute(select(func.count(Bed.id)).where(Bed.status == BedStatus.RESERVED))
        reserved = reserved_res.scalar() or 0

        rate = (occupied / total_beds * 100.0) if total_beds > 0 else 0.0

        # By ward
        wards_res = await db.execute(select(Ward).options(selectinload(Ward.beds)))
        wards = wards_res.scalars().all()

        by_ward_type = []
        for w in wards:
            w_total = len(w.beds)
            w_occ = sum(1 for b in w.beds if b.status == BedStatus.OCCUPIED)
            by_ward_type.append({
                "ward_name": w.name,
                "ward_type": w.ward_type.value if hasattr(w.ward_type, "value") else str(w.ward_type),
                "total": w_total,
                "occupied": w_occ,
                "available": w_total - w_occ,
            })

        return {
            "total_beds": total_beds,
            "occupied": occupied,
            "available": available,
            "maintenance": maintenance,
            "reserved": reserved,
            "occupancy_rate": round(rate, 2),
            "by_ward_type": by_ward_type,
        }


ward_service = WardService()

