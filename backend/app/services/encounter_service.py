"""Encounter service: OPD/IPD workflow, queue, appointments."""

from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.encounter import Encounter, EncounterStatus, EncounterType
from app.models.user import User
from app.schemas.encounter import EncounterCreate, EncounterUpdate


class EncounterService:
    """Business logic for OPD/IPD encounters, queue, and appointments."""

    async def create_encounter(self, db: AsyncSession, data: EncounterCreate) -> Encounter:
        # Assign token number for OPD walk-ins
        token_number = None
        if data.encounter_type == "OPD":
            token_number = await self._get_next_token(db, data.department)

        initial_status = EncounterStatus.SCHEDULED
        if data.appointment_time is None:
            initial_status = EncounterStatus.CHECKED_IN  # Walk-in

        encounter = Encounter(
            patient_id=data.patient_id,
            doctor_id=data.doctor_id,
            encounter_type=data.encounter_type,
            status=initial_status,
            token_number=token_number,
            appointment_time=data.appointment_time,
            check_in_time=datetime.now(timezone.utc) if initial_status == EncounterStatus.CHECKED_IN else None,
            department=data.department,
            chief_complaint=data.chief_complaint,
            priority=data.priority,
        )
        db.add(encounter)
        await db.flush()
        await db.refresh(encounter)
        return encounter

    async def get_encounter(self, db: AsyncSession, encounter_id: str) -> Encounter:
        result = await db.execute(
            select(Encounter).where(Encounter.id == encounter_id, Encounter.is_deleted == False)  # noqa: E712
        )
        encounter = result.scalar_one_or_none()
        if encounter is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")
        return encounter

    async def list_encounters(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        department: Optional[str] = None,
        doctor_id: Optional[str] = None,
        encounter_type: Optional[str] = None,
        status_filter: Optional[str] = None,
        date_filter: Optional[date] = None,
    ) -> dict:
        query = select(Encounter).where(Encounter.is_deleted == False)  # noqa: E712

        if department:
            query = query.where(Encounter.department == department)
        if doctor_id:
            query = query.where(Encounter.doctor_id == doctor_id)
        if encounter_type:
            query = query.where(Encounter.encounter_type == encounter_type)
        if status_filter:
            query = query.where(Encounter.status == status_filter)
        if date_filter:
            query = query.where(func.date(Encounter.created_at) == date_filter)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        query = query.order_by(Encounter.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        items = result.scalars().all()

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def check_in(self, db: AsyncSession, encounter_id: str) -> Encounter:
        encounter = await self.get_encounter(db, encounter_id)
        if encounter.status not in (EncounterStatus.SCHEDULED,):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot check in from status {encounter.status}",
            )
        encounter.status = EncounterStatus.CHECKED_IN
        encounter.check_in_time = datetime.now(timezone.utc)
        if encounter.token_number is None:
            encounter.token_number = await self._get_next_token(db, encounter.department)
        await db.flush()
        return encounter

    async def start_consultation(self, db: AsyncSession, encounter_id: str, doctor_id: str) -> Encounter:
        encounter = await self.get_encounter(db, encounter_id)
        if encounter.status != EncounterStatus.CHECKED_IN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Patient must be checked in first",
            )
        encounter.status = EncounterStatus.IN_PROGRESS
        encounter.start_time = datetime.now(timezone.utc)
        await db.flush()
        return encounter

    async def complete_encounter(self, db: AsyncSession, encounter_id: str) -> Encounter:
        encounter = await self.get_encounter(db, encounter_id)
        if encounter.status != EncounterStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Encounter must be in progress to complete",
            )
        encounter.status = EncounterStatus.COMPLETED
        encounter.end_time = datetime.now(timezone.utc)
        await db.flush()
        return encounter

    async def update_encounter(
        self, db: AsyncSession, encounter_id: str, data: EncounterUpdate
    ) -> Encounter:
        encounter = await self.get_encounter(db, encounter_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(encounter, field, value)
        encounter.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(encounter)
        return encounter

    async def get_queue(self, db: AsyncSession, department: str) -> list:
        """Get OPD queue for a department, ordered by priority and token."""
        today = date.today()
        result = await db.execute(
            select(Encounter)
            .where(
                Encounter.department == department,
                Encounter.encounter_type == EncounterType.OPD,
                Encounter.status.in_([EncounterStatus.CHECKED_IN, EncounterStatus.IN_PROGRESS]),
                func.date(Encounter.created_at) == today,
                Encounter.is_deleted == False,  # noqa: E712
            )
            .order_by(
                Encounter.priority.desc(),
                Encounter.token_number.asc(),
            )
        )
        encounters = result.scalars().all()

        queue = []
        for idx, enc in enumerate(encounters):
            queue.append({
                "token_number": enc.token_number,
                "patient_id": enc.patient_id,
                "patient_name": "—",  # Filled by API layer after decryption
                "doctor_name": "—",
                "department": enc.department,
                "status": enc.status.value if hasattr(enc.status, "value") else enc.status,
                "check_in_time": enc.check_in_time,
                "estimated_wait_minutes": idx * 15,  # Simple estimate: 15 min per patient
            })
        return queue

    async def get_appointment_slots(
        self, db: AsyncSession, doctor_id: str, target_date: date
    ) -> dict:
        """Get available 30-minute slots for a doctor on a given date."""
        # Fetch existing appointments for the doctor on that date
        result = await db.execute(
            select(Encounter.appointment_time)
            .where(
                Encounter.doctor_id == doctor_id,
                func.date(Encounter.appointment_time) == target_date,
                Encounter.status != EncounterStatus.CANCELLED,
                Encounter.is_deleted == False,  # noqa: E712
            )
        )
        booked_times = {row[0].strftime("%H:%M") for row in result.all() if row[0]}

        # Generate slots from 09:00 to 17:00 in 30-min intervals
        all_slots = []
        current = time(9, 0)
        end = time(17, 0)
        while current < end:
            slot_str = current.strftime("%H:%M")
            if slot_str not in booked_times:
                all_slots.append(slot_str)
            # Add 30 minutes
            dt = datetime.combine(target_date, current) + timedelta(minutes=30)
            current = dt.time()

        # Get doctor name
        doc_result = await db.execute(select(User).where(User.id == doctor_id))
        doctor = doc_result.scalar_one_or_none()
        doctor_name = doctor.full_name if doctor else "Unknown"

        return {
            "doctor_id": doctor_id,
            "doctor_name": doctor_name,
            "date": target_date,
            "available_slots": all_slots,
        }

    async def _get_next_token(self, db: AsyncSession, department: str) -> int:
        """Get next sequential token number for the department today."""
        today = date.today()
        result = await db.execute(
            select(func.max(Encounter.token_number))
            .where(
                Encounter.department == department,
                func.date(Encounter.created_at) == today,
            )
        )
        max_token = result.scalar() or 0
        return max_token + 1


encounter_service = EncounterService()

