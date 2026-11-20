"""Registry, referral and NHCX-aligned insurance workflow records."""
from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.core.database import Base


class HFRFacility(Base):
    __tablename__ = "hfr_facilities"
    hfr_id = Column(String(100), unique=True)
    facility_name = Column(String(255), nullable=False)
    facility_type = Column(String(100))
    bridge_code = Column(String(100))
    address = Column(JSONB, nullable=False, default=dict)
    registry_status = Column(String(40), nullable=False, default="PENDING")
    synced_at = Column(DateTime(timezone=True))
    source_payload = Column(JSONB, nullable=False, default=dict)


class HPRPractitioner(Base):
    __tablename__ = "hpr_practitioners"
    hpr_id = Column(String(100), unique=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"))
    practitioner_name = Column(String(255), nullable=False)
    registration_number = Column(String(100))
    bridge_code = Column(String(100))
    specialties = Column(JSONB, nullable=False, default=list)
    registry_status = Column(String(40), nullable=False, default="PENDING")
    synced_at = Column(DateTime(timezone=True))
    source_payload = Column(JSONB, nullable=False, default=dict)


class Referral(Base):
    __tablename__ = "referrals"
    patient_id = Column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False)
    encounter_id = Column(UUID(as_uuid=False), ForeignKey("encounters.id"))
    referral_type = Column(String(30), nullable=False, default="INTERNAL")
    source_department = Column(String(100))
    target_department = Column(String(100))
    target_facility_id = Column(UUID(as_uuid=False), ForeignKey("hfr_facilities.id"))
    practitioner_id = Column(UUID(as_uuid=False), ForeignKey("hpr_practitioners.id"))
    reason = Column(Text, nullable=False)
    clinical_summary = Column(JSONB, nullable=False, default=dict)
    status = Column(String(30), nullable=False, default="DRAFT")
    abdm_request_id = Column(String(100))
    referred_at = Column(DateTime(timezone=True))
    responded_at = Column(DateTime(timezone=True))


class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"
    patient_id = Column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False)
    payer_code = Column(String(100))
    payer_name = Column(String(255), nullable=False)
    policy_number_encrypted = Column(Text)
    member_id_encrypted = Column(Text)
    coverage = Column(JSONB, nullable=False, default=dict)
    valid_from = Column(Date)
    valid_to = Column(Date)
    status = Column(String(30), nullable=False, default="ACTIVE")


class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"
    policy_id = Column(UUID(as_uuid=False), ForeignKey("insurance_policies.id"), nullable=False)
    patient_id = Column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False)
    encounter_id = Column(UUID(as_uuid=False), ForeignKey("encounters.id"))
    claim_number = Column(String(100), unique=True)
    preauth_reference = Column(String(100))
    lifecycle_status = Column(String(30), nullable=False, default="DRAFT")
    requested_amount = Column(Numeric(12, 2), nullable=False, default=0)
    approved_amount = Column(Numeric(12, 2))
    currency = Column(String(3), nullable=False, default="INR")
    nhcx_payload = Column(JSONB, nullable=False, default=dict)
    submitted_at = Column(DateTime(timezone=True))
    adjudicated_at = Column(DateTime(timezone=True))
