"""Stage 2 tests: Cloud adapters portability and tenant onboarding."""
import os
import pytest
from fastapi.testclient import TestClient

from app.core.cloud_adapters import (
    EnvKEKAdapter,
    EnvEnvelopeKMSAdapter,
    AWSKMSAdapter,
    SupabaseStorageAdapter,
    S3StorageAdapter,
    get_kms_provider,
    get_storage_provider,
)
from app.core.config import get_settings
from app.core.encryption import FieldEncryptor
from app.main import app

client = TestClient(app)


def test_env_kek_adapter_generate_and_wrap():
    """Verify EnvKEKAdapter generates and wraps 256-bit DEKs."""
    adapter = EnvKEKAdapter(master_key="stage2-test-master-key-32bytes-min!!")
    dek, wrapped = adapter.generate_data_key()
    assert len(dek) == 32
    assert len(wrapped) > 32
    unwrapped = adapter.unwrap_dek(wrapped, adapter.key_version)
    assert unwrapped == dek


def test_field_encryptor_with_env_kek_adapter():
    """Verify FieldEncryptor roundtrip with EnvKEKAdapter."""
    adapter = EnvKEKAdapter(master_key="stage2-test-master-key-32bytes-min!!")
    encryptor = FieldEncryptor(kms=adapter)
    plaintext = "ABHA-Sensitive-Patient-Data-1234"
    encrypted = encryptor.encrypt(plaintext)
    assert encrypted.startswith("v1:1:")
    decrypted = encryptor.decrypt(encrypted)
    assert decrypted == plaintext


def test_cloud_provider_factories():
    """Verify factory returns appropriate adapter based on CLOUD_PROVIDER."""
    # Free tier default
    kms = get_kms_provider()
    assert isinstance(kms, EnvKEKAdapter)
    storage = get_storage_provider()
    assert isinstance(storage, SupabaseStorageAdapter)


def test_supabase_storage_adapter_initialization():
    """Verify SupabaseStorageAdapter properties."""
    adapter = SupabaseStorageAdapter(
        url="https://mock-proj.supabase.co",
        key="mock-service-role-key",
        bucket="clinical-records",
    )
    assert adapter.url == "https://mock-proj.supabase.co"
    assert adapter.bucket == "clinical-records"


def test_health_check_endpoint():
    """Verify system health check endpoint for Render/Vercel smoke testing."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "abdm_env" in data
    assert "environment" in data


def test_tenant_registration_validation():
    """Verify /api/v1/tenants/register validates payload constraints."""
    invalid_payload = {
        "hospital_name": "",  # Too short
        "hospital_code": "invalid code with spaces!",  # Invalid pattern
        "admin_name": "Dr",
        "admin_email": "not-an-email",
        "admin_password": "short",
    }
    response = client.post("/api/v1/tenants/register", json=invalid_payload)
    assert response.status_code == 422
