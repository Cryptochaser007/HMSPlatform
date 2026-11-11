"""Central Router: aggregates all API v1 module routers."""

from fastapi import APIRouter

from app.abdm.callbacks import router as abdm_callbacks_router
from app.api.v1.abdm import router as abdm_router
from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.clinical import router as clinical_router
from app.api.v1.encounters import router as encounters_router
from app.api.v1.laboratory import router as lab_router
from app.api.v1.patients import router as patients_router
from app.api.v1.pharmacy import router as pharmacy_router
from app.api.v1.quality import router as quality_router
from app.api.v1.radiology import router as radiology_router
from app.api.v1.ward import router as ward_router

api_router = APIRouter()

# Authentication & Staff Management
api_router.include_router(auth_router)

# Patient Registration & Demographics (DPDP Act)
api_router.include_router(patients_router)

# OPD & IPD Workflow / Clinic Queues
api_router.include_router(encounters_router)

# Electronic Medical Records (EMR)
api_router.include_router(clinical_router)

# Pharmacy & Inventory
api_router.include_router(pharmacy_router)

# Laboratory Information System (LIS)
api_router.include_router(lab_router)

# Radiology & PACS
api_router.include_router(radiology_router)

# Billing & Financials
api_router.include_router(billing_router)

# Wards, Beds & Inpatient Admissions
api_router.include_router(ward_router)

# Quality & NABH Accreditation
api_router.include_router(quality_router)

# ABDM Ecosystem Endpoints
api_router.include_router(abdm_router)

# ABDM Webhook Callbacks
api_router.include_router(abdm_callbacks_router, prefix="/abdm")

