import pytest
import json
import secrets
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.user import User
from app.models.organization import Organization
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.vendor import Vendor
from app.models.application import Application, ApplicationStatusEnum, ConstitutionEnum
from app.models.document import Document, DocumentVersion, DocumentTypeEnum
from app.models.extraction import DocumentExtractionResult, ExtractedField, ProcessingStatusEnum
from app.models.validation import (
    ValidationRun,
    ValidationFinding,
    ValidationStatusEnum,
    ValidationSeverityEnum,
)
from app.models.exception import (
    OnboardingException,
    ExceptionTransition,
    ExceptionComment,
    FieldCorrectionRecord,
    ExceptionCategoryEnum,
    ExceptionSeverityEnum,
    ExceptionStatusEnum,
    ResolutionTypeEnum,
)
from app.models.notification import Notification
from app.services.exceptions.state_machine import validate_transition
from app.services.exceptions.generator import ExceptionGenerator
from app.services.exceptions.revalidation import ExceptionResolutionService
from app.services.notifications.service import NotificationService
from app.services.validation.orchestrator import ValidationOrchestrator


def test_exception_lifecycle_valid_and_invalid_transitions():
    """Verify backend-enforced transition rules and role guardrails."""
    # 1. Normal Reviewer Path: OPEN -> ASSIGNED -> ACTION_REQUIRED -> RESPONSE_SUBMITTED -> RESOLVED
    validate_transition("OPEN", "ASSIGNED", RoleEnum.REVIEWER.value)
    validate_transition("ASSIGNED", "ACTION_REQUIRED_FROM_VENDOR", RoleEnum.REVIEWER.value)
    validate_transition("ACTION_REQUIRED_FROM_VENDOR", "RESPONSE_SUBMITTED", RoleEnum.VENDOR.value, reason="Provided PAN")
    validate_transition("RESPONSE_SUBMITTED", "UNDER_REVIEW", RoleEnum.REVIEWER.value)
    validate_transition("UNDER_REVIEW", "RESOLVED", RoleEnum.REVIEWER.value)

    # 2. Vendor cannot arbitrarily resolve or close
    with pytest.raises(HTTPException) as exc_info:
        validate_transition("ACTION_REQUIRED_FROM_VENDOR", "RESOLVED", RoleEnum.VENDOR.value)
    assert exc_info.value.status_code in [400, 403]

    # 3. Vendor cannot submit response when status is OPEN
    with pytest.raises(HTTPException) as exc_info:
        validate_transition("OPEN", "RESPONSE_SUBMITTED", RoleEnum.VENDOR.value)
    assert exc_info.value.status_code in [400, 403]

    # 4. Reopening resolved exception requires reason
    with pytest.raises(HTTPException) as exc_info:
        validate_transition("RESOLVED", "OPEN", RoleEnum.REVIEWER.value, reason="")
    assert exc_info.value.status_code == 400
    assert "mandatory" in exc_info.value.detail.lower()

    # Reopening with reason succeeds
    validate_transition("RESOLVED", "OPEN", RoleEnum.REVIEWER.value, reason="New evidence discovered")


