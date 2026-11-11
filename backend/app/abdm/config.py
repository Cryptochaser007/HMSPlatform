"""
ABDM-specific configuration and settings.

Manages all ABDM Gateway URLs, service endpoints, OAuth configuration,
callback URLs, and FHIR resource type mappings for the integration layer.
"""

from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class ABDMEnvironment(str, Enum):
    """ABDM environment selector."""

    SANDBOX = "sandbox"
    PRODUCTION = "production"


# ---------------------------------------------------------------------------
# Gateway base URLs
# ---------------------------------------------------------------------------
ABDM_GATEWAY_URLS: dict[ABDMEnvironment, str] = {
    ABDMEnvironment.SANDBOX: "https://dev.abdm.gov.in/gateway",
    ABDMEnvironment.PRODUCTION: "https://live.abdm.gov.in/gateway",
}

# ---------------------------------------------------------------------------
# Service endpoint paths (appended to the gateway base URL)
# ---------------------------------------------------------------------------
ABDM_ENDPOINTS = {
    # ABHA creation (Aadhaar flow)
    "abha_aadhaar_generate_otp": "/v1/registration/aadhaar/generateOtp",
    "abha_aadhaar_verify_otp": "/v1/registration/aadhaar/verifyOtp",
    "abha_aadhaar_create": "/v1/registration/aadhaar/createHealthIdWithPreVerified",
    # ABHA creation (Mobile flow)
    "abha_mobile_generate_otp": "/v1/registration/mobile/generateOtp",
    "abha_mobile_verify_otp": "/v1/registration/mobile/verifyOtp",
    "abha_mobile_create": "/v1/registration/mobile/createHealthId",
    # ABHA profile
    "abha_profile": "/v1/account/profile",
    "abha_search": "/v1/search/searchByHealthId",
    # Health Professional Registry
    "hpr_verify": "/v1/doctors/verify",
    "hpr_search": "/v1/doctors/search",
    # Health Facility Registry
    "hfr_register": "/v1/facility/register",
    "hfr_profile": "/v1/facility/{facility_id}",
    "hfr_update": "/v1/facility/{facility_id}",
    # Consent Manager
    "consent_request_init": "/v0.5/consent-requests/init",
    "consent_fetch": "/v0.5/consent-requests/{consent_id}",
    # Health Information Exchange
    "hi_request": "/v0.5/health-information/cm/request",
    "hi_transfer": "/v0.5/health-information/transfer",
    # Patient discovery & linking (HIP → Gateway)
    "on_discover": "/v0.5/care-contexts/on-discover",
    "on_link_init": "/v0.5/links/link/on-init",
    "on_link_confirm": "/v0.5/links/link/on-confirm",
    "on_notify": "/v0.5/consent-requests/on-notify",
}

# ---------------------------------------------------------------------------
# OAuth / token endpoint
# ---------------------------------------------------------------------------
ABDM_TOKEN_ENDPOINTS: dict[ABDMEnvironment, str] = {
    ABDMEnvironment.SANDBOX: "https://dev.abdm.gov.in/gateway/v0.5/sessions",
    ABDMEnvironment.PRODUCTION: "https://live.abdm.gov.in/gateway/v0.5/sessions",
}

# ---------------------------------------------------------------------------
# FHIR resource type → ABDM profile URL mapping
# ---------------------------------------------------------------------------
FHIR_RESOURCE_PROFILES: dict[str, str] = {
    "Patient": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Patient",
    "Encounter": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Encounter",
    "Condition": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Condition",
    "Observation": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Observation",
    "MedicationRequest": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/MedicationRequest",
    "DiagnosticReport": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/DiagnosticReport",
    "DocumentReference": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/DocumentReference",
    "Composition": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Composition",
    "Bundle": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Bundle",
    "AllergyIntolerance": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/AllergyIntolerance",
    "Procedure": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Procedure",
    "Immunization": "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Immunization",
}

# ---------------------------------------------------------------------------
# ABDM Health Information Types
# ---------------------------------------------------------------------------
HEALTH_INFO_TYPES = [
    "OPConsultation",
    "Prescription",
    "DischargeSummary",
    "DiagnosticReport",
    "ImmunizationRecord",
    "HealthDocumentRecord",
    "WellnessRecord",
]

