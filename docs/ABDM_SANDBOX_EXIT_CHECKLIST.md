# ABDM v3 Sandbox Exit & CERT-In WASA Compliance Checklist

> **System:** HMS Platform (FastAPI + PostgreSQL/Supabase + React/Vite)  
> **Scope:** ABDM v3 Milestone 1 (M1), Milestone 2 (M2 - HIP), Milestone 3 (M3 - HIU), and CERT-In Web Application Security Assessment (WASA) Safe-to-Host Readiness  
> **Adapter Mode Control:** `ABDM_ENV` = `MOCK` | `SANDBOX` | `PRODUCTION`

---

## 1. Environment Configuration & Switchover Matrix

Zero secrets or NHA credentials are hardcoded in source control. Configure the following environment variables in `.env` (local/Docker) or Vercel/Kubernetes secret stores:

| Variable | `MOCK` (Dry-Run) | `SANDBOX` (NHA Sandbox Exit) | `PRODUCTION` (Go-Live) |
|---|---|---|---|
| `ABDM_ENV` | `MOCK` | `SANDBOX` | `PRODUCTION` |
| `ABDM_GATEWAY_URL` | `https://dev.abdm.gov.in` | `https://dev.abdm.gov.in` | `https://apis.abdm.gov.in` |
| `ABDM_ABHA_URL` | `https://abhasbx.abdm.gov.in/abha/api/v3` | `https://abhasbx.abdm.gov.in/abha/api/v3` | `https://abha.abdm.gov.in/abha/api/v3` |
| `ABDM_X_CM_ID` | `sbx` | `sbx` | `abdm` |
| `ABDM_CLIENT_ID` | *(empty)* | `<NHA Sandbox Client ID>` | `<NHA Prod Client ID>` |
| `ABDM_CLIENT_SECRET` | *(empty)* | `<NHA Sandbox Secret>` | `<NHA Prod Secret>` |
| `ABDM_BRIDGE_ID` | *(optional)* | `<Registered Bridge ID>` | `<Prod Bridge ID>` |
| `HFR_FACILITY_ID` | *(optional)* | `<HFR Sandbox Facility ID>` | `<HFR Live Facility ID>` |
| `ABDM_WEBHOOK_SECRET` | *(optional)* | `<Shared Webhook Key>` | `<Prod Webhook Key>` |
| `ABDM_CALLBACK_BASE_URL` | `http://localhost:8000` | `https://<public-sandbox-domain>` | `https://<prod-domain>` |

**Outbound Mandatory NHA Headers (`LiveABDMAdapter`):**
- `Authorization: Bearer <OAuth2 accessToken>` (auto-cached & refreshed via `POST /gateway/v0.5/sessions` 5 minutes prior to expiry)
- `X-CM-ID: <ABDM_X_CM_ID>`
- `REQUEST-ID: <UUIDv4>`
- `TIMESTAMP: <YYYY-MM-DDTHH:MM:SS.mmmZ>`
- `X-HIP-ID` / `X-HIU-ID` / `X-BRIDGE-ID`

---

## 2. Database Migration Verification

Execute [`migrations/002_abdm_v3_exit_compliance.sql`](../migrations/002_abdm_v3_exit_compliance.sql) against PostgreSQL/Supabase before running Sandbox Exit tests:

| Table / Schema Change | Purpose | Immutability / Indexing |
|---|---|---|
| `patients.abha_kyc_status`, `patients.abha_verified_at` | Stores ABHA v3 KYC status (`VERIFIED`/`UNVERIFIED`) and verification timestamp | Indexed on `abha_address` & `abha_id` |
| `abdm_share_profiles` | Stores M1 ABHA QR Scan & Share counter check-in profiles & OPD tokens | Indexed on `(status, created_at)` |
| `abdm_care_context_links` | Tracks M2 user-initiated & HIP-initiated care context links (`PENDING`/`LINKED`) | Unique on `(abha_address, care_context_ref)` |
| `abdm_consent_artefacts` | Stores M2 HIP & M3 HIU consent artefacts, HI types, date bounds & signature verification status | Unique on `consent_id` |
| `abdm_transaction_logs` | Append-only evidence log of every outbound/inbound ABDM call with SHA-256 hash & masked summary | PostgreSQL `BEFORE UPDATE OR DELETE` trigger enforces WASA immutability |

---

## 3. Milestone 1 (M1): ABHA v3 Creation, Verification & Scan-and-Share

