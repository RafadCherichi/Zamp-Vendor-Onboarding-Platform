import re
import secrets
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.organization import Organization
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.vendor import Vendor
from app.models.application import Application, ApplicationStatusEnum, ConstitutionEnum
from app.models.document import Document, DocumentVersion
from app.models.extraction import ExtractedField, DocumentExtractionResult
from app.models.validation import (
    ValidationRun,
    ValidationFinding,
    ValidationStatusEnum,
    ValidationSeverityEnum,
)
from app.schemas.validation import ValidationRunResponse, ValidationFindingResponse
from app.core.security import create_access_token
from app.services.checklist import sync_application_documents
from app.services.extraction.extractors.pan import extract_pan_fields, is_valid_name_candidate
from app.services.review.queue_service import QueueAndDashboardService


def create_scoped_token(user: User, org: Organization, role: RoleEnum) -> str:
    return create_access_token({
        "sub": user.id,
        "email": user.email,
        "org_id": org.id,
        "role": role.value if isinstance(role, RoleEnum) else role,
    })


def setup_test_vendor(db_session: Session, org_name="UX Inc", email_prefix="vendor"):
    uid = secrets.token_hex(4)
    org = Organization(name=f"{org_name} {uid}", slug=f"org-{uid}")
    db_session.add(org)
    db_session.flush()

    user = User(email=f"{email_prefix}-{uid}@example.com", full_name=f"Vendor User {uid}", hashed_password="pw")
    db_session.add(user)
    db_session.flush()

    member = OrganisationMember(organisation_id=org.id, user_id=user.id, role=RoleEnum.VENDOR.value)
    db_session.add(member)

    vendor = Vendor(
        organisation_id=org.id,
        created_by_user_id=user.id,
        legal_name=f"Test Supplier {uid}",
        trade_name=f"Supplier {uid}",
        constitution=ConstitutionEnum.PVT_LTD.value,
        pan="AABCT1234D",
    )
    db_session.add(vendor)
    db_session.flush()

    app_record = Application(
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=user.id,
        status=ApplicationStatusEnum.IN_PROGRESS.value,
        reference_number=f"APP-{uid.upper()}",
        legal_name=f"Test Supplier {uid}",
        trade_name=f"Supplier {uid}",
        constitution=ConstitutionEnum.PVT_LTD.value,
        registered_address="123 Tech Park, Sector 4",
        city="Bengaluru",
        state="Karnataka",
        pincode="560001",
        pan="AABCT1234D",
        is_gst_registered=False,
        is_udyam_registered=False,
        cin_llpin="U72200KA2020PTC123456",
        contact_name="Ramesh Sharma",
        contact_email=f"ramesh-{uid}@example.com",
        contact_mobile="+919876543210",
        bank_account_holder_name=f"Test Supplier {uid}",
        bank_account_number="987654321012",
        bank_ifsc="CNRB0005419",
        bank_account_type="CURRENT",
        categories_json='["it_services"]',
        declaration_accurate_info=True,
        declaration_authorised_rep=True,
        declaration_verification_consent=True,
    )
    db_session.add(app_record)
    db_session.flush()
    sync_application_documents(db_session, app_record)
    db_session.commit()
    db_session.refresh(app_record)

    token = create_scoped_token(user, org, RoleEnum.VENDOR)
    return org, user, app_record, token


