"""Ward, Bed and IPD Admission service."""

from collections import Counter
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.encounter import Encounter, EncounterStatus
from app.models.tenant import Hospital
from app.models.ward import Admission, AdmissionStatus, Bed, BedStatus, DischargeType, Ward
from app.schemas.ward import (
    AdmissionCreate,
    DischargeCreate,
    WardCreate,
    WardSetupRequest,
    WardSetupStatus,
)


class WardService:
    """Business logic for ward bed allocation, IPD admissions, and discharges."""

    async def lock_hospital(self, db: AsyncSession, hospital_id: str) -> Hospital:
        result = await db.execute(
            select(Hospital).where(Hospital.id == hospital_id)
            .with_for_update().execution_options(populate_existing=True)
        )
        return result.scalar_one()

    async def get_setup_status(self, db: AsyncSession, hospital_id: str) -> WardSetupStatus:
        configured = await db.scalar(select(exists().where(
            Ward.hospital_id == hospital_id, Ward.is_active.is_(True), Ward.is_deleted.is_(False),
        )))
        if configured:
            return WardSetupStatus(status="configured")
        skipped = await db.scalar(select(Hospital.ward_setup_skipped).where(Hospital.id == hospital_id))
        return WardSetupStatus(status="skipped" if skipped else "pending")

    async def save_setup(
        self, db: AsyncSession, hospital_id: str, data: WardSetupRequest,
    ) -> tuple[WardSetupStatus, bool]:
        hospital = await self.lock_hospital(db, hospital_id)
        existing = (await db.scalars(select(Ward).where(
            Ward.hospital_id == hospital_id, Ward.is_active.is_(True), Ward.is_deleted.is_(False),
        ))).all()
        if existing:
            existing_layout = {
                (ward.name.casefold(), ward.ward_type, ward.floor, ward.total_beds, ward.department)
                for ward in existing
            }
            requested_layout = {
                (ward.name.casefold(), ward.ward_type, ward.floor, ward.total_beds, ward.department)
                for ward in data.wards
            }
            if len(existing) == len(data.wards) and existing_layout == requested_layout:
                return WardSetupStatus(status="configured"), False
            raise HTTPException(status_code=409, detail="Wards are already configured for this hospital.")

        if data.mode == "OPD_ONLY":
            changed = not hospital.ward_setup_skipped
            hospital.ward_setup_skipped = True
            return WardSetupStatus(status="skipped"), changed

        for ward in data.wards:
            await self.create_ward(db, ward)
        hospital.ward_setup_skipped = False
        return WardSetupStatus(status="configured"), True

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

    async def list_wards(self, db: AsyncSession) -> list[Ward]:
        result = await db.execute(
            select(Ward).options(selectinload(Ward.beds)).where(Ward.is_deleted == False)
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
            admission_date=datetime.now(UTC),
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
        admission.actual_discharge = datetime.now(UTC)
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
            encounter.end_time = datetime.now(UTC)

        await db.flush()
        return admission

    async def get_bed_occupancy(self, db: AsyncSession, hospital_id: str) -> dict:
        result = await db.execute(
            select(Ward)
            .where(Ward.hospital_id == hospital_id, Ward.is_active.is_(True), Ward.is_deleted.is_(False))
            .options(
                selectinload(Ward.beds.and_(Bed.hospital_id == hospital_id, Bed.is_deleted.is_(False)))
            )
            .order_by(Ward.floor, Ward.name, Ward.id)
        )
        totals: Counter[BedStatus] = Counter()
        by_ward_type = []
        inventory = []
        for ward in result.scalars():
            beds = sorted(ward.beds, key=lambda bed: (bed.bed_number, bed.id))
            counts = Counter(bed.status for bed in beds)
            totals.update(counts)
            by_ward_type.append({
                "ward_name": ward.name,
                "ward_type": ward.ward_type,
                "total": len(beds),
                "occupied": counts[BedStatus.OCCUPIED],
                "available": counts[BedStatus.AVAILABLE],
            })
            inventory.append({
                "id": ward.id,
                "name": ward.name,
                "ward_type": ward.ward_type,
                "floor": ward.floor,
                "beds": beds,
            })

        total_beds = totals.total()
        occupied = totals[BedStatus.OCCUPIED]
        return {
            "total_beds": total_beds,
            "occupied": occupied,
            "available": totals[BedStatus.AVAILABLE],
            "maintenance": totals[BedStatus.MAINTENANCE],
            "reserved": totals[BedStatus.RESERVED],
            "occupancy_rate": round(occupied / total_beds * 100, 2) if total_beds else 0.0,
            "by_ward_type": by_ward_type,
            "wards": inventory,
        }


ward_service = WardService()