| NHA Functional Test Case | Method & Endpoint | Implementation Module | Auth / Rate Limit | Expected Result |
|---|---|---|---|---|
| **M1-TC01:** Generate Aadhaar OTP (ABHA v3) | `POST /api/v1/abdm/abha/aadhaar/otp` | `app/abdm/abha_service.py` | 5 req / 60s | Returns `txnId`, masked mobile (`XXXXXX1234`), logs masked txn |
| **M1-TC02:** Verify Aadhaar OTP & Enrol ABHA | `POST /api/v1/abdm/abha/aadhaar/verify` | `app/abdm/abha_service.py` | 10 req / 60s | Returns 14-digit `ABHANumber`, `phrAddress`, KYC demographics |
| **M1-TC03:** Generate Mobile OTP (ABHA Login) | `POST /api/v1/abdm/abha/mobile/otp` | `app/abdm/abha_service.py` | 5 req / 60s | Returns `txnId` for mobile-based login/enrolment |
| **M1-TC04:** Verify Mobile OTP | `POST /api/v1/abdm/abha/mobile/verify` | `app/abdm/abha_service.py` | 10 req / 60s | Returns verified profile & token |
| **M1-TC05:** ABHA Address / Number Search | `POST /api/v1/abdm/abha/address/search` | `app/abdm/abha_service.py` | 20 req / 60s | Validates `@sbx`/`@abdm` or 14-digit format, returns `authMethods` |
| **M1-TC06:** Fetch ABHA Profile | `GET /api/v1/abdm/abha/{abha_id}/profile` | `app/abdm/abha_service.py` | 20 req / 60s | Returns verified demographic record |
| **M1-TC07:** Persist Verified ABHA onto Patient | `POST /api/v1/abdm/abha/link-patient` | `app/abdm/abha_service.py` | RBAC `ABDM_LINK` | Persists `abha_id`, `abha_address`, `abha_kyc_status='VERIFIED'`, `abha_verified_at` |
| **M1-TC08:** ABHA QR Scan & Share Counter Check-in | `POST /api/v1/abdm/v3/hip/patient-share` | `app/abdm/callbacks.py` | 60 req / 60s | HTTP `202 Accepted`, issues counter `TKN-xxx` (30m TTL), sends `on-share` callback |
| **M1-TC09:** View Live Scan & Share OPD Queue | `GET /api/v1/abdm/v3/hip/patient-share/queue` | `app/abdm/callbacks.py` | RBAC `PATIENT_READ` | Returns pending QR check-in profiles for 1-click reception onboarding |

---

## 4. Milestone 2 (M2): Health Information Provider (HIP) & FHIR R4 Engine

| NHA Functional Test Case | Method & Endpoint | Implementation Module | Verification / Output |
|---|---|---|---|
| **M2-TC01:** Care Context Discovery | `POST /api/v1/abdm/v0.5/care-contexts/discover` | `hip_service.on_discover` | Matches patient by ABHA ID/Address, returns local encounters via `on-discover` |
| **M2-TC02:** User-Initiated Link Init | `POST /api/v1/abdm/v0.5/links/link/init` | `hip_service.on_link_init` | Persists `PENDING` link in `abdm_care_context_links`, issues `LINK-...` via `on-init` |
| **M2-TC03:** User-Initiated Link Confirm | `POST /api/v1/abdm/v0.5/links/link/confirm` | `hip_service.on_link_confirm` | Validates OTP token, marks contexts `LINKED`, dispatches `on-confirm` |
| **M2-TC04:** HIP-Initiated Linking | `POST /api/v1/abdm/v0.5/links/context/add` | `hip_service.hip_add_care_contexts` | RBAC `ABDM_LINK`; pushes newly created OPD/IPD care contexts to ABDM CM |
| **M2-TC05:** Consent Notification (GRANTED/REVOKED/EXPIRED) | `POST /api/v1/abdm/v0.5/consents/hip/notify` | `hip_service.on_consent_notify` | Verifies `X-ABDM-Signature` (`fidelius.verify_nha_webhook_signature`), stores immutable artefact in `abdm_consent_artefacts`, sends `on-notify` |
| **M2-TC06:** Health Info Request & Fidelius Data Push | `POST /api/v1/abdm/v0.5/health-information/hip/request` | `hip_service.on_data_request` | Checks consent is `GRANTED`; sends `on-request`; builds NRCeS FHIR R4 Bundles (`OPConsultRecord`, `PrescriptionRecord`, `DiagnosticReportRecord`, `DischargeSummaryRecord`); encrypts with **Fidelius X25519 ECDH + HKDF-SHA256 + AES-256-GCM**; POSTs to `dataPushUrl`; dispatches delivery confirmation to `/v0.5/health-information/notify` |