class TestIncrement2UXAndConsistency:
    """Automated tests for Increment 2 UX, Language, Document Experience & Consistency improvements."""

    def test_business_activity_mandatory_and_draft_persistence(self, client: TestClient, db_session: Session):
        """Step 5 activity selection is mandatory, 'other' requires description, and description is cleared when deselected."""
        org, user, app_record, token = setup_test_vendor(db_session, "Activity Co", "act")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Update draft with 'other' and description
        resp = client.patch(
            f"/api/applications/{app_record.id}",
            json={
                "categories": ["other"],
                "other_business_activity_description": "Custom aerospace component manufacturing",
            },
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["categories"] == ["other"]
        assert data["other_business_activity_description"] == "Custom aerospace component manufacturing"

        # Verify DB persistence directly
        db_session.expire_all()
        refreshed = db_session.query(Application).filter(Application.id == app_record.id).first()
        assert refreshed.other_business_activity_description == "Custom aerospace component manufacturing"

        # 2. Deselecting 'other' automatically clears description
        resp = client.patch(
            f"/api/applications/{app_record.id}",
            json={"categories": ["it_services", "consulting"]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "other" not in data["categories"]
        assert data["other_business_activity_description"] is None

        # Verify DB persistence of cleared state
        db_session.expire_all()
        refreshed = db_session.query(Application).filter(Application.id == app_record.id).first()
        assert refreshed.other_business_activity_description is None

    def test_submission_blocked_when_business_activity_empty_or_other_missing(
        self, client: TestClient, db_session: Session
    ):
        """Submission must fail with clear message if categories empty or other description missing."""
        org, user, app_record, token = setup_test_vendor(db_session, "Submit Co", "sub")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Clear categories to empty list
        client.patch(
            f"/api/applications/{app_record.id}",
            json={"categories": []},
            headers=headers,
        )

        resp = client.post(f"/api/applications/{app_record.id}/submit", headers=headers)
        assert resp.status_code == 400
        detail1 = resp.json().get("detail", {})
        errors = detail1.get("errors", []) if isinstance(detail1, dict) else resp.json().get("errors", [])
        assert any("Step 5 (Activity)" in err for err in errors)

        # 2. Set 'other' without description
        client.patch(
            f"/api/applications/{app_record.id}",
            json={"categories": ["other"]},
            headers=headers,
        )

        resp = client.post(f"/api/applications/{app_record.id}/submit", headers=headers)
        assert resp.status_code == 400
        detail2 = resp.json().get("detail", {})
        errors = detail2.get("errors", []) if isinstance(detail2, dict) else resp.json().get("errors", [])
        assert any("Other" in err or "describe your business activity" in err for err in errors)

    def test_reviewer_workspace_includes_other_business_activity(self, db_session: Session):
        """Reviewer comprehensive details service surfaces other_business_activity_description under classification."""
        org, user, app_record, token = setup_test_vendor(db_session, "Rev Co", "rev")

        app_record.categories = ["manufacturing", "other"]
        app_record.other_business_activity_description = "Specialized cryogenic valve assembly"
        db_session.commit()

        # Create reviewer member for scoped access
        rev_user = User(email=f"reviewer-{secrets.token_hex(4)}@example.com", full_name="Compliance Reviewer", hashed_password="pw")
        db_session.add(rev_user)
        db_session.flush()
        rev_member = OrganisationMember(organisation_id=org.id, user_id=rev_user.id, role=RoleEnum.REVIEWER.value)
        db_session.add(rev_member)
        db_session.commit()

        service = QueueAndDashboardService(db_session)
        details = service.get_application_details_comprehensive(app_record.id, rev_member)
        assert details is not None
        classification = details.get("classification", {})
        assert classification.get("other_business_activity_description") == "Specialized cryogenic valve assembly"
        assert "manufacturing" in classification.get("categories", [])
        assert "other" in classification.get("categories", [])

        # Also verify nested under business_details
        nested_classification = details.get("business_details", {}).get("classification", {})
        assert nested_classification.get("other_business_activity_description") == "Specialized cryogenic valve assembly"

    def test_pan_father_name_candidate_guards(self):
        """Candidate validator strictly rejects numbers, dates, and non-name text."""
        assert is_valid_name_candidate("14022022") is False
        assert is_valid_name_candidate("14/02/2022") is False
        assert is_valid_name_candidate("14-02-2022") is False
        assert is_valid_name_candidate("1234567890") is False
        assert is_valid_name_candidate("INCOME TAX DEPARTMENT") is False
        assert is_valid_name_candidate("PERMANENT ACCOUNT NUMBER") is False
        assert is_valid_name_candidate("GOVT OF INDIA") is False
        assert is_valid_name_candidate("A") is False
        assert is_valid_name_candidate("") is False

        # Valid names
        assert is_valid_name_candidate("RAMESH CHAND") is True
        assert is_valid_name_candidate("SURESH KUMAR GUPTA") is True
        assert is_valid_name_candidate("ANAND S") is True

    def test_pan_extraction_rejects_dates_as_father_name_and_respects_constitution(self):
        """PAN extractor guards against extracting dates (like 14022022) as father's name, and skips father for company PANs."""
        # Case 1: Individual PAN (4th char 'P') with a date on the line following FATHER
        ocr_text_with_date = """
        INCOME TAX DEPARTMENT
        GOVT OF INDIA
        RAMESH MALHOTRA
        FATHER'S NAME
        14022022
        DATE OF BIRTH
        14/02/1985
        ABCDE1234F
        """
        res1 = {f.field_name: f.extracted_value for f in extract_pan_fields(ocr_text_with_date)}
        # Father's name must NOT be 14022022 or digits
        father_name1 = res1.get("father_name")
        assert father_name1 is None or not re.match(r"^\d+$", str(father_name1))

        # Case 2: Individual PAN with genuine father's name
        ocr_text_valid = """
        INCOME TAX DEPARTMENT
        GOVT OF INDIA
        VIKRAM MALHOTRA
        FATHER'S NAME
        SURESH MALHOTRA
        DATE OF BIRTH 14/02/1985
        ABCDE1234F
        """
        res2 = {f.field_name: f.extracted_value for f in extract_pan_fields(ocr_text_valid)}
        assert res2.get("father_name") == "SURESH MALHOTRA"

        # Case 3: Company PAN (4th char 'C') - should NOT extract father's name even if the word appears
        ocr_text_company = """
        INCOME TAX DEPARTMENT
        GOVT OF INDIA
        TECH SOLUTIONS PRIVATE LIMITED
        FATHER OF THE FOUNDER
        RAMESH CHAND
        INCORPORATION DATE 10/10/2018
        AAACT1234D
        """
        res3 = {f.field_name: f.extracted_value for f in extract_pan_fields(ocr_text_company)}
        assert res3.get("pan_number") == "AAACT1234D"
        assert res3.get("father_name") is None

    def test_document_extraction_eye_reveal_unmasking(self, client: TestClient, db_session: Session):
        """Document extraction detail endpoint returns raw unmasked value in extracted_value and masked value in normalized_value."""
        org, user, app_record, token = setup_test_vendor(db_session, "Doc Co", "doc")
        headers = {"Authorization": f"Bearer {token}"}

        # Find existing PAN_PROOF slot from synced checklist
        doc = next(d for d in app_record.documents if d.document_type == "PAN_PROOF")
        doc.status = "UPLOADED"

        ver = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            original_filename="pan_card.pdf",
            storage_key="mock/path/pan.pdf",
            file_size_bytes=1024,
            content_type="application/pdf",
            file_checksum="a" * 64,
            uploaded_by_user_id=user.id,
        )
        db_session.add(ver)
        db_session.flush()

        doc.current_version_id = ver.id

        # Create extraction result and extracted field with sensitive PAN number
        ext_result = DocumentExtractionResult(
            document_version_id=ver.id,
            document_id=doc.id,
            application_id=app_record.id,
            status="EXTRACTED",
            detected_document_type="PAN_PROOF",
            classification_confidence=0.99,
        )
        db_session.add(ext_result)
        db_session.flush()

        ef = ExtractedField(
            extraction_result_id=ext_result.id,
            field_name="pan_number",
            extracted_value="AABCT1234D",
            normalized_value="AABCT1234D",
            confidence_score=0.98,
            extraction_method="OCR",
            page_number=1,
        )
        db_session.add(ef)
        db_session.commit()

        resp = client.get(
            f"/api/applications/{app_record.id}/documents/{doc.id}/extraction",
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data["fields"]) >= 1
        pan_field = next(f for f in data["fields"] if f["field_name"] == "pan_number")

        # extracted_value should be the unmasked raw statutory number
        assert pan_field["extracted_value"] == "AABCT1234D"
        # normalized_value should be masked for privacy (e.g. AA*****4D)
        assert "*" in pan_field["normalized_value"]
        assert pan_field["normalized_value"] != pan_field["extracted_value"]

    def test_canara_bank_ifsc_format_validity(self):
        """CNRB0005419 is structurally valid RBI IFSC format with 11 characters and 0 as 5th char."""
        ifsc = "CNRB0005419"
        ifsc_regex = r"^[A-Z]{4}0[A-Z0-9]{6}$"
        assert re.match(ifsc_regex, ifsc) is not None
        assert len(ifsc) == 11
        assert ifsc[4] == "0"
        assert ifsc[:4] == "CNRB"

    def test_deterministic_validation_findings_ordering(self):
        """Validation findings in ValidationRunResponse are sorted deterministically across groups and checks."""
        # Create mock findings in deliberately scrambled order
        now_str = "2026-11-06T00:00:00Z"
        raw_findings = [
            ValidationFindingResponse(
                id=secrets.token_hex(8),
                check_id="V-DUP-001",
                check_name="Duplicate PAN Detection",
                layer="LAYER_D_DUPLICATE",
                status="PASSED",
                severity="HIGH",
                explanation="No duplicate PAN found",
                created_at=now_str,
            ),
            ValidationFindingResponse(
                id=secrets.token_hex(8),
                check_id="V-INP-001",
                check_name="PAN Format and Checksum",
                layer="LAYER_A_INPUT",
                status="PASSED",
                severity="CRITICAL",
                explanation="Valid PAN format",
                created_at=now_str,
            ),
            ValidationFindingResponse(
                id=secrets.token_hex(8),
                check_id="V-EXT-002",
                check_name="PAN Authority Active Check",
                layer="LAYER_C_EXTERNAL",
                status="PASSED",
                severity="HIGH",
                explanation="PAN active in registry",
                created_at=now_str,
            ),
            ValidationFindingResponse(
                id=secrets.token_hex(8),
                check_id="V-INP-004",
                check_name="IFSC Format and Bank Resolution",
                layer="LAYER_A_INPUT",
                status="PASSED",
                severity="HIGH",
                explanation="Valid IFSC format",
                created_at=now_str,
            ),
            ValidationFindingResponse(
                id=secrets.token_hex(8),
                check_id="V-CON-001",
                check_name="Legal Entity & Constitution Consistency",
                layer="LAYER_A_INPUT",
                status="PASSED",
                severity="CRITICAL",
                explanation="Constitution matches name",
                created_at=now_str,
            ),
            ValidationFindingResponse(
                id=secrets.token_hex(8),
                check_id="V-DOC-001",
                check_name="Document Completeness Check",
                layer="LAYER_A_INPUT",
                status="PASSED",
                severity="HIGH",
                explanation="All documents present",
                created_at=now_str,
            ),
        ]

        val_run = ValidationRunResponse(
            id=secrets.token_hex(8),
            application_id=secrets.token_hex(8),
            organisation_id=secrets.token_hex(8),
            run_type="FULL",
            status="PASSED",
            overall_status="PASSED",
            is_current=True,
            summary_notes="Test run",
            passed_count=6,
            failed_count=0,
            warning_count=0,
            unavailable_count=0,
            unverified_count=0,
            findings=raw_findings,
            created_at=now_str,
        )

        sorted_ids = [f.check_id for f in val_run.findings]

        # Verify group ordering:
        # Group 1: V-CON-001 (Constitution / Entity)
        # Group 2: V-INP-001 (PAN / Tax)
        # Group 4: V-INP-004 (Bank / IFSC)
        # Group 5: V-DOC-001 (Document)
        # Group 6: V-EXT-002 (External)
        # Group 7: V-DUP-001 (Duplicate)
        expected_ids = ["V-CON-001", "V-INP-001", "V-INP-004", "V-DOC-001", "V-EXT-002", "V-DUP-001"]
        assert sorted_ids == expected_ids
