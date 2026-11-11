"""
Role-Based Access Control (RBAC) definitions.

Defines roles, permissions, and the mapping between them for the
entire HMS platform.
"""

from enum import Enum
from typing import List, Set


class Role(str, Enum):
    """User roles across the hospital system."""

    SUPER_ADMIN = "SUPER_ADMIN"
    HOSPITAL_ADMIN = "HOSPITAL_ADMIN"
    DOCTOR = "DOCTOR"
    NURSE = "NURSE"
    PHARMACIST = "PHARMACIST"
    LAB_TECHNICIAN = "LAB_TECHNICIAN"
    RADIOLOGIST = "RADIOLOGIST"
    BILLING_CLERK = "BILLING_CLERK"
    FRONT_DESK = "FRONT_DESK"


class Permission(str, Enum):
    """Fine-grained permissions for every module operation."""

    # Patient management
    PATIENT_CREATE = "PATIENT_CREATE"
    PATIENT_READ = "PATIENT_READ"
    PATIENT_UPDATE = "PATIENT_UPDATE"
    PATIENT_DELETE = "PATIENT_DELETE"

    # EMR / Clinical
    EMR_CREATE = "EMR_CREATE"
    EMR_READ = "EMR_READ"
    EMR_UPDATE = "EMR_UPDATE"

    # Prescriptions
    PRESCRIPTION_CREATE = "PRESCRIPTION_CREATE"
    PRESCRIPTION_READ = "PRESCRIPTION_READ"
    PRESCRIPTION_UPDATE = "PRESCRIPTION_UPDATE"
    PRESCRIPTION_DISPENSE = "PRESCRIPTION_DISPENSE"

    # Laboratory
    LAB_ORDER_CREATE = "LAB_ORDER_CREATE"
    LAB_ORDER_READ = "LAB_ORDER_READ"
    LAB_RESULT_CREATE = "LAB_RESULT_CREATE"
    LAB_RESULT_UPDATE = "LAB_RESULT_UPDATE"
    LAB_RESULT_VERIFY = "LAB_RESULT_VERIFY"

    # Radiology
    RADIOLOGY_ORDER_CREATE = "RADIOLOGY_ORDER_CREATE"
    RADIOLOGY_VIEW = "RADIOLOGY_VIEW"
    RADIOLOGY_UPLOAD = "RADIOLOGY_UPLOAD"
    RADIOLOGY_REPORT = "RADIOLOGY_REPORT"

    # Billing & Payments
    BILLING_CREATE = "BILLING_CREATE"
    BILLING_READ = "BILLING_READ"
    BILLING_UPDATE = "BILLING_UPDATE"
    PAYMENT_RECEIVE = "PAYMENT_RECEIVE"

    # Pharmacy / Drug management
    PHARMACY_MANAGE = "PHARMACY_MANAGE"
    DRUG_INVENTORY_READ = "DRUG_INVENTORY_READ"
    DRUG_INVENTORY_MANAGE = "DRUG_INVENTORY_MANAGE"

    # Ward / Bed management
    WARD_MANAGE = "WARD_MANAGE"
    BED_MANAGE = "BED_MANAGE"
    ADMISSION_CREATE = "ADMISSION_CREATE"
    ADMISSION_UPDATE = "ADMISSION_UPDATE"
    ADMISSION_READ = "ADMISSION_READ"

    # Quality & Incidents
    QUALITY_MANAGE = "QUALITY_MANAGE"
    QUALITY_READ = "QUALITY_READ"
    INCIDENT_CREATE = "INCIDENT_CREATE"
    INCIDENT_MANAGE = "INCIDENT_MANAGE"

    # Admin & Reporting
    ADMIN_PANEL = "ADMIN_PANEL"
    USER_MANAGE = "USER_MANAGE"
    REPORT_VIEW = "REPORT_VIEW"
    REPORT_EXPORT = "REPORT_EXPORT"

    # Consent management
    CONSENT_MANAGE = "CONSENT_MANAGE"
    CONSENT_READ = "CONSENT_READ"

    # ABDM
    ABDM_LINK = "ABDM_LINK"
    ABDM_FETCH = "ABDM_FETCH"

    # Encounter
    ENCOUNTER_CREATE = "ENCOUNTER_CREATE"
    ENCOUNTER_READ = "ENCOUNTER_READ"
    ENCOUNTER_UPDATE = "ENCOUNTER_UPDATE"

    # Audit
    AUDIT_READ = "AUDIT_READ"


