import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin
from app.models.role import RoleEnum


class OrganisationMember(Base, TimestampMixin):
    """
    Organisation membership and role assignment table.
    Enforces organisation-level data isolation and role boundaries.
    """
    __tablename__ = "organisation_members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False, default=RoleEnum.VENDOR.value)
    is_active = Column(Boolean, default=True, nullable=False)

    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("organisation_id", "user_id", name="uq_org_member"),
    )
