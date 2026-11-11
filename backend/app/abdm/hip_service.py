"""
HIPService – Health Information Provider service.

When the hospital acts as a HIP, it responds to patient discovery requests,
handles care-context linking, and pushes health records (as FHIR bundles)
to requesting HIUs via the ABDM gateway.

Typical HIP flow:
    1. ABDM gateway sends a **discovery** request (patient lookup).
    2. HIP responds with matched patient and their care contexts.
    3. Gateway initiates **link** flow – HIP sends OTP to patient.
    4. Patient confirms link – care contexts are now accessible.
    5. When a consent-granted data request arrives, HIP packages clinical
       data as FHIR bundles, encrypts them, and pushes to the HIU.
"""

from __future__ import annotations

import base64
import logging
import uuid
from datetime import datetime, date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.abdm.client import ABDMClient, ABDMError
from app.abdm.config import ABDM_ENDPOINTS

logger = logging.getLogger("abdm.hip")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class CareContext(BaseModel):
    """
    Represents a single care context (a visit / encounter / episode).

    In ABDM, care contexts are the atomic units of health information that
    patients can grant or deny consent for.
    """

    reference_number: str = Field(
        ..., description="Unique reference for this care context (e.g. encounter UUID)"
    )
    display: str = Field(
        ..., description='Human-readable label (e.g. "OPD Visit - 2024-01-15")'
    )


class PatientMatch(BaseModel):
    """Patient matching result for discovery."""

    reference_number: str = Field(..., description="Local patient ID")
    display: str = Field(..., description="Patient name")
    care_contexts: list[CareContext] = Field(default_factory=list)
    match_score: float = Field(default=1.0, ge=0.0, le=1.0)


