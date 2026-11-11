"""Patient service: registration, search, DPDP-compliant operations."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt_field, hash_field
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientSearchParams, PatientUpdate
from app.utils.helpers import generate_uhid


class PatientService:
    """Business logic for patient registration and management."""

    async def register_patient(self, db: AsyncSession, data: PatientCreate) -> Patient:
        # Check duplicate ABHA ID
        if data.abha_id:
            result = await db.execute(
                select(Patient).where(Patient.abha_id == data.abha_id, Patient.is_deleted == False)  # noqa: E712
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Patient with this ABHA ID already exists",
                )

        # Generate unique hospital ID
        uhid = generate_uhid()

        # Compute name search hash for encrypted field search
        name_hash = hash_field(f"{data.first_name} {data.last_name}")

        # Hash Aadhaar (never store raw)
        aadhaar_hash = None
        if data.aadhaar_number:
            aadhaar_hash = hash_field(data.aadhaar_number)

        patient = Patient(
            abha_id=data.abha_id,
            first_name=data.first_name,  # EncryptedType handles encryption
            last_name=data.last_name,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            phone=data.phone,
            email=data.email,
            address_line1=data.address_line1,
            address_line2=data.address_line2,
            city=data.city,
            state=data.state,
            pincode=data.pincode,
            blood_group=data.blood_group,
            emergency_contact_name=data.emergency_contact_name,
            emergency_contact_phone=data.emergency_contact_phone,
            allergies=data.allergies,
            registration_number=uhid,
            name_search_hash=name_hash,
            aadhaar_hash=aadhaar_hash,
        )
        db.add(patient)
        await db.flush()
        await db.refresh(patient)
        return patient

    async def get_patient(self, db: AsyncSession, patient_id: str) -> Patient:
        result = await db.execute(
            select(Patient).where(Patient.id == patient_id, Patient.is_deleted == False)  # noqa: E712
        )
        patient = result.scalar_one_or_none()
        if patient is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
        return patient

    async def search_patients(
        self,
        db: AsyncSession,
        params: PatientSearchParams,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        query = select(Patient).where(Patient.is_deleted == False)  # noqa: E712

        if params.registration_number:
            query = query.where(Patient.registration_number == params.registration_number)
        elif params.abha_id:
            query = query.where(Patient.abha_id == params.abha_id)
        elif params.phone:
            # Search by phone hash
            phone_hash = hash_field(params.phone)
            # Since phone is encrypted, we can't directly search. Use name_search_hash approach
            # For MVP, we search by other indexed fields
            query = query.where(Patient.registration_number.ilike(f"%{params.phone}%"))
        elif params.query:
            # Search by name hash
            name_hash = hash_field(params.query)
            query = query.where(Patient.name_search_hash == name_hash)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Patient.created_at.desc())
        result = await db.execute(query)
        patients = result.scalars().all()

        return {
            "items": patients,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_patient(
        self, db: AsyncSession, patient_id: str, data: PatientUpdate
    ) -> Patient:
        patient = await self.get_patient(db, patient_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(patient, field, value)

        # Update name search hash if name changed
        if "first_name" in update_data or "last_name" in update_data:
            patient.name_search_hash = hash_field(
                f"{patient.first_name} {patient.last_name}"
            )

        patient.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(patient)
        return patient

    async def soft_delete_patient(self, db: AsyncSession, patient_id: str) -> None:
        """DPDP Act Right to Erasure — soft-delete patient data."""
        patient = await self.get_patient(db, patient_id)
        patient.is_deleted = True
        # Anonymize PII fields for DPDP compliance
        patient.first_name = "REDACTED"
        patient.last_name = "REDACTED"
        patient.phone = "REDACTED"
        patient.email = "REDACTED"
        patient.address_line1 = "REDACTED"
        patient.emergency_contact_phone = "REDACTED"
        patient.aadhaar_hash = None
        patient.name_search_hash = None
        patient.photo_url = None
        await db.flush()


patient_service = PatientService()

