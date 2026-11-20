"""Versioned AES-256-GCM field encryption with Fernet read compatibility."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import String, TypeDecorator

from app.core.config import get_settings

settings = get_settings()


class FieldEncryptor:
    """Encrypt fields using random per-value DEKs wrapped by the selected KMS adapter."""
    def __init__(self, key: Optional[str] = None, kms=None) -> None:
        self._kms = kms
        # Keep the historical key dedicated to reading unprefixed Fernet rows.
        self._legacy = self._make_fernet(key or settings.ENCRYPTION_KEY)

    @staticmethod
    def _make_fernet(raw: str) -> Fernet:
        try:
            return Fernet(raw.encode())
        except Exception:
            return Fernet(base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest()))

    def _adapter(self):
        if self._kms is None:
            from app.core.cloud_adapters import get_kms_provider
            self._kms = get_kms_provider()
        return self._kms

    def encrypt(self, value: str) -> str:
        dek, wrapped = self._adapter().generate_data_key()
        nonce = os.urandom(12)
        ciphertext = AESGCM(dek).encrypt(nonce, value.encode("utf-8"), b"hms-field:v1")
        envelope = json.dumps({"dek": base64.b64encode(wrapped).decode("ascii"), "data": base64.b64encode(ciphertext).decode("ascii")}, separators=(",", ":")).encode()
        return "v1:{}:{}:{}".format(self._adapter().key_version, base64.b64encode(nonce).decode("ascii"), base64.b64encode(envelope).decode("ascii"))

    def decrypt(self, token: str) -> str:
        if token.startswith("v1:"):
            version, nonce_b64, payload_b64 = token.split(":", 3)[1:]
            envelope = json.loads(base64.b64decode(payload_b64, validate=True))
            dek = self._adapter().unwrap_dek(base64.b64decode(envelope["dek"], validate=True), version)
            plain = AESGCM(dek).decrypt(base64.b64decode(nonce_b64, validate=True), base64.b64decode(envelope["data"], validate=True), b"hms-field:v1")
            return plain.decode("utf-8")
        # Historical DB values are unprefixed Fernet tokens.
        try:
            return self._legacy.decrypt(token.encode()).decode("utf-8")
        except (InvalidToken, ValueError):
            raise


_encryptor: Optional[FieldEncryptor] = None

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

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        return None if value is None else encrypt_field(value)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        return None if value is None else decrypt_field(value)
