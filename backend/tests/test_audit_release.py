"""Regression checks for the approved November audit repair."""
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.schemas.review import QueueItemResponse
from app.services.review.decision_service import ReviewerDecisionService


def test_queue_response_preserves_actionable_details():
    item = QueueItemResponse(id="a", reference_number="APP-1", legal_name="Example", constitution="LLP", status="UNDER_REVIEW", open_exceptions_count=1, critical_exceptions_count=1, ready_for_approval=False, next_action="Review response", blocking_reasons=["Bank holder differs"], vendor_replied=True)
    assert item.model_dump()["blocking_reasons"] == ["Bank holder differs"]
    assert item.model_dump()["vendor_replied"] is True


@pytest.mark.parametrize("state", ["APPROVED", "REJECTED", "DRAFT", "IN_PROGRESS"])
def test_terminal_and_unsubmitted_cases_cannot_receive_decisions(state):
    service = ReviewerDecisionService(MagicMock())
    with pytest.raises(HTTPException):
        service._require_decision_authority(SimpleNamespace(status=state, assigned_reviewer_id="reviewer"), SimpleNamespace(role="reviewer", user_id="reviewer"))


@pytest.mark.parametrize("role,owner", [("procurement_officer", "reviewer"), ("reviewer", "other"), ("admin", "other")])
def test_only_assigned_decision_maker_can_decide(role, owner):
    service = ReviewerDecisionService(MagicMock())
    with pytest.raises(HTTPException) as error:
        service._require_decision_authority(SimpleNamespace(status="UNDER_REVIEW", assigned_reviewer_id=owner), SimpleNamespace(role=role, user_id="reviewer"))
    assert error.value.status_code == 403


def test_invitation_does_not_replace_existing_password():
    from app.api.endpoints.invitations import accept_invitation
    from app.schemas.invitation import InvitationAcceptRequest
    from app.core.security import hash_password
    original = hash_password("ExistingPassword123!")
    user = SimpleNamespace(hashed_password=original, is_active=True)
    invite = SimpleNamespace(status="PENDING", is_expired=False, vendor_email="existing@example.com")
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.first.return_value = invite
    db.query.return_value.filter.return_value.first.return_value = user
    with pytest.raises(HTTPException) as error:
        accept_invitation("synthetic-token", InvitationAcceptRequest(password="AttackerPassword123!", full_name="Example"), db)
    assert error.value.status_code == 401
    assert user.hashed_password == original
    db.commit.assert_not_called()


@pytest.mark.parametrize("proof_status", ["FAILED", "UNVERIFIED"])
def test_material_pan_evidence_requires_review(proof_status):
    finding = SimpleNamespace(id="pan-proof", check_id="B_PAN_DOC_CROSS_MATCH", check_name="PAN proof", status=proof_status, severity="HIGH", is_stale=False)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(status="COMPLETED", findings=[finding])
    db.query.return_value.filter.return_value.all.return_value = []
    eligible, reasons = ReviewerDecisionService(db).check_approval_eligibility(SimpleNamespace(id="app", status="UNDER_REVIEW", documents=[]))
    assert not eligible
    assert any("PAN proof" in reason for reason in reasons)


def test_fourth_failed_check_still_blocks_approval():
    findings = [SimpleNamespace(id=str(i), check_id=f"CHECK_{i}", check_name=f"Check {i}", status="FAILED", is_stale=False) for i in range(4)]
    run = SimpleNamespace(status="COMPLETED", findings=findings)
    # First three findings have current, explicitly documented dispositions.
    exceptions = [SimpleNamespace(source_finding_id=str(i), source_check_ids_json="[]", status="RESOLVED", resolution_type="VERIFIED_MANUALLY", resolution_notes="Evidence reviewed") for i in range(3)]
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = run
    db.query.return_value.filter.return_value.all.side_effect = [[], exceptions]
    app = SimpleNamespace(id="app", status="UNDER_REVIEW", documents=[])
    eligible, reasons = ReviewerDecisionService(db).check_approval_eligibility(app)
    assert not eligible
    assert any("Check 3" in reason for reason in reasons)


def test_document_request_cannot_be_answered_with_explanation_alone():
    from app.services.exceptions.revalidation import ExceptionResolutionService
    exc = SimpleNamespace(status="ACTION_REQUIRED_FROM_VENDOR", application=SimpleNamespace(), related_document_id="doc", related_field_name=None)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = exc
    with pytest.raises(HTTPException) as error:
        ExceptionResolutionService(db).submit_vendor_correction("request", SimpleNamespace(id="vendor"), explanation="Please approve")
    assert error.value.status_code == 400
    assert exc.status == "ACTION_REQUIRED_FROM_VENDOR"
    db.commit.assert_not_called()


