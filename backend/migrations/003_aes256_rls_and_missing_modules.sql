-- HMS 003: encryption metadata, tenant isolation and missing registry/workflow tables.
-- Idempotent; apply after migrations/002_abdm_v3_exit_compliance.sql.
BEGIN;

CREATE TABLE IF NOT EXISTS hospitals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  code VARCHAR(80) UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add tenant ownership without rewriting prior migrations. Existing single-hospital
-- installations are assigned to a stable default hospital before RLS is enabled.
DO $$ DECLARE t TEXT; BEGIN
  FOREACH t IN ARRAY ARRAY['users','patients','encounters','clinical_notes','consents',
    'wards','beds','admissions','drugs','drug_inventory','prescriptions','prescription_items','dispensings',
    'lab_tests','lab_orders','lab_results','radiology_orders','radiology_reports','bills','bill_items',
    'payments','quality_indicators','quality_measurements','incident_reports','audit_logs',
    'abdm_share_profiles','abdm_care_context_links','abdm_consent_artefacts','abdm_transaction_logs']
  LOOP
    IF to_regclass(t) IS NOT NULL THEN
      EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS hospital_id UUID REFERENCES hospitals(id)', t);
      EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I (hospital_id)', 'idx_'||t||'_hospital_id', t);
    END IF;
  END LOOP;
END $$;

ALTER TABLE users ADD COLUMN IF NOT EXISTS tokens_valid_after TIMESTAMPTZ NULL;

INSERT INTO hospitals(name, code) VALUES ('Default Hospital', 'default') ON CONFLICT (code) DO NOTHING;
CREATE OR REPLACE FUNCTION hms_default_hospital_id() RETURNS UUID LANGUAGE SQL STABLE AS $$
  SELECT id FROM hospitals WHERE code='default' LIMIT 1
$$;
CREATE OR REPLACE FUNCTION hms_current_hospital_id() RETURNS UUID LANGUAGE SQL STABLE AS $$
  SELECT COALESCE(NULLIF(current_setting('app.hospital_id', true), '')::uuid, hms_default_hospital_id())
$$;

DO $$ DECLARE t TEXT; BEGIN
  FOREACH t IN ARRAY ARRAY['users','patients','encounters','clinical_notes','consents',
    'wards','beds','admissions','drugs','drug_inventory','prescriptions','prescription_items','dispensings',
    'lab_tests','lab_orders','lab_results','radiology_orders','radiology_reports','bills','bill_items',
    'payments','quality_indicators','quality_measurements','incident_reports','audit_logs',
    'abdm_share_profiles','abdm_care_context_links','abdm_consent_artefacts','abdm_transaction_logs']
  LOOP
    IF to_regclass(t) IS NOT NULL THEN
      IF t = 'abdm_transaction_logs' AND EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid = 'abdm_transaction_logs'::regclass AND tgname = 'trg_abdm_txn_logs_no_update') THEN
        EXECUTE 'ALTER TABLE abdm_transaction_logs DISABLE TRIGGER trg_abdm_txn_logs_no_update';
      END IF;
      -- The security migration may already have installed the append-only
      -- audit trigger. Disable it only for this one-time tenant backfill;
      -- the trigger is immediately restored below in the same transaction.
      IF t = 'audit_logs' AND EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid = 'audit_logs'::regclass AND tgname = 'trg_audit_logs_no_mutation') THEN
        EXECUTE 'ALTER TABLE audit_logs DISABLE TRIGGER trg_audit_logs_no_mutation';
      END IF;
      EXECUTE format('UPDATE %I SET hospital_id = hms_default_hospital_id() WHERE hospital_id IS NULL', t);
      IF t = 'audit_logs' AND EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid = 'audit_logs'::regclass AND tgname = 'trg_audit_logs_no_mutation') THEN
        EXECUTE 'ALTER TABLE audit_logs ENABLE TRIGGER trg_audit_logs_no_mutation';
      END IF;
      IF t = 'abdm_transaction_logs' AND EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid = 'abdm_transaction_logs'::regclass AND tgname = 'trg_abdm_txn_logs_no_update') THEN
        EXECUTE 'ALTER TABLE abdm_transaction_logs ENABLE TRIGGER trg_abdm_txn_logs_no_update';
      END IF;
      EXECUTE format('ALTER TABLE %I ALTER COLUMN hospital_id SET DEFAULT hms_current_hospital_id()', t);
      IF t <> 'users' THEN
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
        EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I', t);
        EXECUTE format('CREATE POLICY tenant_isolation ON %I USING (hospital_id = hms_current_hospital_id()) WITH CHECK (hospital_id = hms_current_hospital_id())', t);
      END IF;
    END IF;
  END LOOP;
