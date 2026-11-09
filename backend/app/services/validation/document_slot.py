from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.extraction import DocumentExtractionResult


def mismatched_required_document_slots(db: Session, application: Application, *, extractions=None):
    """Return required slots whose latest file is confidently another known type."""
    mismatches = []
    for document in application.documents:
        if not document.is_required or document.status != "UPLOADED" or not document.versions:
            continue
        latest_version = document.versions[0]
        extraction = extractions.get(latest_version.id) if extractions is not None else (
            db.query(DocumentExtractionResult)
            .filter(DocumentExtractionResult.document_version_id == latest_version.id)
            .first()
        )
        if (
            extraction
            and extraction.is_type_match is False
            and extraction.detected_document_type
            and extraction.detected_document_type != "UNKNOWN"
        ):
            # The checklist explicitly accepts Udyam as establishment proof
            # for sole proprietors, even when the classifier calls it Udyam.
            if (
                document.document_type == "CONSTITUTION_PROOF"
                and application.constitution == "PROPRIETORSHIP"
                and extraction.detected_document_type == "UDYAM_CERTIFICATE"
            ):
                continue
            mismatches.append((document, extraction))
    return mismatches
