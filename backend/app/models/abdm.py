"""SQLAlchemy models for ABDM v3 Sandbox Exit compliance (M1, M2, M3 & WASA audit)."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class ABDMShareProfile(Base):
    """M1: ABHA QR Scan & Share counter check-in profiles."""

    __tablename__ = "abdm_share_profiles"

    request_id = Column(String(100), unique=True, nullable=False, index=True)
    hip_id = Column(String(100), nullable=False)
    counter_id = Column(String(100), nullable=True)
    token_number = Column(String(20), nullable=False)
    abha_number = Column(String(50), nullable=True)
    abha_address = Column(String(255), nullable=False, index=True)
    patient_name = Column(String(255), nullable=False)
    gender = Column(String(20), nullable=False)
    year_of_birth = Column(Integer, nullable=True)
    mobile_masked = Column(String(32), nullable=True)
    patient_id = Column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=True)
    status = Column(String(30), nullable=False, default="PENDING_CHECKIN")
    expires_at = Column(DateTime(timezone=True), nullable=False)


class ABDMCareContextLink(Base):
    """M2: Care context discovery and linking ledger."""

    __tablename__ = "abdm_care_context_links"

    patient_id = Column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=True, index=True)
    abha_address = Column(String(255), nullable=False, index=True)
    patient_reference = Column(String(100), nullable=False)
    care_context_ref = Column(String(100), nullable=False)
    care_context_display = Column(String(255), nullable=False)
    link_ref_number = Column(String(100), nullable=True, index=True)
    transaction_id = Column(String(100), nullable=True)
    auth_mode = Column(String(30), nullable=False, default="MOBILE_OTP")
    linking_type = Column(String(30), nullable=False, default="USER_INITIATED")
    status = Column(String(30), nullable=False, default="PENDING")
    linked_at = Column(DateTime(timezone=True), nullable=True)


class ABDMConsentArtefact(Base):
    """M2 & M3: Immutable ABDM Consent Artefacts ledger (HIP & HIU)."""

    __tablename__ = "abdm_consent_artefacts"

    consent_id = Column(String(100), unique=True, nullable=False, index=True)
    consent_request_id = Column(String(100), nullable=True, index=True)
    role = Column(String(10), nullable=False)  # HIP | HIU
    patient_abha = Column(String(255), nullable=False, index=True)
    purpose_code = Column(String(50), nullable=False, default="CAREMGT")
    purpose_text = Column(String(255), nullable=False, default="Care Management")
    status = Column(String(30), nullable=False, default="REQUESTED")
    hi_types = Column(JSONB, nullable=False, default=list)
    care_contexts = Column(JSONB, nullable=False, default=list)
    date_from = Column(DateTime(timezone=True), nullable=False)
    date_to = Column(DateTime(timezone=True), nullable=False)
    data_erase_at = Column(DateTime(timezone=True), nullable=False)
    hip_id = Column(String(100), nullable=True)
    hiu_id = Column(String(100), nullable=True)
    requester_name = Column(String(255), nullable=True)
    requester_user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    signature = Column(Text, nullable=True)
    signature_verified = Column(Boolean, nullable=False, default=False)
    artefact_payload = Column(JSONB, nullable=False, default=dict)


class ABDMTransactionLog(Base):
    """WASA & NHA Evidence: Append-only immutable ABDM API transaction audit log."""

    __tablename__ = "abdm_transaction_logs"

    request_id = Column(String(100), nullable=False, index=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    direction = Column(String(16), nullable=False)  # OUTBOUND | INBOUND
    abdm_env = Column(String(20), nullable=False, default="MOCK")
    x_cm_id = Column(String(50), nullable=True)
    http_method = Column(String(10), nullable=False)
    endpoint = Column(String(500), nullable=False)
    http_status = Column(Integer, nullable=True)
    payload_sha256 = Column(String(64), nullable=False)
    masked_summary = Column(JSONB, nullable=False, default=dict)
    error_code = Column(String(100), nullable=True)
    user_id = Column(UUID(as_uuid=False), nullable=True)
