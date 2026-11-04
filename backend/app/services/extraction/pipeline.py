import io
import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.document import Document, DocumentVersion
from app.models.extraction import (
    DocumentProcessingJob,
    DocumentExtractionResult,
    ExtractedField,
    ProcessingStatusEnum,
)
from app.storage.local import get_storage_adapter
from app.services.ocr.engine import extract_document_text
from app.services.classification.classifier import classify_document
from app.services.extraction.providers.ai_gemini import GeminiExtractionProvider

logger = logging.getLogger(__name__)


def run_pipeline_for_document_version(
    document_version_id: str,
    db: Session,
    force_reprocess: bool = False,
) -> Optional[DocumentExtractionResult]:
    """
    Executes the full document processing pipeline:
    1. Retrieval from private storage
    2. OCR / text extraction (PDF / images)
    3. Document classification
    4. Structured field extraction with evidence
    5. Quality & ambiguity assessment
    6. Persistence of extraction results
    """
    start_time = time.time()

    # 1. Fetch version and document
    version = db.query(DocumentVersion).filter(DocumentVersion.id == document_version_id).first()
    if not version:
        logger.error(f"DocumentVersion {document_version_id} not found.")
        return None

    doc = db.query(Document).filter(Document.id == version.document_id).first()
    if not doc:
        logger.error(f"Parent Document for version {document_version_id} not found.")
        return None

    # Idempotency check: if already processed and not forcing reprocess, return existing result
    existing_result = (
        db.query(DocumentExtractionResult)
        .filter(DocumentExtractionResult.document_version_id == version.id)
        .first()
    )
    if existing_result and not force_reprocess and existing_result.status in [ProcessingStatusEnum.EXTRACTED.value, ProcessingStatusEnum.NEEDS_REVIEW.value]:
        logger.info(f"Version {version.id} already processed. Returning existing extraction result.")
        return existing_result

    # 2. Manage processing job
    job = (
        db.query(DocumentProcessingJob)
        .filter(DocumentProcessingJob.document_version_id == version.id)
        .first()
    )
    if not job:
        job = DocumentProcessingJob(
            document_version_id=version.id,
            status=ProcessingStatusEnum.PROCESSING.value,
            attempt_count=1,
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
    else:
        job.attempt_count += 1
        job.status = ProcessingStatusEnum.PROCESSING.value
        job.started_at = datetime.now(timezone.utc)
        job.error_message = None

    db.commit()

    try:
        # 3. Retrieve raw file bytes from private storage
        storage = get_storage_adapter()
        file_obj = storage.get_file(version.storage_key)
        if not file_obj:
            raise ValueError(f"Unable to read file from storage key '{version.storage_key}'")

        file_bytes = file_obj.read()

        # 4. Stage 1: OCR / Text extraction
        ocr_res = extract_document_text(file_bytes, version.content_type)

        # 5. Stage 2: Document classification
        classification = classify_document(ocr_res.full_text, doc.document_type)

        # 6. Stage 3: Structured field extraction
        provider = GeminiExtractionProvider()
        # Use predicted type or target document type for field extraction
        extraction_type = doc.document_type if classification.is_type_match else classification.predicted_type
        extracted_fields_data = provider.extract(ocr_res.full_text, extraction_type)

        # 7. Stage 4: Review flags and ambiguity detection
        review_flags: List[str] = []

        if ocr_res.is_unreadable:
            review_flags.append("Unreadable document: No legible text could be extracted. Manual scan review required.")
        elif ocr_res.average_confidence < 0.60:
            review_flags.append(f"Low OCR clarity: Average recognition confidence is {int(ocr_res.average_confidence * 100)}%. Verify extracted values.")

        if not classification.is_type_match and classification.predicted_type != "UNKNOWN":
            review_flags.append(
                f"Document type mismatch: Expected '{doc.document_type}', but uploaded file resembles '{classification.predicted_type}' ({int(classification.confidence * 100)}% match)."
            )

        if not extracted_fields_data and not ocr_res.is_unreadable:
            review_flags.append(f"No compliance fields extracted for document type '{extraction_type}'.")

        # 8. Determine final processing status
        if ocr_res.is_unreadable:
            final_status = ProcessingStatusEnum.NEEDS_REVIEW.value
        elif review_flags:
            final_status = ProcessingStatusEnum.NEEDS_REVIEW.value
        else:
            final_status = ProcessingStatusEnum.EXTRACTED.value

        duration_ms = int((time.time() - start_time) * 1000)

        # 10. Persist or update DocumentExtractionResult
        if existing_result:
            extraction_record = existing_result
            extraction_record.status = final_status
            extraction_record.detected_document_type = classification.predicted_type
            extraction_record.classification_confidence = classification.confidence
            extraction_record.classification_reason = classification.reason
            extraction_record.is_type_match = classification.is_type_match
            extraction_record.page_count = ocr_res.page_count
            extraction_record.raw_text = ocr_res.full_text[:10000] if ocr_res.full_text else ""
            extraction_record.provider_used = provider.provider_name
            extraction_record.review_flags_json = json.dumps(review_flags) if review_flags else None
            # Clear old fields
            db.query(ExtractedField).filter(ExtractedField.extraction_result_id == extraction_record.id).delete()
            db.flush()
        else:
            extraction_record = DocumentExtractionResult(
                document_version_id=version.id,
                document_id=doc.id,
                application_id=doc.application_id,
                status=final_status,
                detected_document_type=classification.predicted_type,
                classification_confidence=classification.confidence,
                classification_reason=classification.reason,
                is_type_match=classification.is_type_match,
                page_count=ocr_res.page_count,
                raw_text=ocr_res.full_text[:10000] if ocr_res.full_text else "",  # store head for inspection
                provider_used=provider.provider_name,
                review_flags_json=json.dumps(review_flags) if review_flags else None,
            )
            db.add(extraction_record)
            db.flush()

        # 11. Persist ExtractedField rows
        for f in extracted_fields_data:
            field_row = ExtractedField(
                extraction_result_id=extraction_record.id,
                field_name=f.field_name,
                extracted_value=f.extracted_value,
                normalized_value=f.normalized_value,
                confidence_score=f.confidence_score,
                page_number=f.page_number,
                evidence_text=f.evidence_text[:500] if f.evidence_text else None,
                bounding_box_json=json.dumps(f.bounding_box) if f.bounding_box else None,
                extraction_method=f.extraction_method,
            )
            db.add(field_row)

        # 12. Complete processing job
        job.status = final_status
        job.completed_at = datetime.now(timezone.utc)
        job.duration_ms = duration_ms
        db.commit()
        db.refresh(extraction_record)

        logger.info(f"Document processing completed for version {version.id} with status {final_status} in {duration_ms}ms.")
        return extraction_record

    except Exception as e:
        logger.error(f"Document processing failed for version {version.id}: {e}", exc_info=True)
        db.rollback()

        # Update job with failure record
        fail_job = db.query(DocumentProcessingJob).filter(DocumentProcessingJob.document_version_id == version.id).first()
        if fail_job:
            fail_job.status = ProcessingStatusEnum.FAILED.value
            fail_job.error_message = str(e)
            fail_job.completed_at = datetime.now(timezone.utc)
            db.commit()

        # Create or update failed extraction result so UI receives clear feedback
        fail_record = (
            db.query(DocumentExtractionResult)
            .filter(DocumentExtractionResult.document_version_id == version.id)
            .first()
        )
        if not fail_record:
            fail_record = DocumentExtractionResult(
                document_version_id=version.id,
                document_id=doc.id,
                application_id=doc.application_id,
                status=ProcessingStatusEnum.FAILED.value,
                detected_document_type="UNKNOWN",
                classification_confidence=0.0,
                classification_reason=f"Processing pipeline error: {str(e)}",
                is_type_match=False,
                page_count=1,
                raw_text="",
                provider_used="LOCAL_PIPELINE",
                review_flags_json=json.dumps([f"Processing failure: {str(e)}"]),
            )
            db.add(fail_record)
        else:
            fail_record.status = ProcessingStatusEnum.FAILED.value
            fail_record.classification_reason = f"Processing pipeline error: {str(e)}"
            fail_record.review_flags_json = json.dumps([f"Processing failure: {str(e)}"])
        db.commit()
        return fail_record


def background_process_document(document_version_id: str):
    """
    Entrypoint invoked by FastAPI BackgroundTasks to process a document
    asynchronously without blocking the HTTP request.
    """
    db = SessionLocal()
    try:
        run_pipeline_for_document_version(document_version_id, db)
    finally:
        db.close()