def test_repeated_link_of_same_document_response_is_idempotent():
    from app.services.exceptions.revalidation import ExceptionResolutionService
    exc = SimpleNamespace(status="RESPONSE_SUBMITTED", related_version_id="version")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = exc
    assert ExceptionResolutionService(db).link_document_replacement("request", "version", SimpleNamespace(id="vendor")) is exc
    db.commit.assert_not_called()


def test_dashboard_cohorts_match_case_membership(db_session):
    import secrets
    from datetime import datetime, timezone, timedelta
    from app.models.organization import Organization
    from app.models.vendor import Vendor
    from app.models.application import Application
    from app.services.review.queue_service import QueueAndDashboardService
    suffix = secrets.token_hex(4)
    org = Organization(name="Cohort regression", slug=f"cohort-{suffix}")
    db_session.add(org)
    db_session.flush()
    vendor = Vendor(organisation_id=org.id, legal_name="Cohort supplier", constitution="PROPRIETORSHIP")
    db_session.add(vendor)
    db_session.flush()
    now = datetime.now(timezone.utc)
    cases = []
    for name, state, age in [("old", "UNDER_REVIEW", 4), ("fresh", "UNDER_REVIEW", 1), ("draft", "DRAFT", 0), ("progress", "IN_PROGRESS", 0), ("final", "APPROVED", 5)]:
        case = Application(organisation_id=org.id, vendor_id=vendor.id, reference_number=f"COHORT-{suffix}-{name}", legal_name=name, status=state, submitted_at=now-timedelta(days=age))
        db_session.add(case)
        cases.append(case)
    db_session.flush()
    service = QueueAndDashboardService(db_session)
    for cohort, expected in [("OVERDUE_REVIEW", {"old"}), ("BEING_COMPLETED", {"draft", "progress"}), ("UNASSIGNED", {"old", "fresh"})]:
        result = service.query_queue(organisation_id=org.id, status=cohort)
        assert {item["legal_name"] for item in result["items"]} == expected
        assert result["total"] == len(expected)
    db_session.rollback()


def test_validation_task_failure_does_not_publish_partial_run(db_session, monkeypatch):
    from app.models.application import Application
    from app.models.validation import ValidationRun
    from app.services.validation.orchestrator import ValidationOrchestrator
    from app.services.exceptions.generator import ExceptionGenerator
    app = db_session.query(Application).filter_by(reference_number="APP-2026-CLEAN-001").one()
    previous = db_session.query(ValidationRun).filter_by(application_id=app.id, is_current=True).one()
    previous_id = previous.id
    count_before = db_session.query(ValidationRun).filter_by(application_id=app.id).count()
    def fail(*args, **kwargs):
        raise RuntimeError("Injected task creation failure")
    monkeypatch.setattr(ExceptionGenerator, "sync_exceptions_for_application", fail)
    with pytest.raises(RuntimeError, match="Injected task"):
        ValidationOrchestrator(db_session).run_full_validation(application_id=app.id)
    assert db_session.query(ValidationRun).filter_by(application_id=app.id, is_current=True).one().id == previous_id
    assert db_session.query(ValidationRun).filter_by(application_id=app.id).count() == count_before


@pytest.mark.parametrize("adapter_name,identifier", [("SimulatedPanAdapter", "ABCDE1234F"), ("SimulatedGstAdapter", "27ABCDE1234F1Z5"), ("SimulatedMcaAdapter", "U99999MH2020PTC123456"), ("SimulatedBankAccountAdapter", "123456789876")])
def test_unlisted_registry_ids_never_verify_applicant_claims(adapter_name, identifier):
    from app.services.verification import simulated
    adapter = getattr(simulated, adapter_name)()
    first = adapter.verify(identifier, {"legal_name": "Company One", "account_holder_name": "Company One"})
    second = adapter.verify(identifier, {"legal_name": "Company Two", "account_holder_name": "Company Two"})
    assert first.status.value == second.status.value == "UNVERIFIED"
    assert first.returned_attributes == second.returned_attributes == {}


