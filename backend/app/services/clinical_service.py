"""Clinical service: notes, prescriptions, vitals, patient history."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.clinical import ClinicalNote, Prescription, PrescriptionItem, PrescriptionStatus
from app.schemas.clinical import ClinicalNoteCreate, ClinicalNoteUpdate, PrescriptionCreate


class ClinicalService:
    """Business logic for EMR: clinical notes, prescriptions, vitals."""

    async def create_clinical_note(
        self, db: AsyncSession, data: ClinicalNoteCreate, author_id: str
    ) -> ClinicalNote:
        # Calculate BMI if weight and height provided
        vitals_dict = None
        if data.vitals:
            vitals_dict = data.vitals.model_dump(exclude_none=True)
            if data.vitals.weight and data.vitals.height:
                height_m = data.vitals.height / 100.0
                vitals_dict["bmi"] = round(data.vitals.weight / (height_m * height_m), 1)

        note = ClinicalNote(
            encounter_id=data.encounter_id,
            author_id=author_id,
            note_type=data.note_type,
            subjective=data.subjective,
            objective=data.objective,
            assessment=data.assessment,
            plan=data.plan,
            vitals=vitals_dict,
            icd_codes=data.icd_codes,
        )
        db.add(note)
        await db.flush()
        await db.refresh(note)
        return note

    async def get_notes_for_encounter(
        self, db: AsyncSession, encounter_id: str
    ) -> list:
        result = await db.execute(
            select(ClinicalNote)
            .where(
                ClinicalNote.encounter_id == encounter_id,
                ClinicalNote.is_deleted == False,  # noqa: E712
            )
            .order_by(ClinicalNote.created_at.desc())
        )
        return list(result.scalars().all())

    async def amend_note(
        self, db: AsyncSession, note_id: str, data: ClinicalNoteUpdate, author_id: str
    ) -> ClinicalNote:
        """Create an amendment linked to the original note (immutable history)."""
        original = await db.execute(
            select(ClinicalNote).where(ClinicalNote.id == note_id)
        )
        original_note = original.scalar_one_or_none()
        if original_note is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

        vitals_dict = None
        if data.vitals:
            vitals_dict = data.vitals.model_dump(exclude_none=True)

        amendment = ClinicalNote(
            encounter_id=original_note.encounter_id,
            author_id=author_id,
            note_type=original_note.note_type,
            subjective=data.subjective or original_note.subjective,
            objective=data.objective or original_note.objective,
            assessment=data.assessment or original_note.assessment,
            plan=data.plan or original_note.plan,
            vitals=vitals_dict or original_note.vitals,
            icd_codes=data.icd_codes or original_note.icd_codes,
            is_amendment=True,
            amended_from_id=note_id,
        )
        db.add(amendment)
        await db.flush()
        await db.refresh(amendment)
        return amendment

    async def create_prescription(
        self, db: AsyncSession, data: PrescriptionCreate, doctor_id: str
    ) -> Prescription:
        prescription = Prescription(
            encounter_id=data.encounter_id,
            doctor_id=doctor_id,
            status=PrescriptionStatus.DRAFT,
            notes=data.notes,
        )
        db.add(prescription)
        await db.flush()

        for item_data in data.items:
            item = PrescriptionItem(
                prescription_id=prescription.id,
                drug_id=item_data.drug_id,
                drug_name=item_data.drug_name,
                dosage=item_data.dosage,
                frequency=item_data.frequency,
                route=item_data.route,
                duration_days=item_data.duration_days,
                quantity=item_data.quantity,
                instructions=item_data.instructions,
                is_substitutable=item_data.is_substitutable,
            )
            db.add(item)

        await db.flush()
        await db.refresh(prescription)
        return prescription

    async def get_prescriptions_for_encounter(
        self, db: AsyncSession, encounter_id: str
    ) -> list:
        result = await db.execute(
            select(Prescription)
            .options(selectinload(Prescription.items))
            .where(
                Prescription.encounter_id == encounter_id,
                Prescription.is_deleted == False,  # noqa: E712
            )
            .order_by(Prescription.created_at.desc())
        )
        return list(result.scalars().all())

    async def sign_prescription(
        self, db: AsyncSession, prescription_id: str, doctor_id: str
    ) -> Prescription:
        result = await db.execute(
            select(Prescription).where(Prescription.id == prescription_id)
        )
        prescription = result.scalar_one_or_none()
        if prescription is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
        if prescription.doctor_id != doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the prescribing doctor can sign",
            )
        if prescription.status != PrescriptionStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only draft prescriptions can be signed",
            )
        prescription.status = PrescriptionStatus.SIGNED
        await db.flush()
        return prescription

    async def get_patient_history(self, db: AsyncSession, patient_id: str) -> dict:
        """Get complete medical timeline for a patient."""
        from app.models.encounter import Encounter

        # Get all encounters
        enc_result = await db.execute(
            select(Encounter)
            .where(Encounter.patient_id == patient_id, Encounter.is_deleted == False)  # noqa: E712
            .order_by(Encounter.created_at.desc())
        )
        encounters = list(enc_result.scalars().all())

        encounter_ids = [e.id for e in encounters]

        # Get all clinical notes
        notes_result = await db.execute(
            select(ClinicalNote)
            .where(ClinicalNote.encounter_id.in_(encounter_ids))
            .order_by(ClinicalNote.created_at.desc())
        )
        notes = list(notes_result.scalars().all())

        # Get all prescriptions
        rx_result = await db.execute(
            select(Prescription)
            .options(selectinload(Prescription.items))
            .where(Prescription.encounter_id.in_(encounter_ids))
            .order_by(Prescription.created_at.desc())
        )
        prescriptions = list(rx_result.scalars().all())

        return {
            "encounters": encounters,
            "clinical_notes": notes,
            "prescriptions": prescriptions,
        }


clinical_service = ClinicalService()

