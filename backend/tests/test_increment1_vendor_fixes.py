import io
import json
import secrets
from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.organization import Organization
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.invitation import Invitation
from app.models.vendor import Vendor
from app.models.application import Application, ApplicationStatusEnum, ConstitutionEnum
from app.models.document import Document, DocumentVersion
from app.models.exception import (
    OnboardingException,
    ExceptionStatusEnum,
    ExceptionSeverityEnum,
    ExceptionCategoryEnum,
)
from app.models.validation import (
    ValidationRun,
    ValidationFinding,
    ValidationStatusEnum,
    ValidationSeverityEnum,
)
from app.core.security import create_access_token
from app.services.checklist import sync_application_documents
from app.services.validation.orchestrator import ValidationOrchestrator
from app.storage.local import get_storage_adapter


def create_scoped_token(user: User, org: Organization, role: RoleEnum) -> str:
    return create_access_token({
        "sub": user.id,
        "email": user.email,
        "org_id": org.id,
        "role": role.value if isinstance(role, RoleEnum) else role,
    })


def setup_test_vendor(db_session: Session, org_name="Test Corp", email_prefix="vendor"):
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
        constitution=ConstitutionEnum.PROPRIETORSHIP.value,
        pan="ABCDE1234F",
    )
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=user.id,
        status=ApplicationStatusEnum.IN_PROGRESS.value,
        reference_number=f"APP-{uid.upper()}",
        legal_name=f"Test Supplier {uid}",
        trade_name=f"Supplier {uid}",
        constitution=ConstitutionEnum.PROPRIETORSHIP.value,
    )
    db_session.add(app)
    db_session.flush()
    sync_application_documents(db_session, app)
    db_session.commit()

    token = create_scoped_token(user, org, RoleEnum.VENDOR)
    return {
        "org": org,
        "user": user,
        "member": member,
        "vendor": vendor,
        "app": app,
        "token": token,
    }


# ==============================================================================
# 1 & 4. Save & Continue and Save Progress
# ==============================================================================

def test_draft_patch_step_validation_identity(db_session: Session, client: TestClient):
    """Requirement 1 & 4: Save & Continue and Save Progress updates draft without losing data."""
    ctx = setup_test_vendor(db_session)
    app_id = ctx["app"].id
    token = ctx["token"]

    # Save Step 1 (Identity)
    res = client.patch(
        f"/api/applications/{app_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "legal_name": "Acme Precision Tools LLP",
            "trade_name": "Acme Tools",
            "constitution": "LLP",
            "registered_address": "42 Tech Park, Sector 5",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560100",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["legal_name"] == "Acme Precision Tools LLP"
    assert data["pincode"] == "560100"
    assert data["constitution"] == "LLP"


def test_revisit_and_edit_preserves_other_steps(db_session: Session, client: TestClient):
    """Requirement 3: Revisit and edit earlier step without wiping later saved steps."""
    ctx = setup_test_vendor(db_session)
    app_id = ctx["app"].id
    token = ctx["token"]

    # First save Step 4 (Banking)
    r1 = client.patch(
        f"/api/applications/{app_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "bank_account_holder_name": "Acme Precision Tools",
            "bank_account_number": "50200012345678",
            "bank_ifsc": "HDFC0000123",
            "bank_name": "HDFC Bank",
        },
    )
    assert r1.status_code == 200

    # Now revisit Step 1 and change trade_name
    r2 = client.patch(
        f"/api/applications/{app_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "trade_name": "Acme Global Tools",
        },
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["trade_name"] == "Acme Global Tools"
    # Verify banking details are untouched and preserved
    assert data["bank_account_holder_name"] == "Acme Precision Tools"
    assert data["bank_ifsc"] == "HDFC0000123"


# ==============================================================================
# 2 & 8. Missing Mandatory Fields Block Submission with Structured Errors
# ==============================================================================

