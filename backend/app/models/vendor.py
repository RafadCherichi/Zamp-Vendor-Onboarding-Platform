import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin


class Vendor(Base, TimestampMixin):
    """
    Stable vendor legal identity scoped to a buyer organisation.
    A vendor may have multiple applications over time (initial onboarding, renewals, etc.).
    """
    __tablename__ = "vendors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    legal_name = Column(String(255), nullable=False)
    trade_name = Column(String(255), nullable=True)
    constitution = Column(String(50), nullable=True)  # PROPRIETORSHIP, PARTNERSHIP, LLP, PVT_LTD, PUB_LTD
    pan = Column(String(10), nullable=True, index=True)

    # Relationships
    organization = relationship("Organization")
    created_by = relationship("User")
    applications = relationship("Application", back_populates="vendor", cascade="all, delete-orphan")
