"""Cloud portability adapters for DEK wrapping and private object storage.

Optional cloud SDKs are imported only when their adapters are selected.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import quote

from app.core.config import get_settings

settings = get_settings()


class KMSProvider(ABC):
    key_version = "1"

    def generate_data_key(self) -> tuple[bytes, bytes]:
        """Return a fresh plaintext DEK and its wrapped representation."""
        dek = os.urandom(32)
        return dek, self.wrap_dek(dek)

    @abstractmethod
    def wrap_dek(self, dek: bytes) -> bytes: ...

    @abstractmethod
    def unwrap_dek(self, wrapped: bytes, key_version: str) -> bytes: ...


class EnvEnvelopeKMSAdapter(KMSProvider):
    """Free-tier envelope key derived from ENCRYPTION_MASTER_KEY."""
    def __init__(self, master_key: Optional[str] = None) -> None:
        self.key_version = os.environ.get("ENCRYPTION_KEY_VERSION", "1")
        secret = master_key or os.environ.get(f"ENCRYPTION_MASTER_KEY_V{self.key_version}") or getattr(settings, "ENCRYPTION_MASTER_KEY", "")
        if not secret and settings.ENVIRONMENT.lower() != "production":
            # Local/legacy deployments can start during migration; production must
            # provision the dedicated master key explicitly.
            secret = settings.ENCRYPTION_KEY
        if not secret or secret.startswith("CHANGE_ME"):
            raise RuntimeError("Set ENCRYPTION_MASTER_KEY to a strong secret before encryption use")
        self._key = hashlib.sha256(secret.encode()).digest()

    def wrap_dek(self, dek: bytes) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        nonce = os.urandom(12)
        return nonce + AESGCM(self._key).encrypt(nonce, dek, b"hms-dek:v1")

    def unwrap_dek(self, wrapped: bytes, key_version: str) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        if key_version == self.key_version:
            key = self._key
        else:
            old = os.environ.get(f"ENCRYPTION_MASTER_KEY_V{key_version}")
            if not old:
                raise ValueError(f"Missing historical envelope key ENCRYPTION_MASTER_KEY_V{key_version}")
            key = hashlib.sha256(old.encode()).digest()
        return AESGCM(key).decrypt(wrapped[:12], wrapped[12:], b"hms-dek:v1")


class AWSKMSAdapter(KMSProvider):
    def __init__(self, key_id: Optional[str] = None, region: str = "ap-south-1") -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("Install boto3 to use AWS KMS") from exc
        self._kms = boto3.client("kms", region_name=region)
        self._key_id = key_id or os.environ.get("AWS_KMS_KEY_ID")
        if not self._key_id:
            raise RuntimeError("AWS_KMS_KEY_ID is required for AWS KMS")
        # Ciphertext blob identifies the KMS key for decrypt; a delimiter-safe
        # marker avoids putting ARN colons into the v1 envelope field format.
        self.key_version = "aws"

    def wrap_dek(self, dek: bytes) -> bytes:
        return self._kms.encrypt(KeyId=self._key_id, Plaintext=dek, EncryptionContext={"application": "hms"})["CiphertextBlob"]

    def generate_data_key(self) -> tuple[bytes, bytes]:
        response = self._kms.generate_data_key(KeyId=self._key_id, KeySpec="AES_256", EncryptionContext={"application": "hms"})
        return response["Plaintext"], response["CiphertextBlob"]

    def unwrap_dek(self, wrapped: bytes, key_version: str) -> bytes:
        if key_version != "aws":
            raise ValueError(f"Unsupported AWS KMS envelope marker: {key_version}")
        return self._kms.decrypt(CiphertextBlob=wrapped, EncryptionContext={"application": "hms"})["Plaintext"]


class StorageProvider(ABC):
    @abstractmethod
    async def signed_url(self, object_key: str, expires_in: int = 300, **kwargs) -> str: ...

    @abstractmethod
    async def put_object(self, object_key: str, body: bytes, content_type: str = "application/octet-stream") -> dict: ...


class SupabaseStorageAdapter(StorageProvider):
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None, bucket: Optional[str] = None) -> None:
        self.url = (url or os.environ.get("SUPABASE_URL", "")).rstrip("/")
        self.key = key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        self.bucket = bucket or os.environ.get("SUPABASE_PRIVATE_BUCKET", "clinical-records")
        if not self.url or not self.key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")

    async def signed_url(self, object_key: str, expires_in: int = 300, **kwargs) -> str:
        import httpx
        path = quote(object_key, safe="/")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{self.url}/storage/v1/object/sign/{quote(self.bucket)}/{path}", headers={"apikey": self.key, "Authorization": f"Bearer {self.key}"}, json={"expiresIn": expires_in})
            response.raise_for_status()
            data = response.json()
        signed = data.get("signedURL") or data.get("signedUrl")
        if not signed:
            raise RuntimeError("Supabase Storage did not return a signed URL")
        return signed if signed.startswith("http") else f"{self.url}/storage/v1{signed}"

    async def put_object(self, object_key: str, body: bytes, content_type: str = "application/octet-stream") -> dict:
        import httpx
        path = quote(object_key, safe="/")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.url}/storage/v1/object/{quote(self.bucket)}/{path}",
                headers={"apikey": self.key, "Authorization": f"Bearer {self.key}",
                         "Content-Type": content_type, "x-upsert": "false"},
                content=body,
            )
            response.raise_for_status()
            return response.json() if response.content else {"stored": True}


class S3StorageAdapter(StorageProvider):
    def __init__(self, bucket: Optional[str] = None, region: str = "ap-south-1", kms_key_id: Optional[str] = None) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("Install boto3 to use S3") from exc
        self._s3 = boto3.client("s3", region_name=region)
        self.bucket = bucket or os.environ.get("AWS_S3_BUCKET")
        self.kms_key_id = kms_key_id or os.environ.get("AWS_KMS_KEY_ID")
        if not self.bucket or not self.kms_key_id:
            raise RuntimeError("AWS_S3_BUCKET and AWS_KMS_KEY_ID are required")

    async def signed_url(self, object_key: str, expires_in: int = 300, **kwargs) -> str:
        return self._s3.generate_presigned_url("get_object", Params={"Bucket": self.bucket, "Key": object_key, "ResponseContentType": kwargs.get("content_type", "application/octet-stream")}, ExpiresIn=expires_in)

    async def put_object(self, object_key: str, body: bytes, content_type: str = "application/octet-stream") -> dict:
        return self._s3.put_object(Bucket=self.bucket, Key=object_key, Body=body, ContentType=content_type, ServerSideEncryption="aws:kms", SSEKMSKeyId=self.kms_key_id)


def get_kms_provider() -> KMSProvider:
    return AWSKMSAdapter() if getattr(settings, "CLOUD_PROVIDER", "SUPABASE_FREE").upper() == "AWS" else EnvEnvelopeKMSAdapter()


def get_storage_provider() -> StorageProvider:
    return S3StorageAdapter() if getattr(settings, "CLOUD_PROVIDER", "SUPABASE_FREE").upper() == "AWS" else SupabaseStorageAdapter()
