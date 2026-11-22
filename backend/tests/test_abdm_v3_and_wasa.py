"""Unit & integration tests for ABDM v3 Sandbox Exit (M1/M2/M3) and CERT-In WASA controls."""

import json

from app.abdm.client import ABDMClient, LiveABDMAdapter, MockABDMAdapter
from app.abdm.config import ABDMMode, ABDMSettings
from app.abdm.fidelius import (
    decrypt_fhir_bundle,
    encrypt_fhir_bundle,
    generate_ephemeral_keypair,
    verify_nha_webhook_signature,
)
from app.core.wasa_security import compute_payload_sha256, mask_pii_dict, mask_pii_text
from app.main import app
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
    build_prescription_bundle,
    parse_fhir_bundle_to_timeline,
)
from fastapi.testclient import TestClient


def test_fidelius_ecdh_curve25519_aes_gcm_roundtrip():
    """Verify authentic Curve25519 ECDH + HKDF-SHA256 + AES-256-GCM encrypt/decrypt."""
    hiu_kp = generate_ephemeral_keypair()
    sample_bundle = json.dumps({"resourceType": "Bundle", "type": "document", "id": "b-001"})

    ciphertext_b64, hip_kp = encrypt_fhir_bundle(
        plaintext_json=sample_bundle,
        receiver_key_material=hiu_kp.to_key_material(),
    )
    assert ciphertext_b64 != sample_bundle

    decrypted = decrypt_fhir_bundle(
        ciphertext_b64=ciphertext_b64,
        sender_key_material=hip_kp.to_key_material(),
        receiver_keypair=hiu_kp,
    )
    assert decrypted == sample_bundle


def test_nha_webhook_signature_verification():
    import hashlib
    import hmac

    payload = b'{"consentId":"C-1","status":"GRANTED"}'
    secret = "test_nha_secret_key"
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    assert verify_nha_webhook_signature(payload, sig, secret) is True
    assert verify_nha_webhook_signature(payload, f"sha256={sig}", secret) is True
    assert verify_nha_webhook_signature(payload, "bad-signature", secret) is False
    assert verify_nha_webhook_signature(payload, None, secret) is False
    assert verify_nha_webhook_signature(payload, None, "", allow_mock_bypass=True) is True


def test_abdm_strategy_adapter_selection():
    mock_client = ABDMClient(ABDMSettings(abdm_env=ABDMMode.MOCK))
    assert isinstance(mock_client._adapter, MockABDMAdapter)

    sbx_client = ABDMClient(ABDMSettings(abdm_env=ABDMMode.SANDBOX))
    assert isinstance(sbx_client._adapter, LiveABDMAdapter)
    assert sbx_client.settings.gateway_url == "https://dev.abdm.gov.in"
    assert sbx_client.settings.x_cm_id == "sbx"

    prod_client = ABDMClient(ABDMSettings(abdm_env=ABDMMode.PRODUCTION, abdm_x_cm_id="abdm"))
    assert isinstance(prod_client._adapter, LiveABDMAdapter)
    assert prod_client.settings.gateway_url == "https://apis.abdm.gov.in"


def test_nrces_fhir_r4_bundles_and_timeline_parser():
    pat = build_patient_resource("p1", "Arun Kumar", "MALE", "1991-05-14", abha_id="91-4829-1029-4721")
    prac = build_practitioner_resource("doc1", "Dr. Rajesh Sharma", "NMC-2018-94021")
    org = build_organization_resource("org1", "HMS Hospital", "IN2910000123")
    enc = build_encounter_resource("enc1", "p1", "doc1", "COMPLETED", "OPD", "2026-11-18T10:00:00Z")
    cond = build_condition_resource("c1", "p1", "enc1", "I10", "Essential Hypertension")
    obs = build_observation_resource("o1", "p1", "enc1", "8867-4", "Heart rate", 76.0, "bpm")
    med = build_medication_request("m1", "p1", "doc1", "enc1", "Telmisartan 40mg", "1 Tab", "OD", 30)
    diag = build_diagnostic_report_resource("dr1", "p1", "enc1", "CBC", "Normal", ["o1"])

    b_op = build_op_consult_bundle(
        patient=pat, practitioner=prac, organization=org, encounter=enc,
        conditions=[cond], observations=[obs], medications=[med],
    )
    b_rx = build_prescription_bundle(
        patient=pat, practitioner=prac, organization=org, encounter=enc, medications=[med],
    )
    b_lab = build_diagnostic_report_bundle(
        patient=pat, practitioner=prac, organization=org, encounter=enc, report=diag, observations=[obs],
    )
    b_dis = build_discharge_summary_bundle(
        patient=pat, practitioner=prac, organization=org, encounter=enc, conditions=[cond], medications=[med],
    )

    for bundle in (b_op, b_rx, b_lab, b_dis):
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "document"
        timeline = parse_fhir_bundle_to_timeline(bundle)
        assert timeline["facility_name"] == "HMS Hospital"
        assert timeline["practitioner_name"] == "Dr. Rajesh Sharma"


def test_wasa_pii_masking():
    raw_text = "Aadhaar 999988887777 ABHA 91-4829-1029-4721 Mobile 9876543210 Bearer eyJhbGciOiJIUzI1NiJ9"
    masked = mask_pii_text(raw_text)
    assert "99998888" not in masked
    assert "4829-1029" not in masked
    assert "987654" not in masked
    assert "eyJhbGciOiJIUzI1NiJ9" not in masked
    assert "7777" in masked
    assert "4721" in masked

    sanitized = mask_pii_dict({"password": "secret", "otp": "123456", "mobile": "9876543210"})
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["otp"] == "[REDACTED]"
    assert sanitized["mobile"] == "XXXXXX3210"
    assert len(compute_payload_sha256(sanitized)) == 64


def test_wasa_security_headers_and_abdm_status():
    client = TestClient(app)
    res = client.get("/api/v1/abdm/status")
    assert res.status_code == 200
    body = res.json()
    assert body["abdm_env"] in ("MOCK", "SANDBOX", "PRODUCTION")
    assert "client_secret" not in body
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert "max-age=63072000" in res.headers["strict-transport-security"]
    assert "no-store" in res.headers["cache-control"]
    assert "content-security-policy" in res.headers

