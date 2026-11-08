import pytest
import json
import secrets
from datetime import datetime, timezone
from sqlalchemy.orm import Session

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
    ExternalVerificationRecord,
    DuplicateSignal,
    ValidationStatusEnum,
    ValidationSeverityEnum,
    ValidationLayerEnum,
)
from app.services.validation.checksums import (
    calculate_gstin_check_digit,
    validate_gstin_structure,
    validate_pan_structure,
    validate_cin_llpin_structure,
    validate_ifsc_structure,
    validate_udyam_structure,
)
from app.services.validation.name_matching import compare_names, NameMatchOutcome
from app.services.validation.orchestrator import ValidationOrchestrator
from app.services.verification.base import VerificationResult, VerificationStatus


def test_gstin_mod36_checksum_and_structure():
    """Verify official Indian GSTIN Mod-36 weighted checksum algorithm and state codes."""
    # Test valid GSTIN: 29AAACA1234A1ZG
    # Calculate check digit for first 14 chars
    check_char = calculate_gstin_check_digit("29AAACA1234A1Z")
    assert check_char == "G"

    is_valid, err = validate_gstin_structure("29AAACA1234A1ZG")
    assert is_valid is True
    assert err is None

    # Invalid state code: 95
    is_valid, err = validate_gstin_structure("95AAACA1234A1ZG")
    assert is_valid is False
    assert "Invalid state code" in err