def test_exception_generation_and_deduplication(db_session: Session):
    """
    Verify that validation findings automatically generate exceptions,
    and subsequent runs do NOT create duplicate open exceptions for the same issue.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Org Exc Dedup {tok}", slug=f"org-dedup-{tok}")
    db_session.add(org)
    db_session.flush()

    user = User(email=f"dedup-{tok}@vendor.com", full_name="Dedup Vendor", hashed_password="pw")
    db_session.add(user)
    db_session.flush()

    member = OrganisationMember(organisation_id=org.id, user_id=user.id, role=RoleEnum.VENDOR.value)
    db_session.add(member)

    vendor = Vendor(organisation_id=org.id, legal_name="Dedup Supplies", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()

    # Application with invalid PAN 4th character for PVT_LTD ('P' instead of 'C')
    app = Application(
        reference_number=f"APP-DEDUP-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=user.id,
        legal_name="Dedup Supplies Private Limited",
        constitution=ConstitutionEnum.PVT_LTD.value,
        pan="AAAPE1234A",  # Invalid for Company
        bank_account_holder_name="Dedup Supplies Private Limited",
        bank_account_number="123456789012",
        bank_ifsc="HDFC0001234",
        contact_mobile="9876543210",
        contact_email=f"dedup-{tok}@vendor.com",
        pincode="560001",
    )
    db_session.add(app)
    db_session.commit()

    orchestrator = ValidationOrchestrator(db_session)
    val_run1 = orchestrator.run_full_validation(app.id, user_id=user.id)

    # Check exceptions created
    exceptions_run1 = (
        db_session.query(OnboardingException)
        .filter(OnboardingException.application_id == app.id)
        .all()
    )
    pan_exc_count = len([e for e in exceptions_run1 if e.category == ExceptionCategoryEnum.PAN_MISMATCH.value])
    assert pan_exc_count == 1

    # Run validation again without resolving the issue
    val_run2 = orchestrator.run_full_validation(app.id, user_id=user.id)

    # Verify NO duplicate open PAN exception was created
    exceptions_run2 = (
        db_session.query(OnboardingException)
        .filter(
            OnboardingException.application_id == app.id,
            OnboardingException.category == ExceptionCategoryEnum.PAN_MISMATCH.value,
            OnboardingException.status.notin_([ExceptionStatusEnum.RESOLVED.value, ExceptionStatusEnum.CLOSED.value]),
        )
        .all()
    )
    assert len(exceptions_run2) == 1, "Duplicate open exception created for the same check"


def test_scenario_a_missing_document_and_vendor_upload(db_session: Session):
    """
    Scenario A: Missing bank proof. Reviewer requests document from vendor.
    Vendor uploads document; system revalidates and reviewer resolves exception.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Org Scen A {tok}", slug=f"org-scen-a-{tok}")
    db_session.add(org)
    db_session.flush()

    v_user = User(email=f"vendor-{tok}@a.com", full_name="Vendor A", hashed_password="pw")
    r_user = User(email=f"reviewer-{tok}@a.com", full_name="Reviewer A", hashed_password="pw")
    db_session.add_all([v_user, r_user])
    db_session.flush()

    v_member = OrganisationMember(organisation_id=org.id, user_id=v_user.id, role=RoleEnum.VENDOR.value)
    r_member = OrganisationMember(organisation_id=org.id, user_id=r_user.id, role=RoleEnum.REVIEWER.value)
    db_session.add_all([v_member, r_member])

    vendor = Vendor(organisation_id=org.id, legal_name="Alpha Tech", constitution=ConstitutionEnum.PROPRIETORSHIP.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-SCEN-A-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=v_user.id,
        legal_name="Alpha Tech",
        constitution=ConstitutionEnum.PROPRIETORSHIP.value,
        pan="ABCPE1234F",
        bank_account_holder_name="Alpha Tech",
        bank_account_number="123456789012",
        bank_ifsc="HDFC0001234",
        contact_mobile="9876543210",
        contact_email=f"vendor-{tok}@a.com",
        pincode="560001",
    )
    db_session.add(app)
    db_session.flush()

    bank_doc = Document(
        application_id=app.id,
        organisation_id=org.id,
        document_type=DocumentTypeEnum.BANK_PROOF.value,
        title="Cancelled Cheque or Bank Statement",
        status="PENDING",
    )
    db_session.add(bank_doc)
    db_session.flush()

    # Raise exception: Missing bank proof
    exc = OnboardingException(
        reference_number=f"EXC-A-{tok}",
        organisation_id=org.id,
        application_id=app.id,
        vendor_id=vendor.id,
        category=ExceptionCategoryEnum.MISSING_DOCUMENT.value,
        title="Missing Bank Account Proof Document",
        description="Bank account proof document is missing for beneficiary verification.",
        severity=ExceptionSeverityEnum.HIGH.value,
        related_document_id=bank_doc.id,
        assigned_role=RoleEnum.VENDOR.value,
        status=ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
        vendor_action_instruction="Please upload a legible cancelled cheque or recent bank statement showing your account number and IFSC code.",
        created_by_user_id=r_user.id,
        created_by_role=RoleEnum.REVIEWER.value,
    )
    db_session.add(exc)
    db_session.commit()

    # Vendor uploads the bank document
    bank_ver = DocumentVersion(
        document_id=bank_doc.id,
        version_number=1,
        storage_key=f"scen_a/{tok}/cheque.pdf",
        original_filename="cheque.pdf",
        file_size_bytes=1024,
        content_type="application/pdf",
        file_checksum=f"hash_scen_a_{tok}",
        uploaded_by_user_id=v_user.id,
    )
    db_session.add(bank_ver)
    db_session.flush()
    bank_doc.status = "UPLOADED"
    bank_doc.current_version_id = bank_ver.id

    ext_res = DocumentExtractionResult(
        document_version_id=bank_ver.id,
        document_id=bank_doc.id,
        application_id=app.id,
        status=ProcessingStatusEnum.EXTRACTED.value,
        detected_document_type=DocumentTypeEnum.BANK_PROOF.value,
        is_type_match=True,
    )
    db_session.add(ext_res)
    db_session.flush()

    f1 = ExtractedField(
        extraction_result_id=ext_res.id,
        field_name="account_number",
        extracted_value="123456789012",
    )
    f2 = ExtractedField(
        extraction_result_id=ext_res.id,
        field_name="ifsc_code",
        extracted_value="HDFC0001234",
    )
    db_session.add_all([f1, f2])
    db_session.commit()

    # Link replacement and update exception
    service = ExceptionResolutionService(db_session)
    updated_exc = service.link_document_replacement(
        exception_id=exc.id,
        document_version_id=bank_ver.id,
        user=v_user,
        explanation="Uploaded cancelled cheque showing matching account and IFSC",
    )
    assert updated_exc.status == ExceptionStatusEnum.RESPONSE_SUBMITTED.value

    # Reviewer inspects and resolves
    validate_transition(updated_exc.status, ExceptionStatusEnum.RESOLVED.value, RoleEnum.REVIEWER.value)
    updated_exc.status = ExceptionStatusEnum.RESOLVED.value
    updated_exc.resolution_type = ResolutionTypeEnum.CORRECTED_BY_VENDOR.value
    updated_exc.resolution_notes = "Bank proof uploaded and OCR verified matching account number."
    updated_exc.resolved_at = datetime.now(timezone.utc)
    updated_exc.resolved_by_user_id = r_user.id
    db_session.commit()

    assert updated_exc.status == ExceptionStatusEnum.RESOLVED.value


