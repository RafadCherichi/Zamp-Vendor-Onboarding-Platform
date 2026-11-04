import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.core.deps import get_current_user, get_current_member, require_roles
from app.models.user import User
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.vendor import Vendor
from app.models.application import Application, ApplicationStatusEnum, ConstitutionEnum
from app.models.document import Document, DocumentVersion, DocumentTypeEnum
from app.models.extraction import DocumentExtractionResult, ExtractedField, ProcessingStatusEnum
from app.storage.local import get_storage_adapter
from app.services.checklist import (
    evaluate_checklist_rules,
    sync_application_documents,
    parse_categories,
)
from app.services.extraction.pipeline import (
    background_process_document,
    run_pipeline_for_document_version,
)
from app.schemas.application import (
    ApplicationDraftUpdate,
    ApplicationResponse,
    ApplicationSubmitResponse,
    DocumentSlotResponse,
    DocumentVersionResponse,
)
from app.schemas.extraction import (
    DocumentExtractionResponse,
    ExtractedFieldResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def mask_account_number(acc: Optional[str]) -> Optional[str]:
    """Mask bank account number for presentation (e.g. ****5678)."""
    if not acc:
        return None
    clean = acc.strip()
    if len(clean) <= 4:
        return "****"
    return ("*" * (len(clean) - 4)) + clean[-4:]


def mask_sensitive_value(field_name: str, val: Optional[str]) -> str:
    """Mask sensitive compliance values like PAN and Bank Account numbers."""
    if not val:
        return ""
    if field_name == "pan_number" and len(val) >= 5:
        return val[:2] + "*****" + val[-2:]
    if field_name in ["bank_account_number", "account_number"]:
        return mask_account_number(val) or val
    return val


def build_application_response(app: Application, db: Optional[Session] = None) -> ApplicationResponse:
    categories = parse_categories(app.categories_json)
    doc_slots = []
    for d in app.documents:
        current_v = None
        proc_status = None
        detected_type = None
        is_type_match = None
        review_flags: List[str] = []
        fields_summary: Dict[str, str] = {}

        if d.versions:
            latest = d.versions[0]
            current_v = DocumentVersionResponse(
                id=latest.id,
                version_number=latest.version_number,
                original_filename=latest.original_filename,
                file_size_bytes=latest.file_size_bytes,
                content_type=latest.content_type,
                created_at=latest.created_at,
            )

            # Retrieve extraction insights if db session available
            if db:
                extraction = (
                    db.query(DocumentExtractionResult)
                    .filter(DocumentExtractionResult.document_version_id == latest.id)
                    .first()
                )
                if extraction:
                    proc_status = extraction.status
                    detected_type = extraction.detected_document_type
                    is_type_match = extraction.is_type_match
                    if extraction.review_flags_json:
                        try:
                            review_flags = json.loads(extraction.review_flags_json)
                        except Exception:
                            review_flags = []
                    for f in extraction.fields:
                        fields_summary[f.field_name] = mask_sensitive_value(f.field_name, f.normalized_value or f.extracted_value)
                else:
                    proc_status = "QUEUED"

        doc_slots.append(
            DocumentSlotResponse(
                id=d.id,
                document_type=d.document_type,
                title=d.title,
                is_required=d.is_required,
                requirement_reason=d.requirement_reason,
                status=d.status,
                current_version=current_v,
                versions_count=len(d.versions),
                accepted_extensions=[".pdf", ".jpg", ".jpeg", ".png"],
                max_size_mb=15,
                processing_status=proc_status,
                detected_document_type=detected_type,
                is_type_match=is_type_match,
                review_flags=review_flags,
                extracted_fields_summary=fields_summary,
            )
        )

    return ApplicationResponse(
        id=app.id,
        reference_number=app.reference_number,
        organisation_id=app.organisation_id,
        vendor_id=app.vendor_id,
        status=app.status,
        submitted_at=app.submitted_at,
        created_at=app.created_at,
        updated_at=app.updated_at,
        legal_name=app.legal_name,
        trade_name=app.trade_name,
        constitution=app.constitution,
        date_of_establishment=app.date_of_establishment,
        registered_address=app.registered_address,
        operating_address=app.operating_address,
        city=app.city,
        state=app.state,
        pincode=app.pincode,
        pan=app.pan,
        is_gst_registered=app.is_gst_registered,
        gstin=app.gstin,
        is_udyam_registered=app.is_udyam_registered,
        udyam_number=app.udyam_number,
        cin_llpin=app.cin_llpin,
        contact_name=app.contact_name,
        contact_designation=app.contact_designation,
        contact_email=app.contact_email,
        contact_mobile=app.contact_mobile,
        authorised_signatory_name=app.authorised_signatory_name,
        bank_account_holder_name=app.bank_account_holder_name,
        bank_account_number=mask_account_number(app.bank_account_number),
        bank_ifsc=app.bank_ifsc,
        bank_account_type=app.bank_account_type,
        bank_name=app.bank_name,
        categories=categories,
        declaration_accurate_info=app.declaration_accurate_info,
        declaration_authorised_rep=app.declaration_authorised_rep,
        declaration_verification_consent=app.declaration_verification_consent,
        declaration_timestamp=app.declaration_timestamp,
        documents=doc_slots,
    )


def get_scoped_application(application_id: str, member: OrganisationMember, db: Session) -> Application:
    query = db.query(Application).filter(
        Application.id == application_id,
        Application.organisation_id == member.organisation_id,
    )

    # If the user is a vendor, restrict strictly to their own application
    if member.role == RoleEnum.VENDOR.value:
        query = query.filter(Application.created_by_user_id == member.user_id)

    app = query.first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or you do not have permission to access it.",
        )
    return app


