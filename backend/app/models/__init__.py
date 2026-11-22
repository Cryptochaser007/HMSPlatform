"""Central model registry — import all models for Alembic auto-detection."""

from app.models.abdm import (
    ABDMCareContextLink,
    ABDMConsentArtefact,
    ABDMShareProfile,
    ABDMTransactionLog,
)
from app.models.audit import AuditLog
from app.models.billing import (
    Bill,
    BillItem,
    BillItemType,
    BillType,
    Payment,
    PaymentMethod,
    PaymentStatus,
)
from app.models.clinical import (
    ClinicalNote,
    NoteType,
    Prescription,
    PrescriptionItem,
    PrescriptionStatus,
)
from app.models.consent import Consent, ConsentStatus, ConsentType
from app.models.encounter import Encounter, EncounterPriority, EncounterStatus, EncounterType
from app.models.laboratory import (
    LabOrder,
    LabOrderStatus,
    LabPriority,
    LabResult,
    LabTest,
    ResultFlag,
)
from app.models.patient import Gender, Patient
from app.models.pharmacy import Dispensing, Drug, DrugInventory, DrugType
from app.models.quality import (
    IncidentReport,
    IncidentSeverity,
    IncidentStatus,
    IncidentType,
    QualityIndicator,
    QualityMeasurement,
)
from app.models.radiology import Modality, RadiologyOrder, RadiologyOrderStatus, RadiologyReport
from app.models.registry import (
    HFRFacility,
    HPRPractitioner,
    InsuranceClaim,
    InsurancePolicy,
    Referral,
)
from app.models.tenant import Department, Hospital
from app.models.user import User
from app.models.ward import (
    Admission,
    AdmissionStatus,
    Bed,
    BedStatus,
    BedType,
    DischargeType,
    Ward,
    WardType,
)

__all__ = [
    "ABDMCareContextLink",
    "ABDMConsentArtefact",
    "ABDMShareProfile",
    "ABDMTransactionLog",
    "Admission",
    "AdmissionStatus",
    "AuditLog",
    "Bed",
    "BedStatus",
    "BedType",
    "Bill",
    "BillItem",
    "BillItemType",
    "BillType",
    "ClinicalNote",
    "Consent",
    "ConsentStatus",
    "ConsentType",
    "Department",
    "DischargeType",
    "Dispensing",
    "Drug",
    "DrugInventory",
    "DrugType",
    "Encounter",
    "EncounterPriority",
    "EncounterStatus",
    "EncounterType",
    "Gender",
    "HFRFacility",
    "HPRPractitioner",
    "Hospital",
    "IncidentReport",
    "IncidentSeverity",
    "IncidentStatus",
    "IncidentType",
    "InsuranceClaim",
    "InsurancePolicy",
    "LabOrder",
    "LabOrderStatus",
    "LabPriority",
    "LabResult",
    "LabTest",
    "Modality",
    "NoteType",
    "Patient",
    "Payment",
    "PaymentMethod",
    "PaymentStatus",
    "Prescription",
    "PrescriptionItem",
    "PrescriptionStatus",
    "QualityIndicator",
    "QualityMeasurement",
    "RadiologyOrder",
    "RadiologyOrderStatus",
    "RadiologyReport",
    "Referral",
    "ResultFlag",
    "User",
    "Ward",
    "WardType",
]

