"""Central model registry — import all models for Alembic auto-detection."""

from app.models.user import User
from app.models.patient import Patient, Gender
from app.models.encounter import Encounter, EncounterType, EncounterStatus, EncounterPriority
from app.models.clinical import ClinicalNote, NoteType, Prescription, PrescriptionStatus, PrescriptionItem
from app.models.pharmacy import Drug, DrugType, DrugInventory, Dispensing
from app.models.laboratory import LabTest, LabOrder, LabOrderStatus, LabResult, LabPriority, ResultFlag
from app.models.radiology import RadiologyOrder, RadiologyReport, Modality, RadiologyOrderStatus
from app.models.billing import Bill, BillType, BillItem, BillItemType, Payment, PaymentMethod, PaymentStatus
from app.models.ward import Ward, WardType, Bed, BedStatus, BedType, Admission, AdmissionStatus, DischargeType
from app.models.quality import QualityIndicator, QualityMeasurement, IncidentReport, IncidentType, IncidentSeverity, IncidentStatus
from app.models.consent import Consent, ConsentType, ConsentStatus
from app.models.audit import AuditLog

__all__ = [
    "User",
    "Patient", "Gender",
    "Encounter", "EncounterType", "EncounterStatus", "EncounterPriority",
    "ClinicalNote", "NoteType", "Prescription", "PrescriptionStatus", "PrescriptionItem",
    "Drug", "DrugType", "DrugInventory", "Dispensing",
    "LabTest", "LabOrder", "LabOrderStatus", "LabResult", "LabPriority", "ResultFlag",
    "RadiologyOrder", "RadiologyReport", "Modality", "RadiologyOrderStatus",
    "Bill", "BillType", "BillItem", "BillItemType", "Payment", "PaymentMethod", "PaymentStatus",
    "Ward", "WardType", "Bed", "BedStatus", "BedType", "Admission", "AdmissionStatus", "DischargeType",
    "QualityIndicator", "QualityMeasurement", "IncidentReport", "IncidentType", "IncidentSeverity", "IncidentStatus",
    "Consent", "ConsentType", "ConsentStatus",
    "AuditLog",
]

