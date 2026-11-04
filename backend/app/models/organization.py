import uuid
from sqlalchemy import Column, String, Text, Boolean
from app.database import Base
from app.models.base import TimestampMixin


class Organization(Base, TimestampMixin):
    """
    Buyer workspace organisation model.
    Represents an onboarder / buyer organisation context.
    """
    __tablename__ = "organisations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    policy_version = Column(String(50), default="1.0.0", nullable=False)
    settings = Column(Text, nullable=True)  # JSON-encoded string for flexible settings
