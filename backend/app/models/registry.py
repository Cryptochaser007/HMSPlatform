"""Registry, referral and NHCX-aligned insurance workflow records."""
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TenantOwned


class HFRFacility(TenantOwned, Base):
    __tablename__ = "hfr_facilities"
    hfr_id: Mapped[Any] = mapped_column(String(100), unique=True)
    facility_name: Mapped[Any] = mapped_column(String(255), nullable=False)
    facility_type: Mapped[Any] = mapped_column(String(100))
    bridge_code: Mapped[Any] = mapped_column(String(100))
    address: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    registry_status: Mapped[Any] = mapped_column(String(40), nullable=False, default="PENDING")
    synced_at: Mapped[Any] = mapped_column(DateTime(timezone=True))
    source_payload: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)


class HPRPractitioner(TenantOwned, Base):
    __tablename__ = "hpr_practitioners"
    hpr_id: Mapped[Any] = mapped_column(String(100), unique=True)
    user_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"))
    practitioner_name: Mapped[Any] = mapped_column(String(255), nullable=False)
    registration_number: Mapped[Any] = mapped_column(String(100))
    bridge_code: Mapped[Any] = mapped_column(String(100))
    specialties: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    registry_status: Mapped[Any] = mapped_column(String(40), nullable=False, default="PENDING")
    synced_at: Mapped[Any] = mapped_column(DateTime(timezone=True))
    source_payload: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)


class Referral(TenantOwned, Base):
    __tablename__ = "referrals"
    patient_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False)
    encounter_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("encounters.id"))
    referral_type: Mapped[Any] = mapped_column(String(30), nullable=False, default="INTERNAL")
    source_department: Mapped[Any] = mapped_column(String(100))
    target_department: Mapped[Any] = mapped_column(String(100))
    target_facility_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("hfr_facilities.id"))
    practitioner_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("hpr_practitioners.id"))
    reason: Mapped[Any] = mapped_column(Text, nullable=False)
    clinical_summary: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[Any] = mapped_column(String(30), nullable=False, default="DRAFT")
    abdm_request_id: Mapped[Any] = mapped_column(String(100))
    referred_at: Mapped[Any] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[Any] = mapped_column(DateTime(timezone=True))


class InsurancePolicy(TenantOwned, Base):
    __tablename__ = "insurance_policies"
    patient_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False)
    payer_code: Mapped[Any] = mapped_column(String(100))
    payer_name: Mapped[Any] = mapped_column(String(255), nullable=False)
    policy_number_encrypted: Mapped[Any] = mapped_column(Text)
    member_id_encrypted: Mapped[Any] = mapped_column(Text)
    coverage: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    valid_from: Mapped[Any] = mapped_column(Date)
    valid_to: Mapped[Any] = mapped_column(Date)
    status: Mapped[Any] = mapped_column(String(30), nullable=False, default="ACTIVE")


class InsuranceClaim(TenantOwned, Base):
    __tablename__ = "insurance_claims"
    policy_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("insurance_policies.id"), nullable=False)
    patient_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("patients.id"), nullable=False)
    encounter_id: Mapped[Any] = mapped_column(UUID(as_uuid=False), ForeignKey("encounters.id"))
    claim_number: Mapped[Any] = mapped_column(String(100), unique=True)
    preauth_reference: Mapped[Any] = mapped_column(String(100))
    lifecycle_status: Mapped[Any] = mapped_column(String(30), nullable=False, default="DRAFT")
    requested_amount: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    approved_amount: Mapped[Any] = mapped_column(Numeric(12, 2))
    currency: Mapped[Any] = mapped_column(String(3), nullable=False, default="INR")
    nhcx_payload: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    submitted_at: Mapped[Any] = mapped_column(DateTime(timezone=True))
    adjudicated_at: Mapped[Any] = mapped_column(DateTime(timezone=True))
