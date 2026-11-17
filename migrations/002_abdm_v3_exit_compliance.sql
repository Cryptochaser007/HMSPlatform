-- =============================================================================
-- Migration 002: ABDM v3 Sandbox Exit Compliance (M1 + M2 + M3) & WASA Audit
-- Target: PostgreSQL 15+ / Supabase
-- Idempotent: Safe to re-run without destroying existing records.
-- =============================================================================

BEGIN;

-- ── 1. M1: Extend `patients` table with ABHA v3 KYC verification metadata ────
ALTER TABLE patients
    ADD COLUMN IF NOT EXISTS abha_kyc_status VARCHAR(30) NOT NULL DEFAULT 'UNVERIFIED',
    ADD COLUMN IF NOT EXISTS abha_verified_at TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS idx_patients_abha_address
    ON patients (abha_address)
    WHERE abha_address IS NOT NULL;

-- ── 2. M1: ABHA QR Scan & Share Counter Check-in Queue ───────────────────────
CREATE TABLE IF NOT EXISTS abdm_share_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id          VARCHAR(100) NOT NULL UNIQUE,
    hip_id              VARCHAR(100) NOT NULL,
    counter_id          VARCHAR(100) NULL,
    token_number        VARCHAR(20) NOT NULL,
    abha_number         VARCHAR(50) NULL,
    abha_address        VARCHAR(255) NOT NULL,
    patient_name        VARCHAR(255) NOT NULL,
    gender              VARCHAR(20) NOT NULL,
    year_of_birth       INTEGER NULL,
    mobile_masked       VARCHAR(32) NULL,
    patient_id          UUID NULL REFERENCES patients(id) ON DELETE SET NULL,
    status              VARCHAR(30) NOT NULL DEFAULT 'PENDING_CHECKIN',
    expires_at          TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted          BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_abdm_share_profiles_status
    ON abdm_share_profiles (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_abdm_share_profiles_abha
    ON abdm_share_profiles (abha_address);

-- ── 3. M2: ABDM Care Context Links (Discovery & Linking Ledger) ──────────────
CREATE TABLE IF NOT EXISTS abdm_care_context_links (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id          UUID NULL REFERENCES patients(id) ON DELETE SET NULL,
    abha_address        VARCHAR(255) NOT NULL,
    patient_reference   VARCHAR(100) NOT NULL,
    care_context_ref    VARCHAR(100) NOT NULL,
    care_context_display VARCHAR(255) NOT NULL,
    link_ref_number     VARCHAR(100) NULL,
    transaction_id      VARCHAR(100) NULL,
    auth_mode           VARCHAR(30) NOT NULL DEFAULT 'MOBILE_OTP',
    linking_type        VARCHAR(30) NOT NULL DEFAULT 'USER_INITIATED', -- USER_INITIATED | HIP_INITIATED
    status              VARCHAR(30) NOT NULL DEFAULT 'PENDING',        -- PENDING | LINKED | FAILED
    linked_at           TIMESTAMPTZ NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted          BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_abdm_care_context_patient_ref UNIQUE (abha_address, care_context_ref)
);

CREATE INDEX IF NOT EXISTS idx_abdm_care_context_links_patient
    ON abdm_care_context_links (patient_id);

CREATE INDEX IF NOT EXISTS idx_abdm_care_context_links_link_ref
    ON abdm_care_context_links (link_ref_number);

-- ── 4. M2 & M3: Immutable ABDM Consent Artefacts Ledger ──────────────────────
CREATE TABLE IF NOT EXISTS abdm_consent_artefacts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consent_id          VARCHAR(100) NOT NULL UNIQUE,
    consent_request_id  VARCHAR(100) NULL,
    role                VARCHAR(10) NOT NULL CHECK (role IN ('HIP', 'HIU')),
    patient_abha        VARCHAR(255) NOT NULL,
    purpose_code        VARCHAR(50) NOT NULL DEFAULT 'CAREMGT',
    purpose_text        VARCHAR(255) NOT NULL DEFAULT 'Care Management',
    status              VARCHAR(30) NOT NULL DEFAULT 'REQUESTED'
                        CHECK (status IN ('REQUESTED', 'GRANTED', 'DENIED', 'REVOKED', 'EXPIRED')),
    hi_types            JSONB NOT NULL DEFAULT '[]'::jsonb,
    care_contexts       JSONB NOT NULL DEFAULT '[]'::jsonb,
    date_from           TIMESTAMPTZ NOT NULL,
    date_to             TIMESTAMPTZ NOT NULL,
    data_erase_at       TIMESTAMPTZ NOT NULL,
    hip_id              VARCHAR(100) NULL,
    hiu_id              VARCHAR(100) NULL,
    requester_name      VARCHAR(255) NULL,
    requester_user_id   UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    signature           TEXT NULL,
    signature_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    artefact_payload    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted          BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_abdm_consent_artefacts_patient
    ON abdm_consent_artefacts (patient_abha, role, status);

CREATE INDEX IF NOT EXISTS idx_abdm_consent_artefacts_request_id
    ON abdm_consent_artefacts (consent_request_id);

-- ── 5. WASA & NHA Evidence: Append-Only ABDM Transaction Logs ────────────────
CREATE TABLE IF NOT EXISTS abdm_transaction_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id          VARCHAR(100) NOT NULL,
    correlation_id      VARCHAR(100) NULL,
    direction           VARCHAR(16) NOT NULL CHECK (direction IN ('OUTBOUND', 'INBOUND')),
    abdm_env            VARCHAR(20) NOT NULL DEFAULT 'MOCK',
    x_cm_id             VARCHAR(50) NULL,
    http_method         VARCHAR(10) NOT NULL,
    endpoint            VARCHAR(500) NOT NULL,
    http_status         INTEGER NULL,
    payload_sha256      VARCHAR(64) NOT NULL,
    masked_summary      JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_code          VARCHAR(100) NULL,
    user_id             UUID NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted          BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_abdm_txn_logs_request_id
    ON abdm_transaction_logs (request_id);

CREATE INDEX IF NOT EXISTS idx_abdm_txn_logs_correlation_id
    ON abdm_transaction_logs (correlation_id);

CREATE INDEX IF NOT EXISTS idx_abdm_txn_logs_created_at
    ON abdm_transaction_logs (created_at DESC);

-- Enforce append-only immutability at the database engine level (CERT-In WASA)
CREATE OR REPLACE FUNCTION prevent_abdm_txn_log_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'abdm_transaction_logs is strictly append-only (WASA immutability control)';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_abdm_txn_logs_no_update ON abdm_transaction_logs;
CREATE TRIGGER trg_abdm_txn_logs_no_update
    BEFORE UPDATE OR DELETE ON abdm_transaction_logs
    FOR EACH ROW EXECUTE FUNCTION prevent_abdm_txn_log_mutation();

COMMIT;
