"""AES-256-GCM envelope format and historical Fernet reader tests."""
import base64
import json

from app.core.encryption import FieldEncryptor
from cryptography.fernet import Fernet


class TestKMS:
    key_version = "test-1"

    def wrap_dek(self, dek: bytes) -> bytes:
        return dek

    def unwrap_dek(self, wrapped: bytes, key_version: str) -> bytes:
        assert key_version == self.key_version
        return wrapped

    def generate_data_key(self):
        from os import urandom
        dek = urandom(32)
        return dek, dek


def test_aes_gcm_field_envelope_round_trip():
    encryptor = FieldEncryptor(kms=TestKMS())
    encrypted = encryptor.encrypt("sensitive-record")
    parts = encrypted.split(":")
    assert len(parts) == 4 and parts[:2] == ["v1", "test-1"]
    assert encryptor.decrypt(encrypted) == "sensitive-record"


def test_legacy_fernet_value_remains_readable():
    key = Fernet.generate_key().decode()
    legacy = Fernet(key.encode()).encrypt(b"historical-record").decode()
    assert FieldEncryptor(key=key, kms=TestKMS()).decrypt(legacy) == "historical-record"


def test_previous_json_envelope_remains_readable():
    cipher = FieldEncryptor(kms=TestKMS())
    prefix, key_id, nonce, content = cipher.encrypt("previous-envelope").split(":")
    wrapped, ciphertext = content.split(".")
    payload = base64.b64encode(json.dumps({"dek": wrapped, "data": ciphertext}).encode()).decode()
    assert cipher.decrypt(f"{prefix}:{key_id}:{nonce}:{payload}") == "previous-envelope"