def test_missing_mandatory_fields_block_submission_with_actionable_errors(db_session: Session, client: TestClient):
    """Requirement 2 & 8: Missing bank or mandatory fields block submission with actionable step errors."""
    ctx = setup_test_vendor(db_session)
    app_id = ctx["app"].id
    token = ctx["token"]

    # Attempt submit on incomplete application
    res = client.post(
        f"/api/applications/{app_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    err_detail = res.json()["detail"]
    assert "errors" in err_detail
    errors = err_detail["errors"]
    assert any("Step 1" in e for e in errors)
    assert any("Step 4 (Banking)" in e for e in errors)
    assert any("Step 7 (Review)" in e for e in errors)


# ==============================================================================
# 5, 6 & 7. Safe Document Preview with Token Authentication
# ==============================================================================

def test_preview_pdf_with_token_query_param(db_session: Session, client: TestClient):
    """Requirement 5: Document preview with token query param streams PDF inline."""
    ctx = setup_test_vendor(db_session)
    app_id = ctx["app"].id
    token = ctx["token"]

    # Upload dummy PDF
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Title (Test Document) >>\nendobj\n%%EOF"
    upload_res = client.post(
        f"/api/applications/{app_id}/documents/PAN_CARD/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("pancard.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]

    # Preview using query param `?token=` (no auth header, simulates iframe/img)
    preview_res = client.get(f"/api/applications/{app_id}/documents/{doc_id}/preview?token={token}")
    assert preview_res.status_code == 200
    assert preview_res.headers["content-type"].startswith("application/pdf")
    assert "inline" in preview_res.headers.get("content-disposition", "")
    assert preview_res.content == pdf_bytes


def test_preview_image_with_token_query_param(db_session: Session, client: TestClient):
    """Requirement 6: Document preview with image returns 200 with image/png MIME type."""
    ctx = setup_test_vendor(db_session)
    app_id = ctx["app"].id
    token = ctx["token"]

    # Upload dummy PNG (valid minimal PNG 1x1 pixel)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\x9f"
        b"\x01\x01\x04\x00\x00\xff\xff\x02\x05\x01\x02\xa75H\r\x00\x00\x00\x00"
        b"IEND\xaeB`\x82"
    )
    upload_res = client.post(
        f"/api/applications/{app_id}/documents/BANK_ACCOUNT_PROOF/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cheque.png", png_bytes, "image/png")},
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]

    preview_res = client.get(f"/api/applications/{app_id}/documents/{doc_id}/preview?token={token}")
    assert preview_res.status_code == 200
    assert preview_res.headers["content-type"].startswith("image/png")
    assert "inline" in preview_res.headers.get("content-disposition", "")


def test_preview_error_handling_clean_response(db_session: Session, client: TestClient):
    """Requirement 7: Preview for missing or unauthorized document returns clean error without crashing."""
    ctx = setup_test_vendor(db_session)
    app_id = ctx["app"].id
    token = ctx["token"]

    # Nonexistent document ID
    res1 = client.get(f"/api/applications/{app_id}/documents/nonexistent-id/preview?token={token}")
    assert res1.status_code == 404
    assert "not found" in res1.json()["detail"].lower()

    # Invalid token
    res2 = client.get(f"/api/applications/{app_id}/documents/any-id/preview?token=invalid.jwt.token")
    assert res2.status_code == 401


# ==============================================================================
# 9, 10 & 11. GST Registration Logic & Submission Gating
# ==============================================================================