def test_known_registry_record_does_not_change_with_applicant_name():
    from app.services.verification.simulated import SimulatedPanAdapter
    adapter = SimulatedPanAdapter()
    first = adapter.verify("AAPFU0938L", {"legal_name": "Sharma Engineering Works"})
    second = adapter.verify("AAPFU0938L", {"legal_name": "Unrelated Supplier"})
    assert first.returned_attributes == second.returned_attributes


@pytest.mark.parametrize("failure", ["empty", "timeout"])
def test_extraction_records_actual_fallback_provider(monkeypatch, failure):
    from app.services.extraction.providers.ai_gemini import GeminiExtractionProvider
    provider = GeminiExtractionProvider(api_key="synthetic-test-key")
    def remote(*args):
        if failure == "timeout":
            raise TimeoutError("Synthetic timeout")
        return []
    monkeypatch.setattr(provider, "_call_gemini_api", remote)
    monkeypatch.setattr(provider._local_fallback, "extract", lambda *args: [])
    provider.extract("Synthetic evidence", "PAN_PROOF")
    assert provider.provider_name == "LOCAL_DETERMINISTIC"


def test_demo_eligibility_is_bound_to_identity_not_legal_name():
    from app.db.demo_profiles import demo_profile_id, initial_demo_identity
    practice = SimpleNamespace(id="app-apex-base-01", vendor_id="vnd-apex-base-01", created_by_user_id="usr-vendor-apex-01", legal_name="Changed form name", vendor=SimpleNamespace(created_by_user_id="usr-vendor-apex-01"))
    assert demo_profile_id(practice) == "apex-components"
    assert initial_demo_identity(practice)["pan"] is None
    assert initial_demo_identity(practice)["legal_name"] == "Apex Components & Fasteners"
    practice.id = "another-application"
    practice.legal_name = "Apex Components & Fasteners"
    assert demo_profile_id(practice) is None


@pytest.mark.parametrize("first_status", ["APPROVED", "UNDER_REVIEW"])
def test_stale_decision_cannot_overwrite_winner(db_session, first_status):
    import secrets
    from sqlalchemy.orm import Session
    from app.models.organization import Organization
    from app.models.vendor import Vendor
    from app.models.application import Application
    suffix = secrets.token_hex(4)
    org = Organization(name="Decision race", slug=f"race-{suffix}")
    db_session.add(org)
    db_session.flush()
    vendor = Vendor(organisation_id=org.id, legal_name="Race supplier", constitution="PROPRIETORSHIP")
    db_session.add(vendor)
    db_session.flush()
    case = Application(organisation_id=org.id, vendor_id=vendor.id, reference_number=f"RACE-{suffix}", legal_name="Race supplier", status="UNDER_REVIEW")
    db_session.add(case)
    db_session.commit()
    case_id = case.id
    with Session(db_session.get_bind()) as first, Session(db_session.get_bind()) as second:
        first_case = first.get(Application, case_id)
        stale_case = second.get(Application, case_id)
        ReviewerDecisionService(first)._claim_transition(first_case, first_status)
        first.commit()
        with pytest.raises(HTTPException) as error:
            ReviewerDecisionService(second)._claim_transition(stale_case, "REJECTED")
        assert error.value.status_code == 409
        second.expire_all()
        assert second.get(Application, case_id).status == first_status


def test_naive_persisted_timestamps_are_serialized_as_utc():
    from datetime import datetime
    from app.schemas.notification import NotificationResponse
    from app.schemas.common import iso_utc
    stamp = datetime(2026, 11, 9, 8, 2, 49)
    assert iso_utc(stamp) == "2026-11-09T08:02:49+00:00"
    notice = NotificationResponse(id="n", title="Decision", message="Approved", notification_type="STATUS_CHANGE", entity_type="APPLICATION", entity_id="a", is_read=False, created_at=stamp)
    assert notice.model_dump(mode="json")["created_at"].endswith("Z")