# ---------------------------------------------------------------------------
# Coding system URIs
# ---------------------------------------------------------------------------
CODING_SYSTEMS = {
    "snomed": "http://snomed.info/sct",
    "loinc": "http://loinc.org",
    "icd10": "http://hl7.org/fhir/sid/icd-10",
    "rxnorm": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "ndhm_hiu": "https://ndhm.gov.in/hiu",
    "ndhm_hip": "https://ndhm.gov.in/hip",
}


class ABDMSettings(BaseSettings):
    """
    ABDM integration settings, loaded from environment variables.

    Environment variables:
        ABDM_ENVIRONMENT    – "sandbox" or "production" (default: sandbox)
        ABDM_CLIENT_ID      – OAuth2 client ID issued by ABDM
        ABDM_CLIENT_SECRET  – OAuth2 client secret
        ABDM_HIP_ID         – Registered HIP ID with ABDM
        ABDM_HIU_ID         – Registered HIU ID with ABDM
        ABDM_CALLBACK_BASE  – Base URL for ABDM gateway callbacks
        ABDM_REQUEST_TIMEOUT – HTTP request timeout in seconds (default: 30)
        ABDM_ENCRYPTION_KEY  – RSA public key for data encryption (optional)
    """

    model_config = {"env_prefix": "ABDM_"}

    environment: ABDMEnvironment = Field(
        default=ABDMEnvironment.SANDBOX,
        description="ABDM environment: sandbox or production",
    )
    client_id: str = Field(
        default="",
        description="OAuth2 client ID issued by ABDM",
    )
    client_secret: str = Field(
        default="",
        description="OAuth2 client secret issued by ABDM",
    )
    hip_id: str = Field(
        default="",
        description="Registered Health Information Provider ID",
    )
    hiu_id: str = Field(
        default="",
        description="Registered Health Information User ID",
    )
    callback_base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for ABDM gateway callbacks",
    )
    request_timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds",
    )
    encryption_key: Optional[str] = Field(
        default=None,
        description="RSA public key (PEM) for ABDM data encryption",
    )

    # -- derived properties ---------------------------------------------------

    @property
    def gateway_url(self) -> str:
        """Return the ABDM gateway base URL for the configured environment."""
        return ABDM_GATEWAY_URLS[self.environment]

    @property
    def token_url(self) -> str:
        """Return the OAuth2 token endpoint for the configured environment."""
        return ABDM_TOKEN_ENDPOINTS[self.environment]

    @property
    def callback_urls(self) -> dict[str, str]:
        """Return fully-qualified callback URLs for ABDM gateway registration."""
        base = self.callback_base_url.rstrip("/")
        return {
            "on_discover": f"{base}/abdm/v0.5/patients/on-discover",
            "on_link_init": f"{base}/abdm/v0.5/links/link/on-init",
            "on_link_confirm": f"{base}/abdm/v0.5/links/link/on-confirm",
            "on_consent_notify": f"{base}/abdm/v0.5/consent-requests/on-notify",
            "on_data_request": f"{base}/abdm/v0.5/health-information/request",
            "on_data_transfer": f"{base}/abdm/v0.5/health-information/transfer",
        }

    def get_endpoint(self, key: str, **path_params: str) -> str:
        """
        Build the full URL for an ABDM endpoint.

        Args:
            key: Endpoint key from ``ABDM_ENDPOINTS``.
            **path_params: Path parameter substitutions, e.g. facility_id="123".

        Returns:
            Fully-qualified endpoint URL.
        """
        path = ABDM_ENDPOINTS[key]
        if path_params:
            path = path.format(**path_params)
        return f"{self.gateway_url}{path}"

    @property
    def HIU_ID(self) -> str:
        """Uppercase alias for hiu_id."""
        return self.hiu_id

    @property
    def CALLBACK_BASE_URL(self) -> str:
        """Uppercase alias for callback_base_url."""
        return self.callback_base_url


@lru_cache()
def get_abdm_settings() -> ABDMSettings:
    """Return a cached ABDMSettings instance."""
    return ABDMSettings()