### NRCeS FHIR R4 Document Bundle Profiles Implemented (`backend/app/utils/fhir.py`)
- `OPConsultRecord`: `https://nrces.in/ndhm/fhir/r4/StructureDefinition/OPConsultRecord`
- `PrescriptionRecord`: `https://nrces.in/ndhm/fhir/r4/StructureDefinition/PrescriptionRecord`
- `DiagnosticReportRecord`: `https://nrces.in/ndhm/fhir/r4/StructureDefinition/DiagnosticReportRecord`
- `DischargeSummaryRecord`: `https://nrces.in/ndhm/fhir/r4/StructureDefinition/DischargeSummaryRecord`
- Wrapper: `https://nrces.in/ndhm/fhir/r4/StructureDefinition/DocumentBundle`

---

## 5. Milestone 3 (M3): Health Information User (HIU) & Longitudinal Viewer

| NHA Functional Test Case | Method & Endpoint | Implementation Module | Verification / Output |
|---|---|---|---|
| **M3-TC01:** Initiate Consent Request | `POST /api/v1/abdm/hiu/consent/request` | `hiu_service.create_consent_request` | RBAC `ABDM_FETCH`; dispatches `/v0.5/consent-requests/init` with purpose, HI types & date bounds |
| **M3-TC02:** Receive Consent Approval/Revocation | `POST /api/v1/abdm/v0.5/consents/hiu/notify` | `hiu_service.on_consent_hiu_notify` | Verifies signature, updates `abdm_consent_artefacts` status (`GRANTED`/`DENIED`/`REVOKED`/`EXPIRED`) |
| **M3-TC03:** Request Encrypted Health Info | `POST /api/v1/abdm/hiu/health-info/fetch` | `hiu_service.fetch_health_info` | RBAC `ABDM_FETCH`; generates fresh ephemeral **Curve25519 (X25519)** keypair + 32-byte nonce, calls `/v0.5/health-information/cm/request` |
| **M3-TC04:** Receive & Decrypt FHIR R4 Push | `POST /api/v1/abdm/v0.5/health-information/transfer` | `hiu_service.on_health_information_transfer` | Decrypts entries with stored ephemeral private key via `fidelius.decrypt_fhir_bundle`, parses into timeline |
| **M3-TC05:** View Longitudinal Health Record in EMR | `GET /api/v1/abdm/hiu/records/{patient_abha}` & EMR UI Tab | `HIULongitudinalPanel.tsx` | Renders cross-hospital timeline (facilities, dates, clinicians, ICD-10 diagnoses, Rx, lab observations) |

---

## 6. CERT-In WASA & NDHM HDMP Safe-to-Host Security Controls

