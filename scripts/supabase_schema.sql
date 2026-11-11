-- ============================================================================
-- HMS Platform - Supabase PostgreSQL Database DDL
-- Tailored for ABDM (Ayushman Bharat Digital Mission) & NABH 5th Edition
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Required PostgreSQL Extensions
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ----------------------------------------------------------------------------
-- 2. Custom Enumerations (Enum Types)
-- ----------------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE user_role_enum AS ENUM (
        'SUPER_ADMIN', 'HOSPITAL_ADMIN', 'DOCTOR', 'NURSE', 'PHARMACIST',
        'LAB_TECHNICIAN', 'RADIOLOGIST', 'BILLING_CLERK', 'FRONT_DESK'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE gender_enum AS ENUM ('MALE', 'FEMALE', 'OTHER', 'UNDISCLOSED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE encounter_type_enum AS ENUM ('OPD', 'IPD', 'EMERGENCY');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE encounter_status_enum AS ENUM (
        'SCHEDULED', 'CHECKED_IN', 'IN_PROGRESS', 'COMPLETED',
        'CANCELLED', 'ADMITTED', 'DISCHARGED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE encounter_priority_enum AS ENUM ('NORMAL', 'URGENT', 'EMERGENCY');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE note_type_enum AS ENUM ('SOAP', 'PROGRESS', 'DISCHARGE_SUMMARY', 'PROCEDURE', 'NURSING');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE prescription_status_enum AS ENUM ('DRAFT', 'SIGNED', 'DISPENSED', 'PARTIALLY_DISPENSED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE drug_type_enum AS ENUM (
        'TABLET', 'CAPSULE', 'SYRUP', 'INJECTION', 'OINTMENT',
        'DROPS', 'INHALER', 'PATCH', 'POWDER', 'GEL', 'CREAM', 'OTHER'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE ward_type_enum AS ENUM (
        'GENERAL', 'SEMI_PRIVATE', 'PRIVATE', 'ICU', 'NICU', 'PICU', 'ISOLATION', 'EMERGENCY'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE bed_status_enum AS ENUM ('AVAILABLE', 'OCCUPIED', 'MAINTENANCE', 'RESERVED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE bed_type_enum AS ENUM ('REGULAR', 'ELECTRIC', 'ICU', 'VENTILATOR', 'CRADLE');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE admission_status_enum AS ENUM ('ADMITTED', 'DISCHARGED', 'TRANSFERRED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE discharge_type_enum AS ENUM ('NORMAL', 'AGAINST_ADVICE', 'ABSCONDED', 'DEATH', 'TRANSFER');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE lab_order_status_enum AS ENUM ('ORDERED', 'SAMPLE_COLLECTED', 'IN_PROGRESS', 'COMPLETED', 'VERIFIED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE lab_priority_enum AS ENUM ('ROUTINE', 'URGENT', 'STAT');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE result_flag_enum AS ENUM ('NORMAL', 'LOW', 'HIGH', 'CRITICAL');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE modality_enum AS ENUM ('XRAY', 'CT', 'MRI', 'ULTRASOUND', 'MAMMOGRAPHY', 'FLUOROSCOPY', 'PET');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE radiology_order_status_enum AS ENUM ('ORDERED', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'REPORTED', 'VERIFIED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE radiology_priority_enum AS ENUM ('ROUTINE', 'URGENT', 'STAT');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE bill_type_enum AS ENUM ('OPD', 'IPD', 'PHARMACY', 'LAB', 'RADIOLOGY', 'PROCEDURE');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE bill_item_type_enum AS ENUM ('CONSULTATION', 'PROCEDURE', 'MEDICINE', 'LAB_TEST', 'RADIOLOGY', 'BED_CHARGE', 'NURSING', 'OTHER');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE payment_status_enum AS ENUM ('PENDING', 'PARTIAL', 'PAID', 'REFUNDED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE payment_method_enum AS ENUM ('CASH', 'CARD', 'UPI', 'NEFT', 'INSURANCE', 'CHEQUE');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE quality_frequency_enum AS ENUM ('DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE incident_type_enum AS ENUM (
        'PATIENT_SAFETY', 'MEDICATION_ERROR', 'FALL', 'INFECTION', 'EQUIPMENT', 'NEAR_MISS', 'NEEDLE_STICK', 'OTHER'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE incident_severity_enum AS ENUM ('NEAR_MISS', 'MINOR', 'MODERATE', 'MAJOR', 'SENTINEL');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE incident_status_enum AS ENUM ('REPORTED', 'UNDER_INVESTIGATION', 'ACTION_TAKEN', 'CLOSED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE consent_type_enum AS ENUM (
        'ABDM_LINK', 'DATA_SHARE', 'TELEMEDICINE', 'SURGERY', 'RESEARCH', 'GENERAL'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE consent_status_enum AS ENUM ('GRANTED', 'REVOKED', 'EXPIRED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE audit_action_enum AS ENUM (
        'CREATE', 'READ', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT',
        'EXPORT', 'PRINT', 'CONSENT_GRANTED', 'CONSENT_REVOKED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- ----------------------------------------------------------------------------
-- 3. Core Database Tables (Ordered by Dependency)
-- ----------------------------------------------------------------------------

-- Table: users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role user_role_enum NOT NULL,
    department VARCHAR(100),
    registration_number VARCHAR(100),
    phone VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- Table: patients
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_number VARCHAR(50) UNIQUE NOT NULL,
    abha_id VARCHAR(50) UNIQUE,
    abha_address VARCHAR(255),
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender gender_enum NOT NULL,
    phone VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(10),
    aadhaar_hash VARCHAR(64),
    blood_group VARCHAR(10),
    allergies JSONB,
    emergency_contact_name VARCHAR(255),
    emergency_contact_phone VARCHAR(255),
    photo_url VARCHAR(500),
    name_search_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_patients_registration_number ON patients(registration_number);
CREATE INDEX IF NOT EXISTS ix_patients_abha_id ON patients(abha_id);
CREATE INDEX IF NOT EXISTS ix_patients_name_search_hash ON patients(name_search_hash);

-- Table: consents (DPDP Act Compliance)
CREATE TABLE IF NOT EXISTS consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    consent_type consent_type_enum NOT NULL,
    purpose VARCHAR(255) NOT NULL,
    data_categories JSONB NOT NULL,
    granted_to VARCHAR(255),
    status consent_status_enum NOT NULL DEFAULT 'GRANTED',
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    artifact_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_consents_patient_id ON consents(patient_id);

-- Table: wards
CREATE TABLE IF NOT EXISTS wards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    ward_type ward_type_enum NOT NULL,
    floor INTEGER NOT NULL,
    total_beds INTEGER NOT NULL,
    department VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- Table: beds
CREATE TABLE IF NOT EXISTS beds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ward_id UUID NOT NULL REFERENCES wards(id) ON DELETE CASCADE,
    bed_number VARCHAR(20) NOT NULL,
    status bed_status_enum NOT NULL DEFAULT 'AVAILABLE',
    bed_type bed_type_enum NOT NULL DEFAULT 'REGULAR',
    daily_charge NUMERIC(10, 2) NOT NULL DEFAULT 500.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_beds_ward_id ON beds(ward_id);

-- Table: encounters (OPD / IPD / Emergency Visits)
CREATE TABLE IF NOT EXISTS encounters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    doctor_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    encounter_type encounter_type_enum NOT NULL,
    status encounter_status_enum NOT NULL DEFAULT 'SCHEDULED',
    token_number INTEGER,
    appointment_time TIMESTAMPTZ,
    check_in_time TIMESTAMPTZ,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    department VARCHAR(100) NOT NULL,
    room_number VARCHAR(20),
    chief_complaint TEXT,
    notes TEXT,
    follow_up_date DATE,
    priority encounter_priority_enum NOT NULL DEFAULT 'NORMAL',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_encounters_patient_id ON encounters(patient_id);
CREATE INDEX IF NOT EXISTS ix_encounters_doctor_id ON encounters(doctor_id);

-- Table: clinical_notes (EMR SOAP Notes & Discharge Summaries)
CREATE TABLE IF NOT EXISTS clinical_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID NOT NULL REFERENCES encounters(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    note_type note_type_enum NOT NULL DEFAULT 'SOAP',
    subjective TEXT,
    objective TEXT,
    assessment TEXT,
    plan TEXT,
    vitals JSONB,
    icd_codes JSONB,
    attachments JSONB,
    is_amendment BOOLEAN NOT NULL DEFAULT FALSE,
    amended_from_id UUID REFERENCES clinical_notes(id) ON DELETE SET NULL,
    digital_signature VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_clinical_notes_encounter_id ON clinical_notes(encounter_id);

-- Table: admissions (IPD Bed Inpatient Stays)
CREATE TABLE IF NOT EXISTS admissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID NOT NULL REFERENCES encounters(id) ON DELETE RESTRICT,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    bed_id UUID NOT NULL REFERENCES beds(id) ON DELETE RESTRICT,
    admitted_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    admission_date TIMESTAMPTZ NOT NULL,
    expected_discharge DATE,
    actual_discharge TIMESTAMPTZ,
    discharge_type discharge_type_enum,
    discharge_summary_id UUID REFERENCES clinical_notes(id) ON DELETE SET NULL,
    status admission_status_enum NOT NULL DEFAULT 'ADMITTED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_admissions_encounter_id ON admissions(encounter_id);
CREATE INDEX IF NOT EXISTS ix_admissions_patient_id ON admissions(patient_id);

-- Table: drugs (Formulary)
CREATE TABLE IF NOT EXISTS drugs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    generic_name VARCHAR(255) NOT NULL,
    brand_name VARCHAR(255),
    drug_type drug_type_enum NOT NULL,
    strength VARCHAR(50) NOT NULL,
    manufacturer VARCHAR(255),
    hsn_code VARCHAR(20),
    schedule VARCHAR(10),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_drugs_name ON drugs(name);
CREATE INDEX IF NOT EXISTS ix_drugs_generic_name ON drugs(generic_name);

-- Table: drug_inventory (Batches & Stock)
CREATE TABLE IF NOT EXISTS drug_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drug_id UUID NOT NULL REFERENCES drugs(id) ON DELETE RESTRICT,
    batch_number VARCHAR(100) NOT NULL,
    expiry_date DATE NOT NULL,
    quantity_in_stock INTEGER NOT NULL DEFAULT 0,
    unit_price NUMERIC(10, 2) NOT NULL,
    mrp NUMERIC(10, 2) NOT NULL,
    gst_percentage NUMERIC(5, 2) NOT NULL DEFAULT 12.00,
    reorder_level INTEGER NOT NULL DEFAULT 10,
    location VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_drug_inventory_drug_id ON drug_inventory(drug_id);

-- Table: prescriptions
CREATE TABLE IF NOT EXISTS prescriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID NOT NULL REFERENCES encounters(id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    status prescription_status_enum NOT NULL DEFAULT 'DRAFT',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_prescriptions_encounter_id ON prescriptions(encounter_id);

-- Table: prescription_items
CREATE TABLE IF NOT EXISTS prescription_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prescription_id UUID NOT NULL REFERENCES prescriptions(id) ON DELETE CASCADE,
    drug_id UUID REFERENCES drugs(id) ON DELETE SET NULL,
    drug_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(100) NOT NULL,
    frequency VARCHAR(100) NOT NULL,
    route VARCHAR(50) NOT NULL DEFAULT 'Oral',
    duration_days INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    instructions TEXT,
    is_substitutable BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_prescription_items_prescription_id ON prescription_items(prescription_id);

-- Table: dispensings (Pharmacy Dispensing Ledger)
CREATE TABLE IF NOT EXISTS dispensings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prescription_item_id UUID NOT NULL REFERENCES prescription_items(id) ON DELETE RESTRICT,
    drug_inventory_id UUID NOT NULL REFERENCES drug_inventory(id) ON DELETE RESTRICT,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    dispensed_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    quantity_dispensed INTEGER NOT NULL,
    dispensed_at TIMESTAMPTZ NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- Table: lab_tests (Diagnostic Master Catalog)
CREATE TABLE IF NOT EXISTS lab_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL,
    sample_type VARCHAR(100) NOT NULL,
    description TEXT,
    reference_ranges JSONB,
    turnaround_hours INTEGER NOT NULL DEFAULT 24,
    price NUMERIC(10, 2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_lab_tests_code ON lab_tests(code);

-- Table: lab_orders
CREATE TABLE IF NOT EXISTS lab_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID NOT NULL REFERENCES encounters(id) ON DELETE RESTRICT,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    ordered_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    test_id UUID NOT NULL REFERENCES lab_tests(id) ON DELETE RESTRICT,
    status lab_order_status_enum NOT NULL DEFAULT 'ORDERED',
    priority lab_priority_enum NOT NULL DEFAULT 'ROUTINE',
    clinical_notes TEXT,
    sample_id VARCHAR(50) UNIQUE,
    collected_at TIMESTAMPTZ,
    collected_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_lab_orders_encounter_id ON lab_orders(encounter_id);
CREATE INDEX IF NOT EXISTS ix_lab_orders_patient_id ON lab_orders(patient_id);

-- Table: lab_results
CREATE TABLE IF NOT EXISTS lab_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES lab_orders(id) ON DELETE CASCADE,
    parameter_name VARCHAR(255) NOT NULL,
    value VARCHAR(100) NOT NULL,
    unit VARCHAR(50),
    reference_range VARCHAR(100),
    is_abnormal BOOLEAN NOT NULL DEFAULT FALSE,
    flag result_flag_enum,
    performed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    verified_by UUID REFERENCES users(id) ON DELETE SET NULL,
    verified_at TIMESTAMPTZ,
    remarks TEXT,
    attachments JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_lab_results_order_id ON lab_results(order_id);

-- Table: radiology_orders
CREATE TABLE IF NOT EXISTS radiology_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encounter_id UUID NOT NULL REFERENCES encounters(id) ON DELETE RESTRICT,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    ordered_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    modality modality_enum NOT NULL,
    body_part VARCHAR(200) NOT NULL,
    study_description TEXT,
    status radiology_order_status_enum NOT NULL DEFAULT 'ORDERED',
    priority radiology_priority_enum NOT NULL DEFAULT 'ROUTINE',
    clinical_indication TEXT,
    scheduled_at TIMESTAMPTZ,
    orthanc_study_id VARCHAR(255),
    dicom_study_uid VARCHAR(255),
    accession_number VARCHAR(50) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_radiology_orders_encounter_id ON radiology_orders(encounter_id);
CREATE INDEX IF NOT EXISTS ix_radiology_orders_patient_id ON radiology_orders(patient_id);

-- Table: radiology_reports
CREATE TABLE IF NOT EXISTS radiology_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID UNIQUE NOT NULL REFERENCES radiology_orders(id) ON DELETE CASCADE,
    radiologist_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    findings TEXT NOT NULL,
    impression TEXT NOT NULL,
    recommendation TEXT,
    is_critical BOOLEAN NOT NULL DEFAULT FALSE,
    reported_at TIMESTAMPTZ NOT NULL,
    verified_by UUID REFERENCES users(id) ON DELETE SET NULL,
    verified_at TIMESTAMPTZ,
    template_used VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- Table: bills (Itemized Invoices)
CREATE TABLE IF NOT EXISTS bills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bill_number VARCHAR(50) UNIQUE NOT NULL,
    encounter_id UUID REFERENCES encounters(id) ON DELETE SET NULL,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    bill_type bill_type_enum NOT NULL,
    subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    tax_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    total_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    payment_status payment_status_enum NOT NULL DEFAULT 'PENDING',
    notes TEXT,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_bills_bill_number ON bills(bill_number);
CREATE INDEX IF NOT EXISTS ix_bills_patient_id ON bills(patient_id);

-- Table: bill_items
CREATE TABLE IF NOT EXISTS bill_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bill_id UUID NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    item_type bill_item_type_enum NOT NULL,
    description VARCHAR(500) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(10, 2) NOT NULL,
    discount_percent NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    tax_percent NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    total NUMERIC(10, 2) NOT NULL,
    reference_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_bill_items_bill_id ON bill_items(bill_id);

-- Table: payments
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bill_id UUID NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    amount NUMERIC(12, 2) NOT NULL,
    payment_method payment_method_enum NOT NULL,
    transaction_reference VARCHAR(255),
    payment_date TIMESTAMPTZ NOT NULL,
    received_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    receipt_number VARCHAR(50) UNIQUE NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_payments_bill_id ON payments(bill_id);
CREATE INDEX IF NOT EXISTS ix_payments_receipt_number ON payments(receipt_number);

-- Table: quality_indicators (NABH Mandatory Metrics)
CREATE TABLE IF NOT EXISTS quality_indicators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    numerator_description TEXT NOT NULL,
    denominator_description TEXT NOT NULL,
    target_value NUMERIC(5, 2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    frequency quality_frequency_enum NOT NULL,
    is_nabh_mandatory BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_quality_indicators_code ON quality_indicators(code);

-- Table: quality_measurements
CREATE TABLE IF NOT EXISTS quality_measurements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indicator_id UUID NOT NULL REFERENCES quality_indicators(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    numerator_value NUMERIC(10, 2) NOT NULL,
    denominator_value NUMERIC(10, 2) NOT NULL,
    calculated_value NUMERIC(10, 2) NOT NULL,
    recorded_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_quality_measurements_indicator_id ON quality_measurements(indicator_id);

-- Table: incident_reports (NABH Patient Safety & RCA/CAPA)
CREATE TABLE IF NOT EXISTS incident_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_number VARCHAR(50) UNIQUE NOT NULL,
    incident_type incident_type_enum NOT NULL,
    severity incident_severity_enum NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    location VARCHAR(255) NOT NULL,
    incident_date TIMESTAMPTZ NOT NULL,
    reported_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
    root_cause TEXT,
    corrective_action TEXT,
    status incident_status_enum NOT NULL DEFAULT 'REPORTED',
    closed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_incident_reports_incident_number ON incident_reports(incident_number);

-- Table: audit_logs (Immutable DISHA Hash Chain Trail)
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action audit_action_enum NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID,
    old_value JSONB,
    new_value JSONB,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    session_id VARCHAR(255),
    hash_chain VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_entity_type ON audit_logs(entity_type);
CREATE INDEX IF NOT EXISTS ix_audit_logs_entity_id ON audit_logs(entity_id);

