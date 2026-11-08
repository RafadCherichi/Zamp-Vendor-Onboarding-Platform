import uuid
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from app.database import Base
from app.models.base import TimestampMixin, utc_now


class ProcessingStatusEnum(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"


class ExtractionMethodEnum(str, Enum):
    PDF_TEXT = "PDF_TEXT"
    OCR_VISION = "OCR_VISION"
    DETERMINISTIC_PARSER = "DETERMINISTIC_PARSER"
    AI_ASSISTED = "AI_ASSISTED"


class DocumentProcessingJob(Base, TimestampMixin):
    """
    Tracks the execution lifecycle and retries of a background document processing task.
    """
    __tablename__ = "document_processing_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(String(20), default=ProcessingStatusEnum.QUEUED.value, nullable=False, index=True)
    stage = Column(String(32), nullable=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Relationships
    document_version = relationship("DocumentVersion", backref="processing_jobs")


class DocumentExtractionResult(Base, TimestampMixin):
    """
    Persisted extraction results for a specific document version.
    Includes OCR text, classification decision, and review flags.
    """
    __tablename__ = "document_extraction_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(String(20), default=ProcessingStatusEnum.EXTRACTED.value, nullable=False, index=True)
    detected_document_type = Column(String(50), nullable=True)
    classification_confidence = Column(Float, nullable=True)
    classification_reason = Column(Text, nullable=True)
    is_type_match = Column(Boolean, default=True, nullable=False)

    page_count = Column(Integer, default=1, nullable=False)
    raw_text = Column(Text, nullable=True)
    provider_used = Column(String(50), default="LOCAL_PIPELINE", nullable=False)
    review_flags_json = Column(Text, nullable=True)  # JSON array of warning/flag strings

    # Relationships
    document_version = relationship("DocumentVersion", backref=backref("extraction_result", uselist=False))
    document = relationship("Document", backref="extractions")
    application = relationship("Application", backref="document_extractions")
    fields = relationship("ExtractedField", back_populates="extraction_result", cascade="all, delete-orphan", order_by="ExtractedField.field_name")


class ExtractedField(Base, TimestampMixin):
    """
    Individual structured field extracted from the document with provenance and confidence.
    """
    __tablename__ = "extracted_fields"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    extraction_result_id = Column(String(36), ForeignKey("document_extraction_results.id", ondelete="CASCADE"), nullable=False, index=True)

    field_name = Column(String(100), nullable=False, index=True)
    extracted_value = Column(Text, nullable=False)
    normalized_value = Column(Text, nullable=True)
    confidence_score = Column(Float, default=1.0, nullable=False)

    page_number = Column(Integer, default=1, nullable=False)
    evidence_text = Column(Text, nullable=True)
    bounding_box_json = Column(Text, nullable=True)
    extraction_method = Column(String(50), default=ExtractionMethodEnum.DETERMINISTIC_PARSER.value, nullable=False)

    # Relationships
    extraction_result = relationship("DocumentExtractionResult", back_populates="fields")