def test_stale_invitation_claim_is_rejected_without_commit():
    from app.api.endpoints.invitations import claim_invitation
    db = MagicMock()
    db.query.return_value.filter.return_value.update.return_value = 0
    with pytest.raises(HTTPException) as error:
        claim_invitation(db, SimpleNamespace(id="already-claimed"))
    assert error.value.status_code == 409
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_only_one_session_can_claim_an_invitation(db_session):
    import secrets
    from datetime import datetime, timezone, timedelta
    from sqlalchemy.orm import Session
    from app.models.invitation import Invitation
    from app.models.organization import Organization
    from app.models.user import User
    from app.api.endpoints.invitations import claim_invitation
    suffix = secrets.token_hex(4)
    org = Organization(name="Invitation race", slug=f"invite-race-{suffix}")
    user = User(email=f"inviter-{suffix}@example.com", full_name="Inviter", hashed_password="unused")
    db_session.add_all([org, user])
    db_session.flush()
    invitation = Invitation(organisation_id=org.id, invited_by_user_id=user.id, vendor_name="Synthetic supplier", vendor_email=f"supplier-{suffix}@example.com", token_hash=secrets.token_hex(32), status="PENDING", expires_at=datetime.now(timezone.utc)+timedelta(days=1))
    db_session.add(invitation)
    db_session.commit()
    identity = invitation.id
    with Session(db_session.get_bind()) as first, Session(db_session.get_bind()) as second:
        first_invite = first.get(Invitation, identity)
        stale_invite = second.get(Invitation, identity)
        claim_invitation(first, first_invite)
        first.commit()
        with pytest.raises(HTTPException) as error:
            claim_invitation(second, stale_invite)
        assert error.value.status_code == 409
        second.expire_all()
        assert second.get(Invitation, identity).status == "ACCEPTED"


def test_empty_upload_slots_are_not_counted_as_processing(db_session):
    import secrets
    from app.models.organization import Organization
    from app.models.vendor import Vendor
    from app.models.application import Application
    from app.models.document import Document, DocumentVersion
    from app.models.extraction import DocumentProcessingJob
    from app.services.review.queue_service import QueueAndDashboardService
    suffix = secrets.token_hex(4)
    org = Organization(name="Job counts", slug=f"jobs-{suffix}")
    db_session.add(org)
    db_session.flush()
    vendor = Vendor(organisation_id=org.id, legal_name="Job supplier", constitution="PROPRIETORSHIP")
    db_session.add(vendor)
    db_session.flush()
    case = Application(organisation_id=org.id, vendor_id=vendor.id, legal_name="Job supplier", reference_number=f"JOBS-{suffix}", status="IN_PROGRESS")
    db_session.add(case)
    db_session.flush()
    doc = Document(application_id=case.id, organisation_id=org.id, document_type="PAN_PROOF", title="Empty optional proof", status="PENDING", is_required=False)
    db_session.add(doc)
    db_session.flush()
    service = QueueAndDashboardService(db_session)
    assert service.get_dashboard_metrics(org.id)["processing_count"] == 0
    version = DocumentVersion(document_id=doc.id, version_number=1, original_filename="synthetic.pdf", storage_key="synthetic-test", content_type="application/pdf", file_size_bytes=20, file_checksum="synthetic-checksum")
    db_session.add(version)
    db_session.flush()
    doc.current_version_id = version.id
    job = DocumentProcessingJob(document_version_id=version.id, status="PROCESSING")
    db_session.add(job)
    db_session.flush()
    assert service.get_dashboard_metrics(org.id)["processing_count"] == 1
    job.status = "EXTRACTED"
    db_session.flush()
    assert service.get_dashboard_metrics(org.id)["processing_count"] == 0
    db_session.rollback()


def test_competing_upload_cannot_allocate_a_second_current_version(db_session):
    from sqlalchemy.orm import Session
    from app.models.document import Document, DocumentVersion
    from app.api.endpoints.applications import reserve_document_version
    document = db_session.query(Document).filter(Document.current_version_id.isnot(None)).first()
    assert document is not None
    with Session(db_session.get_bind()) as first, Session(db_session.get_bind()) as second:
        first_doc = first.get(Document, document.id)
        stale_doc = second.get(Document, document.id)
        version_id, number = reserve_document_version(first, first_doc)
        first.add(DocumentVersion(id=version_id, document_id=document.id, version_number=number, storage_key="synthetic-race-test", original_filename="synthetic.pdf", file_size_bytes=20, content_type="application/pdf", file_checksum="synthetic-test"))
        first.commit()
        with pytest.raises(HTTPException) as error:
            reserve_document_version(second, stale_doc)
        assert error.value.status_code == 409
        second.expire_all()
        assert second.get(Document, document.id).current_version_id == version_id
        # Restore the private test fixture so other tests retain their original evidence.
        first.query(Document).filter_by(id=document.id).update({"current_version_id": document.current_version_id})
        first.query(DocumentVersion).filter_by(id=version_id).delete()
        first.commit()
