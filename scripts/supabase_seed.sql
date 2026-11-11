-- ============================================================================
-- HMS Platform - Supabase Demo Seed Script
-- Populates Admin Staff, SLA Definitions, Quality Indicators, Tickets,
-- Wards, Inpatient Beds, Formulary, Diagnostic Catalog, and Sample Visits.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Administrative & Clinical Staff Users (Passwords encrypted via bcrypt)
-- Super Admin: admin@hms.local / Admin@123
-- Staff Users: [email] / Staff@123
-- ----------------------------------------------------------------------------
INSERT INTO users (id, email, hashed_password, full_name, role, department, registration_number, is_active, created_at, updated_at)
VALUES 
    (
        '11111111-1111-1111-1111-111111111111',
        'admin@hms.local',
        crypt('Admin@123', gen_salt('bf', 12)),
        'Hospital Super Administrator',
        'SUPER_ADMIN',
        'Management',
        'ADM-001',
        TRUE, NOW(), NOW()
    ),
    (
        '22222222-2222-2222-2222-222222222221',
        'dr.sharma@hms.local',
        crypt('Staff@123', gen_salt('bf', 12)),
        'Dr. Rajesh Sharma',
        'DOCTOR',
        'General Medicine',
        'MCI-45812',
        TRUE, NOW(), NOW()
    ),
    (
        '22222222-2222-2222-2222-222222222222',
        'dr.priya@hms.local',
        crypt('Staff@123', gen_salt('bf', 12)),
        'Dr. Priya Patel',
        'DOCTOR',
        'Cardiology',
        'MCI-78219',
        TRUE, NOW(), NOW()
    ),
    (
        '22222222-2222-2222-2222-222222222223',
        'dr.verma@hms.local',
        crypt('Staff@123', gen_salt('bf', 12)),
        'Dr. Amit Verma',
        'DOCTOR',
        'Orthopedics',
        'MCI-33104',
        TRUE, NOW(), NOW()
    ),
    (
        '22222222-2222-2222-2222-222222222224',
        'pathologist@hms.local',
        crypt('Staff@123', gen_salt('bf', 12)),
        'Dr. Sunita Rao',
        'LAB_TECHNICIAN',
        'Pathology',
        'MCI-11928',
        TRUE, NOW(), NOW()
    ),
    (
        '22222222-2222-2222-2222-222222222225',
        'radiologist@hms.local',
        crypt('Staff@123', gen_salt('bf', 12)),
        'Dr. Vikram Seth',
        'RADIOLOGIST',
        'Radiology',
        'MCI-66231',
        TRUE, NOW(), NOW()
    ),
    (
        '22222222-2222-2222-2222-222222222226',
        'pharmacist@hms.local',
        crypt('Staff@123', gen_salt('bf', 12)),
        'Ramesh Kumar',
        'PHARMACIST',
        'Pharmacy',
        'PH-9921',
        TRUE, NOW(), NOW()
    ),
    (
        '22222222-2222-2222-2222-222222222227',
        'frontdesk@hms.local',
        crypt('Staff@123', gen_salt('bf', 12)),
        'Neha Singh',
        'FRONT_DESK',
        'Reception',
        'FD-101',
        TRUE, NOW(), NOW()
    ),
    (
        '22222222-2222-2222-2222-222222222228',
        'nurse@hms.local',
        crypt('Staff@123', gen_salt('bf', 12)),
        'Sister Mary Mathew',
        'NURSE',
        'Nursing',
        'NR-441',
        TRUE, NOW(), NOW()
    ),
    (
        '22222222-2222-2222-2222-222222222229',
        'billing@hms.local',
        crypt('Staff@123', gen_salt('bf', 12)),
        'Kavita Nair',
        'BILLING_CLERK',
        'Accounts',
        'AC-202',
        TRUE, NOW(), NOW()
    )
