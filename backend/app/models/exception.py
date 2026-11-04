import uuid
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, utc_now


class ExceptionCategoryEnum(str, Enum):
    MISSING_INFORMATION = "MISSING_INFORMATION"
    MISSING_DOCUMENT = "MISSING_DOCUMENT"
    INCORRECT_DOCUMENT_TYPE = "INCORRECT_DOCUMENT_TYPE"
    UNREADABLE_DOCUMENT = "UNREADABLE_DOCUMENT"
    INVALID_IDENTIFIER_FORMAT = "INVALID_IDENTIFIER_FORMAT"
    PAN_MISMATCH = "PAN_MISMATCH"
    GST_MISMATCH = "GST_MISMATCH"
    LEGAL_NAME_MISMATCH = "LEGAL_NAME_MISMATCH"
    CONSTITUTION_MISMATCH = "CONSTITUTION_MISMATCH"
    BANK_DETAIL_MISMATCH = "BANK_DETAIL_MISMATCH"
    EXTERNAL_VERIFICATION_FAILURE = "EXTERNAL_VERIFICATION_FAILURE"
    EXTERNAL_VERIFICATION_UNAVAILABLE = "EXTERNAL_VERIFICATION_UNAVAILABLE"
    POTENTIAL_DUPLICATE_VENDOR = "POTENTIAL_DUPLICATE_VENDOR"
    EXPIRED_LICENCE = "EXPIRED_LICENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    HIGH_RISK_CHANGE = "HIGH_RISK_CHANGE"


class ExceptionSeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ExceptionStatusEnum(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    ACTION_REQUIRED_FROM_VENDOR = "ACTION_REQUIRED_FROM_VENDOR"
    RESPONSE_SUBMITTED = "RESPONSE_SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class ResolutionTypeEnum(str, Enum):
    CORRECTED_BY_VENDOR = "CORRECTED_BY_VENDOR"
    VERIFIED_MANUALLY = "VERIFIED_MANUALLY"
    WAIVED_WITH_JUSTIFICATION = "WAIVED_WITH_JUSTIFICATION"
    OVERRIDDEN_BY_ADMIN = "OVERRIDDEN_BY_ADMIN"
    DISMISSED_AS_FALSE_POSITIVE = "DISMISSED_AS_FALSE_POSITIVE"
    REJECTED = "REJECTED"


class OnboardingException(Base, TimestampMixin):
    """
    First-class Exception model representing an unresolved validation, compliance,
    or documentation issue requiring human judgment or vendor clarification.
    """
    __tablename__ = "onboarding_exceptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference_number = Column(String(50), unique=True, index=True, nullable=False)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(String(36), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)

    category = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), default=ExceptionSeverityEnum.MEDIUM.value, nullable=False, index=True)

    source_check_ids_json = Column(Text, default="[]", nullable=False)  # JSON array of check IDs
    source_finding_id = Column(String(36), ForeignKey("validation_findings.id", ondelete="SET NULL"), nullable=True)

    related_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    related_version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    related_field_name = Column(String(100), nullable=True)

    assigned_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_role = Column(String(50), nullable=True)  # reviewer, procurement_officer, vendor, admin
    status = Column(String(50), default=ExceptionStatusEnum.OPEN.value, nullable=False, index=True)

    vendor_action_instruction = Column(Text, nullable=True)  # Specific, plain-language instruction for the vendor
    resolution_type = Column(String(50), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    created_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_role = Column(String(50), default="SYSTEM", nullable=False)

    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    application = relationship("Application", backref="exceptions")
    vendor = relationship("Vendor", backref="exceptions")
    organization = relationship("Organization")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_user_id])
    related_document = relationship("Document", foreign_keys=[related_document_id])
    related_version = relationship("DocumentVersion", foreign_keys=[related_version_id])

    transitions = relationship(
        "ExceptionTransition",
        back_populates="exception",
        cascade="all, delete-orphan",
        order_by="ExceptionTransition.created_at.asc()",
    )
    comments = relationship(
        "ExceptionComment",
        back_populates="exception",
        cascade="all, delete-orphan",
        order_by="ExceptionComment.created_at.asc()",
    )
    field_corrections = relationship(
        "FieldCorrectionRecord",
        back_populates="exception",
        cascade="all, delete-orphan",
        order_by="FieldCorrectionRecord.created_at.asc()",
    )


class ExceptionTransition(Base):
    """
    Immutable audit history of status changes and actor transitions for an exception.
    """
    __tablename__ = "exception_transitions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exception_id = Column(String(36), ForeignKey("onboarding_exceptions.id", ondelete="CASCADE"), nullable=False, index=True)

    from_status = Column(String(50), nullable=False)
    to_status = Column(String(50), nullable=False)
    actor_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_role = Column(String(50), nullable=False)

    reason = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    exception = relationship("OnboardingException", back_populates="transitions")
    actor = relationship("User")


class ExceptionComment(Base):
    """
    Collaborative communication thread for an exception.
    Supports strict isolation of internal reviewer notes from vendor-facing clarification messages.
    """
    __tablename__ = "exception_comments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exception_id = Column(String(36), ForeignKey("onboarding_exceptions.id", ondelete="CASCADE"), nullable=False, index=True)

    author_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author_role = Column(String(50), nullable=False)

    is_internal = Column(Boolean, default=False, nullable=False, index=True)  # True = Reviewer/Admin only; False = Vendor visible
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    exception = relationship("OnboardingException", back_populates="comments")
    author = relationship("User")


class FieldCorrectionRecord(Base):
    """
    Immutable historical audit log of field-level corrections made during exception resolution.
    Preserves original and revised values.
    """
    __tablename__ = "field_correction_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exception_id = Column(String(36), ForeignKey("onboarding_exceptions.id", ondelete="SET NULL"), nullable=True, index=True)
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)

    field_name = Column(String(100), nullable=False, index=True)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    changed_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_by_role = Column(String(50), nullable=False)
    vendor_explanation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    exception = relationship("OnboardingException", back_populates="field_corrections")
    application = relationship("Application")
    changed_by = relationship("User")
