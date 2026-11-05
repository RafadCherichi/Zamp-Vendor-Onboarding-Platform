import json
import uuid
from enum import Enum
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin


class ApplicationStatusEnum(str, Enum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


class ConstitutionEnum(str, Enum):
    PROPRIETORSHIP = "PROPRIETORSHIP"
    PARTNERSHIP = "PARTNERSHIP"
    LLP = "LLP"
    PVT_LTD = "PVT_LTD"
    PUB_LTD = "PUB_LTD"
    OTHER = "OTHER"


class Application(Base, TimestampMixin):
    """
    Onboarding application record submitted by a vendor to a buyer organisation.
    Maintains relational fields for all six business sections.
    """
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference_number = Column(String(50), unique=True, index=True, nullable=False)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(String(36), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    invitation_id = Column(String(36), ForeignKey("invitations.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    status = Column(String(30), default=ApplicationStatusEnum.DRAFT.value, nullable=False, index=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    # Reviewer Assignment & Decision Tracking
    assigned_reviewer_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    decision_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    clarification_requested_at = Column(DateTime(timezone=True), nullable=True)

    # Section 1: Business Identity
    legal_name = Column(String(255), nullable=False)
    trade_name = Column(String(255), nullable=True)
    constitution = Column(String(50), default=ConstitutionEnum.PROPRIETORSHIP.value, nullable=False)
    date_of_establishment = Column(String(20), nullable=True)  # YYYY-MM-DD
    registered_address = Column(Text, nullable=True)
    operating_address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)

    # Section 2: Tax & Registration
    pan = Column(String(10), nullable=True, index=True)
    is_gst_registered = Column(Boolean, default=False, nullable=False)
    gstin = Column(String(15), nullable=True, index=True)
    is_udyam_registered = Column(Boolean, default=False, nullable=False)
    udyam_number = Column(String(30), nullable=True, index=True)
    cin_llpin = Column(String(25), nullable=True, index=True)

    # Section 3: Authorised Contact
    contact_name = Column(String(255), nullable=True)
    contact_designation = Column(String(100), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_mobile = Column(String(20), nullable=True)
    authorised_signatory_name = Column(String(255), nullable=True)

    # Section 4: Banking Details
    bank_account_holder_name = Column(String(255), nullable=True)
    bank_account_number = Column(String(50), nullable=True)  # Protected/masked in presentation
    bank_ifsc = Column(String(15), nullable=True)
    bank_account_type = Column(String(20), default="CURRENT", nullable=True)  # CURRENT, SAVINGS
    bank_name = Column(String(100), nullable=True)

    # Section 5: Business Classification
    categories_json = Column(Text, default="[]", nullable=False)  # JSON array of category identifiers
    other_business_activity_description = Column(Text, nullable=True)  # Description when 'other' is selected

    @property
    def categories(self):
        if not self.categories_json:
            return []
        try:
            return json.loads(self.categories_json)
        except Exception:
            return []

    @categories.setter
    def categories(self, val):
        if val is None:
            self.categories_json = "[]"
        elif isinstance(val, (list, tuple)):
            self.categories_json = json.dumps(list(val))
        elif isinstance(val, str):
            self.categories_json = val

    # Section 6: Declarations and Consent
    declaration_accurate_info = Column(Boolean, default=False, nullable=False)
    declaration_authorised_rep = Column(Boolean, default=False, nullable=False)
    declaration_verification_consent = Column(Boolean, default=False, nullable=False)
    declaration_timestamp = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization")
    vendor = relationship("Vendor", back_populates="applications")
    invitation = relationship("Invitation")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    assigned_reviewer = relationship("User", foreign_keys=[assigned_reviewer_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])
    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")
