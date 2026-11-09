import pytest
import json
import secrets
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.models.user import User
from app.models.organization import Organization
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.vendor import Vendor
from app.models.application import Application, ApplicationStatusEnum, ConstitutionEnum
from app.models.document import Document, DocumentVersion, DocumentTypeEnum
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
    ValidationLayerEnum,
    ExternalVerificationRecord,
)
from app.models.audit import AuditEvent
from app.core.security import create_access_token
from app.services.review.decision_service import ReviewerDecisionService
from app.services.review.queue_service import QueueAndDashboardService


@pytest.fixture
def client():
    return TestClient(fastapi_app)


def test_dashboard_metrics_against_persisted_data(db_session: Session, client: TestClient):
    """Verify procurement dashboard metrics are derived strictly from persisted database records."""
    tok = secrets.token_hex(4)
    org = Organization(name=f"Metrics Org {tok}", slug=f"metrics-org-{tok}")
    db_session.add(org)
    db_session.flush()

    user_po = User(email=f"po-{tok}@org.com", full_name="PO User", hashed_password="pw")
    db_session.add(user_po)
    db_session.flush()
    db_session.add(OrganisationMember(organisation_id=org.id, user_id=user_po.id, role=RoleEnum.PROCUREMENT_OFFICER.value))

    # Create 3 applications: 1 SUBMITTED, 1 APPROVED, 1 ACTION_REQUIRED
    v1 = Vendor(organisation_id=org.id, legal_name="Vendor 1", constitution=ConstitutionEnum.PVT_LTD.value)
    v2 = Vendor(organisation_id=org.id, legal_name="Vendor 2", constitution=ConstitutionEnum.PROPRIETORSHIP.value)
    v3 = Vendor(organisation_id=org.id, legal_name="Vendor 3", constitution=ConstitutionEnum.LLP.value)
    db_session.add_all([v1, v2, v3])
    db_session.flush()

    app1 = Application(
        reference_number=f"APP-MET-1-{tok}",
        organisation_id=org.id,
        vendor_id=v1.id,
        legal_name="Vendor 1 Pvt Ltd",
        constitution=ConstitutionEnum.PVT_LTD.value,
        status=ApplicationStatusEnum.SUBMITTED.value,
        submitted_at=datetime.now(timezone.utc),
    )
    app2 = Application(
        reference_number=f"APP-MET-2-{tok}",
        organisation_id=org.id,
        vendor_id=v2.id,
        legal_name="Vendor 2 Enterprise",
        constitution=ConstitutionEnum.PROPRIETORSHIP.value,
        status=ApplicationStatusEnum.APPROVED.value,
        submitted_at=datetime.now(timezone.utc),
    )
    app3 = Application(
        reference_number=f"APP-MET-3-{tok}",
        organisation_id=org.id,
        vendor_id=v3.id,
        legal_name="Vendor 3 LLP",
        constitution=ConstitutionEnum.LLP.value,
        status=ApplicationStatusEnum.ACTION_REQUIRED.value,
        submitted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([app1, app2, app3])
    db_session.flush()

    # Create 1 critical open exception on app3
    exc = OnboardingException(
        reference_number=f"EXC-{tok}",
        organisation_id=org.id,
        application_id=app3.id,
        vendor_id=v3.id,
        category=ExceptionCategoryEnum.PAN_MISMATCH.value,
        title="PAN Mismatch",
        description="PAN does not match",
        severity=ExceptionSeverityEnum.CRITICAL.value,
        status=ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
        created_by_role="SYSTEM",
    )
    db_session.add(exc)
    db_session.commit()

    token = create_access_token(data={"sub": user_po.id})
    res = client.get(
        "/api/applications/dashboard/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_applications"] >= 3
    assert data["approved_count"] >= 1
    assert data["awaiting_vendor_count"] >= 1
    assert data["open_exceptions_count"] >= 1
    assert data["high_severity_exceptions_count"] >= 1
    # No exception is not enough: app1 has no completed validation run, so it
    # must stay out of the ready queue until the same approval gate can pass.
    assert data["ready_for_approval_count"] == 0


def test_queue_search_filter_and_pagination(db_session: Session, client: TestClient):
    """Verify application queue search, filter, and pagination capabilities."""
    tok = secrets.token_hex(4)
    org = Organization(name=f"Queue Org {tok}", slug=f"queue-org-{tok}")
    db_session.add(org)
    db_session.flush()

    reviewer = User(email=f"rev-{tok}@org.com", full_name="Reviewer One", hashed_password="pw")
    db_session.add(reviewer)
    db_session.flush()
    db_session.add(OrganisationMember(organisation_id=org.id, user_id=reviewer.id, role=RoleEnum.REVIEWER.value))

    # Add 4 applications with specific search keys
    names = ["Acme Engineering", "Beta Chemicals", "Acme Logistics", "Delta Power"]
    for i, name in enumerate(names):
        v = Vendor(organisation_id=org.id, legal_name=name, constitution=ConstitutionEnum.PVT_LTD.value)
        db_session.add(v)
        db_session.flush()
        app = Application(
            reference_number=f"APP-Q-{tok}-{i+1}",
            organisation_id=org.id,
            vendor_id=v.id,
            legal_name=name,
            constitution=ConstitutionEnum.PVT_LTD.value,
            status=ApplicationStatusEnum.SUBMITTED.value if i < 2 else ApplicationStatusEnum.UNDER_REVIEW.value,
            submitted_at=datetime.now(timezone.utc),
            assigned_reviewer_id=reviewer.id if i == 0 else None,
        )
        db_session.add(app)
    db_session.commit()

    token = create_access_token(data={"sub": reviewer.id})

    # 1. Search by "Acme" -> Should return 2
    res_search = client.get(
        "/api/applications/queue?search=Acme",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_search.status_code == 200
    items_search = res_search.json()["items"]
    assert len(items_search) == 2
    assert all("Acme" in it["legal_name"] for it in items_search)
    by_name = {item["legal_name"]: item for item in items_search}
    assert by_name["Acme Engineering"]["next_action"] == "Reviewer: assess the evidence"
    assert by_name["Acme Logistics"]["next_action"] == "Procurement: assign a reviewer"

    # 2. Filter by status "UNDER_REVIEW" -> Should return 2
    res_status = client.get(
        "/api/applications/queue?status=UNDER_REVIEW",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_status.status_code == 200
    items_status = res_status.json()["items"]
    assert len(items_status) == 2
    assert all(it["status"] == "UNDER_REVIEW" for it in items_status)

    # 3. Filter by assigned_reviewer_id -> Should return 1
    res_rev = client.get(
        f"/api/applications/queue?assigned_reviewer_id={reviewer.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_rev.status_code == 200
    items_rev = res_rev.json()["items"]
    assert len(items_rev) == 1
    assert items_rev[0]["assigned_reviewer_id"] == reviewer.id

    # 4. Pagination: page_size=2, page=1
    res_page = client.get(
        "/api/applications/queue?page=1&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_page.status_code == 200
    data_page = res_page.json()
    assert len(data_page["items"]) == 2
    assert data_page["total"] == 4
    assert data_page["total_pages"] == 2


def test_reviewer_assignment_and_cross_org_rejection(db_session: Session, client: TestClient):
    """Verify assignment updates reviewer and status, while cross-org assignment is forbidden."""
    tok = secrets.token_hex(4)
    org1 = Organization(name=f"Org A {tok}", slug=f"org-a-{tok}")
    org2 = Organization(name=f"Org B {tok}", slug=f"org-b-{tok}")
    db_session.add_all([org1, org2])
    db_session.flush()

    po_user = User(email=f"po-{tok}@a.com", full_name="PO A", hashed_password="pw")
    admin_user = User(email=f"admin-{tok}@a.com", full_name="Admin A", hashed_password="pw")
    rev_a = User(email=f"rev-a-{tok}@a.com", full_name="Reviewer A", hashed_password="pw")
    rev_b = User(email=f"rev-b-{tok}@b.com", full_name="Reviewer B", hashed_password="pw")
    db_session.add_all([po_user, admin_user, rev_a, rev_b])
    db_session.flush()

    db_session.add(OrganisationMember(organisation_id=org1.id, user_id=po_user.id, role=RoleEnum.PROCUREMENT_OFFICER.value))
    db_session.add(OrganisationMember(organisation_id=org1.id, user_id=admin_user.id, role=RoleEnum.ADMIN.value))
    db_session.add(OrganisationMember(organisation_id=org1.id, user_id=rev_a.id, role=RoleEnum.REVIEWER.value))
    db_session.add(OrganisationMember(organisation_id=org2.id, user_id=rev_b.id, role=RoleEnum.REVIEWER.value))

    vendor = Vendor(organisation_id=org1.id, legal_name="App Vendor", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-ASS-{tok}",
        organisation_id=org1.id,
        vendor_id=vendor.id,
        legal_name="App Vendor Ltd",
        constitution=ConstitutionEnum.PVT_LTD.value,
        status=ApplicationStatusEnum.SUBMITTED.value,
    )
    db_session.add(app)
    db_session.commit()

    po_token = create_access_token(data={"sub": po_user.id})

    # 1. Reassigning to user from DIFFERENT organisation (rev_b) MUST fail
    res_bad = client.post(
        f"/api/applications/{app.id}/assign",
        headers={"Authorization": f"Bearer {po_token}"},
        json={"reviewer_user_id": rev_b.id},
    )
    assert res_bad.status_code == 400
    assert "must belong to this organisation" in res_bad.json()["detail"]

    # 2. Assigning to legitimate internal reviewer (rev_a) succeeds
    res_ok = client.post(
        f"/api/applications/{app.id}/assign",
        headers={"Authorization": f"Bearer {po_token}"},
        json={"reviewer_user_id": rev_a.id},
    )
    assert res_ok.status_code == 200
    db_session.refresh(app)
    assert app.assigned_reviewer_id == rev_a.id
    assert app.status == ApplicationStatusEnum.UNDER_REVIEW.value

    # Reviewers cannot reassign work; administrators must record why they do.
    reviewer_token = create_access_token(data={"sub": rev_a.id})
    res_reviewer_assign = client.post(
        f"/api/applications/{app.id}/assign",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"reviewer_user_id": None},
    )
    assert res_reviewer_assign.status_code == 403

    admin_token = create_access_token(data={"sub": admin_user.id})
    res_admin_without_reason = client.post(
        f"/api/applications/{app.id}/assign",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reviewer_user_id": rev_a.id},
    )
    assert res_admin_without_reason.status_code == 400
    res_admin_with_reason = client.post(
        f"/api/applications/{app.id}/assign",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reviewer_user_id": rev_a.id, "reason": "Primary reviewer is covering the case this week."},
    )
    assert res_admin_with_reason.status_code == 200

    # Verify audit event logged
    audit = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.application_id == app.id, AuditEvent.event_type == "REVIEWER_ASSIGNED")
        .first()
    )
    assert audit is not None


def test_scenario_1_clean_application_approval(db_session: Session, client: TestClient):
    """
    Scenario 1: Clean application with complete documents, valid validation run,
    and no open exceptions. Reviewer inspects and approves successfully.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Clean Org {tok}", slug=f"clean-org-{tok}")
    db_session.add(org)
    db_session.flush()

    rev_user = User(email=f"clean-rev-{tok}@org.com", full_name="Clean Reviewer", hashed_password="pw")
    vendor_user = User(email=f"clean-v-{tok}@org.com", full_name="Clean Vendor User", hashed_password="pw")
    db_session.add_all([rev_user, vendor_user])
    db_session.flush()

    db_session.add(OrganisationMember(organisation_id=org.id, user_id=rev_user.id, role=RoleEnum.REVIEWER.value))
    db_session.add(OrganisationMember(organisation_id=org.id, user_id=vendor_user.id, role=RoleEnum.VENDOR.value))

    vendor = Vendor(organisation_id=org.id, legal_name="Clean Corp", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-CLEAN-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        created_by_user_id=vendor_user.id,
        legal_name="Clean Corp Private Limited",
        constitution=ConstitutionEnum.PVT_LTD.value,
        status=ApplicationStatusEnum.UNDER_REVIEW.value,
        submitted_at=datetime.now(timezone.utc),
        pan="AAACC1234A",
    )
    db_session.add(app)
    db_session.flush()

    # Add required documents
    doc = Document(
        application_id=app.id,
        organisation_id=org.id,
        document_type=DocumentTypeEnum.PAN_PROOF.value,
        title="PAN Card Proof",
        is_required=True,
        status="UPLOADED",
    )
    db_session.add(doc)
    db_session.flush()

    ver = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        storage_key=f"clean/{tok}/pan.pdf",
        original_filename="pan.pdf",
        file_size_bytes=1024,
        content_type="application/pdf",
        file_checksum=f"hash_{tok}",
    )
    db_session.add(ver)
    db_session.flush()
    doc.current_version_id = ver.id

    # Add valid completed validation run with no failures
    run = ValidationRun(
        application_id=app.id,
        organisation_id=org.id,
        run_type="FULL",
        status="COMPLETED",
        is_current=True,
        passed_count=5,
        failed_count=0,
    )
    db_session.add(run)
    db_session.commit()

    rev_token = create_access_token(data={"sub": rev_user.id})

    # Reviewer approves
    res_appr = client.post(
        f"/api/applications/{app.id}/approve",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={"notes": "All statutory proof verified. Approved for buyer vendor master."},
    )
    assert res_appr.status_code == 200
    db_session.refresh(app)
    assert app.status == ApplicationStatusEnum.APPROVED.value
    assert app.reviewed_by_user_id == rev_user.id
    assert app.reviewed_at is not None

    queue = client.get("/api/applications/queue", headers={"Authorization": f"Bearer {rev_token}"})
    assert queue.status_code == 200
    queue_item = next(item for item in queue.json()["items"] if item["id"] == app.id)
    assert queue_item["decision_maker_name"] == "Clean Reviewer"
    assert queue_item["next_action"] == "No action: approval recorded"

    # Audit event verified
    audit = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.application_id == app.id, AuditEvent.event_type == "APPLICATION_APPROVED")
        .first()
    )
    assert audit is not None


def test_scenario_2_blocking_exception_prevents_approval(db_session: Session, client: TestClient):
    """
    Scenario 2: Unresolved Critical/High exception prevents approval,
    returning an explainable error with the blocking reason.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Block Org {tok}", slug=f"block-org-{tok}")
    db_session.add(org)
    db_session.flush()

    rev_user = User(email=f"block-rev-{tok}@org.com", full_name="Block Reviewer", hashed_password="pw")
    db_session.add(rev_user)
    db_session.flush()
    db_session.add(OrganisationMember(organisation_id=org.id, user_id=rev_user.id, role=RoleEnum.REVIEWER.value))

    vendor = Vendor(organisation_id=org.id, legal_name="Block Corp", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-BLOCK-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        legal_name="Block Corp",
        constitution=ConstitutionEnum.PVT_LTD.value,
        status=ApplicationStatusEnum.UNDER_REVIEW.value,
        submitted_at=datetime.now(timezone.utc),
    )
    db_session.add(app)
    db_session.flush()

    # Open critical exception
    exc = OnboardingException(
        reference_number=f"EXC-BLK-{tok}",
        organisation_id=org.id,
        application_id=app.id,
        vendor_id=vendor.id,
        category=ExceptionCategoryEnum.PAN_MISMATCH.value,
        title="Unverified PAN Identifier",
        description="Statutory PAN check failed",
        severity=ExceptionSeverityEnum.CRITICAL.value,
        status=ExceptionStatusEnum.OPEN.value,
        created_by_role="SYSTEM",
    )
    db_session.add(exc)
    db_session.commit()

    rev_token = create_access_token(data={"sub": rev_user.id})

    # Attempt to approve
    res_appr = client.post(
        f"/api/applications/{app.id}/approve",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={"notes": "Trying to bypass"},
    )
    assert res_appr.status_code == 400
    detail = res_appr.json()["detail"]
    assert "Mandatory policy requirements not met" in detail["message"]
    assert any("Unresolved CRITICAL exception" in r for r in detail["reasons"])

    # Ensure application remains in review, NOT approved
    db_session.refresh(app)
    assert app.status == ApplicationStatusEnum.UNDER_REVIEW.value


def test_scenario_3_clarification_and_rejection_workflows(db_session: Session, client: TestClient):
    """
    Scenario 3: Reviewer requests clarification, transitioning to ACTION_REQUIRED,
    and rejection requires a mandatory reason.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Workflow Org {tok}", slug=f"wf-org-{tok}")
    db_session.add(org)
    db_session.flush()

    rev_user = User(email=f"wf-rev-{tok}@org.com", full_name="WF Reviewer", hashed_password="pw")
    db_session.add(rev_user)
    db_session.flush()
    db_session.add(OrganisationMember(organisation_id=org.id, user_id=rev_user.id, role=RoleEnum.REVIEWER.value))

    vendor = Vendor(organisation_id=org.id, legal_name="WF Vendor", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-WF-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        legal_name="WF Vendor",
        constitution=ConstitutionEnum.PVT_LTD.value,
        status=ApplicationStatusEnum.UNDER_REVIEW.value,
        submitted_at=datetime.now(timezone.utc),
    )
    db_session.add(app)
    db_session.commit()

    requested_document = Document(
        application_id=app.id,
        organisation_id=org.id,
        document_type=DocumentTypeEnum.GST_CERTIFICATE.value,
        title="GST Registration Certificate",
        is_required=True,
        status="UPLOADED",
    )
    db_session.add(requested_document)
    db_session.commit()

    rev_token = create_access_token(data={"sub": rev_user.id})

    # 1. Request Clarification without instructions -> Fails
    res_clar_empty = client.post(
        f"/api/applications/{app.id}/request-clarification",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={"instructions": "   "},
    )
    assert res_clar_empty.status_code == 400

    # 2. Request Clarification with instructions -> Transitions to ACTION_REQUIRED
    res_clar = client.post(
        f"/api/applications/{app.id}/request-clarification",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={
            "instructions": "Please provide your active GST registration certificate.",
            "related_document_id": requested_document.id,
        },
    )
    assert res_clar.status_code == 200
    db_session.refresh(app)
    assert app.status == ApplicationStatusEnum.ACTION_REQUIRED.value
    clarification_task = db_session.query(OnboardingException).filter(
        OnboardingException.application_id == app.id,
        OnboardingException.status == ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
    ).one()
    assert clarification_task.related_document_id == requested_document.id
    assert clarification_task.vendor_action_instruction == "Please provide your active GST registration certificate."

    # 3. Reject without reason -> Fails
    res_rej_empty = client.post(
        f"/api/applications/{app.id}/reject",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={"reason": ""},
    )
    assert res_rej_empty.status_code == 400

    # 4. Reject with meaningful reason -> Transitions to REJECTED
    res_rej = client.post(
        f"/api/applications/{app.id}/reject",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={"reason": "Entity appears on statutory blacklisted registry and has failed corporate identity verification."},
    )
    assert res_rej.status_code == 200
    db_session.refresh(app)
    assert app.status == ApplicationStatusEnum.REJECTED.value
    assert "blacklisted" in app.rejection_reason


def test_approval_gate_requires_linked_failure_disposition(db_session: Session):
    """An unrelated exception cannot mask a failed check; a documented linked dismissal can."""
    tok = secrets.token_hex(4)
    org = Organization(name=f"Disposition Org {tok}", slug=f"disposition-org-{tok}")
    db_session.add(org)
    db_session.flush()
    vendor = Vendor(organisation_id=org.id, legal_name="Duplicate Candidate", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()
    app = Application(
        reference_number=f"APP-DISPOSITION-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        legal_name="Duplicate Candidate Ltd",
        constitution=ConstitutionEnum.PVT_LTD.value,
        status=ApplicationStatusEnum.UNDER_REVIEW.value,
    )
    db_session.add(app)
    db_session.flush()
    run = ValidationRun(
        application_id=app.id,
        organisation_id=org.id,
        status="COMPLETED",
        is_current=True,
    )
    db_session.add(run)
    db_session.flush()
    finding = ValidationFinding(
        validation_run_id=run.id,
        application_id=app.id,
        check_id="DUPLICATE_VENDOR_MATCH",
        layer=ValidationLayerEnum.LAYER_D_DUPLICATE.value,
        check_name="Possible duplicate supplier",
        status=ValidationStatusEnum.FAILED.value,
        severity=ValidationSeverityEnum.HIGH.value,
        explanation="A close match needs a person to compare the records.",
    )
    db_session.add(finding)
    unrelated_exception = OnboardingException(
        reference_number=f"EXC-UNRELATED-{tok}",
        organisation_id=org.id,
        application_id=app.id,
        vendor_id=vendor.id,
        category=ExceptionCategoryEnum.PAN_MISMATCH.value,
        title="Unrelated low priority issue",
        description="A different check is being reviewed.",
        severity=ExceptionSeverityEnum.LOW.value,
        status=ExceptionStatusEnum.OPEN.value,
        source_check_ids_json='["PAN_FORMAT"]',
        created_by_role="SYSTEM",
    )
    db_session.add(unrelated_exception)
    db_session.commit()

    service = ReviewerDecisionService(db_session)
    eligible, reasons = service.check_approval_eligibility(app)
    assert not eligible
    assert any("Possible duplicate supplier" in reason for reason in reasons)

    unrelated_exception.status = ExceptionStatusEnum.RESOLVED.value
    unrelated_exception.source_finding_id = finding.id
    unrelated_exception.source_check_ids_json = json.dumps([finding.check_id])
    unrelated_exception.resolution_type = "CORRECTED_BY_VENDOR"
    unrelated_exception.resolution_notes = "Vendor supplied a correction; rerun is still needed."
    db_session.commit()
    eligible, reasons = service.check_approval_eligibility(app)
    assert not eligible
    assert any("Possible duplicate supplier" in reason for reason in reasons)

    unrelated_exception.resolution_type = "DISMISSED_AS_FALSE_POSITIVE"
    unrelated_exception.resolution_notes = "Compared the legal name, tax identifier and registered address; this is a distinct entity."
    db_session.commit()
    eligible, reasons = service.check_approval_eligibility(app)
    assert eligible
    assert reasons == []


def test_application_comprehensive_details_endpoint(db_session: Session, client: TestClient):
    """
    Verify /api/applications/{id}/details returns complete 7-section payload
    with sensitive values properly masked and simulated verification labeled.
    """
    tok = secrets.token_hex(4)
    org = Organization(name=f"Details Org {tok}", slug=f"det-org-{tok}")
    db_session.add(org)
    db_session.flush()

    rev_user = User(email=f"det-rev-{tok}@org.com", full_name="Details Reviewer", hashed_password="pw")
    db_session.add(rev_user)
    db_session.flush()
    db_session.add(OrganisationMember(organisation_id=org.id, user_id=rev_user.id, role=RoleEnum.REVIEWER.value))

    vendor = Vendor(organisation_id=org.id, legal_name="Details Enterprise", constitution=ConstitutionEnum.PVT_LTD.value)
    db_session.add(vendor)
    db_session.flush()

    app = Application(
        reference_number=f"APP-DET-{tok}",
        organisation_id=org.id,
        vendor_id=vendor.id,
        legal_name="Details Enterprise Private Limited",
        constitution=ConstitutionEnum.PVT_LTD.value,
        status=ApplicationStatusEnum.SUBMITTED.value,
        submitted_at=datetime.now(timezone.utc),
        pan="AAACD1234A",
        bank_account_number="123456789012",
        bank_ifsc="HDFC0001234",
    )
    db_session.add(app)
    db_session.flush()

    # Add simulated external verification
    ext_rec = ExternalVerificationRecord(
        application_id=app.id,
        organisation_id=org.id,
        verification_type="PAN",
        provider_name="Simulated Protean/NDSL Adapter",
        request_id=f"REQ-{tok}",
        submitted_identifier="AAACD1234A",
        status="VERIFIED",
        is_simulated=True,
    )
    db_session.add(ext_rec)
    db_session.commit()

    rev_token = create_access_token(data={"sub": rev_user.id})

    res = client.get(
        f"/api/applications/{app.id}/details",
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert res.status_code == 200
    payload = res.json()

    # 1. Overview
    assert "overview" in payload
    assert payload["overview"]["reference_number"] == app.reference_number

    # 2. Business details with masked values
    b_details = payload["business_details"]
    assert "AA*****4A" in b_details["tax_and_registrations"]["pan"]
    assert "********9012" in b_details["banking"]["bank_account_number"]

    # 3. Documents
    assert "documents" in payload

    # 4. External verifications labeled as simulated sandbox
    verifs = payload["external_verifications"]
    assert len(verifs) >= 1
    assert verifs[0]["is_simulated"] is True
    assert verifs[0]["environment_label"] == "SIMULATED SANDBOX"

    # 5. Activity trail
    assert "activity_trail" in payload
