"""Read-only, scoped progress for a document being uploaded and checked."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_member
from app.database import get_db
from app.models.document import Document, DocumentVersion
from app.models.extraction import DocumentProcessingJob, ProcessingStatusEnum
from app.models.member import OrganisationMember
from app.api.endpoints.applications import get_scoped_application


router = APIRouter()


class ProcessingProgressResponse(BaseModel):
    status: str
    stage: str
    message: str
    version_number: int


STAGE_MESSAGES = {
    "SENDING_FILE": "Sending your document",
    "QUEUED": "Document received; waiting to read it",
    "READING_TEXT": "Reading the document",
    "CLASSIFYING": "Identifying the type of proof",
    "EXTRACTING_FIELDS": "Reading details from the proof",
    "CHECKING_RESULT": "Checking the details and clarity",
    "COMPLETE": "Document check complete",
    "NEEDS_REVIEW": "Document needs a closer look",
    "FAILED": "We could not process this document",
}


@router.get(
    "/{application_id}/documents/{document_type}/processing",
    response_model=ProcessingProgressResponse,
    summary="Current document processing stage",
)
def get_document_processing_progress(
    application_id: str,
    document_type: str,
    after_version: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> ProcessingProgressResponse:
    app = get_scoped_application(application_id, member, db)
    document = db.query(Document).filter(
        Document.application_id == app.id,
        Document.document_type == document_type,
    ).first()
    version = db.get(DocumentVersion, document.current_version_id) if document and document.current_version_id else None

    if version is None or version.version_number <= after_version:
        return ProcessingProgressResponse(
            status="WAITING_FOR_UPLOAD",
            stage="SENDING_FILE",
            message=STAGE_MESSAGES["SENDING_FILE"],
            version_number=after_version,
        )

    job = db.query(DocumentProcessingJob).filter_by(document_version_id=version.id).first()
    if job is None:
        status = ProcessingStatusEnum.QUEUED.value
        stage = "QUEUED"
    else:
        status = job.status
        stage = job.stage or {
            ProcessingStatusEnum.EXTRACTED.value: "COMPLETE",
            ProcessingStatusEnum.NEEDS_REVIEW.value: "NEEDS_REVIEW",
            ProcessingStatusEnum.FAILED.value: "FAILED",
        }.get(status, "QUEUED")

    return ProcessingProgressResponse(
        status=status,
        stage=stage,
        message=STAGE_MESSAGES[stage],
        version_number=version.version_number,
    )