| Control ID | OWASP / CERT-In WASA Requirement | Implemented Control | Verification Location |
|---|---|---|---|
| **WASA-01** | **Secret & Credential Hygiene** | Zero hardcoded credentials, ABHA IDs, or tokens; all NHA keys loaded from environment variables | `backend/app/abdm/config.py`, `backend/.env.example` |
| **WASA-02** | **PII Redaction in Logs & Errors** | `PIIMaskingLogFilter` masks Aadhaar (`XXXX-XXXX-1234`), ABHA (`XX-XXXX-XXXX-1234`), mobile (`XXXXXX1234`), and strips secrets/OTPs/Bearer tokens in logs and HTTP error responses | `backend/app/core/wasa_security.py`, `backend/app/main.py` |
| **WASA-03** | **Verbose Error Suppression** | Production 500 handler returns opaque `request_id` only; stack traces never exposed unless `DEBUG=true` | `backend/app/main.py` |
| **WASA-04** | **HTTP Security Headers** | `SecurityHeadersMiddleware` enforces HSTS (`max-age=63072000; includeSubDomains; preload`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, strict CSP, `Referrer-Policy`, `Permissions-Policy`, `Cache-Control: no-store` on `/api/`, and strips `Server` header | `backend/app/core/wasa_security.py` |
| **WASA-05** | **Strict CORS Allowlisting** | Explicit allowlisted `CORS_ORIGINS`, explicit HTTP methods & headers (no `*` wildcards) | `backend/app/main.py` |
| **WASA-06** | **Authentication & Refresh Token Rotation** | Short-lived JWT access tokens (30 min), refresh token rotation blacklisting consumed `jti` on every exchange, Redis + in-memory fallback revocation store | `backend/app/core/security.py`, `backend/app/services/auth_service.py` |
| **WASA-07** | **Brute-Force & OTP Flooding Protection** | Sliding-window `RateLimiter` (Redis + fail-closed in-memory fallback) on `/auth/login`, `/auth/signup`, `/auth/refresh`, and all `/abdm/abha/*` OTP endpoints | `backend/app/core/dependencies.py`, `backend/app/api/v1/auth.py`, `backend/app/api/v1/abdm.py` |
| **WASA-08** | **Server-Side RBAC & Anti-IDOR** | FastAPI `require_permissions(...)` enforced server-side on every clinical, patient, ABDM, and audit route | `backend/app/core/security.py`, `backend/app/api/v1/*.py` |
| **WASA-09** | **Input Validation (SQLi / XSS)** | Parameterized SQLAlchemy ORM queries + strict Pydantic v2 regex/length validators rejecting dangerous characters | `backend/app/api/v1/abdm.py`, `backend/app/schemas/*.py` |
| **WASA-10** | **Immutable Cryptographic Audit Trail** | Every ABDM outbound & inbound transaction recorded in append-only `abdm_transaction_logs` (with PostgreSQL mutation-prevention trigger and `payload_sha256`), queryable via `GET /api/v1/abdm/transactions` (`AUDIT_READ`) | `migrations/002_abdm_v3_exit_compliance.sql`, `backend/app/abdm/client.py` |
| **WASA-11** | **Fidelius End-to-End Health Data Encryption** | Curve25519 (X25519) ephemeral ECDH + XOR-nonce HKDF-SHA256 + AES-256-GCM AEAD for HIP -> HIU FHIR R4 transfers | `backend/app/abdm/fidelius.py` |

---

## 7. Quick Postman / cURL Self-Assessment Verification Script (Dry-Run `ABDM_ENV=MOCK`)

```bash
# 1. Verify active ABDM adapter status & security headers
curl -i https://<your-host>/api/v1/abdm/status

# 2. M1: Test Aadhaar OTP generation & verification (rate limited)
curl -X POST https://<your-host>/api/v1/abdm/abha/aadhaar/otp \
  -H "Content-Type: application/json" \
  -d '{"aadhaar_number":"999988887777"}'

# 3. M1: Test ABHA QR Scan & Share counter webhook
curl -X POST https://<your-host>/api/v1/abdm/v3/hip/patient-share \
  -H "Content-Type: application/json" \
  -d '{
    "requestId": "req-qr-001",
    "intent": {"type": "PROFILE_SHARE"},
    "metaData": {"hipId": "HMS_HIP_SANDBOX", "context": "OPD-COUNTER-01"},
    "profile": {
      "patient": {
        "abhaNumber": "91-4829-1029-4721",
        "abhaAddress": "arun.kumar@sbx",
        "name": "Arun Kumar",
        "gender": "M",
        "yearOfBirth": 1991
      }
    }
  }'

# 4. M2: Test HIP Consent Notification + Encrypted FHIR R4 Data Push
curl -X POST https://<your-host>/api/v1/abdm/v0.5/consents/hip/notify \
  -H "Content-Type: application/json" \
  -d '{
    "requestId": "req-consent-001",
    "notification": {
      "consentId": "CONSENT-TEST-001",
      "status": "GRANTED",
      "consentDetail": {
        "patient": {"id": "arun.kumar@sbx"},
        "hiTypes": ["OPConsultation", "Prescription", "DiagnosticReport", "DischargeSummary"],
        "careContexts": [{"careContextReference": "ENC-001"}]
      }
    }
  }'

# 5. M3: Test HIU Consent Initiation & Fidelius-Decrypted Longitudinal Record (with Doctor JWT)
curl -X POST https://<your-host>/api/v1/abdm/hiu/consent/request \
  -H "Authorization: Bearer <DOCTOR_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_abha": "arun.kumar@sbx",
    "purpose": "Care Management",
    "purpose_code": "CAREMGT",
    "date_from": "2025-01-01T00:00:00Z",
    "date_to": "2026-12-31T23:59:59Z",
    "hi_types": ["OPConsultation", "Prescription", "DiagnosticReport", "DischargeSummary"]
  }'
```
