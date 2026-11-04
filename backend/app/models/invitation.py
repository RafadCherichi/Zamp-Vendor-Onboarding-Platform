import uuid
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin


class InvitationStatusEnum(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class Invitation(Base, TimestampMixin):
    """
    Vendor invitation model for invitation-first onboarding.
    Only the SHA-256 hash of the cryptographically generated token is stored.
    """
    __tablename__ = "invitations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    invited_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    vendor_name = Column(String(255), nullable=False)
    vendor_email = Column(String(255), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)

    status = Column(String(20), default=InvitationStatusEnum.PENDING.value, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    custom_message = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)

    organization = relationship("Organization", back_populates="invitations")
    invited_by = relationship("User")

    @property
    def is_expired(self) -> bool:
        if self.status == InvitationStatusEnum.EXPIRED.value:
            return True
        now = datetime.now(timezone.utc)
        # Ensure expires_at is timezone-aware
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now > exp
