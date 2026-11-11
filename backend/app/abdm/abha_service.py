"""
ABHAService – ABHA (Ayushman Bharat Health Account) ID management.

Provides workflows for:
- Aadhaar-based ABHA creation (OTP verification)
- Mobile-based ABHA creation (OTP verification)
- ABHA profile retrieval and search
- Linking ABHA IDs to local patient records

The ABHA ID is a 14-digit unique identifier (format XX-XXXX-XXXX-XXXX)
that acts as a patient's digital health identity across India.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional
from uuid import UUID

# pyrefly: ignore[missing-import]
from pydantic import BaseModel, Field

from app.abdm.client import ABDMClient, ABDMError
from app.abdm.config import ABDM_ENDPOINTS

logger = logging.getLogger("abdm.abha")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ABHAProfile(BaseModel):
    """Represents an ABHA (Ayushman Bharat Health Account) profile."""

    health_id: str = Field(..., description="ABHA address (e.g. user@abdm)")
    health_id_number: str = Field(
        ..., description="14-digit ABHA number (XX-XXXX-XXXX-XXXX)"
    )
    name: str = Field(..., description="Full name as on Aadhaar")
    first_name: Optional[str] = Field(default=None)
    middle_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    gender: str = Field(..., description="M / F / O")
    year_of_birth: int = Field(..., ge=1900)
    month_of_birth: Optional[int] = Field(default=None, ge=1, le=12)
    day_of_birth: Optional[int] = Field(default=None, ge=1, le=31)
    address: Optional[str] = Field(default=None)
    district: Optional[str] = Field(default=None)
    state: Optional[str] = Field(default=None)
    pincode: Optional[str] = Field(default=None)
    mobile: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    profile_photo: Optional[str] = Field(
        default=None, description="Base64-encoded photo"
    )
    kycVerified: bool = Field(default=False, description="Whether KYC is verified")

    @property
    def date_of_birth(self) -> Optional[date]:
        """Return a ``date`` object if full DOB is available."""
        if self.month_of_birth and self.day_of_birth:
            return date(self.year_of_birth, self.month_of_birth, self.day_of_birth)
        return None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ABHAService:
    """
    Service layer for ABHA ID lifecycle management.

    ABHA creation flow (Aadhaar):
        1. ``generate_aadhaar_otp`` → sends OTP to Aadhaar-linked mobile
        2. ``verify_aadhaar_otp``   → verifies the OTP, returns pre-verified token
        3. ``create_abha_via_aadhaar`` → creates ABHA with profile data

    ABHA creation flow (Mobile):
        1. ``generate_mobile_otp``  → sends OTP to mobile number
        2. ``verify_mobile_otp``    → verifies the OTP
        3. ``create_abha_via_mobile`` → creates ABHA with profile data
    """

    def __init__(self, client: Optional[ABDMClient] = None) -> None:
        self._client = client or ABDMClient()

    # ------------------------------------------------------------------
    # Aadhaar-based ABHA creation
    # ------------------------------------------------------------------

    async def generate_aadhaar_otp(self, aadhaar_number: str) -> dict:
        """
        Initiate Aadhaar-based ABHA creation by generating an OTP.

        The ABDM gateway sends an OTP to the mobile number linked with
        the provided Aadhaar number.

        Args:
            aadhaar_number: 12-digit Aadhaar number.

        Returns:
            dict with ``txnId`` (transaction identifier for subsequent calls).

        Raises:
            ABDMError: If Aadhaar is invalid or OTP generation fails.
        """
        aadhaar_clean = aadhaar_number.replace(" ", "").replace("-", "")
        if len(aadhaar_clean) != 12 or not aadhaar_clean.isdigit():
            raise ABDMError(
                message="Aadhaar number must be exactly 12 digits",
                error_code="VALIDATION",
            )

        logger.info("Generating Aadhaar OTP for ABHA creation (masked: XXXX%s)", aadhaar_clean[-4:])

        result = await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["abha_aadhaar_generate_otp"],
            data={"aadhaar": aadhaar_clean},
        )
        logger.info("Aadhaar OTP sent, txnId=%s", result.get("txnId"))
        return result

    async def verify_aadhaar_otp(self, txn_id: str, otp: str) -> dict:
        """
        Verify the OTP received on the Aadhaar-linked mobile.

        Args:
            txn_id: Transaction ID from ``generate_aadhaar_otp``.
            otp: 6-digit OTP entered by the user.

        Returns:
            dict containing a pre-verified token for ABHA creation.

        Raises:
            ABDMError: If OTP is invalid or expired.
        """
        logger.info("Verifying Aadhaar OTP for txnId=%s", txn_id)

        result = await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["abha_aadhaar_verify_otp"],
            data={"txnId": txn_id, "otp": otp},
        )
        logger.info("Aadhaar OTP verified for txnId=%s", txn_id)
        return result

    async def create_abha_via_aadhaar(
        self, txn_id: str, profile_data: dict
    ) -> ABHAProfile:
        """
        Complete ABHA creation using a verified Aadhaar OTP session.

        Args:
            txn_id: Transaction ID from the OTP verification step.
            profile_data: Additional profile fields (e.g. email, preferred
                ABHA address).

        Returns:
            The created ABHAProfile.
        """
        logger.info("Creating ABHA via Aadhaar for txnId=%s", txn_id)

        payload = {"txnId": txn_id, **profile_data}
        result = await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["abha_aadhaar_create"],
            data=payload,
        )

        profile = self._parse_profile(result)
        logger.info("ABHA created: %s (%s)", profile.health_id, profile.health_id_number)
        return profile

    # ------------------------------------------------------------------
    # Mobile-based ABHA creation
    # ------------------------------------------------------------------

    async def generate_mobile_otp(self, mobile: str) -> dict:
        """
        Initiate mobile-based ABHA creation by generating an OTP.

        Args:
            mobile: 10-digit Indian mobile number.

        Returns:
            dict with ``txnId``.
        """
        mobile_clean = mobile.replace(" ", "").replace("-", "").replace("+91", "")
        if len(mobile_clean) != 10 or not mobile_clean.isdigit():
            raise ABDMError(
                message="Mobile number must be 10 digits",
                error_code="VALIDATION",
            )

        logger.info("Generating mobile OTP for ABHA creation (masked: XXXXXX%s)", mobile_clean[-4:])

        result = await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["abha_mobile_generate_otp"],
            data={"mobile": mobile_clean},
        )
        logger.info("Mobile OTP sent, txnId=%s", result.get("txnId"))
        return result

    async def verify_mobile_otp(self, txn_id: str, otp: str) -> dict:
        """
        Verify the OTP sent to the mobile number.

        Args:
            txn_id: Transaction ID from ``generate_mobile_otp``.
            otp: 6-digit OTP.

        Returns:
            dict with pre-verified token.
        """
        logger.info("Verifying mobile OTP for txnId=%s", txn_id)

        result = await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["abha_mobile_verify_otp"],
            data={"txnId": txn_id, "otp": otp},
        )
        logger.info("Mobile OTP verified for txnId=%s", txn_id)
        return result

    async def create_abha_via_mobile(
        self, txn_id: str, profile_data: dict
    ) -> ABHAProfile:
        """
        Complete ABHA creation using a verified mobile OTP session.

        Args:
            txn_id: Transaction ID from the mobile OTP verification step.
            profile_data: Profile details (name, gender, DOB, address, etc.).

        Returns:
            The created ABHAProfile.
        """
        logger.info("Creating ABHA via mobile for txnId=%s", txn_id)

        payload = {"txnId": txn_id, **profile_data}
        result = await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["abha_mobile_create"],
            data=payload,
        )

        profile = self._parse_profile(result)
        logger.info("ABHA created: %s (%s)", profile.health_id, profile.health_id_number)
        return profile

    # ------------------------------------------------------------------
    # Profile retrieval & search
    # ------------------------------------------------------------------

    async def get_abha_profile(self, abha_id: str) -> ABHAProfile:
        """
        Fetch an ABHA profile from the ABDM gateway.

        Args:
            abha_id: ABHA address (e.g. ``user@abdm``) or ABHA number.

        Returns:
            ABHAProfile with full profile data.
        """
        logger.info("Fetching ABHA profile for %s", abha_id)

        result = await self._client._make_request(
            method="GET",
            endpoint=ABDM_ENDPOINTS["abha_profile"],
            headers={"X-Health-Id": abha_id},
        )
        return self._parse_profile(result)

    async def search_by_health_id(self, health_id: str) -> dict:
        """
        Search for an ABHA account by health ID.

        Args:
            health_id: ABHA address or number to search.

        Returns:
            dict with search results including ``authMethods`` and status.
        """
        logger.info("Searching ABHA by health ID: %s", health_id)

        result = await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["abha_search"],
            data={"healthId": health_id},
        )
        return result

    # ------------------------------------------------------------------
    # Linking ABHA to local patient record
    # ------------------------------------------------------------------

    async def link_abha_to_patient(self, patient_id: UUID, abha_id: str) -> dict:
        """
        Link an ABHA ID to a local patient record.

        This is a local operation that updates the patient record in the
        HMS database with the ABHA identifier. It also notifies the ABDM
        gateway about the linking so that the patient's care contexts
        become discoverable.

        Args:
            patient_id: UUID of the local patient record.
            abha_id: ABHA address or number to link.

        Returns:
            dict with linking confirmation details.

        Note:
            This method should be wrapped by the application layer to also
            persist the ABHA linkage in the local database.
        """
        logger.info(
            "Linking ABHA %s to patient %s", abha_id, patient_id
        )

        # Verify the ABHA exists
        profile = await self.get_abha_profile(abha_id)

        # Notify gateway about the link (the actual DB update is the
        # caller's responsibility)
        result = await self._client._make_request(
            method="POST",
            endpoint="/v0.5/links/link/add-contexts",
            data={
                "link": {
                    "accessToken": await self._client.get_access_token(),
                    "patient": {
                        "referenceNumber": str(patient_id),
                        "display": profile.name,
                        "careContexts": [],
                    },
                }
            },
        )

        logger.info("ABHA %s linked to patient %s", abha_id, patient_id)
        return {
            "patient_id": str(patient_id),
            "abha_id": profile.health_id,
            "abha_number": profile.health_id_number,
            "name": profile.name,
            "status": "linked",
            **result,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_profile(data: dict) -> ABHAProfile:
        """
        Parse an ABDM API response into an ``ABHAProfile``.

        The ABDM API uses camelCase keys; this maps them to the Pydantic model.
        """
        return ABHAProfile(
            health_id=data.get("healthId", data.get("healthIdNumber", "")),
            health_id_number=data.get("healthIdNumber", ""),
            name=data.get("name", ""),
            first_name=data.get("firstName"),
            middle_name=data.get("middleName"),
            last_name=data.get("lastName"),
            gender=data.get("gender", ""),
            year_of_birth=int(data.get("yearOfBirth", data.get("yob", 1900))),
            month_of_birth=data.get("monthOfBirth") or data.get("mob"),
            day_of_birth=data.get("dayOfBirth") or data.get("dob"),
            address=data.get("address"),
            district=data.get("districtName") or data.get("district"),
            state=data.get("stateName") or data.get("state"),
            pincode=data.get("pincode"),
            mobile=data.get("mobile"),
            email=data.get("email"),
            profile_photo=data.get("profilePhoto"),
            kycVerified=data.get("kycVerified", False),
        )


abha_service = ABHAService()