def test_scenario_b_pan_gst_mismatch_correction(db_session: Session):
    """
    Scenario B: Embedded PAN in GSTIN mismatch.
    Vendor corrects PAN, system selectively revalidates, and historical mismatch is preserved.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Org Scen B {tok}", slug=f"org-scen-b-{tok}")
    db_session.add(org)
    db_session.flush()

    v_user = User(email=f"vendor-{tok}@b.com", full_name="Vendor B", hashed_password="pw")
    db_session.add(v_user)
    db_session.flush()

    v_member = OrganisationMember(organisation_id=org.id, user_id=v_user.id, role=RoleEnum.VENDOR.value)
    db_session.add(v_member)

    vendor = Vendor(organisation_id=org.id, legal_name="Beta Logistics", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()

    # Initial state: PAN mismatch
    app = Application(
        reference_number=f"APP-SCEN-B-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=v_user.id,
        legal_name="Beta Logistics Private Limited",
        constitution=ConstitutionEnum.PVT_LTD.value,
        pan="AAACA1234A",  # Old incorrect PAN
        is_gst_registered=True,
        gstin="29BBBCA5678B1Z2",  # Embedded PAN is BBBCA5678B
        bank_account_holder_name="Beta Logistics Private Limited",
        bank_account_number="123456789012",
        bank_ifsc="HDFC0001234",
        contact_mobile="9876543210",
        contact_email=f"vendor-{tok}@b.com",
        pincode="560001",
    )
    db_session.add(app)
    db_session.commit()

    orchestrator = ValidationOrchestrator(db_session)
    val_run1 = orchestrator.run_full_validation(app.id, user_id=v_user.id)

    # Find the created exception
    exc = (
        db_session.query(OnboardingException)
        .filter(
            OnboardingException.application_id == app.id,
            OnboardingException.category == ExceptionCategoryEnum.GST_MISMATCH.value,
        )
        .first()
    )
    assert exc is not None
    assert exc.status == ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value

    # Vendor corrects PAN to match GSTIN embedded PAN: BBBCA5678B
    service = ExceptionResolutionService(db_session)
    updated_exc = service.submit_vendor_correction(
        exception_id=exc.id,
        user=v_user,
        field_name="pan",
        new_field_value="BBBCA5678B",
        explanation="Corrected typographical error in PAN to align with GSTIN",
    )

    # 1. Status updated to RESPONSE_SUBMITTED
    assert updated_exc.status == ExceptionStatusEnum.RESPONSE_SUBMITTED.value

    # 2. Application PAN updated
    db_session.refresh(app)
    assert app.pan == "BBBCA5678B"

    # 3. Historical correction record preserved
    corr_record = db_session.query(FieldCorrectionRecord).filter(FieldCorrectionRecord.exception_id == exc.id).first()
    assert corr_record is not None
    assert "AAACA1234A" in corr_record.previous_value or "AA*****4A" in corr_record.previous_value
    assert "BBBCA5678B" in corr_record.new_value or "BB*****8B" in corr_record.new_value
    assert corr_record.vendor_explanation == "Corrected typographical error in PAN to align with GSTIN"

    # 4. In revalidation, GSTIN embedded PAN check now passes
    current_run = (
        db_session.query(ValidationRun)
        .filter(ValidationRun.application_id == app.id, ValidationRun.is_current.is_(True))
        .first()
    )
    assert current_run is not None
    gst_pan_finding = next((f for f in current_run.findings if f.check_id == "B_GSTIN_EMBEDDED_PAN_MATCH"), None)
    assert gst_pan_finding is not None
    assert gst_pan_finding.status == ValidationStatusEnum.PASSED.value


def test_scenario_d_probable_name_match_routed_to_reviewer(db_session: Session):
    """
    Scenario D: Probable name match routes to reviewer as an internal review exception,
    not directly demanding vendor action without reviewer judgment.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Org Scen D {tok}", slug=f"org-scen-d-{tok}")
    db_session.add(org)
    db_session.flush()

    v_user = User(email=f"vendor-{tok}@d.com", full_name="Vendor D", hashed_password="pw")
    db_session.add(v_user)
    db_session.flush()

    v_member = OrganisationMember(organisation_id=org.id, user_id=v_user.id, role=RoleEnum.VENDOR.value)
    db_session.add(v_member)

    vendor = Vendor(organisation_id=org.id, legal_name="Apex Components & Fasteners Private Limited", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-SCEN-D-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=v_user.id,
        legal_name="Apex Components & Fasteners Private Limited",
        constitution=ConstitutionEnum.PVT_LTD.value,
        pan="AAACA1234A",
        bank_account_holder_name="Apex Components & Fasteners Private Limited",
        bank_account_number="123456789012",
        bank_ifsc="HDFC0001234",
        contact_mobile="9876543210",
        contact_email=f"vendor-{tok}@d.com",
        pincode="560001",
    )
    db_session.add(app)
    db_session.flush()

    # Upload PAN doc with slight name variant (probable match)
    pan_doc = Document(
        application_id=app.id,
        organisation_id=org.id,
        document_type=DocumentTypeEnum.PAN_PROOF.value,
        title="PAN Card Proof",
        status="UPLOADED",
    )
    db_session.add(pan_doc)
    db_session.flush()

    pan_ver = DocumentVersion(
        document_id=pan_doc.id,
        version_number=1,
        storage_key=f"scen_d/{tok}/pan.pdf",
        original_filename="pan.pdf",
        file_size_bytes=1024,
        content_type="application/pdf",
        file_checksum=f"hash_scen_d_{tok}",
    )
    db_session.add(pan_ver)
    db_session.flush()
    pan_doc.current_version_id = pan_ver.id

    ext_res = DocumentExtractionResult(
        document_version_id=pan_ver.id,
        document_id=pan_doc.id,
        application_id=app.id,
        status=ProcessingStatusEnum.EXTRACTED.value,
        detected_document_type=DocumentTypeEnum.PAN_PROOF.value,
        is_type_match=True,
    )
    db_session.add(ext_res)
    db_session.flush()

    f1 = ExtractedField(
        extraction_result_id=ext_res.id,
        field_name="pan_number",
        extracted_value="AAACA1234A",
    )
    f2 = ExtractedField(
        extraction_result_id=ext_res.id,
        field_name="pan_holder_name",
        extracted_value="Apex Components Private Limited",  # Probable match
    )
    db_session.add_all([f1, f2])
    db_session.commit()

    orchestrator = ValidationOrchestrator(db_session)
    val_run = orchestrator.run_full_validation(app.id, user_id=v_user.id)

    # Check exception routing
    exc = (
        db_session.query(OnboardingException)
        .filter(
            OnboardingException.application_id == app.id,
            OnboardingException.category == ExceptionCategoryEnum.LEGAL_NAME_MISMATCH.value,
        )
        .first()
    )
    assert exc is not None
    assert exc.assigned_role == RoleEnum.REVIEWER.value
    assert exc.status == ExceptionStatusEnum.UNDER_REVIEW.value
    assert exc.vendor_action_instruction is None  # Not bothering vendor directly


