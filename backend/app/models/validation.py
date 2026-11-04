import uuid
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, utc_now


class ValidationStatusEnum(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    UNVERIFIED = "UNVERIFIED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ValidationSeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ValidationLayerEnum(str, Enum):
    LAYER_A_INPUT = "LAYER_A_INPUT"
    LAYER_B_CONSISTENCY = "LAYER_B_CONSISTENCY"
    LAYER_C_EXTERNAL = "LAYER_C_EXTERNAL"
    LAYER_D_DUPLICATE = "LAYER_D_DUPLICATE"


class VerificationStatusEnum(str, Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNVERIFIED = "UNVERIFIED"
    UNAVAILABLE = "UNAVAILABLE"


class ValidationRun(Base, TimestampMixin):
    """
    Tracks an evaluation run across the validation layers for an application.
    """
    __tablename__ = "validation_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)

    run_type = Column(String(50), default="FULL", nullable=False)  # FULL, SELECTIVE, DEPENDENCY_UPDATE
    status = Column(String(50), default="COMPLETED", nullable=False)
    summary = Column(Text, nullable=True)

    passed_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    warning_count = Column(Integer, default=0, nullable=False)
    unverified_count = Column(Integer, default=0, nullable=False)
    unavailable_count = Column(Integer, default=0, nullable=False)

    is_current = Column(Boolean, default=True, nullable=False, index=True)
    triggered_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    trigger_reason = Column(String(255), nullable=True)

    # Relationships
    application = relationship("Application", backref="validation_runs")
    organization = relationship("Organization")
    findings = relationship("ValidationFinding", back_populates="validation_run", cascade="all, delete-orphan", order_by="ValidationFinding.id")


class ValidationFinding(Base, TimestampMixin):
    """
    Individual granular check finding with explainability, values compared, and recommendation.
    """
    __tablename__ = "validation_findings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    validation_run_id = Column(String(36), ForeignKey("validation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)

    check_id = Column(String(100), nullable=False, index=True)
    layer = Column(String(50), nullable=False, index=True)
    check_name = Column(String(255), nullable=False)
    status = Column(String(50), default=ValidationStatusEnum.PASSED.value, nullable=False, index=True)
    severity = Column(String(50), default=ValidationSeverityEnum.MEDIUM.value, nullable=False)

    source_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    source_version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)

    submitted_value = Column(Text, nullable=True)
    extracted_value = Column(Text, nullable=True)
    external_value = Column(Text, nullable=True)

    evidence = Column(Text, nullable=True)
    explanation = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=True)

    is_stale = Column(Boolean, default=False, nullable=False, index=True)
    stale_reason = Column(String(255), nullable=True)

    # Relationships
    validation_run = relationship("ValidationRun", back_populates="findings")


class ExternalVerificationRecord(Base, TimestampMixin):
    """
    Record of simulated or third-party authoritative verification query.
    """
    __tablename__ = "external_verification_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)

    verification_type = Column(String(50), nullable=False, index=True)  # PAN, GST, MCA, UDYAM, BANK_ACCOUNT
    provider_name = Column(String(150), nullable=False)
    request_id = Column(String(100), nullable=False, index=True)
    submitted_identifier = Column(String(100), nullable=False)  # Masked where appropriate
    status = Column(String(50), default=VerificationStatusEnum.UNVERIFIED.value, nullable=False, index=True)

    is_simulated = Column(Boolean, default=True, nullable=False)
    returned_attributes_json = Column(Text, nullable=True)  # Authoritative attributes from provider
    reason = Column(Text, nullable=True)
    duration_ms = Column(Integer, default=0, nullable=False)

    # Relationships
    application = relationship("Application", backref="external_verifications")
    organization = relationship("Organization")


class DuplicateSignal(Base, TimestampMixin):
    """
    Signal indicating a potential duplicate vendor/application for human review.
    """
    __tablename__ = "duplicate_signals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)

    candidate_application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_vendor_id = Column(String(36), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)

    match_strength = Column(String(20), default="MODERATE", nullable=False)  # STRONG, MODERATE, WEAK
    matching_attributes_json = Column(Text, nullable=False)  # e.g. ["PAN", "GSTIN"]
    explanation = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    is_dismissed = Column(Boolean, default=False, nullable=False)

    # Relationships
    application = relationship("Application", foreign_keys=[application_id], backref="duplicate_signals_source")
    candidate_application = relationship("Application", foreign_keys=[candidate_application_id])
    candidate_vendor = relationship("Vendor")
