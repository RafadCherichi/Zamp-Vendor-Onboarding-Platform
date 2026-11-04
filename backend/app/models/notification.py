import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, utc_now


class Notification(Base):
    """
    In-app notification system tracking exception tasks, assignments,
    vendor correction requests, and resolution updates.
    """
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False, index=True)  # ACTION_REQUIRED, CORRECTION_SUBMITTED, ASSIGNMENT, RESOLVED, REJECTED, ESCALATED
    entity_type = Column(String(50), nullable=False)  # EXCEPTION, APPLICATION
    entity_id = Column(String(50), nullable=False)

    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    organization = relationship("Organization")
    recipient = relationship("User")
