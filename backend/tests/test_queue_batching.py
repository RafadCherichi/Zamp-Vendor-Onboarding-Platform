"""Readiness must retain the decision gate without per-case database reads."""
import secrets
from sqlalchemy import event
from app.models.organization import Organization
from app.models.vendor import Vendor
from app.models.application import Application
from app.models.validation import ValidationRun
from app.models.exception import OnboardingException
from app.services.review.queue_service import QueueAndDashboardService
from app.services.review.decision_service import ReviewerDecisionService


def test_ready_queue_batches_evidence_and_preserves_blockers(db_session):
    db = db_session
    suffix = secrets.token_hex(4)
    org = Organization(name="Queue batching", slug=f"batch-{suffix}")
    db.add(org)
    db.flush()
    vendor = Vendor(organisation_id=org.id, legal_name="Batch supplier", constitution="PROPRIETORSHIP")
    db.add(vendor)
    db.flush()
    for index in range(30):
        case = Application(organisation_id=org.id, vendor_id=vendor.id, reference_number=f"BATCH-{suffix}-{index}", legal_name=f"Supplier {index}", status="UNDER_REVIEW")
        db.add(case)
        db.flush()
        db.add(ValidationRun(application_id=case.id, organisation_id=org.id, status="COMPLETED", is_current=True))
        if index == 0:
            db.add(OnboardingException(application_id=case.id, organisation_id=org.id, vendor_id=vendor.id, reference_number=f"BLOCK-{suffix}", title="Unresolved concern", description="Must block", category="MISSING_INFORMATION", severity="HIGH", status="OPEN", created_by_role="SYSTEM"))
    db.commit()
    org_id = org.id
    db.expunge_all()
    calls = []
    def count(*args):
        calls.append(1)
    event.listen(db.bind, "before_cursor_execute", count)
    try:
        result = QueueAndDashboardService(db).query_queue(org_id, ready_for_approval_only=True)
    finally:
        event.remove(db.bind, "before_cursor_execute", count)
    assert result["total"] == 29
    assert len(result["items"]) == 10
    assert all(item["ready_for_approval"] for item in result["items"])
    assert len(calls) <= 20, f"Readiness used {len(calls)} SQL queries for 30 cases"


def test_batched_gate_matches_fresh_gate_for_seeded_evidence(db_session):
    service = ReviewerDecisionService(db_session)
    applications = db_session.query(Application).limit(12).all()
    evidence = service.prepare_eligibility(applications)
    for case in applications:
        assert service.check_approval_eligibility(case, evidence=evidence) == service.check_approval_eligibility(case)
