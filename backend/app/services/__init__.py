"""Central services registry."""

from app.services.auth_service import AuthService, auth_service
from app.services.billing_service import BillingService, billing_service
from app.services.clinical_service import ClinicalService, clinical_service
from app.services.encounter_service import EncounterService, encounter_service
from app.services.lab_service import LabService, lab_service
from app.services.patient_service import PatientService, patient_service
from app.services.pharmacy_service import PharmacyService, pharmacy_service
from app.services.quality_service import QualityService, quality_service
from app.services.radiology_service import RadiologyService, radiology_service
from app.services.ward_service import WardService, ward_service

__all__ = [
    "AuthService",
    "BillingService",
    "ClinicalService",
    "EncounterService",
    "LabService",
    "PatientService",
    "PharmacyService",
    "QualityService",
    "RadiologyService",
    "WardService",
    "auth_service",
    "billing_service",
    "clinical_service",
    "encounter_service",
    "lab_service",
    "patient_service",
    "pharmacy_service",
    "quality_service",
    "radiology_service",
    "ward_service",
]