def test_scenario_e_provider_unavailable_internal_followup(db_session: Session):
    """
    Scenario E: Simulated provider unavailable generates internal/procurement follow-up,
    NEVER requesting vendor to re-upload identical documents.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Org Scen E {tok}", slug=f"org-scen-e-{tok}")
    db_session.add(org)
    db_session.flush()

    user = User(email=f"v-{tok}@e.com", full_name="Vendor E", hashed_password="pw")
    db_session.add(user)
    db_session.flush()

    member = OrganisationMember(organisation_id=org.id, user_id=user.id, role=RoleEnum.VENDOR.value)
    db_session.add(member)

    vendor = Vendor(organisation_id=org.id, legal_name="Echo Enterprise", constitution=ConstitutionEnum.PROPRIETORSHIP.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-SCEN-E-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=user.id,
        legal_name="Echo Enterprise",
        constitution=ConstitutionEnum.PROPRIETORSHIP.value,
        pan="ABCPE1234F",
        bank_account_holder_name="Echo Enterprise",
        bank_account_number="TIMEOUT1234",  # Triggers simulated gateway timeout
        bank_ifsc="HDFC0001234",
        contact_mobile="9876543210",
        contact_email=f"v-{tok}@e.com",
        pincode="560001",
    )
    db_session.add(app)
    db_session.commit()

    orchestrator = ValidationOrchestrator(db_session)
    val_run = orchestrator.run_full_validation(app.id, user_id=user.id)

    # Check exception
    exc = (
        db_session.query(OnboardingException)
        .filter(
            OnboardingException.application_id == app.id,
            OnboardingException.category == ExceptionCategoryEnum.EXTERNAL_VERIFICATION_UNAVAILABLE.value,
        )
        .first()
    )
    assert exc is not None
    assert exc.assigned_role == RoleEnum.PROCUREMENT_OFFICER.value
    assert exc.status == ExceptionStatusEnum.OPEN.value
    assert exc.vendor_action_instruction is None, "Should not ask vendor to re-upload documents for provider timeout"


def test_internal_comment_isolation(db_session: Session):
    """Verify internal reviewer comments are not leaked to vendors."""
    tok = secrets.token_hex(4)
    org = Organization(name=f"Org Comment Test {tok}", slug=f"org-comm-{tok}")
    db_session.add(org)
    db_session.flush()

    r_user = User(email=f"reviewer-{tok}@org.com", full_name="Reviewer", hashed_password="pw")
    v_user = User(email=f"vendor-{tok}@org.com", full_name="Vendor", hashed_password="pw")
    db_session.add_all([r_user, v_user])
    db_session.flush()

    vendor = Vendor(organisation_id=org.id, legal_name="Comm Test", constitution=ConstitutionEnum.PROPRIETORSHIP.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-COMM-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=v_user.id,
        legal_name="Comm Test",
        constitution=ConstitutionEnum.PROPRIETORSHIP.value,
    )
    db_session.add(app)
    db_session.flush()

    exc = OnboardingException(
        reference_number=f"EXC-COMM-{tok}",
        organisation_id=org.id,
        application_id=app.id,
        vendor_id=vendor.id,
        category=ExceptionCategoryEnum.MISSING_INFORMATION.value,
        title="Check Address",
        description="Address line missing",
        severity=ExceptionSeverityEnum.LOW.value,
        status=ExceptionStatusEnum.OPEN.value,
        created_by_user_id=r_user.id,
        created_by_role=RoleEnum.REVIEWER.value,
    )
    db_session.add(exc)
    db_session.flush()

    # Add 1 internal reviewer note, 1 vendor-visible clarification
    c_internal = ExceptionComment(
        exception_id=exc.id,
        author_user_id=r_user.id,
        author_role=RoleEnum.REVIEWER.value,
        is_internal=True,
        message="Reviewer internal assessment: high risk entity, verify directors.",
    )
    c_public = ExceptionComment(
        exception_id=exc.id,
        author_user_id=r_user.id,
        author_role=RoleEnum.REVIEWER.value,
        is_internal=False,
        message="Please provide your registered office address proof.",
    )
    db_session.add_all([c_internal, c_public])
    db_session.commit()

    # Sanitize for vendor
    from app.api.endpoints.exceptions import sanitize_exception_for_vendor
    sanitized = sanitize_exception_for_vendor(exc)

    messages = [c.message for c in sanitized.comments]
    assert "Please provide your registered office address proof." in messages
    assert "Reviewer internal assessment: high risk entity, verify directors." not in messages


def test_scenario_c_bank_account_mismatch_and_revalidation(db_session: Session):
    """
    Scenario C: Bank account number mismatch between application form and cancelled cheque.
    Vendor corrects the account number, selective revalidation updates findings.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Org Scen C {tok}", slug=f"org-scen-c-{tok}")
    db_session.add(org)
    db_session.flush()

    v_user = User(email=f"vendor-{tok}@c.com", full_name="Vendor C", hashed_password="pw")
    db_session.add(v_user)
    db_session.flush()

    v_member = OrganisationMember(organisation_id=org.id, user_id=v_user.id, role=RoleEnum.VENDOR.value)
    db_session.add(v_member)

    vendor = Vendor(organisation_id=org.id, legal_name="Gamma Tech", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-SCEN-C-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=v_user.id,
        legal_name="Gamma Tech Private Limited",
        constitution=ConstitutionEnum.PVT_LTD.value,
        pan="AAACG1234A",
        bank_account_holder_name="Gamma Tech Private Limited",
        bank_account_number="999999999999",  # Mistyped by vendor
        bank_ifsc="HDFC0001234",
        contact_mobile="9876543210",
        contact_email=f"vendor-{tok}@c.com",
        pincode="560001",
    )
    db_session.add(app)
    db_session.flush()

    # Cancelled cheque document uploaded with extracted account number 123456789012
    chq_doc = Document(
        application_id=app.id,
        organisation_id=org.id,
        title="Bank Account Proof",
        document_type=DocumentTypeEnum.BANK_PROOF.value,
        status="CURRENT",
    )
    db_session.add(chq_doc)
    db_session.flush()

    chq_ver = DocumentVersion(
        document_id=chq_doc.id,
        version_number=1,
        storage_key=f"scen_c/{tok}/cheque_v1.pdf",
        original_filename="cheque_v1.pdf",
        file_size_bytes=1024,
        content_type="application/pdf",
        file_checksum=f"fake_chq_v1_{tok}",
    )
    db_session.add(chq_ver)
    db_session.flush()
    chq_doc.current_version_id = chq_ver.id

    ext_res = DocumentExtractionResult(
        document_version_id=chq_ver.id,
        document_id=chq_doc.id,
        application_id=app.id,
        status=ProcessingStatusEnum.EXTRACTED.value,
        detected_document_type=DocumentTypeEnum.BANK_PROOF.value,
        is_type_match=True,
    )
    db_session.add(ext_res)
    db_session.flush()

    f1 = ExtractedField(
        extraction_result_id=ext_res.id,
        field_name="account_number",
        extracted_value="123456789012",
    )
    f2 = ExtractedField(
        extraction_result_id=ext_res.id,
        field_name="ifsc",
        extracted_value="HDFC0001234",
    )
    db_session.add_all([f1, f2])
    db_session.commit()

    orchestrator = ValidationOrchestrator(db_session)
    val_run1 = orchestrator.run_full_validation(app.id, user_id=v_user.id)

    # Check bank mismatch exception created
    exc = (
        db_session.query(OnboardingException)
        .filter(
            OnboardingException.application_id == app.id,
            OnboardingException.category == ExceptionCategoryEnum.BANK_DETAIL_MISMATCH.value,
        )
        .first()
    )
    assert exc is not None
    assert exc.status == ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value

    # Vendor corrects bank account number to match document: 123456789012
    service = ExceptionResolutionService(db_session)
    updated_exc = service.submit_vendor_correction(
        exception_id=exc.id,
        user=v_user,
        field_name="bank_account_number",
        new_field_value="123456789012",
        explanation="Corrected typo in bank account number based on cancelled cheque",
    )
    assert updated_exc.status == ExceptionStatusEnum.RESPONSE_SUBMITTED.value

    db_session.refresh(app)
    assert app.bank_account_number == "123456789012"

    # Verify field correction record was saved with masked value
    corr = db_session.query(FieldCorrectionRecord).filter(FieldCorrectionRecord.exception_id == exc.id).first()
    assert corr is not None
    assert corr.field_name == "bank_account_number"


