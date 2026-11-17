"""
ABDM v3 & v0.5 Environment-Driven Configuration and Endpoint Registry.

Controls execution mode strictly via ``ABDM_ENV`` (MOCK | SANDBOX | PRODUCTION)
and binds all NHA gateway, ABHA v3, X-CM-ID, bridge, and HFR facility settings
exclusively from environment variables (zero hardcoded credentials).
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ABDMMode(str, Enum):
    """Execution strategy for the ABDM Strategy/Adapter layer."""

    MOCK = "MOCK"
    SANDBOX = "SANDBOX"
    PRODUCTION = "PRODUCTION"


# Backward-compatible alias
ABDMEnvironment = ABDMMode


# ---------------------------------------------------------------------------
# Default base URLs by environment (overridable via ABDM_GATEWAY_URL / ABDM_ABHA_URL)
# ---------------------------------------------------------------------------
ABDM_GATEWAY_URLS: dict[ABDMMode, str] = {
    ABDMMode.MOCK: "https://dev.abdm.gov.in",
    ABDMMode.SANDBOX: "https://dev.abdm.gov.in",
    ABDMMode.PRODUCTION: "https://apis.abdm.gov.in",
}

ABDM_ABHA_URLS: dict[ABDMMode, str] = {
    ABDMMode.MOCK: "https://abhasbx.abdm.gov.in/abha/api/v3",
    ABDMMode.SANDBOX: "https://abhasbx.abdm.gov.in/abha/api/v3",
    ABDMMode.PRODUCTION: "https://abha.abdm.gov.in/abha/api/v3",
}

ABDM_TOKEN_PATHS: dict[ABDMMode, str] = {
    ABDMMode.MOCK: "/gateway/v0.5/sessions",
    ABDMMode.SANDBOX: "/gateway/v0.5/sessions",
    ABDMMode.PRODUCTION: "/gateway/v0.5/sessions",
}

# ---------------------------------------------------------------------------
# Service endpoint paths (ABDM v3 ABHA + v0.5/v3 HIE-CM Gateway)
# ---------------------------------------------------------------------------
ABDM_ENDPOINTS: dict[str, str] = {
    # Sessions (OAuth 2.0)
    "sessions_v05": "/gateway/v0.5/sessions",
    "sessions_v3": "/api/hiecm/gateway/v3/sessions",
    # M1: ABHA v3 Creation & Verification (relative to ABDM_ABHA_URL)
    "abha_aadhaar_generate_otp": "/enrollment/request/otp",
    "abha_aadhaar_verify_otp": "/enrollment/enrol/byAadhaar",
    "abha_aadhaar_create": "/enrollment/enrol/byAadhaar",
    "abha_mobile_generate_otp": "/profile/login/request/otp",
    "abha_mobile_verify_otp": "/profile/login/verify",
    "abha_mobile_create": "/enrollment/enrol/byMobile",
    "abha_address_search": "/phr/web/login/abha/search",
    "abha_profile": "/profile/account",
    "abha_search": "/phr/web/login/abha/search",
    # M1: Scan & Share (HIP Counter Check-in)
    "patient_share_on_share": "/gateway/v3/hip/patient-share/on-share",
    # HPR / HFR
    "hpr_verify": "/gateway/v1/doctors/verify",
    "hpr_search": "/gateway/v1/doctors/search",
    "hfr_register": "/gateway/v1/facility/register",
    "hfr_profile": "/gateway/v1/facility/{facility_id}",
    "hfr_update": "/gateway/v1/facility/{facility_id}",
    # M2: HIP Discovery & Linking (HIP -> Gateway)
    "on_discover": "/gateway/v0.5/care-contexts/on-discover",
    "on_link_init": "/gateway/v0.5/links/link/on-init",
    "on_link_confirm": "/gateway/v0.5/links/link/on-confirm",
    "hip_link_add_contexts": "/gateway/v0.5/links/context/add",
    "hip_consent_on_notify": "/gateway/v0.5/consents/hip/on-notify",
    "hip_hi_on_request": "/gateway/v0.5/health-information/hip/on-request",
    "hi_notify": "/gateway/v0.5/health-information/notify",
    # M3: HIU Consent Manager & Health Information Exchange
    "consent_request_init": "/gateway/v0.5/consent-requests/init",
    "consent_fetch": "/gateway/v0.5/consent-requests/{consent_id}",
    "hi_request": "/gateway/v0.5/health-information/cm/request",
    "hi_transfer": "/gateway/v0.5/health-information/transfer",
    "on_notify": "/gateway/v0.5/consents/hip/on-notify",
}

# ---------------------------------------------------------------------------
# FHIR R4 NRCeS Profiles
# ---------------------------------------------------------------------------
FHIR_RESOURCE_PROFILES: dict[str, str] = {
    "Patient": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Patient",
    "Practitioner": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Practitioner",
    "Organization": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Organization",
    "Encounter": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Encounter",
    "Condition": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Condition",
    "Observation": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Observation",
    "MedicationRequest": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/MedicationRequest",
    "DiagnosticReport": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/DiagnosticReportLab",
    "DocumentReference": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/DocumentReference",
    "OPConsultRecord": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/OPConsultRecord",
    "PrescriptionRecord": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/PrescriptionRecord",
    "DiagnosticReportRecord": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/DiagnosticReportRecord",
    "DischargeSummaryRecord": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/DischargeSummaryRecord",
    "DocumentBundle": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/DocumentBundle",
    "AllergyIntolerance": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/AllergyIntolerance",
    "Procedure": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Procedure",
}

HEALTH_INFO_TYPES: list[str] = [
    "OPConsultation",
    "Prescription",
    "DischargeSummary",
    "DiagnosticReport",
    "ImmunizationRecord",
    "HealthDocumentRecord",
    "WellnessRecord",
]

CODING_SYSTEMS: dict[str, str] = {
    "snomed": "http://snomed.info/sct",
    "loinc": "http://loinc.org",
    "icd10": "http://hl7.org/fhir/sid/icd-10",
    "rxnorm": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "ndhm_hiu": "https://ndhm.gov.in/hiu",
    "ndhm_hip": "https://ndhm.gov.in/hip",
}


class ABDMSettings(BaseSettings):
    """Environment-driven ABDM v3 configuration (no hardcoded credentials)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    abdm_env: ABDMMode = Field(
        default=ABDMMode.MOCK,
        description="ABDM execution mode: MOCK | SANDBOX | PRODUCTION",
    )
    abdm_gateway_url: Optional[str] = Field(
        default=None,
        description="NHA Gateway base URL (e.g. https://dev.abdm.gov.in)",
    )
    abdm_abha_url: Optional[str] = Field(
        default=None,
        description="ABHA v3 API base URL (e.g. https://abhasbx.abdm.gov.in/abha/api/v3)",
    )
    abdm_x_cm_id: str = Field(
        default="sbx",
        description="Consent Manager ID header X-CM-ID (sbx for Sandbox, abdm for Production)",
    )
    abdm_client_id: str = Field(default="", description="NHA OAuth2 Client ID")
    abdm_client_secret: str = Field(default="", description="NHA OAuth2 Client Secret")
    abdm_bridge_id: str = Field(default="", description="Registered ABDM Bridge ID")
    hfr_facility_id: str = Field(
        default="",
        description="Health Facility Registry (HFR) Facility ID",
    )
    abdm_hip_id: str = Field(default="", description="Registered HIP ID (defaults to HFR_FACILITY_ID)")
    abdm_hiu_id: str = Field(default="", description="Registered HIU ID (defaults to HFR_FACILITY_ID)")
    abdm_callback_base_url: str = Field(
        default="http://localhost:8000",
        description="Public HTTPS callback base URL registered with NHA Bridge",
    )
    abdm_webhook_secret: str = Field(
        default="",
        description="Shared secret / key for verifying NHA webhook signatures",
    )
    abdm_request_timeout: int = Field(default=30, ge=5, le=120)

    @field_validator("abdm_env", mode="before")
    @classmethod
    def normalize_env(cls, v: object) -> str:
        if isinstance(v, ABDMMode):
            return v.value
        raw = str(v or os.environ.get("ABDM_ENV", "MOCK")).strip().upper()
        if raw in ("MOCK", "SANDBOX", "PRODUCTION"):
            return raw
        return "MOCK"

    # -- Convenience properties (preserving backward compatibility) -----------

    @property
    def environment(self) -> ABDMMode:
        return self.abdm_env

    @property
    def client_id(self) -> str:
        return self.abdm_client_id

    @property
    def client_secret(self) -> str:
        return self.abdm_client_secret

    @property
    def x_cm_id(self) -> str:
        return self.abdm_x_cm_id or ("abdm" if self.abdm_env == ABDMMode.PRODUCTION else "sbx")

    @property
    def bridge_id(self) -> str:
        return self.abdm_bridge_id

    @property
    def hip_id(self) -> str:
        return self.abdm_hip_id or self.hfr_facility_id or "HMS_HIP_SANDBOX"

    @property
    def hiu_id(self) -> str:
        return self.abdm_hiu_id or self.hfr_facility_id or "HMS_HIU_SANDBOX"

    @property
    def callback_base_url(self) -> str:
        return self.abdm_callback_base_url.rstrip("/")

    @property
    def request_timeout(self) -> int:
        return self.abdm_request_timeout

    @property
    def gateway_url(self) -> str:
        return (self.abdm_gateway_url or ABDM_GATEWAY_URLS[self.abdm_env]).rstrip("/")

    @property
    def abha_url(self) -> str:
        return (self.abdm_abha_url or ABDM_ABHA_URLS[self.abdm_env]).rstrip("/")

    @property
    def token_url(self) -> str:
        return f"{self.gateway_url}{ABDM_TOKEN_PATHS[self.abdm_env]}"

    @property
    def callback_urls(self) -> dict[str, str]:
        base = self.callback_base_url
        return {
            "patient_share": f"{base}/api/v1/abdm/v3/hip/patient-share",
            "discover": f"{base}/api/v1/abdm/v0.5/care-contexts/discover",
            "link_init": f"{base}/api/v1/abdm/v0.5/links/link/init",
            "link_confirm": f"{base}/api/v1/abdm/v0.5/links/link/confirm",
            "hip_consent_notify": f"{base}/api/v1/abdm/v0.5/consents/hip/notify",
            "hip_hi_request": f"{base}/api/v1/abdm/v0.5/health-information/hip/request",
            "hiu_consent_notify": f"{base}/api/v1/abdm/v0.5/consents/hiu/notify",
            "hi_transfer": f"{base}/api/v1/abdm/v0.5/health-information/transfer",
        }

    def get_endpoint(self, key: str, **path_params: str) -> str:
        path = ABDM_ENDPOINTS[key]
        if path_params:
            path = path.format(**path_params)
        return path

    def public_status(self) -> dict:
        """Return safe, non-sensitive ABDM integration status (zero secrets)."""
        has_creds = bool(self.abdm_client_id and self.abdm_client_secret)
        return {
            "abdm_env": self.abdm_env.value,
            "gateway_url": self.gateway_url,
            "abha_url": self.abha_url,
            "x_cm_id": self.x_cm_id,
            "hfr_facility_id": self.hfr_facility_id or "NOT_CONFIGURED",
            "bridge_id_configured": bool(self.abdm_bridge_id),
            "credentials_configured": has_creds,
            "access_status": (
                "SIMULATED_MOCK"
                if self.abdm_env == ABDMMode.MOCK
                else ("CONFIGURED" if has_creds else "PENDING_CREDENTIALS")
            ),
        }


@lru_cache()
def get_abdm_settings() -> ABDMSettings:
    """Return cached ABDMSettings instance."""
    return ABDMSettings()