def test_verified_pan_without_returned_name_is_not_reported_as_failed(db_session: Session, monkeypatch):
    token = secrets.token_hex(4)
    org = Organization(name=f"Org PAN Copy {token}", slug=f"org-pan-copy-{token}")
    db_session.add(org)
    db_session.flush()
    user = User(email=f"pan-copy-{token}@vendor.com", full_name="PAN Test", hashed_password="pw")
    db_session.add(user)
    db_session.flush()
    vendor = Vendor(organisation_id=org.id, legal_name="Example Components Private Limited", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()
    app = Application(
        reference_number=f"APP-PAN-COPY-{token}", organisation_id=org.id, vendor_id=vendor.id,
        created_by_user_id=user.id, legal_name=vendor.legal_name, constitution=ConstitutionEnum.PVT_LTD.value,
        pan="AAACA1234A", is_gst_registered=False, is_udyam_registered=False,
        contact_email=user.email, contact_mobile="9876543210", pincode="560001",
    )
    db_session.add(app)
    db_session.flush()
    orchestrator = ValidationOrchestrator(db_session)
    monkeypatch.setattr(
        orchestrator.pan_adapter,
        "verify",
        lambda identifier, context: VerificationResult(
            verification_type="PAN", provider_name="Test sandbox", request_id="test-1",
            submitted_identifier="XXXX1234A", status=VerificationStatus.VERIFIED,
            is_simulated=True, returned_attributes={}, reason="Active record", duration_ms=1,
        ),
    )

    pan_finding = next(
        finding for finding in orchestrator.run_layer_c_verifications(app)
        if finding["check_id"] == "C_PAN_EXTERNAL_VERIFICATION"
    )

    assert pan_finding["status"] == ValidationStatusEnum.PASSED.value
    assert "failed" not in pan_finding["explanation"].lower()
    assert "No registered taxpayer name" in pan_finding["explanation"]

    # Checksum mismatch
    is_valid, err = validate_gstin_structure("29AAACA1234A1Z9")
    assert is_valid is False
    assert "checksum mismatch" in err


def test_pan_constitution_aware_validation():
    """Verify 4th character of PAN conforms to business constitution."""
    # Individual / Sole Proprietor -> 4th char 'P'. Here 'C' is company, so should mismatch.
    is_valid, err = validate_pan_structure("ABCCE1234F", "PROPRIETORSHIP")
    assert is_valid is False
    assert "PAN 4th character must be 'P'" in err

    is_valid, err = validate_pan_structure("ABCPE1234F", "PROPRIETORSHIP")
    assert is_valid is True

    # Company -> 4th char 'C'
    is_valid, err = validate_pan_structure("AAACE1234F", "PVT_LTD")
    assert is_valid is True

    is_valid, err = validate_pan_structure("AAAPE1234F", "PVT_LTD")
    assert is_valid is False
    assert "PAN 4th character must be 'C'" in err

    # LLP -> 4th char 'L'
    is_valid, err = validate_pan_structure("AAALE1234F", "LLP")
    assert is_valid is True


def test_entity_aware_name_matching():
    """Verify 5-tier entity-aware name comparison logic."""
    # Exact Match
    res = compare_names("Acme Tech Solutions Private Limited", "Acme Tech Solutions Private Limited")
    assert res.outcome == NameMatchOutcome.EXACT_MATCH
    assert res.similarity_score == 1.0

    # Normalised Match (legal suffix stripping and casing)
    res = compare_names("Acme Tech Solutions Pvt Ltd", "ACME TECH SOLUTIONS LIMITED")
    assert res.outcome == NameMatchOutcome.NORMALISED_MATCH
    assert res.similarity_score == 1.0

    # Probable Match (abbreviation / word variant)
    res = compare_names("Apex Components and Fasteners Pvt Ltd", "Apex Components Pvt Ltd")
    assert res.outcome == NameMatchOutcome.PROBABLE_MATCH
    assert res.similarity_score >= 0.80

    # Significant Mismatch
    res = compare_names("Apex Components Pvt Ltd", "Bharat Logistics Global Limited")
    assert res.outcome == NameMatchOutcome.SIGNIFICANT_MISMATCH
    assert res.similarity_score < 0.50


def test_scenario_a_clean_vendor(db_session: Session):
    """
    Scenario A: Clean vendor application with consistent PAN, GST, bank details and documents.
    Validates Layer A, Layer B, Layer C, and Layer D pass without failures.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Org Clean Vendor {tok}", slug=f"org-clean-{tok}")
    db_session.add(org)
    db_session.flush()

    user = User(email=f"clean-{tok}@vendor.com", full_name="Clean Vendor Admin", hashed_password="pw")
    db_session.add(user)
    db_session.flush()

    member = OrganisationMember(organisation_id=org.id, user_id=user.id, role=RoleEnum.VENDOR.value)
    db_session.add(member)

    vendor = Vendor(organisation_id=org.id, legal_name="Acme Infotech Private Limited", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-CLEAN-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=user.id,
        legal_name="Acme Infotech Private Limited",
        constitution=ConstitutionEnum.PVT_LTD.value,
        pan="AAACA1234A",
        is_gst_registered=True,
        gstin="29AAACA1234A1ZG",
        cin_llpin="U72200KA2020PTC123456",
        bank_account_holder_name="Acme Infotech Private Limited",
        bank_account_number="987654321098",
        bank_ifsc="HDFC0001234",
        contact_mobile="9876543210",
        contact_email=f"clean-{tok}@vendor.com",
        pincode="560001",
        status=ApplicationStatusEnum.SUBMITTED.value,
    )
    db_session.add(app)
    db_session.flush()

    # Create matching PAN Document and OCR Extraction
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
        storage_key=f"clean/{tok}/pan.pdf",
        original_filename="pan.pdf",
        file_size_bytes=1024,
        content_type="application/pdf",
        file_checksum=f"hash1_{tok}",
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
        normalized_value="AAACA1234A",
    )
    f2 = ExtractedField(
        extraction_result_id=ext_res.id,
        field_name="pan_holder_name",
        extracted_value="Acme Infotech Private Limited",
        normalized_value="Acme Infotech Private Limited",
    )
    db_session.add_all([f1, f2])
    db_session.commit()

    orchestrator = ValidationOrchestrator(db_session)
    val_run = orchestrator.run_full_validation(app.id, user_id=user.id)

    assert val_run.status == "COMPLETED"
    assert val_run.is_current is True
    assert val_run.failed_count == 0
    assert val_run.passed_count > 5


def test_scenario_b_gst_pan_mismatch(db_session: Session):
    """
    Scenario B: Embedded PAN in GSTIN does not match declared business PAN.
    Verifies Layer B cross-field check flags critical failure.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Org Mismatch {tok}", slug=f"org-mismatch-{tok}")
    db_session.add(org)
    db_session.flush()

    user = User(email=f"mismatch-{tok}@vendor.com", full_name="Mismatch Admin", hashed_password="pw")
    db_session.add(user)
    db_session.flush()

    vendor = Vendor(organisation_id=org.id, legal_name="Beta Trading Ltd", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()

    # Application has PAN AAACA1234A, but GSTIN has embedded PAN BBBCA5678B
    app = Application(
        reference_number=f"APP-MISMATCH-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=user.id,
        legal_name="Beta Trading Ltd",
        constitution=ConstitutionEnum.PVT_LTD.value,
        pan="AAACA1234A",
        is_gst_registered=True,
        gstin="29BBBCA5678B1Z2",  # Checksum digit 2
        cin_llpin="U72200KA2020PTC123456",
        bank_account_holder_name="Beta Trading Ltd",
        bank_account_number="112233445566",
        bank_ifsc="SBIN0001234",
        contact_mobile="9876543210",
        contact_email=f"mismatch-{tok}@vendor.com",
        pincode="560001",
    )
    db_session.add(app)
    db_session.commit()

    orchestrator = ValidationOrchestrator(db_session)
    val_run = orchestrator.run_full_validation(app.id, user_id=user.id)

    # Check finding for B_GSTIN_EMBEDDED_PAN_MATCH
    finding = next((f for f in val_run.findings if f.check_id == "B_GSTIN_EMBEDDED_PAN_MATCH"), None)
    assert finding is not None
    assert finding.status == ValidationStatusEnum.FAILED.value
    assert finding.severity == ValidationSeverityEnum.CRITICAL.value
    assert "Statutory mismatch: Embedded PAN" in finding.explanation


def test_scenario_c_name_variation_warning(db_session: Session):
    """
    Scenario C: Name variation between application and document (e.g. Apex Tech vs Apex Technologies).
    Verifies that it triggers a WARNING (Probable Match) rather than a hard failure.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Org Name Variation {tok}", slug=f"org-name-var-{tok}")
    db_session.add(org)
    db_session.flush()

    user = User(email=f"apex-{tok}@vendor.com", full_name="Apex Admin", hashed_password="pw")
    db_session.add(user)
    db_session.flush()

    vendor = Vendor(organisation_id=org.id, legal_name="Apex Components & Fasteners Private Limited", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-VAR-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=user.id,
        legal_name="Apex Components & Fasteners Private Limited",
        constitution=ConstitutionEnum.PVT_LTD.value,
        pan="AAACA1234A",
        is_gst_registered=False,
        cin_llpin="U72200KA2020PTC123456",
        bank_account_holder_name="Apex Components & Fasteners Private Limited",
        bank_account_number="112233445566",
        bank_ifsc="HDFC0001234",
        contact_mobile="9876543210",
        contact_email=f"apex-{tok}@vendor.com",
        pincode="560001",
    )
    db_session.add(app)
    db_session.flush()

    # Upload PAN doc with slight name variation: "Apex Components Private Limited"
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
        storage_key=f"apex/{tok}/pan.pdf",
        original_filename="pan.pdf",
        file_size_bytes=1024,
        content_type="application/pdf",
        file_checksum=f"hash_apex_{tok}",
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
        extracted_value="Apex Components Private Limited",
    )
    db_session.add_all([f1, f2])
    db_session.commit()

    orchestrator = ValidationOrchestrator(db_session)
    val_run = orchestrator.run_full_validation(app.id, user_id=user.id)

    name_finding = next((f for f in val_run.findings if f.check_id == "B_NAME_PAN_DOC_MATCH"), None)
    assert name_finding is not None
    assert name_finding.status == ValidationStatusEnum.WARNING.value
    assert "Probable match" in name_finding.evidence or "score:" in name_finding.evidence


def test_scenario_d_bank_account_mismatch(db_session: Session):
    """
    Scenario D: Form bank account number differs from extracted bank document.
    Verifies Layer B flags bank account number mismatch as CRITICAL FAILED.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Org Bank Mismatch {tok}", slug=f"org-bank-{tok}")
    db_session.add(org)
    db_session.flush()

    user = User(email=f"bank-{tok}@vendor.com", full_name="Bank Admin", hashed_password="pw")
    db_session.add(user)
    db_session.flush()

    vendor = Vendor(organisation_id=org.id, legal_name="Delta Services", constitution=ConstitutionEnum.PROPRIETORSHIP.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-BANK-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=user.id,
        legal_name="Delta Services",
        constitution=ConstitutionEnum.PROPRIETORSHIP.value,
        pan="ABCPE1234F",
        bank_account_holder_name="Delta Services",
        bank_account_number="123456789012",
        bank_ifsc="ICIC0001234",
        contact_mobile="9876543210",
        contact_email=f"bank-{tok}@vendor.com",
        pincode="560001",
    )
    db_session.add(app)
    db_session.flush()

    # Upload Bank doc where extracted account is different: 999999999999
    bank_doc = Document(
        application_id=app.id,
        organisation_id=org.id,
        document_type=DocumentTypeEnum.BANK_PROOF.value,
        title="Cancelled Cheque",
        status="UPLOADED",
    )
    db_session.add(bank_doc)
    db_session.flush()

    bank_ver = DocumentVersion(
        document_id=bank_doc.id,
        version_number=1,
        storage_key=f"delta/{tok}/cheque.pdf",
        original_filename="cheque.pdf",
        file_size_bytes=1024,
        content_type="application/pdf",
        file_checksum=f"hash_bank_{tok}",
    )
    db_session.add(bank_ver)
    db_session.flush()
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
        extracted_value="999999999999",
    )
    f2 = ExtractedField(
        extraction_result_id=ext_res.id,
        field_name="ifsc_code",
        extracted_value="ICIC0001234",
    )
    db_session.add_all([f1, f2])
    db_session.commit()

    orchestrator = ValidationOrchestrator(db_session)
    val_run = orchestrator.run_full_validation(app.id, user_id=user.id)

    bank_finding = next((f for f in val_run.findings if f.check_id == "B_BANK_ACCOUNT_NUM_MATCH"), None)
    assert bank_finding is not None
    assert bank_finding.status == ValidationStatusEnum.FAILED.value
    assert bank_finding.severity == ValidationSeverityEnum.CRITICAL.value


def test_scenario_e_provider_unavailable(db_session: Session):
    """
    Scenario E: Simulated external provider times out / becomes unavailable.
    Verifies that it outputs status UNAVAILABLE (not FAILED), and is explainable.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Org Unavailable {tok}", slug=f"org-unavail-{tok}")
    db_session.add(org)
    db_session.flush()

    user = User(email=f"unavail-{tok}@vendor.com", full_name="Unavail Admin", hashed_password="pw")
    db_session.add(user)
    db_session.flush()

    vendor = Vendor(organisation_id=org.id, legal_name="Echo Tech", constitution=ConstitutionEnum.PROPRIETORSHIP.value)
    db_session.add(vendor)
    db_session.flush()

    # Special keyword "TIMEOUT" in PAN triggers simulated timeout
    app = Application(
        reference_number=f"APP-UNAVAIL-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=user.id,
        legal_name="Echo Tech",
        constitution=ConstitutionEnum.PROPRIETORSHIP.value,
        pan="ABCPE1234F",
        bank_account_holder_name="Echo Tech",
        bank_account_number="TIMEOUT1234",  # Triggers bank adapter timeout
        bank_ifsc="HDFC0001234",
        contact_mobile="9876543210",
        contact_email=f"unavail-{tok}@vendor.com",
        pincode="560001",
    )
    db_session.add(app)
    db_session.commit()

    orchestrator = ValidationOrchestrator(db_session)
    val_run = orchestrator.run_full_validation(app.id, user_id=user.id)

    bank_verif_finding = next((f for f in val_run.findings if f.check_id == "C_BANK_PENNY_DROP_VERIFICATION"), None)
    assert bank_verif_finding is not None
    assert bank_verif_finding.status == ValidationStatusEnum.UNAVAILABLE.value
    assert "timeout" in bank_verif_finding.explanation.lower() or "gateway timeout" in bank_verif_finding.explanation.lower()


def test_scenario_f_duplicate_candidate_detection(db_session: Session):
    """
    Scenario F: Duplicate vendor candidate detected strictly within the same organisation.
    Checks that DuplicateSignal is generated and organisation boundary is respected.
    """
    tok = secrets.token_hex(4)
    org1 = Organization(name=f"Org One {tok}", slug=f"org-one-{tok}")
    org2 = Organization(name=f"Org Two {tok}", slug=f"org-two-{tok}")
    db_session.add_all([org1, org2])
    db_session.flush()

    user1 = User(email=f"v1-{tok}@org1.com", full_name="Vendor One", hashed_password="pw")
    user2 = User(email=f"v2-{tok}@org1.com", full_name="Vendor Two", hashed_password="pw")
    user3 = User(email=f"v3-{tok}@org2.com", full_name="Vendor Three", hashed_password="pw")
    db_session.add_all([user1, user2, user3])
    db_session.flush()

    shared_pan = f"AAA{tok[:2].upper()}9999A"

    # App 1 in Org 1
    v1 = Vendor(organisation_id=org1.id, legal_name="Prime Supplies", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(v1)
    db_session.flush()

    app1 = Application(
        reference_number=f"APP-ORG1-01-{tok}",
        organisation_id=org1.id,
        vendor_id=v1.id,
        created_by_user_id=user1.id,
        legal_name="Prime Supplies Pvt Ltd",
        constitution=ConstitutionEnum.PVT_LTD.value,
        pan=shared_pan,
        bank_account_holder_name="Prime Supplies Pvt Ltd",
        bank_account_number="123456789012",
        bank_ifsc="HDFC0001234",
        contact_mobile="9876543210",
        contact_email=f"v1-{tok}@org1.com",
        pincode="560001",
    )
    db_session.add(app1)

    # App 2 in Org 1 (same PAN -> MUST trigger duplicate signal)
    v2 = Vendor(organisation_id=org1.id, legal_name="Prime Supplies Branch 2", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(v2)
    db_session.flush()

    app2 = Application(
        reference_number=f"APP-ORG1-02-{tok}",
        organisation_id=org1.id,
        vendor_id=v2.id,
        created_by_user_id=user2.id,
        legal_name="Prime Supplies Branch 2",
        constitution=ConstitutionEnum.PVT_LTD.value,
        pan=shared_pan,
        bank_account_holder_name="Prime Supplies Branch 2",
        bank_account_number="987654321098",
        bank_ifsc="HDFC0001234",
        contact_mobile="9876543211",
        contact_email=f"v2-{tok}@org1.com",
        pincode="560001",
    )
    db_session.add(app2)

    # App 3 in Org 2 (same PAN, but DIFFERENT organisation -> MUST NOT trigger duplicate in Org 1)
    v3 = Vendor(organisation_id=org2.id, legal_name="Prime Supplies Org 2", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(v3)
    db_session.flush()

    app3 = Application(
        reference_number=f"APP-ORG2-01-{tok}",
        organisation_id=org2.id,
        vendor_id=v3.id,
        created_by_user_id=user3.id,
        legal_name="Prime Supplies Org 2",
        constitution=ConstitutionEnum.PVT_LTD.value,
        pan=shared_pan,
        bank_account_holder_name="Prime Supplies Org 2",
        bank_account_number="123456789012",
        bank_ifsc="HDFC0001234",
        contact_mobile="9876543210",
        contact_email=f"v3-{tok}@org2.com",
        pincode="560001",
    )
    db_session.add(app3)
    db_session.commit()

    orchestrator = ValidationOrchestrator(db_session)
    val_run2 = orchestrator.run_full_validation(app2.id, user_id=user2.id)

    # Check that duplicate signal was recorded for App 2 pointing to App 1
    dup_signals = db_session.query(DuplicateSignal).filter(DuplicateSignal.application_id == app2.id).all()
    assert len(dup_signals) == 1
    assert dup_signals[0].candidate_application_id == app1.id
    assert dup_signals[0].match_strength == "STRONG"
    assert "PAN" in dup_signals[0].matching_attributes_json

    # Org 2 App 3 should NOT be listed as a candidate
    candidate_app_ids = [s.candidate_application_id for s in dup_signals]
    assert app3.id not in candidate_app_ids

    # Layer D check finding in val_run2
    dup_finding = next((f for f in val_run2.findings if f.check_id == "D_DUPLICATE_DETECTION_CHECK"), None)
    assert dup_finding is not None
    assert dup_finding.status in [ValidationStatusEnum.FAILED.value, ValidationStatusEnum.WARNING.value]


def test_change_aware_invalidation(db_session: Session):
    """
    Verify that re-uploading a document marks its dependent findings as stale,
    and subsequent validation run archives the prior run as non-current.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Org Stale Test {tok}", slug=f"org-stale-{tok}")
    db_session.add(org)
    db_session.flush()

    user = User(email=f"stale-{tok}@vendor.com", full_name="Stale Admin", hashed_password="pw")
    db_session.add(user)
    db_session.flush()

    vendor = Vendor(organisation_id=org.id, legal_name="Stale Inc", constitution=ConstitutionEnum.PROPRIETORSHIP.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-STALE-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=user.id,
        legal_name="Stale Inc",
        constitution=ConstitutionEnum.PROPRIETORSHIP.value,
        pan="ABCPE1234F",
        bank_account_holder_name="Stale Inc",
        bank_account_number="123456789012",
        bank_ifsc="HDFC0001234",
        contact_mobile="9876543210",
        contact_email=f"stale-{tok}@vendor.com",
        pincode="560001",
    )
    db_session.add(app)
    db_session.flush()

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
        storage_key=f"stale/{tok}/pan.pdf",
        original_filename="pan.pdf",
        file_size_bytes=1024,
        content_type="application/pdf",
        file_checksum=f"hash_stale_{tok}",
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
        extracted_value="ABCPE1234F",
    )
    db_session.add(f1)
    db_session.commit()

    orchestrator = ValidationOrchestrator(db_session)
    run_1 = orchestrator.run_full_validation(app.id, user_id=user.id)
    assert run_1.is_current is True

    # Now mark stale findings for pan_doc
    count_stale = orchestrator.mark_stale_findings_for_document(pan_doc.id, reason="Document re-uploaded")
    assert count_stale >= 1

    # Check that finding is stale in db
    stale_finding = db_session.query(ValidationFinding).filter(ValidationFinding.source_document_id == pan_doc.id).first()
    assert stale_finding.is_stale is True
    assert stale_finding.stale_reason == "Document re-uploaded"

    # Trigger Run 2
    run_2 = orchestrator.run_full_validation(app.id, user_id=user.id, trigger_reason="Document update")
    assert run_2.is_current is True

    db_session.refresh(run_1)
    assert run_1.is_current is False
