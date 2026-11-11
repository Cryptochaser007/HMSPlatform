# 🏥 ABDM-Enabled Hospital Management System (HMS) for NABH Accreditation

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![ABDM Ready](https://img.shields.io/badge/ABDM-M1%20%7C%20M2%20%7C%20M3-orange.svg)](https://abdm.gov.in/)
[![NABH Tailored](https://img.shields.io/badge/NABH-5th%20Edition-red.svg)](https://nabh.co/)
[![DPDP Act](https://img.shields.io/badge/Compliance-DPDP%20%26%20DISHA-success.svg)](#security--compliance)

A cloud-native, enterprise-grade Hospital Management Software (HMS) built specifically to meet the digital requirements of the **Ayushman Bharat Digital Mission (ABDM)** and the clinical governance benchmarks of the **National Accreditation Board for Hospitals & Healthcare Providers (NABH 5th Edition)**.

---

## 📑 Table of Contents
1. [Core Modules](#-core-modules)
2. [Regulatory & Security Compliance](#-regulatory--security-compliance)
3. [Architecture & Tech Stack](#-architecture--tech-stack)
4. [ABDM Ecosystem Integration](#-abdm-ecosystem-integration)
5. [Directory Layout](#-directory-layout)
6. [Quick Start & Local Setup](#-quick-start--local-setup)
7. [Docker & Kubernetes Deployment](#-docker--kubernetes-deployment)
8. [API Documentation](#-api-documentation)

---

## 🌟 Core Modules

### 1. Patient Registration & Demographics
- **UHID Generation**: Auto-generates unique hospital identification numbers (`UHID-YYYYMMDD-XXXXX`).
- **ABHA Onboarding**: Seamless Aadhaar and Mobile OTP verification to link or create 14-digit ABHA IDs.
- **DPDP Consent Ledger**: Granular consent recording for medical treatment, data processing, and health record sharing.
- **Field-Level Encryption**: All PII (Name, Phone, Aadhaar, Address) encrypted at rest using AES-256 (Fernet).

### 2. OPD / IPD Clinical Workflows
- **Outpatient Clinic Queue**: Tokenized OPD queue with wait-time estimation and doctor assignment.
- **Appointment Scheduling**: Real-time slot availability engine for multi-speciality consultants.
- **Inpatient Admissions (IPD)**: Bed allocation, inter-ward transfers, and structured discharge processing.

### 3. Electronic Medical Records (EMR)
- **SOAP Notes**: Structured Subjective, Objective, Assessment, and Plan documentation.
- **Vitals Monitoring**: Temperature, BP (Systolic/Diastolic), Pulse, SpO2, Respiratory Rate, and auto-computed BMI.
- **E-Prescriptions**: Digital drug orders with dosage, route, frequency, and duration; ready for pharmacy fulfillment.
- **Immutable Clinical History**: Amendments create linked version chains preserving original records.

### 4. Pharmacy & Inventory Control
- **Indian Formulary Master**: Schedules H, H1, X classification, HSN codes, and generic mapping.
- **Batch Inventory**: Real-time stock tracking by batch number, expiry date, purchase price, and MRP.
- **Safety Alerts**: Automated triggers for low-stock reorder thresholds and near-expiry medications.
- **Dispensing Ledger**: Deducts stock directly against signed prescriptions.

### 5. Laboratory Information System (LIS)
- **Diagnostic Catalog**: Pre-configured test profiles (CBC, LFT, KFT, Lipid Profile, HbA1c, Urine Routine).
- **Phlebotomy Workflow**: Barcoded Sample ID generation on specimen collection.
- **Auto Abnormal Flagging**: Instant flagging (LOW, HIGH, CRITICAL) against age- and gender-specific reference ranges.
- **Pathologist Verification**: Multi-stage review and digital signing before report release.

### 6. Radiology (PACS & OHIF Viewer Integration)
- **Imaging Modalities**: X-Ray, CT, MRI, Ultrasound, Mammography, and PET order tracking.
- **PACS Integration**: Accession number generation and Orthanc DICOM Web server linkage.
- **Embedded OHIF Web Viewer**: Zero-footprint DICOM viewing directly embedded inside clinical charts.

### 7. Billing & Financial Management
- **Itemized Invoicing**: Automatic consolidation of consultations, procedures, lab assays, and bed days.
- **Flexible Payments**: Cash, Credit/Debit Cards, UPI, Net Banking, and TPA Insurance claims.
- **GST Compliance**: Item-level GST calculation and formal payment receipt generation (`RCP-YYYYMMDD-XXXXX`).

### 8. Quality & NABH Accreditation Management
- **Mandatory NABH Indicators**: Automated tracking of Surgical Site Infection (SSI), CAUTI, Medication Errors, Patient Falls, Hand Hygiene Compliance, and Average Length of Stay (ALOS).
- **Incident Reporting System**: Root Cause Analysis (RCA) and Corrective and Preventive Actions (CAPA) workflow for Sentinel Events and Near Misses.
- **Accreditation Dashboard**: Real-time audit dashboard comparing performance against NABH quality thresholds.

---

## 🔒 Regulatory & Security Compliance

### India Digital Personal Data Protection (DPDP) Act 2023
- **Purpose Limitation & Explicit Consent**: All processing requires structured consent artifacts.
- **Right to Erasure**: Soft-deletion pipeline that anonymizes and redacts PII data while preserving de-identified clinical counts for statutory reporting.

### DISHA (Digital Information Security in Healthcare Act) Guidelines
- **End-to-End Encryption**: 
  - **In Transit**: TLS 1.3 encryption across all API and gateway communication.
  - **At Rest**: AES-256 field-level Fernet symmetric encryption for demographic columns.
- **Immutable Audit Trail**: Append-only audit logger using **SHA-256 hash chains** (`hash(prev_hash + current_record)`). Every login, read, update, prescription, and note edit is cryptographically chained for tamper detection.
- **Role-Based Access Control (RBAC)**: Strict permission boundaries covering 9 roles (Super Admin, Hospital Admin, Doctor, Nurse, Pharmacist, Lab Technician, Radiologist, Billing Clerk, Front Desk).

---

## 🏗️ Architecture & Tech Stack

```
[ Frontend: React / TypeScript / Vite ]
                 │ (HTTPS / TLS 1.3)
                 ▼
[ Nginx Reverse Proxy / Ingress Controller ]
                 │
                 ▼
[ FastAPI Async Gateway (Python 3.12) ]
   ├── Auth & RBAC Middleware
   ├── Field Encryption Layer (Fernet AES-256)
   ├── Cryptographic Audit Engine (SHA-256 Chain)
   └── ABDM HIP/HIU M1-M3 Integration Layer
                 │
        ┌────────┴────────┐
        ▼                 ▼
[ PostgreSQL 16 ]    [ Redis 7 ]
  - Row Security       - Token Blacklist
  - JSONB FHIR Docs    - Sliding Rate Limiter
  - PII Encrypted      - Session Cache
```

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Backend API** | FastAPI 0.115 (Python 3.12) | High-performance asynchronous REST API |
| **Database** | PostgreSQL 16 + asyncpg | Relational data + JSONB document storage |
| **ORM** | SQLAlchemy 2.0 (Async) | Type-safe declarative database models |
| **Migrations**| Alembic | Automated schema evolution |
| **Caching/Queue**| Redis 7 | JWT blacklisting & sliding rate limiting |
| **PACS Server** | Orthanc DICOM Server | Open-source enterprise PACS archive |
| **Orchestration**| Docker Compose / Kubernetes | Containerized micro-service stack |

---

## 🇮🇳 ABDM Ecosystem Integration

1. **M1 (ABHA Creation & Verification)**:
   - Aadhaar OTP generation & verification.
   - Mobile OTP generation & verification.
   - Demographic profile retrieval and local patient linkage.
2. **M2 (Health Information Provider - HIP)**:
   - Patient discovery (`/v0.5/patients/on-discover`).
   - Care context linking (`/v0.5/links/link/on-confirm`).
   - FHIR R4 Bundle compilation and data transfer to ABDM Gateway.
3. **M3 (Health Information User - HIU)**:
   - Consent request generation (`/v0.5/consent-requests/init`).
   - Encrypted health data exchange with external healthcare institutions.

---

## 📁 Directory Layout

```
HMSPlatform/
├── backend/
│   ├── alembic/                # Database migrations
│   ├── app/
│   │   ├── abdm/               # ABDM Gateway, ABHA, HIP, HIU, HPR, HFR
│   │   ├── api/v1/             # Module REST endpoints (Auth, EMR, Billing, etc.)
│   │   ├── core/               # Security, RBAC, Encryption, Audit logger
│   │   ├── models/             # SQLAlchemy ORM models (20+ entities)
│   │   ├── schemas/            # Pydantic v2 validation models
│   │   ├── services/           # Encapsulated business logic services
│   │   ├── utils/              # FHIR R4 generators, Indian validators & helpers
│   │   └── main.py             # FastAPI entrypoint & middleware
│   ├── tests/                  # Pytest async test suite
│   ├── alembic.ini             # Alembic configuration
│   └── requirements.txt        # Pinned dependencies
├── docker/
│   ├── Dockerfile.backend      # Multi-stage production container
│   ├── Dockerfile.frontend     # Web client container
│   └── nginx.conf              # Production reverse proxy
├── k8s/                        # Production Kubernetes manifests
│   ├── backend-deployment.yaml
│   ├── postgres-statefulset.yaml
│   ├── ingress.yaml, hpa.yaml, network-policy.yaml, etc.
├── scripts/
│   ├── seed_data.py            # Master data seeder (Staff, Wards, Drugs, Tests)
│   ├── setup.sh                # Linux / macOS bootstrap
│   └── setup.ps1               # Windows PowerShell bootstrap
├── docker-compose.yml          # Local multi-container development environment
└── README.md
```

---

## 🚀 Quick Start & Local Setup

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Python 3.12+](https://www.python.org/)

### 1. Automated Setup (Recommended)
On Windows (PowerShell):
```powershell
.\scripts\setup.ps1
```

On Linux / macOS:
```bash
chmod +x ./scripts/setup.sh
./scripts/setup.sh
```

### 2. Manual Step-by-Step Setup
1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
2. Start the database and backing services:
   ```bash
   docker compose up -d db redis orthanc
   ```
3. Install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. Run master data seeding:
   ```bash
   python scripts/seed_data.py
   ```
5. Launch the backend API server:
   ```bash
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Default Credentials
- **Super Admin**: `admin@hms.local` | Password: `Admin@123`
- **OPD Doctor**: `dr.sharma@hms.local` | Password: `Staff@123`
- **Pharmacist**: `pharmacist@hms.local` | Password: `Staff@123`
- **Front Desk**: `frontdesk@hms.local` | Password: `Staff@123`

---

## 🚢 Docker & Kubernetes Deployment

### Full Docker Compose Stack
```bash
docker compose up -d --build
```
Access points:
- **API Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Database Administration (Adminer)**: [http://localhost:8080](http://localhost:8080)
- **Orthanc PACS Explorer**: [http://localhost:8042](http://localhost:8042)

### Kubernetes Production Cluster
Deploy to any CNCF-certified Kubernetes cluster (GKE, EKS, AKS):
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/network-policy.yaml
kubectl apply -f k8s/ingress.yaml
```

---

## 🧪 Testing

Execute automated unit and integration tests:
```bash
cd backend
pytest tests/ -v
```

