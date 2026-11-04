import uuid
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimestampMixin, utc_now


class DocumentTypeEnum(str, Enum):
    PAN_PROOF = "PAN_PROOF"
    GST_CERTIFICATE = "GST_CERTIFICATE"
    CONSTITUTION_PROOF = "CONSTITUTION_PROOF"
    BANK_PROOF = "BANK_PROOF"
    SIGNATORY_PROOF = "SIGNATORY_PROOF"
    UDYAM_CERTIFICATE = "UDYAM_CERTIFICATE"
    INDUSTRY_LICENCE = "INDUSTRY_LICENCE"
    BUYER_SPECIFIC = "BUYER_SPECIFIC"


class Document(Base, TimestampMixin):
    """
    Logical document slot required for an onboarding application.
    May contain multiple versions over time as documents are replaced.
    """
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)

    document_type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    is_required = Column(Boolean, default=True, nullable=False)
    requirement_reason = Column(Text, nullable=True)
    status = Column(String(20), default="PENDING", nullable=False)  # PENDING, UPLOADED

    current_version_id = Column(String(36), nullable=True)

    # Relationships
    application = relationship("Application", back_populates="documents")
    organization = relationship("Organization")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan", order_by="desc(DocumentVersion.version_number)")

    @property
    def current_version(self):
        if self.versions:
            return self.versions[0]
        return None


class DocumentVersion(Base):
    """
    Immutable document file version record stored in private object storage.
    Preserves historical files when a vendor uploads a replacement.
    """
    __tablename__ = "document_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, default=1, nullable=False)

    storage_key = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=False)
    file_checksum = Column(String(64), nullable=False)  # SHA-256 hash of file content

    uploaded_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    document = relationship("Document", back_populates="versions")
    uploaded_by = relationship("User")