def test_non_gst_registered_vendor_onboarding(db_session: Session, client: TestClient):
    """Requirement 10: Vendor with is_gst_registered=False can complete onboarding without GSTIN or GST certificate."""
    ctx = setup_test_vendor(db_session)
    app_id = ctx["app"].id
    token = ctx["token"]

    # Populate details with is_gst_registered = False and gstin = None
    r_patch = client.patch(
        f"/api/applications/{app_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "legal_name": "Ramesh Hardware Store",
            "trade_name": "Ramesh Hardware",
            "constitution": "PROPRIETORSHIP",
            "registered_address": "12 Market Street",
            "city": "Jaipur",
            "state": "Rajasthan",
            "pincode": "302001",
            "pan": "ABCDE1234F",
            "is_gst_registered": False,
            "gstin": None,
            "is_udyam_registered": False,
            "contact_name": "Ramesh Kumar",
            "contact_email": "ramesh@example.com",
            "contact_mobile": "+91 98765 43210",
            "bank_account_holder_name": "Ramesh Kumar",
            "bank_account_number": "123456789012",
            "bank_ifsc": "SBIN0001234",
            "declaration_accurate_info": True,
            "declaration_authorised_rep": True,
            "declaration_verification_consent": True,
            "categories": ["goods_supplier"],
        },
    )
    assert r_patch.status_code == 200
    app_data = r_patch.json()
    assert app_data["is_gst_registered"] is False
    assert app_data["gstin"] is None

    # Verify checklist: GST certificate must NOT be required
    r_check = client.get(
        f"/api/applications/{app_id}/checklist",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_check.status_code == 200
    checklist = r_check.json()
    gst_item = next((item for item in checklist if item["document_type"] == "GST_CERTIFICATE"), None)
    if gst_item:
        assert gst_item["is_required"] is False

    # Upload only the mandatory documents for proprietorship (PAN, Constitution, Bank)
    pdf_bytes = b"%PDF-1.4\nTest dummy doc\n%%EOF"
    client.post(
        f"/api/applications/{app_id}/documents/PAN_PROOF/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("pan.pdf", pdf_bytes, "application/pdf")},
    )
    client.post(
        f"/api/applications/{app_id}/documents/CONSTITUTION_PROOF/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("trade_licence.pdf", pdf_bytes, "application/pdf")},
    )
    client.post(
        f"/api/applications/{app_id}/documents/BANK_PROOF/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cheque.pdf", pdf_bytes, "application/pdf")},
    )

    # Submitting must succeed without GSTIN and without GST certificate!
    r_sub = client.post(
        f"/api/applications/{app_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_sub.status_code == 200
    sub_data = r_sub.json()
    assert sub_data["success"] is True
    assert sub_data["status"] == "SUBMITTED"


def test_gst_registered_vendor_enforces_gstin_and_document(db_session: Session, client: TestClient):
    """Requirement 11: Vendor with is_gst_registered=True cannot submit without GSTIN and GST certificate."""
    ctx = setup_test_vendor(db_session)
    app_id = ctx["app"].id
    token = ctx["token"]

    # Set is_gst_registered = True but no GSTIN
    client.patch(
        f"/api/applications/{app_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "legal_name": "GST Registered Supplier",
            "constitution": "PROPRIETORSHIP",
            "registered_address": "12 Market Street",
            "city": "Jaipur",
            "state": "Rajasthan",
            "pincode": "302001",
            "pan": "ABCDE1234F",
            "is_gst_registered": True,
            "gstin": None,
            "contact_name": "Rajesh",
            "contact_email": "rajesh@example.com",
            "contact_mobile": "+91 98765 43210",
            "bank_account_holder_name": "Rajesh",
            "bank_account_number": "123456789012",
            "bank_ifsc": "SBIN0001234",
            "declaration_accurate_info": True,
            "declaration_authorised_rep": True,
            "declaration_verification_consent": True,
            "categories": ["goods_supplier"],
        },
    )

    # Attempt submit - must fail due to missing GSTIN
    r_sub = client.post(
        f"/api/applications/{app_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_sub.status_code == 400
    errs = r_sub.json()["detail"]["errors"]
    assert any("GSTIN is required when registered for GST" in e for e in errs)


# ==============================================================================
# 12 & 13. Exception Isolation & Submitted Response Semantics
# ==============================================================================

def test_exceptions_scoped_strictly_to_vendor_application(db_session: Session, client: TestClient):
    """Requirement 12: Exceptions from other applications are not visible in vendor dashboard."""
    # Vendor A
    ctx_a = setup_test_vendor(db_session, org_name="Org A", email_prefix="vendora")
    app_a = ctx_a["app"]
    token_a = ctx_a["token"]

    # Vendor B
    ctx_b = setup_test_vendor(db_session, org_name="Org B", email_prefix="vendorb")
    app_b = ctx_b["app"]

    # Create an exception on Application B
    exc_b = OnboardingException(
        organisation_id=ctx_b["org"].id,
        application_id=app_b.id,
        vendor_id=app_b.vendor_id,
        reference_number=f"EXC-{secrets.token_hex(4).upper()}",
        category=ExceptionCategoryEnum.PAN_MISMATCH.value,
        severity=ExceptionSeverityEnum.HIGH.value,
        status=ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
        related_field_name="pan",
        title="PAN Mismatch for Vendor B",
        description="Vendor B PAN does not match document",
    )
    db_session.add(exc_b)
    db_session.commit()

    # Vendor A requests their exceptions
    res = client.get(
        f"/api/exceptions?application_id={app_a.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 200
    exc_list = res.json()
    # Vendor A must not see Vendor B's exception
    assert not any(e["id"] == exc_b.id for e in exc_list)


def test_submitted_exception_responses_status_semantics(db_session: Session, client: TestClient):
    """Requirement 13: Submitted exception responses are distinguished by status."""
    ctx = setup_test_vendor(db_session)
    app = ctx["app"]
    token = ctx["token"]

    # Create an exception in RESPONSE_SUBMITTED status
    exc = OnboardingException(
        organisation_id=ctx["org"].id,
        application_id=app.id,
        vendor_id=app.vendor_id,
        reference_number=f"EXC-{secrets.token_hex(4).upper()}",
        category=ExceptionCategoryEnum.LEGAL_NAME_MISMATCH.value,
        severity=ExceptionSeverityEnum.HIGH.value,
        status=ExceptionStatusEnum.RESPONSE_SUBMITTED.value,
        related_field_name="trade_name",
        title="Trade Name Clarification",
        description="Please explain trade name difference",
        vendor_action_instruction="Please provide updated trade license",
    )
    db_session.add(exc)
    db_session.commit()

    res = client.get(
        f"/api/exceptions?application_id={app.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    # Status is RESPONSE_SUBMITTED, not ACTION_REQUIRED_FROM_VENDOR
    assert items[0]["status"] == "RESPONSE_SUBMITTED"
    assert items[0]["vendor_action_instruction"] == "Please provide updated trade license"


# ==============================================================================
# 14. Revalidation Preserves Run History
# ==============================================================================

def test_revalidation_updates_findings_and_run_history(db_session: Session, client: TestClient):
    """Requirement 14: Revalidation creates a new ValidationRun entry and preserves historical records."""
    ctx = setup_test_vendor(db_session)
    app = ctx["app"]

    service = ValidationOrchestrator(db_session)
    # Run 1
    run1 = service.run_full_validation(application_id=app.id)
    db_session.commit()

    # Run 2
    run2 = service.run_full_validation(application_id=app.id)
    db_session.commit()

    runs = db_session.query(ValidationRun).filter(ValidationRun.application_id == app.id).all()
    assert len(runs) >= 2
    assert run1.id != run2.id


# ==============================================================================
# 15. Mismatched Documents Semantics
# ==============================================================================

def test_mismatched_documents_status_semantics(db_session: Session, client: TestClient):
    """Requirement 15: Document checklist reflects current document and version status."""
    ctx = setup_test_vendor(db_session)
    app = ctx["app"]
    token = ctx["token"]

    # Upload document
    pdf_bytes = b"%PDF-1.4\nTest Document\n%%EOF"
    upload_res = client.post(
        f"/api/applications/{app.id}/documents/PAN_CARD/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("pan.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_res.status_code == 200
    data = upload_res.json()
    assert data["status"] == "UPLOADED"
    assert "current_version" in data
    assert data["current_version"]["original_filename"] == "pan.pdf"


# ==============================================================================
# 16. Organisation Isolation
# ==============================================================================

def test_organization_isolation_security(db_session: Session, client: TestClient):
    """Requirement 16: Vendor cannot access applications or documents belonging to another organisation."""
    ctx_a = setup_test_vendor(db_session, org_name="Org Alpha", email_prefix="user_alpha")
    ctx_b = setup_test_vendor(db_session, org_name="Org Beta", email_prefix="user_beta")

    token_a = ctx_a["token"]
    app_b_id = ctx_b["app"].id

    # Vendor A attempts to read Application B
    res_app = client.get(
        f"/api/applications/{app_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_app.status_code in [403, 404]

    # Vendor A attempts to submit Application B
    res_sub = client.post(
        f"/api/applications/{app_b_id}/submit",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_sub.status_code in [403, 404]


def test_submission_prevent_duplicate_double_submit(db_session: Session, client: TestClient):
    """Test duplicate submission prevention."""
    ctx = setup_test_vendor(db_session)
    app = ctx["app"]
    token = ctx["token"]

    app.status = ApplicationStatusEnum.SUBMITTED.value
    db_session.commit()

    res = client.post(
        f"/api/applications/{app.id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "already been submitted" in res.json()["detail"].lower()


def test_masked_account_number_patch_protection(db_session: Session, client: TestClient):
    """Test that submitting masked bullets does not corrupt real account number."""
    ctx = setup_test_vendor(db_session)
    app = ctx["app"]
    token = ctx["token"]

    # Save real account number
    client.patch(
        f"/api/applications/{app.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"bank_account_number": "98765432101234"},
    )
    db_session.refresh(app)
    assert app.bank_account_number == "98765432101234"

    # Send masked bullet string
    client.patch(
        f"/api/applications/{app.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"bank_account_number": "••••••••1234", "bank_name": "Axis Bank"},
    )
    db_session.refresh(app)
    # Must preserve the real stored account number!
    assert app.bank_account_number == "98765432101234"
    assert app.bank_name == "Axis Bank"


def test_cin_llpin_mandatory_for_corporate_entities(db_session: Session, client: TestClient):
    """Test that Private Limited company requires CIN/LLPIN."""
    ctx = setup_test_vendor(db_session)
    app = ctx["app"]
    token = ctx["token"]

    client.patch(
        f"/api/applications/{app.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "legal_name": "Acme Technologies Pvt Ltd",
            "constitution": "PVT_LTD",
            "registered_address": "Cyber City Phase 2",
            "city": "Gurugram",
            "state": "Haryana",
            "pincode": "122002",
            "pan": "AAACA1234C",
            "is_gst_registered": False,
            "cin_llpin": None,  # Missing CIN
            "contact_name": "Rohan",
            "contact_email": "rohan@acme.com",
            "contact_mobile": "+91 99999 88888",
            "bank_account_holder_name": "Acme Technologies Pvt Ltd",
            "bank_account_number": "112233445566",
            "bank_ifsc": "ICIC0000001",
            "declaration_accurate_info": True,
            "declaration_authorised_rep": True,
            "declaration_verification_consent": True,
            "categories": ["goods_supplier"],
        },
    )

    res = client.post(
        f"/api/applications/{app.id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    errors = res.json()["detail"]["errors"]
    assert any("CIN/LLPIN is required for PVT LTD" in e for e in errors)

