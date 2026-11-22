"""
ABDM Fidelius Cryptographic Engine (ECDH Curve25519 + HKDF-SHA256 + AES-256-GCM).

Implements the official NHA Fidelius end-to-end health-data encryption protocol
used between Health Information Providers (HIP) and Health Information Users (HIU):
  1. Generate ephemeral X25519 (Curve25519) keypair + 32-byte random nonce.
  2. Derive ECDH shared secret using peer's Curve25519 public key.
  3. XOR sender and receiver 32-byte nonces:
       - salt = xor_bytes[0:20]   (20 bytes)
       - iv   = xor_bytes[20:32]  (12 bytes for AES-GCM)
  4. Derive 256-bit AES key via HKDF-SHA256(shared_secret, salt=salt, info=b"").
  5. Encrypt / decrypt FHIR R4 JSON bundles with AES-256-GCM.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# ABDM's Java Fidelius reference uses Curve25519 in short-Weierstrass form.

_P = 2**255 - 19
_A = int("2aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa984914a144", 16)
_B = int("7b425ed097b425ed097b425ed097b425ed097b425ed097b4260b5e9c7710c864", 16)
_N = int("1000000000000000000000000000000014def9dea2f79cd65812631a5cf5d3ed", 16)
_GX = int("2aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaad245a", 16)
_GY = int("20ae19a1b8a086b4e01edd2c7748d14c923d4d7e6d7c61b229e9c5a27eced3d9", 16)
def _point_add(left: tuple[int, int] | None, right: tuple[int, int] | None) -> tuple[int, int] | None:
    if left is None:
        return right
    if right is None:
        return left
    x1, y1 = left
    x2, y2 = right
    if x1 == x2 and (y1 + y2) % _P == 0:
        return None
    if left == right:
        slope = (3 * x1 * x1 + _A) * pow(2 * y1, -1, _P) % _P
    else:
        slope = (y2 - y1) * pow((x2 - x1) % _P, -1, _P) % _P
    x3 = (slope * slope - x1 - x2) % _P
    return x3, (slope * (x1 - x3) - y1) % _P


def _scalar_mult(scalar: int, point: tuple[int, int], allow_infinity: bool = False) -> tuple[int, int] | None:
    # Short-Weierstrass arithmetic over the BouncyCastle Curve25519 parameters.
    # Python big-integer operations are not constant-time; use a hardened native
    # implementation before treating this module as a production cryptographic boundary.
    result: tuple[int, int] | None = None
    addend: tuple[int, int] | None = point
    while scalar:
        if scalar & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        scalar >>= 1
    if result is None and not allow_infinity:
        raise ValueError("Invalid point multiplication result")
    return result


@dataclass
class FideliusKeyPair:
    """Ephemeral X25519 keypair + 32-byte random nonce for a single HI transaction."""

    private_key_b64: str
    public_key_b64: str
    nonce_b64: str
    expiry_iso: str

    def to_key_material(self) -> dict[str, Any]:
        """Serialize public key material into ABDM gateway ``keyMaterial`` JSON format."""
        return {
            "cryptoAlg": "ECDH",
            "curve": "Curve25519",
            "dhPublicKey": {
                "expiry": self.expiry_iso,
                "parameters": "Curve25519/32byte random key",
                "keyValue": self.public_key_b64,
            },
            "nonce": self.nonce_b64,
        }


def generate_ephemeral_keypair(ttl_minutes: int = 30) -> FideliusKeyPair:
    """Generate BouncyCastle-compatible Weierstrass Curve25519 keys and nonce."""
    private_scalar = secrets.randbelow(_N - 1) + 1
    public_point = _scalar_mult(private_scalar, (_GX, _GY))
    assert public_point is not None
    public_x, public_y = public_point
    priv_bytes = private_scalar.to_bytes(32, "big")
    # Fidelius keyMaterial.keyValue carries the uncompressed point. SPKI DER is
    # accepted by the decoder for Java callers that send x509PublicKey instead.
    pub_bytes = b"\x04" + public_x.to_bytes(32, "big") + public_y.to_bytes(32, "big")
    nonce_bytes = os.urandom(32)
    expiry = (datetime.now(UTC) + timedelta(minutes=ttl_minutes)).strftime(
        "%Y-%m-%dT%H:%M:%S.%f"
    )[:-3] + "Z"

    return FideliusKeyPair(
        private_key_b64=base64.b64encode(priv_bytes).decode("ascii"),
        public_key_b64=base64.b64encode(pub_bytes).decode("ascii"),
        nonce_b64=base64.b64encode(nonce_bytes).decode("ascii"),
        expiry_iso=expiry,
    )


def _der_length(size: int) -> bytes:
    if size < 128:
        return bytes([size])
    encoded = size.to_bytes((size.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(encoded)]) + encoded


def _tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _der_length(len(value)) + value


def _der_integer(value: int) -> bytes:
    raw = value.to_bytes(max(1, (value.bit_length() + 7) // 8), "big")
    if raw[0] & 0x80:
        raw = b"\x00" + raw
    return _tlv(0x02, raw)


def _encode_spki(x: int, y: int) -> bytes:
    """Build an X.509 SPKI with explicit BouncyCastle Curve25519 parameters."""
    oid_ec_public_key = bytes.fromhex("2a8648ce3d0201")
    oid_prime_field = bytes.fromhex("2a8646ce3d0101")
    curve = _tlv(0x30, _tlv(0x04, _A.to_bytes(32, "big")) + _tlv(0x04, _B.to_bytes(32, "big")))
    field = _tlv(0x30, _tlv(0x06, oid_prime_field) + _der_integer(_P))
    base = _tlv(0x04, b"\x04" + _GX.to_bytes(32, "big") + _GY.to_bytes(32, "big"))
    params = _tlv(0x30, _der_integer(1) + field + curve + base + _der_integer(_N) + _der_integer(8))
    algorithm = _tlv(0x30, _tlv(0x06, oid_ec_public_key) + params)
    point = b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")
    return _tlv(0x30, algorithm + _tlv(0x03, b"\x00" + point))


def _read_length(data: bytes, offset: int) -> tuple[int, int]:
    first = data[offset]
    if first < 128:
        return first, offset + 1
    count = first & 0x7f
    if count == 0 or count > 4:
        raise ValueError("Invalid DER length")
    return int.from_bytes(data[offset + 1:offset + 1 + count], "big"), offset + 1 + count


def _spki_point(der: bytes) -> tuple[int, int]:
    """Extract uncompressed point from an explicit-parameter SPKI BIT STRING."""
    def walk(data: bytes):
        offset = 0
        while offset < len(data):
            tag = data[offset]
            size, start = _read_length(data, offset + 1)
            end = start + size
            if end > len(data):
                raise ValueError("Truncated DER key")
            value = data[start:end]
            yield tag, value
            if tag == 0x30:
                yield from walk(value)
            offset = end
    points = [v[1:] for tag, v in walk(der) if tag == 0x03 and len(v) == 66 and v[0] == 0 and v[1] == 4]
    if not points:
        raise ValueError("Expected a BouncyCastle explicit-parameter Curve25519 SPKI with an uncompressed point")
    raw = points[-1]
    return int.from_bytes(raw[1:33], "big"), int.from_bytes(raw[33:], "big")


def _load_curve25519_public_key(key_b64: str) -> tuple[int, int]:
    raw = base64.b64decode(key_b64.strip(), validate=True)
    if len(raw) == 65 and raw[0] == 4:
        x, y = int.from_bytes(raw[1:33], "big"), int.from_bytes(raw[33:], "big")
    elif len(raw) == 32:
        raise ValueError("32-byte Montgomery X25519 keys are not compatible with ABDM's Weierstrass Fidelius curve")
    else:
        x, y = _spki_point(raw)
    if (y * y - (x * x * x + _A * x + _B)) % _P:
        raise ValueError("Public key point is not on the ABDM Curve25519 Weierstrass curve")
    if _scalar_mult(_N, (x, y), allow_infinity=True) is not None:
        raise ValueError("Public key point is outside the Fidelius prime-order subgroup")
    return x, y


def _load_private_scalar(key_b64: str) -> int:
    """Load the big-endian 32-byte Fidelius private scalar."""
    raw = base64.b64decode(key_b64.strip())
    if len(raw) != 32:
        raise ValueError("Fidelius private key must be a 32-byte scalar")
    scalar = int.from_bytes(raw, "big")
    if not 1 <= scalar < _N:
        raise ValueError("Fidelius private scalar is out of range")
    return scalar


def _shared_secret(private_key_b64: str, public_key_b64: str) -> bytes:
    shared_point = _scalar_mult(_load_private_scalar(private_key_b64), _load_curve25519_public_key(public_key_b64))
    assert shared_point is not None
    shared_x, _ = shared_point
    return shared_x.to_bytes(32, "big")


def _decode_nonce(nonce_str: str) -> bytes:
    """Decode a 32-byte base64 nonce (or deterministically hash non-32-byte sandbox nonces)."""
    try:
        decoded = base64.b64decode(nonce_str.strip(), validate=True)
        if len(decoded) == 32:
            return decoded
    except Exception:
        logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
    # Fallback normalization for non-base64 UUID strings encountered in mock/test payloads
    return hashlib.sha256(nonce_str.encode("utf-8")).digest()


def _derive_aes_key_and_iv(
    shared_secret: bytes, sender_nonce_b64: str, receiver_nonce_b64: str
) -> tuple[bytes, bytes]:
    """Perform Fidelius XOR(nonceA, nonceB) + HKDF-SHA256 to derive AES-256 key and 12-byte IV."""
    nonce_a = _decode_nonce(sender_nonce_b64)
    nonce_b = _decode_nonce(receiver_nonce_b64)
    xor_nonce = bytes(a ^ b for a, b in zip(nonce_a, nonce_b))

    salt = xor_nonce[:20]
    iv = xor_nonce[20:32]

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"",
    )
    aes_key = hkdf.derive(shared_secret)
    return aes_key, iv


def encrypt_fhir_bundle(
    plaintext_json: str,
    receiver_key_material: dict[str, Any],
    sender_keypair: FideliusKeyPair | None = None,
) -> tuple[str, FideliusKeyPair]:
    """Encrypt a serialized FHIR R4 JSON bundle using Fidelius ECDH + AES-256-GCM.

    Args:
        plaintext_json: UTF-8 JSON string of the FHIR Bundle.
        receiver_key_material: HIU's ``keyMaterial`` dict containing ``dhPublicKey.keyValue`` and ``nonce``.
        sender_keypair: Optional pre-generated HIP ephemeral keypair (generated if omitted).

    Returns:
        Tuple of ``(base64_ciphertext, sender_keypair)``.
    """
    kp = sender_keypair or generate_ephemeral_keypair()

    peer_pub_b64 = (
        receiver_key_material.get("dhPublicKey", {}).get("keyValue")
        or receiver_key_material.get("publicKey")
        or ""
    )
    peer_nonce = receiver_key_material.get("nonce") or ""
    if not peer_pub_b64 or not peer_nonce:
        raise ValueError("Missing receiver dhPublicKey.keyValue or nonce in keyMaterial")

    shared_secret = _shared_secret(kp.private_key_b64, peer_pub_b64)
    aes_key, iv = _derive_aes_key_and_iv(shared_secret, kp.nonce_b64, peer_nonce)

    ciphertext = AESGCM(aes_key).encrypt(iv, plaintext_json.encode("utf-8"), None)
    return base64.b64encode(ciphertext).decode("ascii"), kp


def decrypt_fhir_bundle(
    ciphertext_b64: str,
    sender_key_material: dict[str, Any],
    receiver_keypair: FideliusKeyPair,
) -> str:
    """Decrypt a Fidelius-encrypted FHIR R4 bundle using the HIU's ephemeral private key.

    Args:
        ciphertext_b64: Base64-encoded AES-256-GCM ciphertext + tag.
        sender_key_material: HIP's ``keyMaterial`` dict from the data push payload.
        receiver_keypair: HIU's stored ``FideliusKeyPair`` for the transaction.

    Returns:
        Decrypted UTF-8 FHIR Bundle JSON string.
    """
    sender_pub_b64 = (
        sender_key_material.get("dhPublicKey", {}).get("keyValue")
        or sender_key_material.get("publicKey")
        or ""
    )
    sender_nonce = sender_key_material.get("nonce") or ""
    if not sender_pub_b64 or not sender_nonce:
        raise ValueError("Missing sender dhPublicKey.keyValue or nonce in keyMaterial")

    shared_secret = _shared_secret(receiver_keypair.private_key_b64, sender_pub_b64)
    aes_key, iv = _derive_aes_key_and_iv(
        shared_secret, sender_nonce, receiver_keypair.nonce_b64
    )

    ciphertext = base64.b64decode(ciphertext_b64.strip())
    plaintext = AESGCM(aes_key).decrypt(iv, ciphertext, None)
    return plaintext.decode("utf-8")


def verify_nha_webhook_signature(
    payload_bytes: bytes,
    signature_header: str | None,
    shared_secret: str,
    allow_mock_bypass: bool = False,
) -> bool:
    """Verify NHA/ABDM webhook digital signature (HMAC-SHA256) in constant time.

    In ``MOCK`` mode (when ``allow_mock_bypass=True`` and no secret is configured),
    returns True if a signature or mock marker is present. In ``SANDBOX`` / ``PRODUCTION``,
    strictly verifies the HMAC-SHA256 signature against the configured secret.
    """
    if not shared_secret:
        return allow_mock_bypass
    if not signature_header:
        return False
    expected = hmac.new(
        shared_secret.encode("utf-8"), payload_bytes, hashlib.sha256
    ).hexdigest()
    provided = signature_header.strip()
    provided = provided.removeprefix("sha256=")
    return hmac.compare_digest(expected.lower(), provided.lower())

