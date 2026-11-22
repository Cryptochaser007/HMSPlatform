-- Stage 1. Apply using the migration owner before deploying the application.
-- Existing hospital IDs and encrypted fields are preserved.
BEGIN;
CREATE TABLE IF NOT EXISTS hospitals (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name VARCHAR(255) NOT NULL,
 code VARCHAR(80) UNIQUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE hospitals
 ADD COLUMN IF NOT EXISTS slug VARCHAR(80),
 ADD COLUMN IF NOT EXISTS hfr_facility_id VARCHAR(100),
 ADD COLUMN IF NOT EXISTS hip_id VARCHAR(100),
 ADD COLUMN IF NOT EXISTS hiu_id VARCHAR(100),
 ADD COLUMN IF NOT EXISTS abdm_env VARCHAR(20) NOT NULL DEFAULT 'MOCK',
 ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(30) NOT NULL DEFAULT 'TRIAL',
 ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true,
 ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT false;
UPDATE hospitals SET slug = COALESCE(code, id::text) WHERE slug IS NULL;
INSERT INTO hospitals(name, code, slug)
 SELECT 'Demo General Hospital', 'default', 'demo-general-hospital'
 WHERE NOT EXISTS (SELECT 1 FROM hospitals WHERE code='default');
UPDATE hospitals SET name='Demo General Hospital', slug='demo-general-hospital' WHERE code='default';
ALTER TABLE hospitals ALTER COLUMN slug SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS hospitals_slug_unique ON hospitals(slug);
CREATE OR REPLACE FUNCTION hms_demo_hospital_id() RETURNS UUID
 LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT id FROM public.hospitals WHERE code='default' LIMIT 1
$$;
CREATE OR REPLACE FUNCTION hms_current_hospital_id() RETURNS UUID
 LANGUAGE sql STABLE AS $$
 SELECT NULLIF(current_setting('app.current_hospital_id', true), '')::uuid
$$;
CREATE TABLE IF NOT EXISTS departments (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 hospital_id UUID NOT NULL REFERENCES hospitals(id) DEFAULT hms_current_hospital_id(),
 name VARCHAR(100) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 is_deleted BOOLEAN NOT NULL DEFAULT false,
 UNIQUE(hospital_id,name)
);
ALTER TABLE users ADD COLUMN IF NOT EXISTS tokens_valid_after TIMESTAMPTZ,
 ADD COLUMN IF NOT EXISTS last_failed_login TIMESTAMPTZ;
-- Align legacy ORM-created role types with the unchanged Supabase schema.
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='user_role_enum') THEN
  CREATE TYPE user_role_enum AS ENUM ('SUPER_ADMIN','HOSPITAL_ADMIN','DOCTOR','NURSE',
   'PHARMACIST','LAB_TECHNICIAN','RADIOLOGIST','BILLING_CLERK','FRONT_DESK');
 END IF;
 IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public'
            AND table_name='users' AND column_name='role' AND udt_name<>'user_role_enum') THEN
  ALTER TABLE users ALTER COLUMN role TYPE user_role_enum USING role::text::user_role_enum;
 END IF;