ON CONFLICT (email) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 2. NABH SLA & Key Quality Indicator Definitions (Mandatory Benchmarks)
-- ----------------------------------------------------------------------------
INSERT INTO quality_indicators (id, name, code, category, description, numerator_description, denominator_description, target_value, unit, frequency, is_nabh_mandatory, is_active)
VALUES
    (
        '33333333-3333-3333-3333-333333333301',
        'Emergency Triage-to-Doctor SLA',
        'SLA-EMR-01',
        'Clinical Service SLA',
        'Patient triage to emergency physician consultation response SLA (< 10 minutes)',
        'Emergency patients evaluated by physician within 10 minutes of arrival',
        'Total emergency department patient visits',
        98.00,
        '%',
        'DAILY',
        TRUE,
        TRUE
    ),
    (
        '33333333-3333-3333-3333-333333333302',
        'Diagnostic Lab Turnaround Time (TAT) SLA',
        'SLA-LAB-01',
        'Laboratory SLA',
        'Compliance with defined lab test profile turnaround times (sample collection to verification)',
        'Number of lab test reports issued within stated turnaround hours',
        'Total lab tests ordered',
        95.00,
        '%',
        'DAILY',
        TRUE,
        TRUE
    ),
    (
        '33333333-3333-3333-3333-333333333303',
        'OPD Consultation Wait Time SLA',
        'SLA-OPD-01',
        'Patient Flow SLA',
        'Patients seen within 30 minutes of scheduled queue token time',
        'Number of patients entering consultation within 30 minutes of token issue',
        'Total OPD check-in encounters',
        90.00,
        '%',
        'WEEKLY',
        TRUE,
        TRUE
    ),
    (
        '33333333-3333-3333-3333-333333333304',
        'Surgical Site Infection (SSI) Rate',
        'NABH-QI-01',
        'Infection Control',
        'Infections developing within 30 days of surgical intervention',
        'Number of surgical site infections',
        'Total surgical operations performed',
        1.50,
        '%',
        'MONTHLY',
        TRUE,
        TRUE
    ),
    (
        '33333333-3333-3333-3333-333333333305',
        'Catheter-Associated UTI (CAUTI) Rate',
        'NABH-QI-02',
        'Infection Control',
        'Incidence of CAUTI per 1000 indwelling catheter days',
        'Number of CAUTI cases identified',
        'Total urinary catheter days * 1000',
        2.00,
        'per 1000 days',
        'MONTHLY',
        TRUE,
        TRUE
    ),
    (
        '33333333-3333-3333-3333-333333333306',
        'Medication Error Incident Rate',
        'NABH-QI-03',
        'Patient Safety',
        'Prescribing, dispensing, or administration errors per total inpatient admissions',
        'Total medication error events recorded',
        'Total patient admissions',
        0.50,
        '%',
        'MONTHLY',
        TRUE,
        TRUE
    ),
    (
        '33333333-3333-3333-3333-333333333307',
        'Hand Hygiene Compliance Rate',
        'NABH-QI-05',
        'Quality Assurance',
        'Adherence to WHO 5 Moments of Hand Hygiene protocol by healthcare staff',
        'Observed hand hygiene actions executed',
        'Total observed opportunities',
        90.00,
        '%',
        'MONTHLY',
        TRUE,
        TRUE
    ),
    (
        '33333333-3333-3333-3333-333333333308',
        'Average Length of Stay (ALOS)',
        'NABH-QI-06',
        'Clinical Efficiency',
        'Average duration in days for inpatient care before safe discharge',
        'Total inpatient days for all discharged patients',
        'Total discharges in the reporting period',
        4.00,
        'days',
        'MONTHLY',
        TRUE,
        TRUE
    )
ON CONFLICT (code) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 3. Diagnostic Lab Catalog (with strict SLA Turnaround Hours)
-- ----------------------------------------------------------------------------
INSERT INTO lab_tests (id, name, code, category, sample_type, description, reference_ranges, price, turnaround_hours, is_active)
VALUES
    (
        '44444444-4444-4444-4444-444444444401',
        'Complete Blood Count (CBC)',
        'CBC001',
        'Hematology',
        'Blood (EDTA)',
        'Full hemogram: Hb, TLC, DLC, Platelet count',
        '{"Hemoglobin": "13.0-17.0 g/dL", "TLC": "4000-11000 /cumm", "Platelets": "150000-450000 /cumm"}'::jsonb,
        350.00,
        4,
        TRUE
    ),
    (
        '44444444-4444-4444-4444-444444444402',
        'Liver Function Test (LFT)',
        'LFT001',
        'Biochemistry',
        'Blood (Serum)',
        'Total Bilirubin, SGOT, SGPT, Alkaline Phosphatase, Total Protein',
        '{"Bilirubin Total": "0.2-1.2 mg/dL", "SGOT": "5-40 U/L", "SGPT": "5-45 U/L"}'::jsonb,
        750.00,
        6,
        TRUE
    ),
    (
        '44444444-4444-4444-4444-444444444403',
        'Kidney Function Test (KFT / RFT)',
        'KFT001',
        'Biochemistry',
        'Blood (Serum)',
        'Blood Urea, Serum Creatinine, Uric Acid, Electrolytes',
        '{"Blood Urea": "15-45 mg/dL", "Serum Creatinine": "0.6-1.2 mg/dL"}'::jsonb,
        650.00,
        6,
        TRUE
    ),
    (
        '44444444-4444-4444-4444-444444444404',
        'Fasting Blood Glucose (FBS)',
        'FBS001',
        'Biochemistry',
        'Blood (Fluoride)',
        'Fasting Plasma Glucose for diabetes diagnosis and monitoring',
        '{"Fasting Glucose": "70-100 mg/dL"}'::jsonb,
        100.00,
        2,
        TRUE
    ),
    (
        '44444444-4444-4444-4444-444444444405',
        'Glycated Hemoglobin (HbA1c)',
        'HBA001',
        'Biochemistry',
        'Blood (EDTA)',
        '3-month average plasma glucose concentration',
        '{"HbA1c": "4.0-5.6 % (Normal), 5.7-6.4 % (Prediabetes)"}'::jsonb,
        500.00,
        4,
        TRUE
    )
