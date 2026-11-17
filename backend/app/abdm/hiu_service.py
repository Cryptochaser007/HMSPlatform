"""
HIUService – ABDM v3/v0.5 Milestone 3 (M3) Health Information User Engine.

Enables clinicians to:
  1. Initiate ABDM Consent Requests (`/v0.5/consent-requests/init`) with purpose, HI types & date bounds
  2. Receive Consent Manager approval callbacks (`/v0.5/consents/hiu/notify`)
  3. Request encrypted Health Information (`/v0.5/health-information/cm/request`) using real
     ephemeral Fidelius Curve25519 (X25519) keypairs
  4. Receive & decrypt Fidelius-encrypted FHIR R4 Document Bundles (`/v0.5/health-information/transfer`)
  5. Serve structured Longitudinal Health Record timelines in the Doctor EMR station
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.abdm.client import ABDMClient, ABDMError, utc_timestamp_iso
from app.abdm.config import ABDM_ENDPOINTS, ABDMMode, get_abdm_settings
from app.abdm.fidelius import (
    FideliusKeyPair,
    decrypt_fhir_bundle,
    encrypt_fhir_bundle,
    generate_ephemeral_keypair,
    verify_nha_webhook_signature,
)
from app.utils.fhir import (
    build_condition_resource,
    build_diagnostic_report_bundle,
    build_diagnostic_report_resource,
    build_discharge_summary_bundle,
    build_encounter_resource,
    build_medication_request,
    build_observation_resource,
    build_op_consult_bundle,
    build_organization_resource,
    build_patient_resource,
    build_practitioner_resource,
    parse_fhir_bundle_to_timeline,
)

logger = logging.getLogger("abdm.hiu")

# Ephemeral keypair store (transaction_id -> (FideliusKeyPair, patient_abha))
_ephemeral_hiu_keys: Dict[str, tuple[FideliusKeyPair, str]] = {}
# Consent cache & decrypted longitudinal timeline store
_hiu_consents_memory: Dict[str, Dict[str, Any]] = {}
_longitudinal_records: Dict[str, List[Dict[str, Any]]] = {}


class ConsentRequest(BaseModel):
    patient_abha: str = Field(..., min_length=4, max_length=255)
    purpose: str = Field(default="Care Management", max_length=200)
    purpose_code: str = Field(default="CAREMGT", max_length=30)
    date_from: datetime
    date_to: datetime
    hi_types: List[str] = Field(
        default=["OPConsultation", "Prescription", "DiagnosticReport", "DischargeSummary"]
    )

    @field_validator("patient_abha")
    @classmethod
    def validate_abha(cls, v: str) -> str:
        cleaned = v.strip()
        if any(ch in cleaned for ch in ("<", ">", ";", "'", '"')):
            raise ValueError("Invalid characters in ABHA address")
        return cleaned


class ConsentNotification(BaseModel):
    consent_request_id: str
    status: str  # GRANTED, DENIED, REVOKED, EXPIRED
    consent_artefact_id: Optional[str] = None
    signature: Optional[str] = None


class HealthData(BaseModel):
    care_context_reference: str
    bundle_data: Dict[str, Any]


class HIUService:
    """Health Information User (HIU) orchestrator for ABDM M3 certification."""

    def __init__(self, client: Optional[ABDMClient] = None) -> None:
        self.settings = get_abdm_settings()
        self.client = client or ABDMClient()

    # ------------------------------------------------------------------
    # 1. Initiate Consent Request (`/v0.5/consent-requests/init`)
    # ------------------------------------------------------------------

    async def create_consent_request(
        self,
        db: AsyncSession,
        request: ConsentRequest,
        *,
        requester_name: str = "Consulting Physician",
        requester_reg: str = "NMC-2018-94021",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        erase_at = now + timedelta(days=30)

        payload = {
            "requestId": request_id,
            "timestamp": utc_timestamp_iso(),
            "consent": {
                "purpose": {
                    "text": request.purpose,
                    "code": request.purpose_code,
                },
                "patient": {"id": request.patient_abha},
                "hiu": {"id": self.settings.hiu_id},
                "requester": {
                    "name": requester_name,
                    "identifier": {
                        "type": "REGNO",
                        "value": requester_reg,
                        "system": "https://www.mciindia.org",
                    },
                },
                "hiTypes": request.hi_types,
                "permission": {
                    "accessMode": "VIEW",
                    "dateRange": {
                        "from": request.date_from.isoformat(),
                        "to": request.date_to.isoformat(),
                    },
                    "dataEraseAt": erase_at.isoformat(),
                    "frequency": {"unit": "HOUR", "value": 1, "repeats": 0},
                },
            },
        }

        gateway_res = await self.client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["consent_request_init"],
            data=payload,
            user_id=user_id,
        )

        # In MOCK mode, immediately issue a simulated GRANTED consent artefact for end-to-end demo
        is_mock = self.client.mode == ABDMMode.MOCK
        consent_artefact_id = f"CONSENT-{uuid.uuid4().hex[:12].upper()}" if is_mock else request_id
        initial_status = "GRANTED" if is_mock else "REQUESTED"

        record = {
            "consent_id": consent_artefact_id,
            "consent_request_id": request_id,
            "role": "HIU",
            "patient_abha": request.patient_abha,
            "purpose_code": request.purpose_code,
            "purpose_text": request.purpose,
            "status": initial_status,
            "hi_types": request.hi_types,
            "date_from": request.date_from.isoformat(),
            "date_to": request.date_to.isoformat(),
            "data_erase_at": erase_at.isoformat(),
            "hiu_id": self.settings.hiu_id,
            "requester_name": requester_name,
            "abdm_mode": self.client.mode.value,
            "created_at": now.isoformat(),
        }
        _hiu_consents_memory[consent_artefact_id] = record

        try:
            from app.models.abdm import ABDMConsentArtefact

            db.add(
                ABDMConsentArtefact(
                    consent_id=consent_artefact_id,
                    consent_request_id=request_id,
                    role="HIU",
                    patient_abha=request.patient_abha,
                    purpose_code=request.purpose_code,
                    purpose_text=request.purpose,
                    status=initial_status,
                    hi_types=request.hi_types,
                    date_from=request.date_from,
                    date_to=request.date_to,
                    data_erase_at=erase_at,
                    hiu_id=self.settings.hiu_id,
                    requester_name=requester_name,
                    requester_user_id=user_id,
                    signature_verified=is_mock,
                    artefact_payload=payload,
                )
            )
            await db.flush()
        except Exception as exc:
            logger.debug("HIU consent DB persist fallback: %s", exc)

        return {
            **record,
            "gateway_response": gateway_res,
            "message": (
                "Consent artefact simulated as GRANTED (ABDM_ENV=MOCK); ready to fetch Fidelius-encrypted records."
                if is_mock
                else "Consent request dispatched to ABDM Consent Manager. Awaiting patient approval on ABHA app."
            ),
        }

    # ------------------------------------------------------------------
    # 2. Consent Approval Callback (`/v0.5/consents/hiu/notify`)
    # ------------------------------------------------------------------

    async def on_consent_hiu_notify(
        self,
        db: AsyncSession,
        payload: Dict[str, Any],
        raw_body: bytes,
        signature_header: Optional[str] = None,
    ) -> Dict[str, Any]:
        req_id = payload.get("requestId") or str(uuid.uuid4())
        notification = payload.get("notification") or {}
        consent_req_id = notification.get("consentRequestId") or ""
        consent_status = str(notification.get("status", "GRANTED")).upper()
        artefacts = notification.get("consentArtefacts") or []

        is_verified = verify_nha_webhook_signature(
            payload_bytes=raw_body,
            signature_header=signature_header,
            shared_secret=self.settings.abdm_webhook_secret,
            allow_mock_bypass=(self.client.mode == ABDMMode.MOCK),
        )
        if not is_verified and self.client.mode != ABDMMode.MOCK:
            raise ABDMError(
                message="Invalid NHA signature on HIU consent notification",
                error_code="ABDM-SIG-INVALID",
                http_status=401,
            )

        await self.client.record_transaction(
            request_id=req_id,
            correlation_id=consent_req_id,
            direction="INBOUND",
            http_method="POST",
            endpoint="/api/v1/abdm/v0.5/consents/hiu/notify",
            http_status=202,
            payload=payload,
        )

        artefact_ids = [a.get("id") for a in artefacts if isinstance(a, dict) and a.get("id")]
        primary_id = artefact_ids[0] if artefact_ids else consent_req_id

        for cid, rec in list(_hiu_consents_memory.items()):
            if rec.get("consent_request_id") == consent_req_id or cid == consent_req_id:
                rec["status"] = consent_status
                if primary_id and primary_id != cid:
                    rec["consent_id"] = primary_id
                    _hiu_consents_memory[primary_id] = rec

        try:
            from app.models.abdm import ABDMConsentArtefact

            row = (
                await db.execute(
                    select(ABDMConsentArtefact).where(
                        ABDMConsentArtefact.consent_request_id == consent_req_id
                    )
                )
            ).scalar_one_or_none()
            if row:
                row.status = consent_status
                if primary_id:
                    row.consent_id = primary_id
                row.signature_verified = is_verified
                await db.flush()
        except Exception as exc:
            logger.debug("HIU consent notify DB update fallback: %s", exc)

        return {
            "status": "ACK",
            "consent_request_id": consent_req_id,
            "consent_status": consent_status,
            "artefact_ids": artefact_ids,
        }

    # ------------------------------------------------------------------
    # 3. Fetch Health Information (`/v0.5/health-information/cm/request`)
    # ------------------------------------------------------------------

    async def fetch_health_info(
        self,
        db: AsyncSession,
        consent_artefact_id: str,
        *,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        consent = await self._find_hiu_consent(db, consent_artefact_id)
        if not consent:
            raise ABDMError(
                message=f"HIU Consent artefact {consent_artefact_id} not found",
                error_code="ABDM-1005",
                http_status=404,
            )
        if consent["status"] != "GRANTED":
            raise ABDMError(
                message=f"Consent status is {consent['status']}; must be GRANTED before fetching HI",
                error_code="ABDM-1006",
                http_status=403,
            )

        # Generate real ephemeral Curve25519 keypair + 32-byte nonce for this HI session
        hiu_keypair = generate_ephemeral_keypair(ttl_minutes=30)
        txn_id = str(uuid.uuid4())
        _ephemeral_hiu_keys[txn_id] = (hiu_keypair, consent["patient_abha"])

        payload = {
            "requestId": str(uuid.uuid4()),
            "timestamp": utc_timestamp_iso(),
            "hiRequest": {
                "consent": {"id": consent_artefact_id},
                "dateRange": {
                    "from": consent["date_from"],
                    "to": consent["date_to"],
                },
                "dataPushUrl": f"{self.settings.callback_base_url}/api/v1/abdm/v0.5/health-information/transfer",
                "keyMaterial": hiu_keypair.to_key_material(),
            },
        }

        gateway_res = await self.client._make_request(
            method="POST",
            endpoint=ABDM_ENDPOINTS["hi_request"],
            data=payload,
            correlation_id=txn_id,
            user_id=user_id,
        )

        # In MOCK mode, run a REAL Fidelius ECDH+AES-256-GCM encrypt -> decrypt loop
        # on NRCeS FHIR R4 bundles so the doctor immediately sees verified decrypted records
        if self.client.mode == ABDMMode.MOCK:
            simulated_push = self._build_fidelius_encrypted_mock_push(
                txn_id=txn_id,
                patient_abha=consent["patient_abha"],
                hiu_key_material=hiu_keypair.to_key_material(),
            )
            decrypted_result = await self.on_health_information_transfer(simulated_push)
            return {
                "transaction_id": txn_id,
                "consent_artefact_id": consent_artefact_id,
                "patient_abha": consent["patient_abha"],
                "status": "RECEIVED_AND_DECRYPTED",
                "encryption_verified": "FIDELIUS_ECDH_CURVE25519_AES256_GCM",
                "records_decrypted": decrypted_result["records_decrypted"],
                "timeline": decrypted_result["timeline"],
                "abdm_mode": "MOCK",
            }

        return {
            "transaction_id": txn_id,
            "consent_artefact_id": consent_artefact_id,
            "patient_abha": consent["patient_abha"],
            "status": "REQUESTED",
            "encryption_key_algorithm": "ECDH/Curve25519",
            "gateway_response": gateway_res,
            "abdm_mode": self.client.mode.value,
        }

    # ------------------------------------------------------------------
    # 4. Data Push Receiver & Fidelius Decryption (`/v0.5/health-information/transfer`)
    # ------------------------------------------------------------------

    async def on_health_information_transfer(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        txn_id = payload.get("transactionId") or ""
        entries = payload.get("entries") or []
        sender_key_material = payload.get("keyMaterial") or {}

        await self.client.record_transaction(
            request_id=str(uuid.uuid4()),
            correlation_id=txn_id,
            direction="INBOUND",
            http_method="POST",
            endpoint="/api/v1/abdm/v0.5/health-information/transfer",
            http_status=200,
            payload={"transactionId": txn_id, "entry_count": len(entries)},
        )

        stored = _ephemeral_hiu_keys.get(txn_id)
        if not stored:
            raise ABDMError(
                message=f"No active HIU ephemeral keypair found for transaction {txn_id}",
                error_code="ABDM-1007",
                http_status=400,
            )

        hiu_keypair, patient_abha = stored
        timeline_items: List[Dict[str, Any]] = []

        for entry in entries:
            ciphertext_b64 = entry.get("content") or ""
            care_context_ref = entry.get("careContextReference") or "EXTERNAL-CONTEXT"
            if not ciphertext_b64:
                continue

            plaintext_json = decrypt_fhir_bundle(
                ciphertext_b64=ciphertext_b64,
                sender_key_material=sender_key_material,
                receiver_keypair=hiu_keypair,
            )
            bundle = json.loads(plaintext_json)
            parsed = parse_fhir_bundle_to_timeline(bundle)
            parsed["care_context_reference"] = care_context_ref
            parsed["transaction_id"] = txn_id
            parsed["decryption_cipher"] = "Fidelius ECDH (Curve25519) + AES-256-GCM"
            timeline_items.append(parsed)

        existing = _longitudinal_records.get(patient_abha, [])
        existing_ids = {item["bundle_id"] for item in existing}
        for item in timeline_items:
            if item["bundle_id"] not in existing_ids:
                existing.insert(0, item)
        _longitudinal_records[patient_abha] = existing

        return {
            "status": "RECEIVED",
            "transaction_id": txn_id,
            "patient_abha": patient_abha,
            "records_decrypted": len(timeline_items),
            "timeline": existing,
        }

    # ------------------------------------------------------------------
    # 5. Query helpers for Doctor EMR Longitudinal Viewer
    # ------------------------------------------------------------------

    async def list_consents(
        self, db: AsyncSession, patient_abha: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        seen: set[str] = set()
        try:
            from app.models.abdm import ABDMConsentArtefact

            q = select(ABDMConsentArtefact).where(
                ABDMConsentArtefact.role == "HIU",
                ABDMConsentArtefact.is_deleted == False,  # noqa: E712
            )
            if patient_abha:
                q = q.where(ABDMConsentArtefact.patient_abha == patient_abha)
            q = q.order_by(desc(ABDMConsentArtefact.created_at)).limit(30)
            rows = (await db.execute(q)).scalars().all()
            for r in rows:
                seen.add(r.consent_id)
                results.append(
                    {
                        "consent_id": r.consent_id,
                        "consent_request_id": r.consent_request_id,
                        "patient_abha": r.patient_abha,
                        "purpose_code": r.purpose_code,
                        "purpose_text": r.purpose_text,
                        "status": r.status,
                        "hi_types": r.hi_types,
                        "date_from": r.date_from.isoformat(),
                        "date_to": r.date_to.isoformat(),
                        "created_at": r.created_at.isoformat(),
                    }
                )
        except Exception:
            pass

        for cid, rec in _hiu_consents_memory.items():
            if cid not in seen:
                if not patient_abha or rec["patient_abha"] == patient_abha:
                    results.append(rec)
        return results

    def get_longitudinal_records(self, patient_abha: str) -> List[Dict[str, Any]]:
        return _longitudinal_records.get(patient_abha.strip(), [])

    async def _find_hiu_consent(
        self, db: AsyncSession, consent_id: str
    ) -> Optional[Dict[str, Any]]:
        if consent_id in _hiu_consents_memory:
            return _hiu_consents_memory[consent_id]
        try:
            from app.models.abdm import ABDMConsentArtefact

            row = (
                await db.execute(
                    select(ABDMConsentArtefact).where(
                        ABDMConsentArtefact.consent_id == consent_id
                    )
                )
            ).scalar_one_or_none()
            if row:
                return {
                    "consent_id": row.consent_id,
                    "patient_abha": row.patient_abha,
                    "status": row.status,
                    "date_from": row.date_from.isoformat(),
                    "date_to": row.date_to.isoformat(),
                    "hi_types": row.hi_types,
                }
        except Exception:
            pass
        return None

    def _build_fidelius_encrypted_mock_push(
        self,
        *,
        txn_id: str,
        patient_abha: str,
        hiu_key_material: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build 3 NRCeS FHIR R4 Bundles from external HIPs and encrypt with real Fidelius ECDH+AES-GCM."""
        pat = build_patient_resource(
            patient_id="pat-ext-001",
            name=patient_abha.split("@")[0].replace(".", " ").title(),
            gender="MALE",
            dob="1991-05-14",
            abha_id=patient_abha,
        )
        # Bundle 1: External Cardiology OP Consult
        prac1 = build_practitioner_resource("prac-ext-1", "Dr. Vikram Deshmukh, DM (Cardiology)", "MMC-77219")
        org1 = build_organization_resource("IN2910000123", "Manipal Heart & Multispeciality Institute, Bengaluru", "IN2910000123")
        enc1 = build_encounter_resource("enc-ext-1", pat["id"], prac1["id"], "COMPLETED", "OPD", "2026-08-14T10:30:00Z")
        b1 = build_op_consult_bundle(
            patient=pat,
            practitioner=prac1,
            organization=org1,
            encounter=enc1,
            conditions=[build_condition_resource("c1", pat["id"], enc1["id"], "I10", "Essential (primary) hypertension")],
            observations=[build_observation_resource("o1", pat["id"], enc1["id"], "8480-6", "Systolic blood pressure", 146.0, "mmHg")],
            medications=[build_medication_request("m1", pat["id"], prac1["id"], enc1["id"], "Telmisartan 40mg Tablet", "1 Tab", "OD", 30)],
            chief_complaint="Routine Hypertension Follow-up",
        )

        # Bundle 2: External Diagnostic Lab Report
        prac2 = build_practitioner_resource("prac-ext-2", "Dr. Meera Nair, MD (Pathology)", "KMC-55102")
        org2 = build_organization_resource("IN2910000456", "SRL National Reference Diagnostics, Bengaluru", "IN2910000456")
        enc2 = build_encounter_resource("enc-ext-2", pat["id"], prac2["id"], "COMPLETED", "OPD", "2026-09-22T08:15:00Z")
        obs_hba1c = build_observation_resource("o2", pat["id"], enc2["id"], "4548-4", "Hemoglobin A1c (HbA1c)", 7.6, "%")
        obs_chol = build_observation_resource("o3", pat["id"], enc2["id"], "2093-3", "Total Cholesterol", 224.0, "mg/dL")
        diag = build_diagnostic_report_resource(
            "dr-ext-1",
            pat["id"],
            enc2["id"],
            "Glycemic & Lipid Metabolic Panel",
            "Elevated HbA1c (7.6%) and borderline hypercholesterolemia. Recommend lifestyle + Metformin review.",
            [obs_hba1c["id"], obs_chol["id"]],
            issued="2026-09-22T14:00:00Z",
        )
        b2 = build_diagnostic_report_bundle(
            patient=pat,
            practitioner=prac2,
            organization=org2,
            encounter=enc2,
            report=diag,
            observations=[obs_hba1c, obs_chol],
        )

        # Bundle 3: External IPD Discharge Summary
        prac3 = build_practitioner_resource("prac-ext-3", "Dr. Arvind Menon, MS (General Surgery)", "KMC-31890")
        org3 = build_organization_resource("IN2910000789", "Apollo Tertiary Care Centre, Bengaluru", "IN2910000789")
        enc3 = build_encounter_resource("enc-ext-3", pat["id"], prac3["id"], "COMPLETED", "IPD", "2026-06-02T09:00:00Z")
        b3 = build_discharge_summary_bundle(
            patient=pat,
            practitioner=prac3,
            organization=org3,
            encounter=enc3,
            conditions=[build_condition_resource("c3", pat["id"], enc3["id"], "K35.80", "Acute Appendicitis - Post Laparoscopic Appendectomy")],
            medications=[build_medication_request("m3", pat["id"], prac3["id"], enc3["id"], "Cefuroxime 500mg Tablet", "1 Tab", "BD", 5)],
            summary_text="Uncomplicated laparoscopic appendectomy performed. Post-op recovery uneventful. Afebrile at discharge.",
        )

        hip_keypair = generate_ephemeral_keypair()
        entries = []
        for idx, bundle in enumerate([b1, b2, b3], start=1):
            cipher_b64, hip_keypair = encrypt_fhir_bundle(
                plaintext_json=json.dumps(bundle),
                receiver_key_material=hiu_key_material,
                sender_keypair=hip_keypair,
            )
            entries.append(
                {
                    "careContextReference": f"EXT-CARE-CTX-00{idx}",
                    "content": cipher_b64,
                    "media": "application/fhir+json",
                }
            )

        return {
            "pageNumber": 1,
            "pageCount": 1,
            "transactionId": txn_id,
            "entries": entries,
            "keyMaterial": hip_keypair.to_key_material(),
        }


hiu_service = HIUService()