END $$;
-- Extend all owned child tables as well, so direct child queries obey RLS.
DO $$
DECLARE t text; trigger_name text; enabled_triggers text[];
BEGIN
 FOREACH t IN ARRAY ARRAY['users','patients','encounters','clinical_notes','admissions',
 'prescriptions','prescription_items','lab_tests','lab_orders','lab_results',
 'radiology_orders','radiology_reports','bills','bill_items','payments','wards','beds',
 'drugs','drug_inventory','dispensings','quality_indicators','quality_measurements',
 'incident_reports','consents','abdm_share_profiles','abdm_care_context_links',
 'abdm_consent_artefacts','abdm_transaction_logs','audit_logs','hfr_facilities',
 'hpr_practitioners','referrals','insurance_policies','insurance_claims']
 LOOP
  IF to_regclass('public.'||t) IS NOT NULL THEN
   EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS hospital_id UUID REFERENCES hospitals(id)',t);
   -- Tenant metadata backfill only. Restore each previously enabled user trigger.
   SELECT array_agg(tgname::text) INTO enabled_triggers FROM pg_trigger
    WHERE tgrelid=to_regclass('public.'||t) AND NOT tgisinternal AND tgenabled='O';
   FOREACH trigger_name IN ARRAY COALESCE(enabled_triggers,ARRAY[]::text[])
   LOOP
    EXECUTE format('ALTER TABLE %I DISABLE TRIGGER %I',t,trigger_name);
   END LOOP;
   EXECUTE format('UPDATE %I SET hospital_id=hms_demo_hospital_id() WHERE hospital_id IS NULL',t);
   FOREACH trigger_name IN ARRAY COALESCE(enabled_triggers,ARRAY[]::text[])
   LOOP
    EXECUTE format('ALTER TABLE %I ENABLE TRIGGER %I',t,trigger_name);
   END LOOP;
   EXECUTE format('ALTER TABLE %I ALTER COLUMN hospital_id SET NOT NULL',t);
   EXECUTE format('ALTER TABLE %I ALTER COLUMN hospital_id SET DEFAULT hms_current_hospital_id()',t);
   EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I(hospital_id)','idx_'||t||'_hospital_id',t);
   EXECUTE format('CREATE UNIQUE INDEX IF NOT EXISTS %I ON %I(hospital_id,id)','uq_'||t||'_tenant_id',t);
   EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
   EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
   EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I',t);
   EXECUTE format('CREATE POLICY tenant_isolation ON %I USING
    (hospital_id=hms_current_hospital_id() OR current_setting(''app.is_superadmin'',true)=''true'')
    WITH CHECK (hospital_id=hms_current_hospital_id() OR current_setting(''app.is_superadmin'',true)=''true'')',t);
  END IF;
 END LOOP;
END $$;
-- Published demo credentials must never grant access to other hospitals.
UPDATE users SET role='HOSPITAL_ADMIN'
 WHERE email='admin@hms.local' AND hospital_id=hms_demo_hospital_id() AND role='SUPER_ADMIN';
-- The authentication lookup is constrained to the email supplied to login.
-- The application clears this context immediately after lookup.
DROP POLICY IF EXISTS login_lookup ON users;
CREATE POLICY login_lookup ON users FOR SELECT USING
 (email=NULLIF(current_setting('app.login_email',true),''));
ALTER TABLE hospitals ENABLE ROW LEVEL SECURITY;
ALTER TABLE hospitals FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON hospitals;
CREATE POLICY tenant_isolation ON hospitals USING
 (id=hms_current_hospital_id() OR current_setting('app.is_superadmin',true)='true')
 WITH CHECK (id=hms_current_hospital_id() OR current_setting('app.is_superadmin',true)='true');
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE departments FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON departments;
CREATE POLICY tenant_isolation ON departments USING
 (hospital_id=hms_current_hospital_id() OR current_setting('app.is_superadmin',true)='true')
 WITH CHECK (hospital_id=hms_current_hospital_id() OR current_setting('app.is_superadmin',true)='true');
-- Parent references must belong to the same hospital, even if their UUID is known.
DO $$
DECLARE fk record; constraint_name text;
BEGIN
 FOR fk IN
  SELECT c.conrelid::regclass AS child, c.confrelid::regclass AS parent,
         a.attname AS column_name, c.oid
  FROM pg_constraint c
  JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=c.conkey[1]
  WHERE c.contype='f' AND array_length(c.conkey,1)=1 AND a.attname<>'hospital_id'
   AND c.connamespace='public'::regnamespace
   AND EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid=c.conrelid AND attname='hospital_id')
   AND EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid=c.confrelid AND attname='hospital_id')
 LOOP
  constraint_name='stage1_tenant_fk_'||fk.oid;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid=fk.child AND conname=constraint_name) THEN
   EXECUTE format('ALTER TABLE %s ADD CONSTRAINT %I FOREIGN KEY(hospital_id,%I)
     REFERENCES %s(hospital_id,id)',fk.child,constraint_name,fk.column_name,fk.parent);
  END IF;
 END LOOP;
END $$;
-- Indicator codes repeat across hospitals.
ALTER TABLE quality_indicators DROP CONSTRAINT IF EXISTS quality_indicators_code_key;
DROP INDEX IF EXISTS ix_quality_indicators_code;
CREATE UNIQUE INDEX IF NOT EXISTS quality_indicators_tenant_code ON quality_indicators(hospital_id,code);
CREATE OR REPLACE FUNCTION prevent_audit_log_mutation() RETURNS trigger
 LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'audit_logs is strictly append-only'; END $$;
DROP TRIGGER IF EXISTS trg_audit_logs_no_mutation ON audit_logs;
CREATE TRIGGER trg_audit_logs_no_mutation BEFORE UPDATE OR DELETE ON audit_logs
 FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();
-- Trusted maintenance can use a separate database role, never the runtime login.
DO $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='hms_system') THEN
  CREATE ROLE hms_system NOLOGIN NOBYPASSRLS;
 END IF;
END $$;
GRANT USAGE ON SCHEMA public TO hms_system;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO hms_system;
DO $$ DECLARE t record; BEGIN
 FOR t IN SELECT tablename FROM pg_tables WHERE schemaname='public' AND rowsecurity LOOP
  EXECUTE format('DROP POLICY IF EXISTS system_access ON %I',t.tablename);
  EXECUTE format('CREATE POLICY system_access ON %I TO hms_system USING (true) WITH CHECK (true)',t.tablename);
 END LOOP;
END $$;
COMMIT;