class DiscoverRequest(BaseModel):
    """Incoming patient discovery request from the ABDM gateway."""

    request_id: str = Field(..., description="Unique request identifier")
    transaction_id: str = Field(..., description="ABDM transaction ID")
    patient: dict = Field(
        ..., description="Patient identifiers (ABHA ID, name, gender, YOB)"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DiscoverResponse(BaseModel):
    """Response to a patient discovery request."""

    request_id: str
    transaction_id: str
    patient: Optional[PatientMatch] = None
    error: Optional[dict] = None


class LinkInitRequest(BaseModel):
    """Request to initialise care-context linking."""

    request_id: str
    transaction_id: str
    patient: dict = Field(
        ..., description="Patient reference and care contexts to link"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LinkInitResponse(BaseModel):
    """Response acknowledging link initialisation (OTP sent)."""

    request_id: str
    transaction_id: str
    link: dict = Field(
        ..., description="Contains referenceNumber and authenticator info"
    )
    error: Optional[dict] = None


class LinkConfirmRequest(BaseModel):
    """Request to confirm care-context link (OTP verification)."""

    request_id: str
    transaction_id: str
    confirmation: dict = Field(..., description="Contains linkRefNumber and OTP token")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LinkConfirmResponse(BaseModel):
    """Response confirming successful care-context linking."""

    request_id: str
    transaction_id: str
    patient: Optional[dict] = None
    error: Optional[dict] = None


class DataRequest(BaseModel):
    """Health information data request from HIU via ABDM gateway."""

    request_id: str = Field(..., description="Unique request identifier")
    transaction_id: str = Field(..., description="Transaction identifier")
    consent_id: str = Field(..., description="Granted consent artefact ID")
    care_contexts: list[dict] = Field(
        ..., description="Care contexts to retrieve data for"
    )
    date_range: dict = Field(
        ..., description='Date range filter {"from": ..., "to": ...}'
    )
    data_push_url: str = Field(
        ..., description="URL to push encrypted FHIR bundles to"
    )
    key_material: dict = Field(
        ..., description="HIU public key for data encryption"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class HIPService:
    """
    Health Information Provider (HIP) service.

    Handles ABDM gateway callbacks for patient discovery, linking, and
    health data provision.
    """

    def __init__(self, client: Optional[ABDMClient] = None) -> None:
        self._client = client or ABDMClient()

    # ------------------------------------------------------------------
    # Patient discovery
    # ------------------------------------------------------------------

    async def on_discover(self, request: DiscoverRequest) -> DiscoverResponse:
        """
        Handle a patient discovery request from an HIU via the ABDM gateway.

        The gateway forwards a discovery request containing patient
        identifiers (ABHA ID, demographics). This method looks up the
        patient in the local system and returns matched care contexts.

        Args:
            request: Incoming discovery request with patient identifiers.

        Returns:
            DiscoverResponse with matched patient and care contexts, or
            an error if no match is found.
        """
        logger.info(
            "Discovery request %s (txn=%s): patient=%s",
            request.request_id,
            request.transaction_id,
            request.patient,
        )

        try:
            patient_identifiers = request.patient
            abha_id = None
            for identifier in patient_identifiers.get("verifiedIdentifiers", []):
                if identifier.get("type") == "HEALTH_ID":
                    abha_id = identifier.get("value")
                    break

            # Search local database for matching patient
            matched_patient = await self._find_patient_locally(
                abha_id=abha_id,
                name=patient_identifiers.get("name"),
                gender=patient_identifiers.get("gender"),
                year_of_birth=patient_identifiers.get("yearOfBirth"),
            )

            if not matched_patient:
                logger.warning(
                    "Discovery: no patient match for request %s", request.request_id
                )
                response = DiscoverResponse(
                    request_id=request.request_id,
                    transaction_id=request.transaction_id,
                    error={
                        "code": 1000,
                        "message": "No patient found matching the given identifiers",
                    },
                )
            else:
                care_contexts = await self.get_care_contexts(
                    UUID(matched_patient["patient_id"])
                )
                response = DiscoverResponse(
                    request_id=request.request_id,
                    transaction_id=request.transaction_id,
                    patient=PatientMatch(
                        reference_number=matched_patient["patient_id"],
                        display=matched_patient["name"],
                        care_contexts=care_contexts,
                    ),
                )

            # Acknowledge back to gateway
            await self._client._make_request(
                method="POST",
                endpoint=ABDM_ENDPOINTS["on_discover"],
                data={
                    "requestId": str(uuid.uuid4()),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "transactionId": request.transaction_id,
                    "resp": {"requestId": request.request_id},
                    "patient": response.patient.model_dump() if response.patient else None,
                    "error": response.error,
                },
            )

            return response

        except Exception as exc:
            logger.error("Discovery error for request %s: %s", request.request_id, exc)
            error_response = DiscoverResponse(
                request_id=request.request_id,
                transaction_id=request.transaction_id,
                error={
                    "code": 1500,
                    "message": f"Internal error during discovery: {exc}",
                },
            )
            return error_response

    # ------------------------------------------------------------------
    # Care-context linking
    # ------------------------------------------------------------------

    async def on_link_init(self, request: LinkInitRequest) -> LinkInitResponse:
        """
        Handle link initialisation request.

        When a patient wants to link their care contexts at this facility,
        the ABDM gateway sends a link-init request. The HIP must send an
        OTP or other authentication to the patient.

        Args:
            request: Link initialisation request.

        Returns:
            LinkInitResponse with link reference for OTP verification.
        """
        logger.info(
            "Link-init request %s (txn=%s)", request.request_id, request.transaction_id
        )

        patient_ref = request.patient.get("referenceNumber", "")
        care_contexts = request.patient.get("careContexts", [])

        # Generate a link reference number for this linking session
        link_ref_number = f"LINK-{uuid.uuid4().hex[:12].upper()}"

        # In production, send OTP to the patient's registered mobile
        # For now, we create the link reference and store it
        logger.info(
            "Link-init: ref=%s, patient=%s, contexts=%d",
            link_ref_number,
            patient_ref,
            len(care_contexts),
        )

        response = LinkInitResponse(
            request_id=request.request_id,
            transaction_id=request.transaction_id,
            link={
                "referenceNumber": link_ref_number,
                "authenticationType": "DIRECT",
                "meta": {
                    "communicationMedium": "MOBILE",
                    "communicationHint": "OTP sent to registered mobile",
                    "communicationExpiry": (
                        datetime.utcnow().isoformat() + "Z"
                    ),
                },
            },
        )

        # Acknowledge back to gateway
        await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["on_link_init"],
            data={
                "requestId": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "transactionId": request.transaction_id,
                "resp": {"requestId": request.request_id},
                "link": response.link,
                "error": response.error,
            },
        )

        return response

    async def on_link_confirm(
        self, request: LinkConfirmRequest
    ) -> LinkConfirmResponse:
        """
        Handle link confirmation (OTP verified by patient).

        After the patient enters the OTP, the gateway sends a link-confirm
        request. The HIP confirms the linking of care contexts.

        Args:
            request: Link confirmation request with OTP token.

        Returns:
            LinkConfirmResponse with confirmed patient and care contexts.
        """
        logger.info(
            "Link-confirm request %s (txn=%s)",
            request.request_id,
            request.transaction_id,
        )

        link_ref = request.confirmation.get("linkRefNumber", "")
        token = request.confirmation.get("token", "")

        # Verify the OTP / token (simplified – production would validate
        # against stored OTP)
        logger.info("Link-confirm: ref=%s, verifying token", link_ref)

        # Build the confirmed patient with their linked care contexts
        # In production, retrieve from the linking session store
        response = LinkConfirmResponse(
            request_id=request.request_id,
            transaction_id=request.transaction_id,
            patient={
                "referenceNumber": link_ref,
                "display": "Patient",
                "careContexts": [],  # Populated from link session
            },
        )

        # Acknowledge back to gateway
        await self._client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["on_link_confirm"],
            data={
                "requestId": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "resp": {"requestId": request.request_id},
                "patient": response.patient,
                "error": response.error,
            },
        )

        return response

    # ------------------------------------------------------------------
    # Health data provision
    # ------------------------------------------------------------------

    async def on_data_request(self, request: DataRequest) -> None:
        """
        Handle a health information data request from an HIU.

        When a consent artefact is granted, the HIU requests data for
        specific care contexts. This method:
        1. Retrieves the clinical data for the requested care contexts.
        2. Packages it as FHIR bundles.
        3. Encrypts the data using the HIU's public key.
        4. Pushes the encrypted data to the provided data_push_url.

        Args:
            request: Data request with consent ID, care contexts, and
                encryption key material.
        """
        logger.info(
            "Data request %s (consent=%s): %d care contexts",
            request.request_id,
            request.consent_id,
            len(request.care_contexts),
        )

        try:
            await self.push_health_data(
                consent_id=request.consent_id,
                data_push_url=request.data_push_url,
                care_contexts=request.care_contexts,
                key_material=request.key_material,
                transaction_id=request.transaction_id,
            )
            logger.info("Data push completed for consent %s", request.consent_id)

        except Exception as exc:
            logger.error(
                "Data push failed for consent %s: %s", request.consent_id, exc
            )
            raise

    async def push_health_data(
        self,
        consent_id: str,
        data_push_url: str,
        care_contexts: list,
        key_material: Optional[dict] = None,
        transaction_id: Optional[str] = None,
    ) -> None:
        """
        Package clinical data as FHIR bundles, encrypt, and push to HIU.

        For each care context, the method:
        1. Retrieves clinical data from the local system.
        2. Builds a FHIR Bundle (document type) with the relevant resources.
        3. Encrypts the bundle content using the requester's public key
           (Curve25519 ECDH + AES-GCM as per ABDM spec).
        4. POSTs the encrypted data to the HIU's data push URL.

        Args:
            consent_id: The granted consent artefact ID.
            data_push_url: URL provided by the HIU to receive data.
            care_contexts: List of care context dicts with reference numbers.
            key_material: HIU's public key material for encryption.
            transaction_id: Transaction ID for tracking.
        """
        import json

        entries = []
        for ctx in care_contexts:
            ref = ctx.get("careContextReference", ctx.get("reference_number", ""))
            logger.debug("Packaging data for care context: %s", ref)

            # Retrieve clinical data for this care context
            clinical_data = await self._get_clinical_data_for_context(ref)

            # Build FHIR bundle
            from app.utils.fhir import build_bundle

            bundle = build_bundle(
                resources=clinical_data.get("resources", []),
                bundle_type="document",
            )

            # Encrypt bundle content
            bundle_json = json.dumps(bundle)
            encrypted_content = self._encrypt_data(
                data=bundle_json,
                key_material=key_material or {},
            )

            entries.append(
                {
                    "careContextReference": ref,
                    "content": encrypted_content,
                }
            )

        # Push encrypted data to HIU
        payload = {
            "pageNumber": 1,
            "pageCount": 1,
            "transactionId": transaction_id or str(uuid.uuid4()),
            "entries": entries,
            "keyMaterial": self._generate_key_material(),
        }

        await self._client._make_request(
            method="POST",
            endpoint=data_push_url,
            data=payload,
        )

        logger.info(
            "Pushed %d care context(s) for consent %s", len(entries), consent_id
        )

    # ------------------------------------------------------------------
    # Care context retrieval
    # ------------------------------------------------------------------

    async def get_care_contexts(self, patient_id: UUID) -> list[CareContext]:
        """
        Retrieve all care contexts (encounters) for a patient.

        Maps local encounters, admissions, lab visits, etc. to ABDM
        care contexts with human-readable labels.

        Args:
            patient_id: UUID of the local patient record.

        Returns:
            List of CareContext objects.
        """
        logger.info("Retrieving care contexts for patient %s", patient_id)

        # In production, this queries the local database for all encounters
        # belonging to this patient. For now, return a placeholder structure.
        # The actual implementation would look like:
        #
        #   encounters = await db.execute(
        #       select(Encounter).where(Encounter.patient_id == patient_id)
        #   )
        #   return [
        #       CareContext(
        #           reference_number=str(enc.id),
        #           display=f"{enc.encounter_type} - {enc.date.isoformat()}"
        #       )
        #       for enc in encounters
        #   ]

        return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _find_patient_locally(
        self,
        abha_id: Optional[str] = None,
        name: Optional[str] = None,
        gender: Optional[str] = None,
        year_of_birth: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Search the local patient database for a matching patient.

        Matching priority:
        1. Exact ABHA ID match
        2. Demographic match (name + gender + YOB)

        Returns:
            dict with patient_id, name, and match details, or None.

        Note:
            This is a stub. Production implementation should query the
            Patient model from the database.
        """
        logger.debug(
            "Local patient search: abha=%s, name=%s, gender=%s, yob=%s",
            abha_id,
            name,
            gender,
            year_of_birth,
        )
        # Stub: return None – implement with actual DB query
        # Example:
        # patient = await db.execute(
        #     select(Patient).where(Patient.abha_id == abha_id)
        # )
        # if patient:
        #     return {"patient_id": str(patient.id), "name": patient.full_name}
        return None

    async def _get_clinical_data_for_context(
        self, care_context_ref: str
    ) -> dict:
        """
        Retrieve clinical data for a specific care context.

        Returns:
            dict with a ``resources`` key containing FHIR resource dicts.

        Note:
            Stub – implement with actual clinical data retrieval.
        """
        logger.debug("Retrieving clinical data for context: %s", care_context_ref)
        # Production: query encounters, conditions, observations, etc.
        return {"resources": []}

    @staticmethod
    def _encrypt_data(data: str, key_material: dict) -> str:
        """
        Encrypt data using the requester's public key.

        ABDM mandates Curve25519 ECDH key exchange followed by AES-256-GCM
        encryption. This stub performs base64 encoding as a placeholder.

        Args:
            data: JSON string to encrypt.
            key_material: HIU's public key and nonce.

        Returns:
            Base64-encoded encrypted content.

        TODO:
            Implement proper ECDH + AES-GCM encryption per ABDM spec.
        """
        # Placeholder – in production use cryptography library:
        #   from cryptography.hazmat.primitives.asymmetric.x25519 import (
        #       X25519PrivateKey, X25519PublicKey,
        #   )
        #   from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        return base64.b64encode(data.encode("utf-8")).decode("utf-8")

    @staticmethod
    def _generate_key_material() -> dict:
        """
        Generate ephemeral key material for the HIP side of the ECDH exchange.

        Returns:
            dict with ``cryptoAlg``, ``curve``, ``dhPublicKey``, and ``nonce``.

        TODO:
            Generate a real X25519 ephemeral key pair.
        """
        return {
            "cryptoAlg": "ECDH",
            "curve": "Curve25519",
            "dhPublicKey": {
                "expiry": datetime.utcnow().isoformat() + "Z",
                "parameters": "Curve25519/32byte random key",
                "keyValue": "",  # Placeholder
            },
            "nonce": uuid.uuid4().hex,
        }


hip_service = HIPService()
