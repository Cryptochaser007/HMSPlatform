"""Comprehensive database seed script for HMS Platform.

Populates initial administrative users, clinical departments, medical doctors,
hospital wards, beds, Indian drug formulary, diagnostic lab tests, and NABH indicators.
"""

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select

from app.core.database import async_session_factory, Base, engine
from app.core.rbac import Role
from app.core.security import hash_password
from app.models.user import User
from app.models.pharmacy import Drug, DrugType, DrugInventory
from app.models.laboratory import LabTest
from app.models.ward import Ward, WardType, Bed, BedStatus, BedType
from app.models.quality import QualityIndicator, QualityFrequency


async def seed() -> None:
    print("🌱 Starting database seeding...")

    async with engine.begin() as conn:
        # Create all tables if not exist
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        # ── 1. Create Super Admin User ──────────────────────────────────────
        admin_email = "admin@hms.local"
        res = await session.execute(select(User).where(User.email == admin_email))
        admin = res.scalar_one_or_none()
        if not admin:
            admin = User(
                email=admin_email,
                hashed_password=hash_password("Admin@123"),
                full_name="Hospital Super Administrator",
                role=Role.SUPER_ADMIN,
                department="Management",
                is_active=True,
                is_verified=True,
            )
            session.add(admin)
            print("  ✅ Created Super Admin: admin@hms.local (Password: Admin@123)")

        # ── 2. Create Doctors & Staff ───────────────────────────────────────
        doctors_data = [
            ("dr.sharma@hms.local", "Dr. Rajesh Sharma", Role.DOCTOR, "General Medicine", "MCI-45812"),
            ("dr.priya@hms.local", "Dr. Priya Patel", Role.DOCTOR, "Cardiology", "MCI-78219"),
            ("dr.verma@hms.local", "Dr. Amit Verma", Role.DOCTOR, "Orthopedics", "MCI-33104"),
            ("dr.anita@hms.local", "Dr. Anita Desai", Role.DOCTOR, "Pediatrics", "MCI-90145"),
            ("pathologist@hms.local", "Dr. Sunita Rao", Role.LAB_TECHNICIAN, "Pathology", "MCI-11928"),
            ("radiologist@hms.local", "Dr. Vikram Seth", Role.RADIOLOGIST, "Radiology", "MCI-66231"),
            ("pharmacist@hms.local", "Ramesh Kumar", Role.PHARMACIST, "Pharmacy", "PH-9921"),
            ("frontdesk@hms.local", "Neha Singh", Role.FRONT_DESK, "Reception", "FD-101"),
            ("billing@hms.local", "Kavita Nair", Role.BILLING_CLERK, "Accounts", "AC-202"),
            ("nurse@hms.local", "Sister Mary Mathew", Role.NURSE, "Nursing", "NR-441"),
        ]

        for email, name, role, dept, reg in doctors_data:
            res = await session.execute(select(User).where(User.email == email))
            if not res.scalar_one_or_none():
                staff = User(
                    email=email,
                    hashed_password=hash_password("Staff@123"),
                    full_name=name,
                    role=role,
                    department=dept,
                    registration_number=reg,
                    is_active=True,
                    is_verified=True,
                )
                session.add(staff)
        print("  ✅ Seeded Clinical and Administrative Staff accounts")

        # ── 3. Create Wards & Beds ──────────────────────────────────────────
        wards_data = [
            ("Intensive Care Unit (ICU)", WardType.ICU, 2, 8, "Critical Care", BedType.ICU, Decimal("5000.00")),
            ("General Ward Male", WardType.GENERAL, 1, 12, "General Medicine", BedType.REGULAR, Decimal("800.00")),
            ("General Ward Female", WardType.GENERAL, 1, 12, "General Medicine", BedType.REGULAR, Decimal("800.00")),
            ("Private Deluxe Ward", WardType.PRIVATE, 3, 6, "Speciality", BedType.ELECTRIC, Decimal("3500.00")),
            ("Semi-Private Ward", WardType.SEMI_PRIVATE, 3, 8, "Speciality", BedType.REGULAR, Decimal("1800.00")),
        ]

        for name, w_type, floor, total, dept, bed_type, charge in wards_data:
            res = await session.execute(select(Ward).where(Ward.name == name))
            if not res.scalar_one_or_none():
                ward = Ward(
                    name=name,
                    ward_type=w_type,
                    floor=floor,
                    total_beds=total,
                    department=dept,
                )
                session.add(ward)
                await session.flush()

                for i in range(1, total + 1):
                    prefix = name[:3].upper()
                    bed = Bed(
                        ward_id=ward.id,
                        bed_number=f"{prefix}-{floor}{i:02d}",
                        status=BedStatus.AVAILABLE,
                        bed_type=bed_type,
                        daily_charge=charge,
                    )
                    session.add(bed)
        print("  ✅ Seeded Hospital Wards and Inpatient Beds")

        # ── 4. Create Indian Drug Master & Initial Inventory ────────────────
        drugs_data = [
            ("Paracetamol 650mg", "Paracetamol", "Dolo 650", DrugType.TABLET, "650mg", "Micro Labs", "H", Decimal("30.00"), Decimal("35.00")),
            ("Amoxicillin + Clavulanate 625mg", "Amoxicillin & Potassium Clavulanate", "Augmentin 625", DrugType.TABLET, "625mg", "GSK", "H1", Decimal("180.00"), Decimal("220.00")),
            ("Pantoprazole 40mg", "Pantoprazole Sodium", "Pan 40", DrugType.TABLET, "40mg", "Alkem", "H", Decimal("110.00"), Decimal("130.00")),
            ("Metformin 500mg", "Metformin Hydrochloride", "Glycomet 500", DrugType.TABLET, "500mg", "USV", "H", Decimal("40.00"), Decimal("50.00")),
            ("Telmisartan 40mg", "Telmisartan", "Telma 40", DrugType.TABLET, "40mg", "Glenmark", "H", Decimal("90.00"), Decimal("110.00")),
            ("Atorvastatin 10mg", "Atorvastatin Calcium", "Atorva 10", DrugType.TABLET, "10mg", "Zydus", "H", Decimal("80.00"), Decimal("95.00")),
            ("Azithromycin 500mg", "Azithromycin", "Azee 500", DrugType.TABLET, "500mg", "Cipla", "H1", Decimal("105.00"), Decimal("125.00")),
            ("Ceftriaxone 1g Injection", "Ceftriaxone Sodium", "Monocef 1g", DrugType.INJECTION, "1g", "Aristo", "H1", Decimal("60.00"), Decimal("75.00")),
            ("Ondansetron 4mg", "Ondansetron", "Emeset 4", DrugType.TABLET, "4mg", "Cipla", "H", Decimal("45.00"), Decimal("55.00")),
            ("Cough Syrup 100ml", "Dextromethorphan + Chlorpheniramine", "Benadryl DR", DrugType.SYRUP, "100ml", "J&J", "H", Decimal("120.00"), Decimal("140.00")),
        ]

        for d_name, gen_name, brand, d_type, strg, mfg, sched, u_price, mrp in drugs_data:
            res = await session.execute(select(Drug).where(Drug.name == d_name))
            drug = res.scalar_one_or_none()
            if not drug:
                drug = Drug(
                    name=d_name,
                    generic_name=gen_name,
                    brand_name=brand,
                    drug_type=d_type,
                    strength=strg,
                    manufacturer=mfg,
                    schedule=sched,
                )
                session.add(drug)
                await session.flush()

                # Add stock batch
                inv = DrugInventory(
                    drug_id=drug.id,
                    batch_number=f"B-{date.today().year}-{drug.name[:3].upper()}",
                    expiry_date=date(date.today().year + 2, 12, 31),
                    quantity_in_stock=500,
                    unit_price=u_price,
                    mrp=mrp,
                    gst_percentage=Decimal("12.00"),
                    reorder_level=50,
                    location="Central Pharmacy Shelf A",
                )
                session.add(inv)
        print("  ✅ Seeded Drug Formulary and Batch Inventory")

        # ── 5. Create Lab Diagnostic Tests ──────────────────────────────────
        tests_data = [
            (
                "Complete Blood Count (CBC)", "CBC001", "Hematology", "Blood (EDTA)",
                "Full hemogram including Hb, TLC, DLC, Platelets",
                {"Hemoglobin": "13.0-17.0 g/dL", "TLC": "4000-11000 /cumm", "Platelets": "150000-450000 /cumm"},
                Decimal("350.00"), 4
            ),
            (
                "Liver Function Test (LFT)", "LFT001", "Biochemistry", "Blood (Serum)",
                "Total Bilirubin, SGOT, SGPT, Alkaline Phosphatase, Total Protein",
                {"Bilirubin Total": "0.2-1.2 mg/dL", "SGOT": "5-40 U/L", "SGPT": "5-45 U/L", "Total Protein": "6.0-8.3 g/dL"},
                Decimal("750.00"), 6
            ),
            (
                "Kidney Function Test (KFT / RFT)", "KFT001", "Biochemistry", "Blood (Serum)",
                "Blood Urea, Serum Creatinine, Uric Acid, Electrolytes",
                {"Blood Urea": "15-45 mg/dL", "Serum Creatinine": "0.6-1.2 mg/dL", "Uric Acid": "3.5-7.2 mg/dL"},
                Decimal("650.00"), 6
            ),
            (
                "Fasting Blood Glucose", "FBS001", "Biochemistry", "Blood (Fluoride)",
                "Fasting Plasma Glucose for diabetes screening",
                {"Fasting Blood Sugar": "70-100 mg/dL"},
                Decimal("100.00"), 2
            ),
            (
                "Glycated Hemoglobin (HbA1c)", "HBA001", "Biochemistry", "Blood (EDTA)",
                "3-month average blood glucose control",
                {"HbA1c": "4.0-5.6 %"},
                Decimal("500.00"), 4
            ),
            (
                "Lipid Profile", "LIP001", "Biochemistry", "Blood (Serum)",
                "Total Cholesterol, Triglycerides, HDL, LDL, VLDL",
                {"Total Cholesterol": "< 200 mg/dL", "Triglycerides": "< 150 mg/dL", "HDL Cholesterol": "> 40 mg/dL", "LDL Cholesterol": "< 100 mg/dL"},
                Decimal("800.00"), 6
            ),
            (
                "Urine Routine & Microscopic Examination", "URN001", "Clinical Pathology", "Urine",
                "Color, Specific Gravity, Protein, Sugar, Pus Cells, RBCs",
                {"Pus Cells": "0-5 /HPF", "RBC": "Nil", "Protein": "Nil", "Sugar": "Nil"},
                Decimal("150.00"), 2
            ),
        ]

        for name, code, cat, samp, desc, ref_ranges, price, tat in tests_data:
            res = await session.execute(select(LabTest).where(LabTest.code == code))
            if not res.scalar_one_or_none():
                test = LabTest(
                    name=name,
                    code=code,
                    category=cat,
                    sample_type=samp,
                    description=desc,
                    reference_ranges=ref_ranges,
                    price=price,
                    turnaround_hours=tat,
                )
                session.add(test)
        print("  ✅ Seeded Diagnostic Laboratory Test Catalog")

        # ── 6. Create NABH Mandatory Quality Indicators ─────────────────────
        nabh_indicators = [
            (
                "Surgical Site Infection (SSI) Rate", "NABH-QI-01", "Infection Control",
                "Rate of infections developing within 30 days of surgical procedure",
                "Number of surgical site infections in a month",
                "Total number of surgeries performed in that month",
                Decimal("1.50"), "%", QualityFrequency.MONTHLY, True
            ),
            (
                "Catheter-Associated Urinary Tract Infection (CAUTI) Rate", "NABH-QI-02", "Infection Control",
                "Incidence of CAUTI per 1000 urinary catheter days",
                "Number of CAUTI cases",
                "Total urinary catheter days * 1000",
                Decimal("2.00"), "per 1000 days", QualityFrequency.MONTHLY, True
            ),
            (
                "Medication Error Rate", "NABH-QI-03", "Patient Safety",
                "Rate of medication dispensing, administration, or prescription errors",
                "Total medication error events recorded",
                "Total patient admissions",
                Decimal("0.50"), "%", QualityFrequency.MONTHLY, True
            ),
            (
                "Inpatient Fall Rate", "NABH-QI-04", "Patient Safety",
                "Rate of accidental patient falls in wards per 1000 patient days",
                "Total patient falls",
                "Total inpatient bed days * 1000",
                Decimal("1.00"), "per 1000 days", QualityFrequency.MONTHLY, True
            ),
            (
                "Hand Hygiene Compliance Rate", "NABH-QI-05", "Quality Assurance",
                "Adherence to WHO 5 Moments of Hand Hygiene by staff",
                "Observed hand hygiene actions executed",
                "Total observed hand hygiene opportunities",
                Decimal("90.00"), "%", QualityFrequency.MONTHLY, True
            ),
            (
                "Average Length of Stay (ALOS)", "NABH-QI-06", "Clinical Efficiency",
                "Average duration in days that an inpatient stays in hospital",
                "Total inpatient days for all discharged patients",
                "Total discharges in the month",
                Decimal("4.00"), "days", QualityFrequency.MONTHLY, True
            ),
            (
                "Hospital-wide Gross Mortality Rate", "NABH-QI-07", "Clinical Outcomes",
                "Gross mortality percentage among admitted patients",
                "Total inpatient deaths",
                "Total admissions in the period",
                Decimal("2.00"), "%", QualityFrequency.MONTHLY, True
            ),
        ]

        for name, code, cat, desc, num, den, tgt, unit, freq, nabh_mand in nabh_indicators:
            res = await session.execute(select(QualityIndicator).where(QualityIndicator.code == code))
            if not res.scalar_one_or_none():
                ind = QualityIndicator(
                    name=name,
                    code=code,
                    category=cat,
                    description=desc,
                    numerator_description=num,
                    denominator_description=den,
                    target_value=tgt,
                    unit=unit,
                    frequency=freq,
                    is_nabh_mandatory=nabh_mand,
                )
                session.add(ind)
        print("  ✅ Seeded NABH Mandatory Quality & Safety Indicators")

        await session.commit()
    print("✨ Seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())