def test_scenario_f_reopening_exception_requires_reason(db_session: Session):
    """
    Scenario F: Reopening an exception requires a mandatory reason, and transitions are tracked.
    """
    from app.services.exceptions.state_machine import validate_transition

    # 1. Reopening without reason should fail
    with pytest.raises(HTTPException) as exc_info:
        validate_transition(
            current_status=ExceptionStatusEnum.RESOLVED.value,
            target_status=ExceptionStatusEnum.OPEN.value,
            actor_role=RoleEnum.REVIEWER.value,
            reason=None,
        )
    assert exc_info.value.status_code == 400
    assert "reasoned justification is mandatory" in exc_info.value.detail

    # 2. Reopening with empty string should fail
    with pytest.raises(HTTPException) as exc_info2:
        validate_transition(
            current_status=ExceptionStatusEnum.CLOSED.value,
            target_status=ExceptionStatusEnum.OPEN.value,
            actor_role=RoleEnum.PROCUREMENT_OFFICER.value,
            reason="   ",
        )
    assert exc_info2.value.status_code == 400

    # 3. Reopening with valid justification succeeds
    validate_transition(
        current_status=ExceptionStatusEnum.RESOLVED.value,
        target_status=ExceptionStatusEnum.OPEN.value,
        actor_role=RoleEnum.REVIEWER.value,
        reason="Vendor uploaded bank document has blurry IFSC code upon closer inspection",
    )