END $$;

CREATE TABLE IF NOT EXISTS hfr_facilities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), hospital_id UUID NOT NULL REFERENCES hospitals(id),
  hfr_id VARCHAR(100) UNIQUE, facility_name VARCHAR(255) NOT NULL, facility_type VARCHAR(100),
  bridge_code VARCHAR(100), address JSONB NOT NULL DEFAULT '{}', registry_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
  synced_at TIMESTAMPTZ, source_payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), is_deleted BOOLEAN NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS hpr_practitioners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), hospital_id UUID NOT NULL REFERENCES hospitals(id),
  hpr_id VARCHAR(100) UNIQUE, user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  practitioner_name VARCHAR(255) NOT NULL, registration_number VARCHAR(100), bridge_code VARCHAR(100),
  specialties JSONB NOT NULL DEFAULT '[]', registry_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
  synced_at TIMESTAMPTZ, source_payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), is_deleted BOOLEAN NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS referrals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), hospital_id UUID NOT NULL REFERENCES hospitals(id),
  patient_id UUID NOT NULL REFERENCES patients(id), encounter_id UUID REFERENCES encounters(id),
  referral_type VARCHAR(30) NOT NULL DEFAULT 'INTERNAL', source_department VARCHAR(100), target_department VARCHAR(100),
  target_facility_id UUID REFERENCES hfr_facilities(id), practitioner_id UUID REFERENCES hpr_practitioners(id),
  reason TEXT NOT NULL, clinical_summary JSONB NOT NULL DEFAULT '{}', status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
  abdm_request_id VARCHAR(100), referred_at TIMESTAMPTZ, responded_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), is_deleted BOOLEAN NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS insurance_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), hospital_id UUID NOT NULL REFERENCES hospitals(id),
  patient_id UUID NOT NULL REFERENCES patients(id), payer_code VARCHAR(100), payer_name VARCHAR(255) NOT NULL,
  policy_number_encrypted TEXT, member_id_encrypted TEXT, coverage JSONB NOT NULL DEFAULT '{}',
  valid_from DATE, valid_to DATE, status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), is_deleted BOOLEAN NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS insurance_claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), hospital_id UUID NOT NULL REFERENCES hospitals(id),
  policy_id UUID NOT NULL REFERENCES insurance_policies(id), patient_id UUID NOT NULL REFERENCES patients(id),
  encounter_id UUID REFERENCES encounters(id), claim_number VARCHAR(100) UNIQUE, preauth_reference VARCHAR(100),
  lifecycle_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT', requested_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
  approved_amount NUMERIC(12,2), currency CHAR(3) NOT NULL DEFAULT 'INR', nhcx_payload JSONB NOT NULL DEFAULT '{}',
  submitted_at TIMESTAMPTZ, adjudicated_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), is_deleted BOOLEAN NOT NULL DEFAULT false
);

DO $$ DECLARE t TEXT; BEGIN
  FOREACH t IN ARRAY ARRAY['hfr_facilities','hpr_practitioners','referrals','insurance_policies','insurance_claims'] LOOP
    EXECUTE format('ALTER TABLE %I ALTER COLUMN hospital_id SET DEFAULT hms_current_hospital_id()', t);
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I', t);
    EXECUTE format('CREATE POLICY tenant_isolation ON %I USING (hospital_id = hms_current_hospital_id()) WITH CHECK (hospital_id = hms_current_hospital_id())', t);
  END LOOP;
END $$;

CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
RETURNS TRIGGER AS $$ BEGIN
  RAISE EXCEPTION 'audit_logs is strictly append-only';
END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_audit_logs_no_mutation ON audit_logs;
CREATE TRIGGER trg_audit_logs_no_mutation BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();

COMMIT;
