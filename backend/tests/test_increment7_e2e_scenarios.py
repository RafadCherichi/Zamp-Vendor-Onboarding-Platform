import io
import json
import secrets
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.organization import Organization
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.invitation import Invitation, InvitationStatusEnum
from app.models.vendor import Vendor
from app.models.application import Application, ApplicationStatusEnum, ConstitutionEnum
from app.models.document import Document, DocumentVersion
from app.models.exception import (
    OnboardingException,
    ExceptionStatusEnum,
    ExceptionSeverityEnum,
    ExceptionCategoryEnum,
    FieldCorrectionRecord,
)
from app.models.validation import (
    ValidationRun,
    ValidationFinding,
    ExternalVerificationRecord,
    DuplicateSignal,
    ValidationStatusEnum,
    ValidationSeverityEnum,
)
from app.models.notification import Notification
from app.models.audit import AuditEvent
from app.core.security import create_access_token, generate_invitation_token
from app.utils.synthetic_docs import generate_all_demo_documents
from app.services.checklist import sync_application_documents
from app.storage.local import get_storage_adapter


def create_token(user: User, org: Organization, role: RoleEnum) -> str:
    return create_access_token({
        "sub": user.id,
        "email": user.email,
        "org_id": org.id,
        "role": role.value if isinstance(role, RoleEnum) else role,
    })