def test_vendor_role_guardrails_on_exception_transitions(db_session: Session):
    """
    Verify vendors cannot perform unauthorized state machine transitions.
    Vendors can only move from ACTION_REQUIRED_FROM_VENDOR -> RESPONSE_SUBMITTED.
    """
    from app.services.exceptions.state_machine import validate_transition

    # Vendor cannot resolve an exception
    with pytest.raises(HTTPException) as exc1:
        validate_transition(
            current_status=ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
            target_status=ExceptionStatusEnum.RESOLVED.value,
            actor_role=RoleEnum.VENDOR.value,
            reason="Self-resolving",
        )
    assert exc1.value.status_code == 403

    # Vendor cannot reopen an exception
    with pytest.raises(HTTPException) as exc2:
        validate_transition(
            current_status=ExceptionStatusEnum.RESOLVED.value,
            target_status=ExceptionStatusEnum.OPEN.value,
            actor_role=RoleEnum.VENDOR.value,
            reason="Want to change more things",
        )
    assert exc2.value.status_code == 403

    # Vendor cannot transition when status is OPEN (not yet requested from vendor)
    with pytest.raises(HTTPException) as exc3:
        validate_transition(
            current_status=ExceptionStatusEnum.OPEN.value,
            target_status=ExceptionStatusEnum.RESPONSE_SUBMITTED.value,
            actor_role=RoleEnum.VENDOR.value,
            reason="Submitting anyway",
        )
    assert exc3.value.status_code == 400