# ── Role → Permissions mapping ───────────────────────────────────────────

ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.SUPER_ADMIN: set(Permission),  # all permissions

    Role.HOSPITAL_ADMIN: {
        Permission.PATIENT_CREATE, Permission.PATIENT_READ, Permission.PATIENT_UPDATE,
        Permission.PATIENT_DELETE,
        Permission.EMR_READ,
        Permission.PRESCRIPTION_READ,
        Permission.LAB_ORDER_READ, Permission.LAB_RESULT_UPDATE,
        Permission.RADIOLOGY_VIEW,
        Permission.BILLING_CREATE, Permission.BILLING_READ, Permission.BILLING_UPDATE,
        Permission.PAYMENT_RECEIVE,
        Permission.PHARMACY_MANAGE, Permission.DRUG_INVENTORY_READ,
        Permission.DRUG_INVENTORY_MANAGE,
        Permission.WARD_MANAGE, Permission.BED_MANAGE,
        Permission.ADMISSION_CREATE, Permission.ADMISSION_UPDATE, Permission.ADMISSION_READ,
        Permission.QUALITY_MANAGE, Permission.QUALITY_READ,
        Permission.INCIDENT_CREATE, Permission.INCIDENT_MANAGE,
        Permission.ADMIN_PANEL, Permission.USER_MANAGE,
        Permission.REPORT_VIEW, Permission.REPORT_EXPORT,
        Permission.CONSENT_MANAGE, Permission.CONSENT_READ,
        Permission.ABDM_LINK, Permission.ABDM_FETCH,
        Permission.ENCOUNTER_CREATE, Permission.ENCOUNTER_READ, Permission.ENCOUNTER_UPDATE,
        Permission.AUDIT_READ,
    },

    Role.DOCTOR: {
        Permission.PATIENT_CREATE, Permission.PATIENT_READ, Permission.PATIENT_UPDATE,
        Permission.EMR_CREATE, Permission.EMR_READ, Permission.EMR_UPDATE,
        Permission.PRESCRIPTION_CREATE, Permission.PRESCRIPTION_READ,
        Permission.PRESCRIPTION_UPDATE,
        Permission.LAB_ORDER_CREATE, Permission.LAB_ORDER_READ,
        Permission.LAB_RESULT_CREATE,
        Permission.RADIOLOGY_ORDER_CREATE, Permission.RADIOLOGY_VIEW,
        Permission.BILLING_READ,
        Permission.DRUG_INVENTORY_READ,
        Permission.ADMISSION_CREATE, Permission.ADMISSION_UPDATE, Permission.ADMISSION_READ,
        Permission.QUALITY_READ,
        Permission.INCIDENT_CREATE,
        Permission.REPORT_VIEW,
        Permission.CONSENT_READ,
        Permission.ABDM_LINK, Permission.ABDM_FETCH,
        Permission.ENCOUNTER_CREATE, Permission.ENCOUNTER_READ, Permission.ENCOUNTER_UPDATE,
    },

    Role.NURSE: {
        Permission.PATIENT_READ, Permission.PATIENT_UPDATE,
        Permission.EMR_CREATE, Permission.EMR_READ, Permission.EMR_UPDATE,
        Permission.PRESCRIPTION_READ,
        Permission.LAB_ORDER_READ,
        Permission.RADIOLOGY_VIEW,
        Permission.DRUG_INVENTORY_READ,
        Permission.ADMISSION_READ, Permission.ADMISSION_UPDATE,
        Permission.BED_MANAGE,
        Permission.QUALITY_READ,
        Permission.INCIDENT_CREATE,
        Permission.CONSENT_READ,
        Permission.ENCOUNTER_READ, Permission.ENCOUNTER_UPDATE,
    },

    Role.PHARMACIST: {
        Permission.PATIENT_READ,
        Permission.PRESCRIPTION_READ, Permission.PRESCRIPTION_DISPENSE,
        Permission.PHARMACY_MANAGE,
        Permission.DRUG_INVENTORY_READ, Permission.DRUG_INVENTORY_MANAGE,
        Permission.BILLING_CREATE, Permission.BILLING_READ,
        Permission.PAYMENT_RECEIVE,
        Permission.INCIDENT_CREATE,
    },

    Role.LAB_TECHNICIAN: {
        Permission.PATIENT_READ,
        Permission.LAB_ORDER_READ,
        Permission.LAB_RESULT_CREATE, Permission.LAB_RESULT_UPDATE,
        Permission.LAB_RESULT_VERIFY,
        Permission.INCIDENT_CREATE,
        Permission.ENCOUNTER_READ,
    },

    Role.RADIOLOGIST: {
        Permission.PATIENT_READ,
        Permission.RADIOLOGY_VIEW, Permission.RADIOLOGY_UPLOAD,
        Permission.RADIOLOGY_REPORT, Permission.RADIOLOGY_ORDER_CREATE,
        Permission.INCIDENT_CREATE,
        Permission.ENCOUNTER_READ,
    },

    Role.BILLING_CLERK: {
        Permission.PATIENT_READ,
        Permission.BILLING_CREATE, Permission.BILLING_READ, Permission.BILLING_UPDATE,
        Permission.PAYMENT_RECEIVE,
        Permission.PRESCRIPTION_READ,
        Permission.LAB_ORDER_READ,
        Permission.RADIOLOGY_VIEW,
        Permission.REPORT_VIEW,
        Permission.ENCOUNTER_READ,
    },

    Role.FRONT_DESK: {
        Permission.PATIENT_CREATE, Permission.PATIENT_READ, Permission.PATIENT_UPDATE,
        Permission.ENCOUNTER_CREATE, Permission.ENCOUNTER_READ, Permission.ENCOUNTER_UPDATE,
        Permission.BILLING_CREATE, Permission.BILLING_READ,
        Permission.PAYMENT_RECEIVE,
        Permission.ADMISSION_CREATE, Permission.ADMISSION_READ,
        Permission.BED_MANAGE,
        Permission.CONSENT_MANAGE, Permission.CONSENT_READ,
        Permission.ABDM_LINK,
    },
}


def has_permission(role: Role, permission: Permission) -> bool:
    """Return True if *role* includes *permission*."""
    role_perms = ROLE_PERMISSIONS.get(role)
    if role_perms is None:
        return False
    return permission in role_perms


def has_any_permission(role: Role, permissions: List[Permission]) -> bool:
    """Return True if *role* includes **at least one** of *permissions*."""
    role_perms = ROLE_PERMISSIONS.get(role)
    if role_perms is None:
        return False
    return bool(role_perms & set(permissions))
