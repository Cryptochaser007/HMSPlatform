"""Fidelius interoperability vectors for raw X25519 and X.509 SPKI inputs."""
import base64
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.abdm.fidelius import (
    FideliusKeyPair,
    _encode_spki,
    _load_curve25519_public_key,
    decrypt_fhir_bundle,
    encrypt_fhir_bundle,
    generate_ephemeral_keypair,
)


def test_curve25519_uncompressed_and_spki_der_load_to_same_public_point():
    point = (int("2aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaad245a", 16), int("20ae19a1b8a086b4e01edd2c7748d14c923d4d7e6d7c61b229e9c5a27eced3d9", 16))
    raw = b"\x04" + point[0].to_bytes(32, "big") + point[1].to_bytes(32, "big")
    spki = _encode_spki(*point)
    loaded_raw = _load_curve25519_public_key(base64.b64encode(raw).decode())
    loaded_der = _load_curve25519_public_key(base64.b64encode(spki).decode())
    assert loaded_raw == point
    assert loaded_der == point


def test_reject_weierstrass_ec_key_as_not_nha_curve25519():
    der = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with pytest.raises(ValueError, match="not on the ABDM Curve25519"):
        _load_curve25519_public_key(base64.b64encode(der).decode())


def test_fidelius_payload_round_trip_with_spki_public_keys():
    hip = generate_ephemeral_keypair()
    hiu = generate_ephemeral_keypair()
    receiver_material = hiu.to_key_material()
    encrypted, hip = encrypt_fhir_bundle('{"resourceType":"Bundle","id":"vector-1"}', receiver_material, hip)
    plain = decrypt_fhir_bundle(encrypted, hip.to_key_material(), hiu)
    assert plain == '{"resourceType":"Bundle","id":"vector-1"}'


def test_java_fidelius_cli_reference_vector_decrypts():
    receiver = FideliusKeyPair(
        private_key_b64="DMxHPri8d7IT23KgLk281zZenMfVHSdeamq0RhwlIBk=",
        public_key_b64="",
        nonce_b64="6uj1RdDUbcpI3lVMZvijkMC8Te20O4Bcyz0SyivX8Eg=",
        expiry_iso="",
    )
    sender = {"dhPublicKey": {"keyValue": "BABVt+mpRLMXiQpIfEq6bj8hlXsdtXIxLsspmMgLNI1SR5mHgDVbjHO2A+U4QlMddGzqyEidzm1AkhtSxSO2Ahg="}, "nonce": "lmXgblZwotx+DfBgKJF0lZXtAXgBEYr5khh79Zytr2Y="}
    ciphertext = "pzMvVZNNVtJzqPkkxcCbBUWgDEBy/mBXIeT2dJWI16ZAQnnXUb9lI+S4k8XK6mgZSKKSRIHkcNvJpllnBg548wUgavBa0vCRRwdL6kY6Yw=="
    assert decrypt_fhir_bundle(ciphertext, sender, receiver) == "Wormtail should never have been Potter cottage's secret keeper."
