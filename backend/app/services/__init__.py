"""Central services registry."""

from app.services.auth_service import AuthService, auth_service
from app.services.patient_service import PatientService, patient_service
from app.services.encounter_service import EncounterService, encounter_service
from app.services.clinical_service import ClinicalService, clinical_service
from app.services.pharmacy_service import PharmacyService, pharmacy_service
from app.services.lab_service import LabService, lab_service
from app.services.radiology_service import RadiologyService, radiology_service
from app.services.billing_service import BillingService, billing_service
from app.services.ward_service import WardService, ward_service
from app.services.quality_service import QualityService, quality_service

__all__ = [
    "AuthService", "auth_service",
    "PatientService", "patient_service",
    "EncounterService", "encounter_service",
    "ClinicalService", "clinical_service",
    "PharmacyService", "pharmacy_service",
    "LabService", "lab_service",
    "RadiologyService", "radiology_service",
    "BillingService", "billing_service",
    "WardService", "ward_service",
    "QualityService", "quality_service",
]
