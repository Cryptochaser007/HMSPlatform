"""Versioned AES-256-GCM field encryption with Fernet read compatibility."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import String, TypeDecorator

from app.core.config import get_settings

settings = get_settings()


class FieldEncryptor:
    """Encrypt fields using random per-value DEKs wrapped by the selected KMS adapter."""
    def __init__(self, key: str | None = None, kms=None) -> None:
        self._kms = kms
        self._envelope_writes = kms is not None
        self._key_secret = key or settings.ENCRYPTION_MASTER_KEY or settings.ENCRYPTION_KEY
        # Keep the historical key dedicated to reading unprefixed Fernet rows.
        self._legacy = self._make_fernet(key or settings.ENCRYPTION_KEY)

    @staticmethod
    def _make_fernet(raw: str) -> Fernet:
        try:
            return Fernet(raw.encode())
        except Exception:
            logging.getLogger(__name__).exception("Operation failed at an application boundary", exc_info=False)
            return Fernet(base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest()))

    def _adapter(self):
        if self._kms is None:
            from app.core.cloud_adapters import get_kms_provider
            self._kms = get_kms_provider()
        return self._kms

    def encrypt(self, value: str) -> str:
        if not self._envelope_writes:
            nonce = os.urandom(12)
            ciphertext = AESGCM(self._direct_key()).encrypt(nonce, value.encode("utf-8"), b"hms-field:v1")
            return "v1:{}:{}".format(base64.b64encode(nonce).decode("ascii"),
                                     base64.b64encode(ciphertext).decode("ascii"))
        dek, wrapped = self._adapter().generate_data_key()
        nonce = os.urandom(12)
        ciphertext = AESGCM(dek).encrypt(nonce, value.encode("utf-8"), b"hms-field:v1")
        # Four-part, delimiter-safe envelope: version, key identifier, nonce,
        # and wrapped DEK + authenticated ciphertext/tag. Base64 preserves the
        # binary 12-byte nonce and KMS ciphertext in a database-safe string.
        payload = base64.b64encode(wrapped).decode("ascii") + "." + base64.b64encode(ciphertext).decode("ascii")
        return "v1:{}:{}:{}".format(
            self._adapter().key_version,
            base64.b64encode(nonce).decode("ascii"),
            payload,
        )

    def decrypt(self, token: str) -> str:
        if token.startswith("v1:"):
            if token.count(":") == 2:
                _, nonce, ciphertext = token.split(":")
                return AESGCM(self._direct_key()).decrypt(
                    base64.b64decode(nonce, validate=True),
                    base64.b64decode(ciphertext, validate=True), b"hms-field:v1",
                ).decode("utf-8")
            version, nonce_b64, payload_b64 = token.split(":", 3)[1:]
            if "." in payload_b64:
                wrapped_b64, ciphertext_b64 = payload_b64.split(".", 1)
            else:
                # Read the earlier v1 JSON envelope written by the initial
                # AES-GCM rollout; new writes use the compact four-field form.
                legacy_envelope = json.loads(base64.b64decode(payload_b64, validate=True))
                wrapped_b64 = legacy_envelope["dek"]
                ciphertext_b64 = legacy_envelope["data"]
            dek = self._adapter().unwrap_dek(base64.b64decode(wrapped_b64, validate=True), version)
            plain = AESGCM(dek).decrypt(base64.b64decode(nonce_b64, validate=True), base64.b64decode(ciphertext_b64, validate=True), b"hms-field:v1")
            return plain.decode("utf-8")
        # Historical DB values are unprefixed Fernet tokens.
        return self._legacy.decrypt(token.encode()).decode("utf-8")

    def _direct_key(self) -> bytes:
        if not self._key_secret or self._key_secret.startswith("CHANGE_ME"):
            raise RuntimeError("Configure the existing encryption secret before encrypting fields")
        return hashlib.sha256(self._key_secret.encode("utf-8")).digest()


_encryptor: FieldEncryptor | None = None

def _get_encryptor() -> FieldEncryptor:
    global _encryptor
    if _encryptor is None:
        _encryptor = FieldEncryptor()
    return _encryptor

def encrypt_field(value: str) -> str:
    return _get_encryptor().encrypt(value)

def decrypt_field(token: str) -> str:
    return _get_encryptor().decrypt(token)

def hash_field(value: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), value.lower().strip().encode(), hashlib.sha256).hexdigest()

class EncryptedType(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        return None if value is None else encrypt_field(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        return None if value is None else decrypt_field(value)
