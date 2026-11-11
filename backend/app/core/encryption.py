"""
Field-level encryption for PII columns.

Provides:
- ``FieldEncryptor``  – encrypts / decrypts arbitrary strings with Fernet.
- ``EncryptedType``   – SQLAlchemy ``TypeDecorator`` that transparently
  encrypts on write and decrypts on read.
- ``hash_field``      – HMAC-SHA256 for searchable encrypted fields.
"""

import base64
import hashlib
import hmac
from typing import Optional

from cryptography.fernet import Fernet
from sqlalchemy import String, TypeDecorator

from app.core.config import get_settings

settings = get_settings()


class FieldEncryptor:
    """Symmetric Fernet encryption helper bound to the app's ENCRYPTION_KEY."""

    def __init__(self, key: Optional[str] = None) -> None:
        raw_key = key or settings.ENCRYPTION_KEY
        # Fernet requires url-safe base64-encoded 32-byte key.
        # If the configured value is already valid, use it directly;
        # otherwise derive one via SHA-256 and base64-encode.
        try:
            self._fernet = Fernet(raw_key.encode())
        except Exception:
            derived = hashlib.sha256(raw_key.encode()).digest()
            self._fernet = Fernet(base64.urlsafe_b64encode(derived))

    def encrypt(self, value: str) -> str:
        """Encrypt *value* and return a URL-safe base64 ciphertext string."""
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, token: str) -> str:
        """Decrypt a ciphertext *token* back to the original plaintext."""
        return self._fernet.decrypt(token.encode()).decode()


# Module-level singleton
_encryptor: Optional[FieldEncryptor] = None


def _get_encryptor() -> FieldEncryptor:
    global _encryptor
    if _encryptor is None:
        _encryptor = FieldEncryptor()
    return _encryptor


def encrypt_field(value: str) -> str:
    """Encrypt a plaintext string and return base64-encoded ciphertext."""
    return _get_encryptor().encrypt(value)


def decrypt_field(token: str) -> str:
    """Decrypt a base64-encoded ciphertext back to plaintext."""
    return _get_encryptor().decrypt(token)


def hash_field(value: str) -> str:
    """Compute an HMAC-SHA256 digest of *value* for indexed search over
    encrypted columns.  The key is the application's ``SECRET_KEY``."""
    return hmac.new(
        settings.SECRET_KEY.encode(),
        value.lower().strip().encode(),
        hashlib.sha256,
    ).hexdigest()


# ── SQLAlchemy TypeDecorator ─────────────────────────────────────────────

class EncryptedType(TypeDecorator):
    """A SQLAlchemy column type that stores values encrypted at rest.

    Usage::

        class Patient(Base):
            first_name = Column(EncryptedType, nullable=False)
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:  # type: ignore[override]
        if value is None:
            return None
        return encrypt_field(value)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:  # type: ignore[override]
        if value is None:
            return None
        return decrypt_field(value)