ON CONFLICT (code) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 4. Hospital Wards & Inpatient Beds
-- ----------------------------------------------------------------------------
INSERT INTO wards (id, name, ward_type, floor, total_beds, department, is_active)
VALUES
    ('55555555-5555-5555-5555-555555555501', 'Intensive Care Unit (ICU)', 'ICU', 2, 8, 'Critical Care', TRUE),
    ('55555555-5555-5555-5555-555555555502', 'General Ward Male', 'GENERAL', 1, 12, 'General Medicine', TRUE),
    ('55555555-5555-5555-5555-555555555503', 'General Ward Female', 'GENERAL', 1, 12, 'General Medicine', TRUE),
    ('55555555-5555-5555-5555-555555555504', 'Private Deluxe Suite', 'PRIVATE', 3, 6, 'Speciality', TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO beds (ward_id, bed_number, status, bed_type, daily_charge)
VALUES
    ('55555555-5555-5555-5555-555555555501', 'ICU-201', 'AVAILABLE', 'ICU', 5000.00),
    ('55555555-5555-5555-5555-555555555501', 'ICU-202', 'AVAILABLE', 'VENTILATOR', 7500.00),
    ('55555555-5555-5555-5555-555555555502', 'GWM-101', 'AVAILABLE', 'REGULAR', 800.00),
    ('55555555-5555-5555-5555-555555555502', 'GWM-102', 'AVAILABLE', 'REGULAR', 800.00),
    ('55555555-5555-5555-5555-555555555503', 'GWF-101', 'AVAILABLE', 'REGULAR', 800.00),
    ('55555555-5555-5555-5555-555555555504', 'PVT-301', 'AVAILABLE', 'ELECTRIC', 3500.00)
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------------------
-- 5. Indian Drug Master & Pharmacy Inventory Batches
-- ----------------------------------------------------------------------------
INSERT INTO drugs (id, name, generic_name, brand_name, drug_type, strength, manufacturer, schedule, is_active)
VALUES
    ('66666666-6666-6666-6666-666666666601', 'Paracetamol 650mg', 'Paracetamol', 'Dolo 650', 'TABLET', '650mg', 'Micro Labs', 'H', TRUE),
    ('66666666-6666-6666-6666-666666666602', 'Amoxicillin + Clavulanate 625mg', 'Amoxicillin & Clavulanate', 'Augmentin 625', 'TABLET', '625mg', 'GSK', 'H1', TRUE),
    ('66666666-6666-6666-6666-666666666603', 'Pantoprazole 40mg', 'Pantoprazole Sodium', 'Pan 40', 'TABLET', '40mg', 'Alkem', 'H', TRUE),
    ('66666666-6666-6666-6666-666666666604', 'Metformin 500mg', 'Metformin Hydrochloride', 'Glycomet 500', 'TABLET', '500mg', 'USV', 'H', TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO drug_inventory (drug_id, batch_number, expiry_date, quantity_in_stock, unit_price, mrp, gst_percentage, reorder_level, location)
VALUES
    ('66666666-6666-6666-6666-666666666601', 'BAT-PAR-2026', '2028-12-31', 1000, 30.00, 35.00, 12.00, 100, 'Rack A-1'),
    ('66666666-6666-6666-6666-666666666602', 'BAT-AUG-2026', '2028-06-30', 500, 180.00, 220.00, 12.00, 50, 'Rack A-2'),
    ('66666666-6666-6666-6666-666666666603', 'BAT-PAN-2026', '2028-11-30', 800, 110.00, 130.00, 12.00, 50, 'Rack B-1')
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------------------
-- 6. Demo Registered Patient (with UHID & ABHA)
-- ----------------------------------------------------------------------------
INSERT INTO patients (
    id, registration_number, abha_id, abha_address, first_name, last_name, 
    date_of_birth, gender, phone, email, city, state, pincode, blood_group, is_deleted
)
VALUES (
    '77777777-7777-7777-7777-777777777701',
    'UHID-202611-0001',
    '91-1234-5678-9012',
    'rohan.verma@abdm',
    'Rohan',
    'Verma',
    '1995-04-20',
    'MALE',
    '9876543210',
    'rohan.verma@example.com',
    'Bengaluru',
    'Karnataka',
    '560001',
    'O+',
    FALSE
)
ON CONFLICT (registration_number) DO NOTHING;

-- DPDP Consent Record
INSERT INTO consents (
    patient_id, consent_type, purpose, data_categories, granted_to, status, granted_at
)
VALUES (
    '77777777-7777-7777-7777-777777777701',
    'ABDM_LINK',
    'Care Context Linking & Consultation Records Exchange',
    '["demographics", "clinical", "prescriptions"]'::jsonb,
    'HMS Platform',
    'GRANTED',
    NOW()
)
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------------------
-- 7. Demo OPD Encounter Queue Token ("Ticket")
-- ----------------------------------------------------------------------------
INSERT INTO encounters (
    id, patient_id, doctor_id, encounter_type, status, token_number,
    appointment_time, check_in_time, department, room_number, chief_complaint, priority
)
VALUES (
    '88888888-8888-8888-8888-888888888801',
    '77777777-7777-7777-7777-777777777701',
    '22222222-2222-2222-2222-222222222221',
    'OPD',
    'CHECKED_IN',
    101,
    NOW(),
    NOW(),
    'General Medicine',
    'Room 104',
    'High fever and persistent cough for 3 days',
    'NORMAL'
)
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------------------
-- 8. NABH Clinical Incident Reports / Safety Tickets (with RCA / CAPA)
-- ----------------------------------------------------------------------------
INSERT INTO incident_reports (
    id, incident_number, incident_type, severity, title, description, location,
    incident_date, reported_by, root_cause, corrective_action, status
)
VALUES
    (
        '99999999-9999-9999-9999-999999999901',
        'INC-202611-0001',
        'MEDICATION_ERROR',
        'NEAR_MISS',
        'Near-miss sound-alike drug selection prevented at dispensing',
        'Staff intercepted Metformin instead of Metoprolol prescription before delivery to patient',
        'Central Pharmacy Counter B',
        NOW() - INTERVAL '2 days',
        '22222222-2222-2222-2222-222222222226',
        'Sound-alike look-alike (LASA) drugs stored adjacent to each other on Shelf A',
        'Separated LASA medicines and affixed prominent color-coded Tall Man lettering warning labels',
        'CLOSED'
    ),
    (
        '99999999-9999-9999-9999-999999999902',
        'INC-202611-0002',
        'FALL',
        'MINOR',
        'Patient slip in semi-private ward washroom',
        'Elderly patient slipped on wet floor while ambulating without call-bell assistance',
        'Semi-Private Ward 3 Bathroom',
        NOW() - INTERVAL '1 day',
        '22222222-2222-2222-2222-222222222228',
        'Water spill from cleaning with missing caution wet-floor cone sign',
        'Installed high-traction anti-slip mats, additional grab bars, and mandatory wet floor signage',
        'ACTION_TAKEN'
    ),
    (
        '99999999-9999-9999-9999-999999999903',
        'INC-202611-0003',
        'EQUIPMENT',
        'NEAR_MISS',
        'Diagnostic Barcode Scanner Latency',
        'Phlebotomy handheld barcode scanner intermittently failing to scan blood vial labels',
        'Pathology Sample Collection Desk',
        NOW(),
        '22222222-2222-2222-2222-222222222224',
        'Low battery and dirty optical lens on wireless barcode unit',
        'Replaced scanner optical protective shield and docked in fast-charging cradle',
        'REPORTED'
    )
ON CONFLICT (incident_number) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 9. Historical Quality Measurements (Evaluating Compliance Against SLAs)
-- ----------------------------------------------------------------------------
INSERT INTO quality_measurements (
    indicator_id, period_start, period_end, numerator_value, denominator_value, calculated_value, recorded_by, notes
)
VALUES
    (
        '33333333-3333-3333-3333-333333333301',
        CURRENT_DATE - INTERVAL '30 days',
        CURRENT_DATE,
        985.00,
        1000.00,
        98.50,
        '11111111-1111-1111-1111-111111111111',
        'Emergency triage SLA achieved 98.5% compliance against 98.0% target.'
    ),
    (
        '33333333-3333-3333-3333-333333333302',
        CURRENT_DATE - INTERVAL '30 days',
        CURRENT_DATE,
        480.00,
        500.00,
        96.00,
        '11111111-1111-1111-1111-111111111111',
        'Lab turnaround SLA achieved 96.0% compliance against 95.0% target.'
    ),
    (
        '33333333-3333-3333-3333-333333333307',
        CURRENT_DATE - INTERVAL '30 days',
        CURRENT_DATE,
        920.00,
        1000.00,
        92.00,
        '11111111-1111-1111-1111-111111111111',
        'WHO Hand Hygiene compliance achieved 92.0% compliance against 90.0% benchmark.'
    )
ON CONFLICT DO NOTHING;