@router.get(
    "/",
    response_model=List[ApplicationResponse],
    summary="List Organisation Applications",
    description="Retrieve all applications belonging to the authenticated member's organisation.",
)
def list_organisation_applications(
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([
        RoleEnum.PROCUREMENT_OFFICER,
        RoleEnum.REVIEWER,
        RoleEnum.ADMIN,
    ])),
) -> List[ApplicationResponse]:
    apps = (
        db.query(Application)
        .filter(Application.organisation_id == member.organisation_id)
        .order_by(Application.created_at.desc())
        .all()
    )
    return [build_application_response(a, db) for a in apps]


@router.get(
    "/current",
    response_model=ApplicationResponse,
    summary="Get Active Vendor Application",
    description="Retrieve or initialize the active onboarding application draft for the authenticated vendor.",
)
def get_current_application(
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([RoleEnum.VENDOR])),
) -> ApplicationResponse:
    # 1. Retrieve or create Vendor record
    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.organisation_id == member.organisation_id,
            Vendor.created_by_user_id == member.user_id,
        )
        .first()
    )
    now = datetime.now(timezone.utc)
    if not vendor:
        vendor = Vendor(
            organisation_id=member.organisation_id,
            created_by_user_id=member.user_id,
            legal_name=member.user.full_name or "New Vendor",
            constitution=ConstitutionEnum.PROPRIETORSHIP.value,
        )
        db.add(vendor)
        db.flush()

    # 2. Retrieve or create active Application
    application = (
        db.query(Application)
        .filter(
            Application.vendor_id == vendor.id,
            Application.organisation_id == member.organisation_id,
        )
        .order_by(Application.created_at.desc())
        .first()
    )

    if not application:
        ref_num = f"APP-{now.year}-{secrets.token_hex(3).upper()}"
        application = Application(
            organisation_id=member.organisation_id,
            vendor_id=vendor.id,
            created_by_user_id=member.user_id,
            reference_number=ref_num,
            legal_name=vendor.legal_name,
            contact_email=member.user.email,
            status=ApplicationStatusEnum.IN_PROGRESS.value,
            categories_json="[]",
        )
        db.add(application)
        db.flush()

    # Sync dynamic documents checklist
    sync_application_documents(db, application)
    db.commit()
    db.refresh(application)

    return build_application_response(application, db)


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Get Application by ID",
    description="Retrieve a permitted application by ID with organisation scoping.",
)
def get_application(
    application_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> ApplicationResponse:
    app = get_scoped_application(application_id, member, db)
    sync_application_documents(db, app)
    return build_application_response(app, db)


@router.patch(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Update Application Draft",
    description="Partially update vendor onboarding form fields and recalculate document requirements.",
)
def update_application_draft(
    application_id: str,
    data: ApplicationDraftUpdate,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> ApplicationResponse:
    app = get_scoped_application(application_id, member, db)

    # Locked if already submitted
    if app.status == ApplicationStatusEnum.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application has already been submitted and cannot be modified.",
        )

    # Update provided fields
    update_dict = data.model_dump(exclude_unset=True)

    if "categories" in update_dict:
        cats = update_dict.pop("categories")
        app.categories_json = json.dumps(cats if isinstance(cats, list) else [])

    for field, val in update_dict.items():
        if hasattr(app, field) and val is not None:
            setattr(app, field, val)

    app.status = ApplicationStatusEnum.IN_PROGRESS.value

    # Recalculate dynamic checklist based on updated fields
    sync_application_documents(db, app)
    db.commit()
    db.refresh(app)

    return build_application_response(app, db)


@router.get(
    "/{application_id}/checklist",
    response_model=List[DocumentSlotResponse],
    summary="Get Dynamic Document Checklist",
    description="Get evaluated document checklist slots and current upload status.",
)
def get_application_checklist(
    application_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> List[DocumentSlotResponse]:
    app = get_scoped_application(application_id, member, db)
    sync_application_documents(db, app)
    full_resp = build_application_response(app, db)
    return full_resp.documents


ALLOWED_MIME_TYPES = {
    "application/pdf": [b"%PDF"],
    "image/jpeg": [b"\xFF\xD8\xFF"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
}

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


@router.post(
    "/{application_id}/documents/{document_type}/upload",
    response_model=DocumentSlotResponse,
    summary="Upload or Replace Application Document",
    description="Upload a document file to an application slot. Automatically increments version number and triggers extraction pipeline.",
)
async def upload_document(
    application_id: str,
    document_type: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> DocumentSlotResponse:
    app = get_scoped_application(application_id, member, db)

    # 0. Check active exception if application is already submitted
    active_exc = None
    if app.status == ApplicationStatusEnum.SUBMITTED.value:
        doc_slot = db.query(Document).filter(
            Document.application_id == app.id,
            Document.document_type == document_type,
        ).first()
        if doc_slot:
            from app.models.exception import OnboardingException, ExceptionStatusEnum
            active_exc = (
                db.query(OnboardingException)
                .filter(
                    OnboardingException.application_id == app.id,
                    OnboardingException.related_document_id == doc_slot.id,
                    OnboardingException.status == ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
                )
                .first()
            )
        if not active_exc and member.role == RoleEnum.VENDOR.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot upload documents to an already submitted application unless requested by an active exception.",
            )

    # 1. Validate filename and extension
    filename = file.filename or "uploaded_file"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Accepted formats: PDF, JPG, JPEG, PNG.",
        )

    # 2. Read content and validate size (max 15MB)
    content = await file.read()
    file_size = len(content)
    max_bytes = settings.MAX_FILE_SIZE_BYTES
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {max_bytes // (1024 * 1024)}MB. Actual: {file_size // (1024 * 1024)}MB.",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot upload empty file.",
        )

    # 3. Magic header sniffing to verify actual content type
    detected_mime = None
    for mime, signatures in ALLOWED_MIME_TYPES.items():
        for sig in signatures:
            if content.startswith(sig):
                detected_mime = mime
                break
        if detected_mime:
            break

    # Also accept image/jpeg if starting with \xff\xd8
    if not detected_mime and ext in [".jpg", ".jpeg"] and content[:2] == b"\xff\xd8":
        detected_mime = "image/jpeg"

    if not detected_mime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match an allowed format (PDF, JPEG, PNG). Untrusted file rejected.",
        )

    # 4. Checksum
    checksum = hashlib.sha256(content).hexdigest()

    # 5. Find or create Document slot
    doc = (
        db.query(Document)
        .filter(
            Document.application_id == app.id,
            Document.document_type == document_type,
        )
        .first()
    )

    if not doc:
        doc = Document(
            application_id=app.id,
            organisation_id=app.organisation_id,
            document_type=document_type,
            title=document_type.replace("_", " ").title(),
            is_required=True,
            status="PENDING",
        )
        db.add(doc)
        db.flush()

    # 6. Save in private object storage
    storage = get_storage_adapter()
    version_num = len(doc.versions) + 1
    safe_token = secrets.token_hex(6)
    dest_path = f"org_{app.organisation_id}/app_{app.id}/{document_type}_v{version_num}_{safe_token}{ext}"

    import io
    file_io = io.BytesIO(content)
    storage_key = storage.save_file(file_io, dest_path, detected_mime)

    # 7. Create immutable DocumentVersion record
    version = DocumentVersion(
        document_id=doc.id,
        version_number=version_num,
        storage_key=storage_key,
        original_filename=filename,
        file_size_bytes=file_size,
        content_type=detected_mime,
        file_checksum=checksum,
        uploaded_by_user_id=member.user_id,
    )
    db.add(version)
    db.flush()

    # 8. Update Document slot
    doc.status = "UPLOADED"
    doc.current_version_id = version.id
    db.commit()
    db.refresh(doc)

    # Invalidate existing validation findings that depended on this document
    try:
        from app.services.validation.orchestrator import ValidationOrchestrator
        ValidationOrchestrator(db).mark_stale_findings_for_document(doc.id, reason="Document re-uploaded")
    except Exception as e:
        logger.warning(f"Error marking stale findings for document {doc.id}: {e}")

    # 9. Trigger processing pipeline
    # Process synchronously so upload response has instant extraction insights; background task ensures async resilience
    background_tasks.add_task(background_process_document, version.id)
    extraction = run_pipeline_for_document_version(version.id, db)

    # If linked to an active exception requiring vendor action, update exception
    if active_exc:
        try:
            from app.services.exceptions.revalidation import ExceptionResolutionService
            ExceptionResolutionService(db).link_document_replacement(
                exception_id=active_exc.id,
                document_version_id=version.id,
                user=member.user,
                explanation="Replacement statutory document uploaded",
            )
        except Exception as e:
            logger.warning(f"Error linking replacement document to exception {active_exc.id}: {e}")

    proc_status = extraction.status if extraction else "PROCESSING"
    det_type = extraction.detected_document_type if extraction else None
    is_match = extraction.is_type_match if extraction else None
    flags: List[str] = []
    fields_summary: Dict[str, str] = {}

    if extraction:
        if extraction.review_flags_json:
            try:
                flags = json.loads(extraction.review_flags_json)
            except Exception:
                flags = []
        for f in extraction.fields:
            fields_summary[f.field_name] = mask_sensitive_value(f.field_name, f.normalized_value or f.extracted_value)

    return DocumentSlotResponse(
        id=doc.id,
        document_type=doc.document_type,
        title=doc.title,
        is_required=doc.is_required,
        requirement_reason=doc.requirement_reason,
        status=doc.status,
        current_version=DocumentVersionResponse(
            id=version.id,
            version_number=version.version_number,
            original_filename=version.original_filename,
            file_size_bytes=version.file_size_bytes,
            content_type=version.content_type,
            created_at=version.created_at,
        ),
        versions_count=len(doc.versions),
        accepted_extensions=[".pdf", ".jpg", ".jpeg", ".png"],
        max_size_mb=15,
        processing_status=proc_status,
        detected_document_type=det_type,
        is_type_match=is_match,
        review_flags=flags,
        extracted_fields_summary=fields_summary,
    )


@router.get(
    "/{application_id}/documents/{document_id}/extraction",
    response_model=DocumentExtractionResponse,
    summary="Get Document Extraction Result",
    description="Retrieve detailed OCR extraction results, detected document type, and structured fields with confidence scores.",
)
def get_document_extraction(
    application_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> DocumentExtractionResponse:
    app = get_scoped_application(application_id, member, db)
    doc = db.query(Document).filter(Document.id == document_id, Document.application_id == app.id).first()
    if not doc or not doc.current_version_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document or uploaded version not found.")

    extraction = (
        db.query(DocumentExtractionResult)
        .filter(DocumentExtractionResult.document_version_id == doc.current_version_id)
        .first()
    )
    if not extraction:
        extraction = run_pipeline_for_document_version(doc.current_version_id, db)

    if not extraction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction result not available.")

    flags: List[str] = []
    if extraction.review_flags_json:
        try:
            flags = json.loads(extraction.review_flags_json)
        except Exception:
            flags = []

    fields_resp = [
        ExtractedFieldResponse(
            id=f.id,
            field_name=f.field_name,
            extracted_value=mask_sensitive_value(f.field_name, f.extracted_value),
            normalized_value=mask_sensitive_value(f.field_name, f.normalized_value) if f.normalized_value else None,
            confidence_score=f.confidence_score,
            page_number=f.page_number,
            evidence_text=f.evidence_text,
            extraction_method=f.extraction_method,
        )
        for f in extraction.fields
    ]

    return DocumentExtractionResponse(
        id=extraction.id,
        document_id=doc.id,
        document_version_id=extraction.document_version_id,
        status=extraction.status,
        detected_document_type=extraction.detected_document_type,
        classification_confidence=extraction.classification_confidence,
        classification_reason=extraction.classification_reason,
        is_type_match=extraction.is_type_match,
        page_count=extraction.page_count,
        provider_used=extraction.provider_used,
        review_flags=flags,
        fields=fields_resp,
        created_at=extraction.created_at,
    )


@router.post(
    "/{application_id}/documents/{document_id}/reprocess",
    response_model=DocumentExtractionResponse,
    summary="Reprocess Document Version",
    description="Manually re-run OCR extraction and document classification on the current version.",
)
def reprocess_document(
    application_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> DocumentExtractionResponse:
    app = get_scoped_application(application_id, member, db)
    doc = db.query(Document).filter(Document.id == document_id, Document.application_id == app.id).first()
    if not doc or not doc.current_version_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document or uploaded version not found.")

    extraction = run_pipeline_for_document_version(doc.current_version_id, db, force_reprocess=True)
    if not extraction:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Reprocessing failed.")

    flags: List[str] = []
    if extraction.review_flags_json:
        try:
            flags = json.loads(extraction.review_flags_json)
        except Exception:
            flags = []

    fields_resp = [
        ExtractedFieldResponse(
            id=f.id,
            field_name=f.field_name,
            extracted_value=mask_sensitive_value(f.field_name, f.extracted_value),
            normalized_value=mask_sensitive_value(f.field_name, f.normalized_value) if f.normalized_value else None,
            confidence_score=f.confidence_score,
            page_number=f.page_number,
            evidence_text=f.evidence_text,
            extraction_method=f.extraction_method,
        )
        for f in extraction.fields
    ]

    return DocumentExtractionResponse(
        id=extraction.id,
        document_id=doc.id,
        document_version_id=extraction.document_version_id,
        status=extraction.status,
        detected_document_type=extraction.detected_document_type,
        classification_confidence=extraction.classification_confidence,
        classification_reason=extraction.classification_reason,
        is_type_match=extraction.is_type_match,
        page_count=extraction.page_count,
        provider_used=extraction.provider_used,
        review_flags=flags,
        fields=fields_resp,
        created_at=extraction.created_at,
    )


@router.get(
    "/{application_id}/documents/{document_id}/preview",
    summary="Safe Document Preview",
    description="Stream an uploaded document securely for inline preview with access authorization.",
)
def preview_document(
    application_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
):
    app = get_scoped_application(application_id, member, db)
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.application_id == app.id)
        .first()
    )

    if not doc or not doc.versions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found.")

    latest_version = doc.versions[0]
    storage = get_storage_adapter()
    file_path = storage._resolve_path(latest_version.storage_key)

    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Underlying storage file not found.")

    return FileResponse(
        path=str(file_path),
        media_type=latest_version.content_type,
        filename=latest_version.original_filename,
        content_disposition_type="inline",
    )


@router.post(
    "/{application_id}/submit",
    response_model=ApplicationSubmitResponse,
    summary="Submit Onboarding Application",
    description="Validate all required business fields, mandatory document uploads, and declarations, then transition to SUBMITTED.",
)
def submit_application(
    application_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([RoleEnum.VENDOR])),
) -> ApplicationSubmitResponse:
    app = get_scoped_application(application_id, member, db)

    if app.status == ApplicationStatusEnum.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application has already been submitted.",
        )

    # Synchronize checklist to ensure we validate against the latest rules
    sync_application_documents(db, app)

    missing_fields = []

    # Section 1: Business Identity
    if not app.legal_name or not app.legal_name.strip():
        missing_fields.append("Section 1: Legal Business Name is required")
    if not app.constitution:
        missing_fields.append("Section 1: Legal Constitution is required")
    if not app.registered_address or not app.registered_address.strip():
        missing_fields.append("Section 1: Registered Address is required")
    if not app.city or not app.city.strip():
        missing_fields.append("Section 1: City is required")
    if not app.state or not app.state.strip():
        missing_fields.append("Section 1: State is required")
    if not app.pincode or not app.pincode.strip():
        missing_fields.append("Section 1: PIN Code is required")

    # Section 2: Tax & Registration
    if not app.pan or not app.pan.strip():
        missing_fields.append("Section 2: PAN is required")
    if app.is_gst_registered and (not app.gstin or not app.gstin.strip()):
        missing_fields.append("Section 2: GSTIN is required when registered for GST")
    if app.is_udyam_registered and (not app.udyam_number or not app.udyam_number.strip()):
        missing_fields.append("Section 2: Udyam Registration Number is required when registered under MSME")
    if app.constitution in [ConstitutionEnum.PVT_LTD.value, ConstitutionEnum.PUB_LTD.value, ConstitutionEnum.LLP.value]:
        if not app.cin_llpin or not app.cin_llpin.strip():
            missing_fields.append(f"Section 2: CIN/LLPIN is required for {app.constitution.replace('_', ' ')}")

    # Section 3: Authorised Contact
    if not app.contact_name or not app.contact_name.strip():
        missing_fields.append("Section 3: Contact Person Name is required")
    if not app.contact_email or not app.contact_email.strip():
        missing_fields.append("Section 3: Contact Email is required")
    if not app.contact_mobile or not app.contact_mobile.strip():
        missing_fields.append("Section 3: Contact Mobile is required")

    # Section 4: Banking Details
    if not app.bank_account_holder_name or not app.bank_account_holder_name.strip():
        missing_fields.append("Section 4: Bank Account Holder Name is required")
    if not app.bank_account_number or not app.bank_account_number.strip():
        missing_fields.append("Section 4: Bank Account Number is required")
    if not app.bank_ifsc or not app.bank_ifsc.strip():
        missing_fields.append("Section 4: Bank IFSC Code is required")

    # Section 6: Declarations
    if not app.declaration_accurate_info:
        missing_fields.append("Section 6: Accuracy declaration must be confirmed")
    if not app.declaration_authorised_rep:
        missing_fields.append("Section 6: Authorised representation declaration must be confirmed")
    if not app.declaration_verification_consent:
        missing_fields.append("Section 6: Verification and processing consent must be confirmed")

    # Mandatory Documents
    missing_docs = []
    for doc in app.documents:
        if doc.is_required and doc.status != "UPLOADED":
            missing_docs.append(f"Document missing: {doc.title}")

    all_errors = missing_fields + missing_docs
    if all_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"Cannot submit application. {len(all_errors)} mandatory requirement(s) missing.",
                "errors": all_errors,
            },
        )

    # Transition to SUBMITTED
    now = datetime.now(timezone.utc)
    app.status = ApplicationStatusEnum.SUBMITTED.value
    app.submitted_at = now
    app.declaration_timestamp = now

    # Propagate canonical legal identity back to Vendor record
    if app.vendor:
        app.vendor.legal_name = app.legal_name
        app.vendor.trade_name = app.trade_name
        app.vendor.constitution = app.constitution
        app.vendor.pan = app.pan

    # Automatically execute deterministic validation run upon submission
    try:
        from app.services.validation.orchestrator import ValidationOrchestrator
        ValidationOrchestrator(db).run_full_validation(
            application_id=app.id,
            user_id=member.user_id,
            run_type="SUBMISSION_RUN",
            trigger_reason="Automatic submission evaluation",
        )
    except Exception as e:
        logger.warning(f"Error running validation on submission: {e}")

    db.commit()
    db.refresh(app)

    return ApplicationSubmitResponse(
        success=True,
        reference_number=app.reference_number,
        status=app.status,
        submitted_at=app.submitted_at,
        message="Application submitted successfully. It is now queued for verification and human review.",
    )