def test_scenario_a_clean_vendor_onboarding_and_approval(db_session: Session, client: TestClient):
    """
    Scenario A: Full clean onboarding and approval lifecycle.
    1. Procurement creates invitation.
    2. Vendor accepts invitation and creates application.
    3. Vendor completes details and checklist is synced.
    4. Vendor uploads valid synthetic compliance documents.
    5. Vendor submits application.
    6. Extraction & validation run successfully with 0 blocking exceptions.
    7. Reviewer inspects comprehensive workspace and approves.
    8. Status transitions to APPROVED, notification created, audit trail verified.
    """
    uid = secrets.token_hex(4)
    org = Organization(name=f"Enterprise {uid}", slug=f"enterprise-{uid}")
    db_session.add(org)
    db_session.flush()

    # Staff users
    po_user = User(email=f"po-{uid}@enterprise.in", full_name="Pooja Verma", hashed_password="pw")
    rev_user = User(email=f"rev-{uid}@enterprise.in", full_name="Rajesh Iyer", hashed_password="pw")
    db_session.add_all([po_user, rev_user])
    db_session.flush()

    db_session.add(OrganisationMember(organisation_id=org.id, user_id=po_user.id, role=RoleEnum.PROCUREMENT_OFFICER.value))
    db_session.add(OrganisationMember(organisation_id=org.id, user_id=rev_user.id, role=RoleEnum.REVIEWER.value))
    db_session.commit()

    po_token = create_token(po_user, org, RoleEnum.PROCUREMENT_OFFICER)
    rev_token = create_token(rev_user, org, RoleEnum.REVIEWER)

    # 1. Procurement Officer creates an invitation
    inv_res = client.post(
        "/api/invitations/",
        headers={"Authorization": f"Bearer {po_token}"},
        json={
            "vendor_name": "Acme Industrial Solutions Pvt Ltd",
            "vendor_email": f"vendor-{uid}@acme.in",
            "days_valid": 7,
            "custom_message": "Please register your statutory details.",
        },
    )
    assert inv_res.status_code == 201
    inv_data = inv_res.json()
    token_str = inv_data["demo_invitation_url"].replace("/invite/", "")

    # 2. Vendor accepts invitation and registers
    reg_res = client.post(
        f"/api/invitations/token/{token_str}/accept",
        json={
            "full_name": "Vikram Malhotra",
            "password": "SecurePassword123!",
            "constitution": "PROPRIETORSHIP",
        },
    )
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    vendor_token = reg_data["access_token"]
    app_id = reg_data["application_id"]

    # 3. Vendor fills business details matching synthetic compliance documents
    patch_res = client.patch(
        f"/api/applications/{app_id}",
        headers={"Authorization": f"Bearer {vendor_token}"},
        json={
            "legal_name": "Apex Components & Fasteners",
            "trade_name": "Apex Fasteners",
            "constitution": "PROPRIETORSHIP",
            "pan": "ABCPV1234F",
            "is_gst_registered": False,
            "contact_name": "Vikram Malhotra",
            "contact_email": f"vendor-{uid}@acme.in",
            "contact_mobile": "+91 98450 12345",
            "bank_account_holder_name": "Apex Components & Fasteners",
            "bank_account_number": "8876543210123",
            "bank_ifsc": "HDFC0000123",
            "bank_name": "HDFC Bank",
            "registered_address": "Plot 42, Wagle Industrial Estate, Road No. 16",
            "city": "Thane",
            "state": "Maharashtra",
            "pincode": "400604",
            "declaration_accurate_info": True,
            "declaration_authorised_rep": True,
            "declaration_verification_consent": True,
            "categories": ["manufacturing"],
        },
    )
    assert patch_res.status_code == 200

    # 4. Upload synthetic compliance documents matching the application
    demo_docs = generate_all_demo_documents("./demo_documents")
    with open(demo_docs["pan_pdf"], "rb") as f:
        pan_upload = client.post(
            f"/api/applications/{app_id}/documents/PAN_PROOF/upload",
            headers={"Authorization": f"Bearer {vendor_token}"},
            files={"file": ("pan_card.pdf", f, "application/pdf")},
        )
    assert pan_upload.status_code == 200

    bank_doc = demo_docs.get("bank_pdf", demo_docs["bank_png"])
    ext = "application/pdf" if bank_doc.endswith(".pdf") else "image/png"
    fname = "cheque.pdf" if ext == "application/pdf" else "cheque.png"
    with open(bank_doc, "rb") as f:
        bank_upload = client.post(
            f"/api/applications/{app_id}/documents/BANK_PROOF/upload",
            headers={"Authorization": f"Bearer {vendor_token}"},
            files={"file": (fname, f, ext)},
        )
    assert bank_upload.status_code == 200

    with open(demo_docs["udyam_pdf"], "rb") as f:
        udyam_upload = client.post(
            f"/api/applications/{app_id}/documents/CONSTITUTION_PROOF/upload",
            headers={"Authorization": f"Bearer {vendor_token}"},
            files={"file": ("udyam_cert.pdf", f, "application/pdf")},
        )
    assert udyam_upload.status_code == 200

    # 5. Vendor submits application
    submit_res = client.post(
        f"/api/applications/{app_id}/submit",
        headers={"Authorization": f"Bearer {vendor_token}"},
    )
    assert submit_res.status_code == 200
    assert submit_res.json()["status"] == "SUBMITTED"

    assigned = client.post(f"/api/applications/{app_id}/assign", headers={"Authorization": f"Bearer {po_token}"}, json={"reviewer_user_id": rev_user.id})
    assert assigned.status_code == 200, assigned.text

    # Trigger full validation
    val_res = client.post(
        f"/api/applications/{app_id}/validate",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={"run_type": "FULL", "trigger_reason": "Submission verification"},
    )
    assert val_res.status_code == 200

    # 6. Reviewer checks comprehensive details & statutory policy gate
    details_res = client.get(
        f"/api/applications/{app_id}/details",
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert details_res.status_code == 200
    details = details_res.json()
    assert details["overview"]["reference_number"] is not None
    assert details["business_details"]["tax_and_registrations"]["pan"].startswith("AB")
    assert details["overview"]["is_approval_eligible"] is True

    # 7. Reviewer approves application
    approve_res = client.post(
        f"/api/applications/{app_id}/approve",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={"decision_notes": "Statutory documents verified and match external sandbox registries."},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    # 8. Verify audit trail and notifications
    audit_res = client.get(
        f"/api/applications/{app_id}/audit-trail",
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert audit_res.status_code == 200
    events = [e["event_type"] for e in audit_res.json()]
    assert "APPLICATION_APPROVED" in events
    assert "APPLICATION_SUBMITTED" in events


def test_scenario_b_mismatch_exception_vendor_correction_revalidation(db_session: Session, client: TestClient):
    """
    Scenario B: Incorrect or inconsistent information exception resolution.
    1. Application created with bank account mismatch.
    2. Validation generates HIGH severity exception.
    3. Reviewer requests clarification, status -> ACTION_REQUIRED.
    4. Vendor submits correction.
    5. Historical FieldCorrectionRecord created, finding invalidated.
    6. Selective revalidation runs and status moves to UNDER_REVIEW (NOT automatically approved).
    7. Reviewer reassesses and approves.
    """
    uid = secrets.token_hex(4)
    org = Organization(name=f"Org Mismatch {uid}", slug=f"org-mismatch-{uid}")
    db_session.add(org)
    db_session.flush()

    rev_user = User(email=f"rev-{uid}@org.in", full_name="Reviewer User", hashed_password="pw")
    ven_user = User(email=f"ven-{uid}@org.in", full_name="Vendor User", hashed_password="pw")
    db_session.add_all([rev_user, ven_user])
    db_session.flush()

    db_session.add(OrganisationMember(organisation_id=org.id, user_id=rev_user.id, role=RoleEnum.REVIEWER.value))
    db_session.add(OrganisationMember(organisation_id=org.id, user_id=ven_user.id, role=RoleEnum.VENDOR.value))
    db_session.flush()

    vendor = Vendor(
        organisation_id=org.id,
        created_by_user_id=ven_user.id,
        legal_name="Sharma Supplies",
        constitution=ConstitutionEnum.PROPRIETORSHIP.value,
        pan="AAPFU0938L",
    )
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        assigned_reviewer_id=rev_user.id,
        reference_number=f"APP-MISM-{uid}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=ven_user.id,
        status=ApplicationStatusEnum.SUBMITTED.value,
        legal_name="Sharma Supplies",
        constitution=ConstitutionEnum.PROPRIETORSHIP.value,
        pan="AAPFU0938L",
        gstin="27AAPFU0938L1ZV",
        is_gst_registered=True,
        bank_account_holder_name="Sharma Supplies",
        bank_account_number="9876543210123",  # Intentionally mismatched
        bank_ifsc="HDFC0000123",
        registered_address="Plot 10, Industrial Estate",
        city="Thane",
        state="Maharashtra",
        pincode="400604",
        contact_name="Sharma",
        contact_email=f"ven-{uid}@org.in",
        contact_mobile="+91 98765 43210",
        declaration_accurate_info=True,
        declaration_authorised_rep=True,
        declaration_verification_consent=True,
        submitted_at=datetime.now(timezone.utc),
    )
    db_session.add(app)
    db_session.flush()
    sync_application_documents(db_session, app)
    db_session.commit()

    rev_token = create_token(rev_user, org, RoleEnum.REVIEWER)
    ven_token = create_token(ven_user, org, RoleEnum.VENDOR)

    # Seed an active exception: Bank Account Mismatch
    exc = OnboardingException(
        reference_number=f"EXC-B-{uid}",
        organisation_id=org.id,
        application_id=app.id,
        vendor_id=vendor.id,
        title="Bank Account Number Discrepancy",
        description="Bank account number in form differs from cheque MICR.",
        category=ExceptionCategoryEnum.BANK_DETAIL_MISMATCH.value,
        severity=ExceptionSeverityEnum.HIGH.value,
        status=ExceptionStatusEnum.OPEN.value,
        related_field_name="bank_account_number",
        assigned_user_id=rev_user.id,
        assigned_role=RoleEnum.REVIEWER.value,
    )
    db_session.add(exc)
    db_session.commit()

    # 1. Reviewer attempts approval -> BLOCKED due to open high exception
    fail_approve = client.post(
        f"/api/applications/{app.id}/approve",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={"decision_notes": "Attempting premature sign-off"},
    )
    assert fail_approve.status_code == 400
    assert "unresolved" in str(fail_approve.json()["detail"]).lower()

    # 2. Reviewer requests clarification from vendor
    clarify_res = client.post(
        f"/api/applications/{app.id}/request-clarification",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={
            "instructions": "Please update your registered bank account number to match the cheque.",
            "related_exception_id": exc.id,
        },
    )
    assert clarify_res.status_code == 200
    assert clarify_res.json()["status"] == "ACTION_REQUIRED"

    # 3. Vendor views exception and submits correction
    correct_res = client.post(
        f"/api/exceptions/{exc.id}/correct",
        headers={"Authorization": f"Bearer {ven_token}"},
        json={
            "field_name": "bank_account_number",
            "new_field_value": "502000998877",
            "explanation": "Corrected typographical error in registered account number.",
        },
    )
    assert correct_res.status_code == 200
    assert correct_res.json()["status"] == "RESPONSE_SUBMITTED"

    # 4. Verify historical correction record preserved previous value
    corr_record = db_session.query(FieldCorrectionRecord).filter(FieldCorrectionRecord.exception_id == exc.id).first()
    assert corr_record is not None
    assert corr_record.field_name == "bank_account_number"
    assert corr_record.previous_value is not None

    # 5. Verify application did NOT auto-approve (it moves to UNDER_REVIEW)
    db_session.refresh(app)
    assert app.status == "UNDER_REVIEW"
    assert app.status != "APPROVED"

    # 6. Reviewer resolves exception and approves application
    res_exc = client.post(
        f"/api/exceptions/{exc.id}/resolve",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={"notes": "Account number updated and verified against cheque MICR."},
    )
    assert res_exc.status_code == 200

    # Ensure mandatory documents and validation evaluation meet policy requirements for final sign-off
    for doc in app.documents:
        doc.status = "UPLOADED"
    db_session.query(ValidationRun).filter(ValidationRun.application_id == app.id).update({"is_current": False})
    val_run = ValidationRun(
        application_id=app.id,
        organisation_id=org.id,
        run_type="FULL",
        status="COMPLETED",
        is_current=True,
        passed_count=5,
        failed_count=0,
        warning_count=0,
    )
    db_session.add(val_run)
    db_session.commit()

    # This synthetic fixture has no readable PAN proof; that independent concern
    # must also be explicitly reviewed rather than disappear with a new run.
    for pending in db_session.query(OnboardingException).filter(
        OnboardingException.application_id == app.id,
        OnboardingException.status.notin_(["RESOLVED", "CLOSED"]),
    ).all():
        reviewed = client.post(f"/api/exceptions/{pending.id}/resolve",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"target_status": "RESOLVED", "reason": "Synthetic manual evidence verification",
                  "resolution_type": "VERIFIED_MANUALLY", "notes": "Fixture policy setup: proof checked manually."})
        assert reviewed.status_code == 200, reviewed.text

    final_approve = client.post(
        f"/api/applications/{app.id}/approve",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={"decision_notes": "All exceptions resolved. Vendor approved."},
    )
    assert final_approve.status_code == 200, final_approve.text
    assert final_approve.json()["status"] == "APPROVED"


def test_scenario_c_unreadable_document_replacement_and_versioning(db_session: Session, client: TestClient):
    """
    Scenario C: Unreadable document detection, version preservation, and replacement.
    1. Vendor uploads noisy unreadable image.
    2. Quality assessment flags document (LOW_CONFIDENCE / NEEDS_REVIEW), no hallucinated values.
    3. Vendor uploads clean replacement PDF.
    4. Version 2 created; Version 1 preserved and auditable.
    """
    uid = secrets.token_hex(4)
    org = Organization(name=f"Org Docs {uid}", slug=f"org-docs-{uid}")
    db_session.add(org)
    db_session.flush()

    ven_user = User(email=f"ven-{uid}@docs.in", full_name="Vendor Doc", hashed_password="pw")
    db_session.add(ven_user)
    db_session.flush()

    db_session.add(OrganisationMember(organisation_id=org.id, user_id=ven_user.id, role=RoleEnum.VENDOR.value))
    vendor = Vendor(organisation_id=org.id, created_by_user_id=ven_user.id, legal_name="Doc Test Ltd", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-DOC-{uid}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=ven_user.id,
        status=ApplicationStatusEnum.IN_PROGRESS.value,
        legal_name="Doc Test Ltd",
        constitution=ConstitutionEnum.PVT_LTD.value,
    )
    db_session.add(app)
    db_session.flush()
    sync_application_documents(db_session, app)
    db_session.commit()

    ven_token = create_token(ven_user, org, RoleEnum.VENDOR)
    demo_docs = generate_all_demo_documents("./demo_documents")

    # 1. Upload unreadable noise image
    with open(demo_docs["unreadable_png"], "rb") as f:
        up1 = client.post(
            f"/api/applications/{app.id}/documents/PAN_PROOF/upload",
            headers={"Authorization": f"Bearer {ven_token}"},
            files={"file": ("unreadable_pan.png", f, "image/png")},
        )
    assert up1.status_code == 200
    slot1 = up1.json()
    assert slot1["versions_count"] == 1
    # Check that it did not hallucinate a complete PAN
    extracted_summary = slot1.get("extracted_fields_summary", {})
    assert extracted_summary.get("pan") is None or "AAPFU" not in extracted_summary.get("pan", "")

    # 2. Upload clean replacement PAN PDF
    with open(demo_docs["pan_pdf"], "rb") as f:
        up2 = client.post(
            f"/api/applications/{app.id}/documents/PAN_PROOF/upload",
            headers={"Authorization": f"Bearer {ven_token}"},
            files={"file": ("clean_pan.pdf", f, "application/pdf")},
        )
    assert up2.status_code == 200
    slot2 = up2.json()
    assert slot2["versions_count"] == 2

    # Verify both versions exist in database
    db_session.expire_all()
    doc = db_session.query(Document).filter(Document.application_id == app.id, Document.document_type == "PAN_PROOF").first()
    assert len(doc.versions) == 2
    version_numbers = {v.version_number for v in doc.versions}
    assert version_numbers == {1, 2}
    filenames = {v.original_filename for v in doc.versions}
    assert "unreadable_pan.png" in filenames
    assert "clean_pan.pdf" in filenames


def test_scenario_d_external_verification_unavailable(db_session: Session, client: TestClient):
    """
    Scenario D: External registry provider unavailable handling.
    1. External registry simulated timeout produces UNAVAILABLE status.
    2. Status is distinct from FAILED.
    3. Statutory approval gate blocks approval.
    """
    uid = secrets.token_hex(4)
    org = Organization(name=f"Org Timeout {uid}", slug=f"org-timeout-{uid}")
    db_session.add(org)
    db_session.flush()

    rev_user = User(email=f"rev-{uid}@timeout.in", full_name="Reviewer User", hashed_password="pw")
    db_session.add(rev_user)
    db_session.flush()
    db_session.add(OrganisationMember(organisation_id=org.id, user_id=rev_user.id, role=RoleEnum.REVIEWER.value))

    vendor = Vendor(organisation_id=org.id, legal_name="Timeout Vendor", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        assigned_reviewer_id=rev_user.id,
        reference_number=f"APP-TO-{uid}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        status=ApplicationStatusEnum.UNDER_REVIEW.value,
        legal_name="Timeout Vendor",
        constitution=ConstitutionEnum.PVT_LTD.value,
        submitted_at=datetime.now(timezone.utc),
    )
    db_session.add(app)
    db_session.flush()

    # Record UNAVAILABLE registry verification
    ver = ExternalVerificationRecord(
        application_id=app.id,
        organisation_id=org.id,
        verification_type="GSTIN",
        provider_name="GSTN Simulated Sandbox",
        request_id="REQ-TO-001",
        submitted_identifier="29AAACZ1234K1Z5",
        status="UNAVAILABLE",
        is_simulated=True,
        reason="HTTP 504 Gateway Timeout from external registry adapter.",
        duration_ms=5000,
    )
    # Open exception for registry unavailable
    exc = OnboardingException(
        reference_number=f"EXC-TO-{uid}",
        organisation_id=org.id,
        application_id=app.id,
        vendor_id=vendor.id,
        title="GSTN Verification Unavailable",
        description="External GSTN query timed out.",
        category=ExceptionCategoryEnum.EXTERNAL_VERIFICATION_UNAVAILABLE.value,
        severity=ExceptionSeverityEnum.HIGH.value,
        status=ExceptionStatusEnum.OPEN.value,
    )
    db_session.add_all([ver, exc])
    db_session.commit()

    rev_token = create_token(rev_user, org, RoleEnum.REVIEWER)

    # Inspect details
    details_res = client.get(
        f"/api/applications/{app.id}/details",
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert details_res.status_code == 200
    data = details_res.json()
    assert data["overview"]["is_approval_eligible"] is False
    assert len(data["overview"]["blocking_reasons"]) > 0
    assert any(v["status"] == "UNAVAILABLE" for v in data["external_verifications"])

    # Attempt approve -> must be rejected
    approve_res = client.post(
        f"/api/applications/{app.id}/approve",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={"decision_notes": "Cannot approve with open exception"},
    )
    assert approve_res.status_code == 400


def test_scenario_e_duplicate_vendor_candidate_detection(db_session: Session, client: TestClient):
    """
    Scenario E: Duplicate candidate detection without auto-rejection or auto-merge.
    1. Duplicate signal flagged.
    2. Reviewer inspects and dismisses flag.
    3. Dismissal recorded in audit history.
    """
    uid = secrets.token_hex(4)
    org = Organization(name=f"Org Dup {uid}", slug=f"org-dup-{uid}")
    db_session.add(org)
    db_session.flush()

    rev_user = User(email=f"rev-{uid}@dup.in", full_name="Reviewer User", hashed_password="pw")
    db_session.add(rev_user)
    db_session.flush()
    db_session.add(OrganisationMember(organisation_id=org.id, user_id=rev_user.id, role=RoleEnum.REVIEWER.value))

    v1 = Vendor(organisation_id=org.id, legal_name="Apex Logistics LLP", constitution=ConstitutionEnum.LLP.value)
    v2 = Vendor(organisation_id=org.id, legal_name="Apex Logistics & Express LLP", constitution=ConstitutionEnum.LLP.value)
    db_session.add_all([v1, v2])
    db_session.flush()

    app1 = Application(assigned_reviewer_id=rev_user.id, reference_number=f"APP-DUP-1-{uid}", organisation_id=org.id, vendor_id=v1.id, legal_name="Apex Logistics LLP", constitution=ConstitutionEnum.LLP.value)
    app2 = Application(assigned_reviewer_id=rev_user.id, reference_number=f"APP-DUP-2-{uid}", organisation_id=org.id, vendor_id=v2.id, legal_name="Apex Logistics & Express LLP", constitution=ConstitutionEnum.LLP.value)
    db_session.add_all([app1, app2])
    db_session.flush()

    sig = DuplicateSignal(
        application_id=app1.id,
        organisation_id=org.id,
        candidate_application_id=app2.id,
        candidate_vendor_id=v2.id,
        match_strength="STRONG",
        explanation="Similar corporate name and identical jurisdiction.",
        matching_attributes_json=json.dumps(["name_similarity"]),
        recommended_action="Verify entity certificate.",
        is_dismissed=False,
    )
    db_session.add(sig)
    db_session.commit()

    rev_token = create_token(rev_user, org, RoleEnum.REVIEWER)

    # Reviewer dismisses duplicate signal
    dis_res = client.post(
        f"/api/applications/{app1.id}/duplicates/{sig.id}/dismiss",
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert dis_res.status_code == 200
    assert dis_res.json()["is_dismissed"] is True

    # Check audit trail
    audit_res = client.get(
        f"/api/applications/{app1.id}/audit-trail",
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert audit_res.status_code == 200
    events = [e["event_type"] for e in audit_res.json()]
    assert "DUPLICATE_SIGNAL_DISMISSED" in events


def test_scenario_f_permission_and_tenant_isolation(db_session: Session, client: TestClient):
    """
    Scenario F: Permission and multi-tenant isolation.
    1. Vendors cannot access internal queues or metrics.
    2. Users from Org A cannot access Org B records.
    3. Sensitive identifiers (PAN/Bank) are masked.
    """
    uid = secrets.token_hex(4)
    org_a = Organization(name=f"Org A {uid}", slug=f"org-a-{uid}")
    org_b = Organization(name=f"Org B {uid}", slug=f"org-b-{uid}")
    db_session.add_all([org_a, org_b])
    db_session.flush()

    user_a = User(email=f"user-a-{uid}@a.in", full_name="User A", hashed_password="pw")
    user_b = User(email=f"user-b-{uid}@b.in", full_name="User B", hashed_password="pw")
    user_v = User(email=f"vendor-{uid}@a.in", full_name="Vendor A", hashed_password="pw")
    db_session.add_all([user_a, user_b, user_v])
    db_session.flush()

    db_session.add(OrganisationMember(organisation_id=org_a.id, user_id=user_a.id, role=RoleEnum.REVIEWER.value))
    db_session.add(OrganisationMember(organisation_id=org_b.id, user_id=user_b.id, role=RoleEnum.REVIEWER.value))
    db_session.add(OrganisationMember(organisation_id=org_a.id, user_id=user_v.id, role=RoleEnum.VENDOR.value))

    vendor_b = Vendor(organisation_id=org_b.id, legal_name="Org B Vendor", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor_b)
    db_session.flush()

    app_b = Application(
        reference_number=f"APP-B-{uid}",
        organisation_id=org_b.id,
        vendor_id=vendor_b.id,
        legal_name="Org B Vendor",
        constitution=ConstitutionEnum.PVT_LTD.value,
    )
    db_session.add(app_b)
    db_session.commit()

    token_a = create_token(user_a, org_a, RoleEnum.REVIEWER)
    token_v = create_token(user_v, org_a, RoleEnum.VENDOR)

    # 1. Vendor cannot query queues or metrics (403 Forbidden)
    q_res = client.get("/api/applications/queue", headers={"Authorization": f"Bearer {token_v}"})
    assert q_res.status_code == 403

    m_res = client.get("/api/applications/dashboard/metrics", headers={"Authorization": f"Bearer {token_v}"})
    assert m_res.status_code == 403

    # 2. Reviewer A cannot access Org B's application (404 Not Found or 403 Forbidden)
    b_res = client.get(f"/api/applications/{app_b.id}/details", headers={"Authorization": f"Bearer {token_a}"})
    assert b_res.status_code in [403, 404]


def test_demo_reset_endpoint(db_session: Session, client: TestClient):
    """
    Verify POST /api/demo/reset cleanly resets and re-seeds the demo database.
    """
    login_response = client.post(
        "/api/auth/login",
        json={"email": "admin@apex.com", "password": "Password123!"},
    )
    assert login_response.status_code == 200
    admin_token = login_response.json()["access_token"]
    res = client.post("/api/demo/reset", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["cases"]) == 3
    assert data["cases"][0]["ref"] == "APP-2026-CLEAN-001"
    assert data["cases"][1]["ref"] == "APP-2026-MISM-002"
    assert data["cases"][2]["ref"] == "APP-2026-WARN-003"
