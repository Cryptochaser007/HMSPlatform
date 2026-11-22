"""SQLAlchemy models for ABDM v3 Sandbox Exit compliance (M1, M2, M3 & WASA audit)."""

from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TenantOwned


class ABDMShareProfile(TenantOwned, Base):
    """M1: ABHA QR Scan & Share counter check-in profiles."""

    __tablename__ = "abdm_share_profiles"

    request_id: Mapped[Any] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hip_id: Mapped[Any] = mapped_column(String(100), nullable=False)
    counter_id: Mapped[Any] = mapped_column(String(100), nullable=True)
    token_number: Mapped[Any] = mapped_column(String(20), nullable=False)
    abha_number: Mapped[Any] = mapped_column(String(50), nullable=True)
    abha_address: Mapped[Any] = mapped_column(String(255), nullable=False, index=True)
    patient_name: Mapped[Any] = mapped_column(String(255), nullable=False)
    gender: Mapped[Any] = mapped_column(String(20), nullable=False)
    year_of_birth: Mapped[Any] = mapped_column(Integer, nullable=True)
    mobile_masked: Mapped[Any] = mapped_column(String(32), nullable=True)
    patient_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=True)
    status: Mapped[Any] = mapped_column(String(30), nullable=False, default="PENDING_CHECKIN")
    expires_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)


class ABDMCareContextLink(TenantOwned, Base):
    """M2: Care context discovery and linking ledger."""

    __tablename__ = "abdm_care_context_links"

    patient_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=True, index=True)
    abha_address: Mapped[Any] = mapped_column(String(255), nullable=False, index=True)
    patient_reference: Mapped[Any] = mapped_column(String(100), nullable=False)
    care_context_ref: Mapped[Any] = mapped_column(String(100), nullable=False)
    care_context_display: Mapped[Any] = mapped_column(String(255), nullable=False)
    link_ref_number: Mapped[Any] = mapped_column(String(100), nullable=True, index=True)
    transaction_id: Mapped[Any] = mapped_column(String(100), nullable=True)
    auth_mode: Mapped[Any] = mapped_column(String(30), nullable=False, default="MOBILE_OTP")
    linking_type: Mapped[Any] = mapped_column(String(30), nullable=False, default="USER_INITIATED")
    status: Mapped[Any] = mapped_column(String(30), nullable=False, default="PENDING")
    linked_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=True)


class ABDMConsentArtefact(TenantOwned, Base):
    """M2 & M3: Immutable ABDM Consent Artefacts ledger (HIP & HIU)."""

    __tablename__ = "abdm_consent_artefacts"

    consent_id: Mapped[Any] = mapped_column(String(100), unique=True, nullable=False, index=True)
    consent_request_id: Mapped[Any] = mapped_column(String(100), nullable=True, index=True)
    role: Mapped[Any] = mapped_column(String(10), nullable=False)  # HIP | HIU
    patient_abha: Mapped[Any] = mapped_column(String(255), nullable=False, index=True)
    purpose_code: Mapped[Any] = mapped_column(String(50), nullable=False, default="CAREMGT")
    purpose_text: Mapped[Any] = mapped_column(String(255), nullable=False, default="Care Management")
    status: Mapped[Any] = mapped_column(String(30), nullable=False, default="REQUESTED")
    hi_types: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    care_contexts: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    date_from: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
    date_to: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
    data_erase_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
    hip_id: Mapped[Any] = mapped_column(String(100), nullable=True)
    hiu_id: Mapped[Any] = mapped_column(String(100), nullable=True)
    requester_name: Mapped[Any] = mapped_column(String(255), nullable=True)
    requester_user_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    signature: Mapped[Any] = mapped_column(Text, nullable=True)
    signature_verified: Mapped[Any] = mapped_column(Boolean, nullable=False, default=False)
    artefact_payload: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)


class ABDMTransactionLog(TenantOwned, Base):
    """WASA & NHA Evidence: Append-only immutable ABDM API transaction audit log."""

    __tablename__ = "abdm_transaction_logs"

    request_id: Mapped[Any] = mapped_column(String(100), nullable=False, index=True)
    correlation_id: Mapped[Any] = mapped_column(String(100), nullable=True, index=True)
    direction: Mapped[Any] = mapped_column(String(16), nullable=False)  # OUTBOUND | INBOUND
    abdm_env: Mapped[Any] = mapped_column(String(20), nullable=False, default="MOCK")
    x_cm_id: Mapped[Any] = mapped_column(String(50), nullable=True)
    http_method: Mapped[Any] = mapped_column(String(10), nullable=False)
    endpoint: Mapped[Any] = mapped_column(String(500), nullable=False)
    http_status: Mapped[Any] = mapped_column(Integer, nullable=True)
    payload_sha256: Mapped[Any] = mapped_column(String(64), nullable=False)
    masked_summary: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    error_code: Mapped[Any] = mapped_column(String(100), nullable=True)
    user_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), nullable=True)

