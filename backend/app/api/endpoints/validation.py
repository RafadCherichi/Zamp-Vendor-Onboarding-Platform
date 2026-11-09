import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_member, require_roles
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.application import Application
from app.models.validation import (
    ValidationRun,
    ValidationFinding,
    ExternalVerificationRecord,
    DuplicateSignal,
)
from app.models.audit import AuditEvent
from app.schemas.validation import (
    ValidationRunResponse,
    ValidationRunHistoryItemResponse,
    ValidationFindingResponse,
    ExternalVerificationResponse,
    DuplicateSignalResponse,
    AuditEventResponse,
    ValidationTriggerRequest,
)
from app.services.validation.orchestrator import ValidationOrchestrator
from app.api.endpoints.applications import get_scoped_application

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/runs",
    response_model=List[ValidationRunHistoryItemResponse],
    summary="List validation runs for the current organisation",
    description="Returns real validation executions with the current human decision state and a concise reason.",
)
def list_validation_runs(
    limit: int = 50,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([
        RoleEnum.REVIEWER,
        RoleEnum.PROCUREMENT_OFFICER,
        RoleEnum.ADMIN,
    ])),
) -> List[ValidationRunHistoryItemResponse]:
    bounded_limit = max(1, min(limit, 100))
    runs = (
        db.query(ValidationRun)
        .join(Application, ValidationRun.application_id == Application.id)
        .filter(
            ValidationRun.organisation_id == member.organisation_id,
            Application.organisation_id == member.organisation_id,
            *([Application.assigned_reviewer_id == member.user_id] if member.role == RoleEnum.REVIEWER.value else []),
        )
        .order_by(ValidationRun.created_at.desc(), ValidationRun.id.desc())
        .limit(bounded_limit)
        .all()
    )

    items: List[ValidationRunHistoryItemResponse] = []
    pending_statuses = {
        "DRAFT", "IN_PROGRESS", "SUBMITTED", "ACTION_REQUIRED", "UNDER_REVIEW", "ESCALATED"
    }
    for run in runs:
        application = run.application
        if application.status == "APPROVED":
            outcome = "APPROVED"
        elif application.status == "REJECTED":
            outcome = "REJECTED"
        elif application.status in pending_statuses:
            outcome = "PENDING"
        else:
            outcome = "PENDING"

        reason = ""
        if not reason:
            relevant = next(
                (
                    finding
                    for finding in run.findings
                    if finding.status in {"FAILED", "UNVERIFIED", "UNAVAILABLE"}
                    or finding.is_stale
                ),
                None,
            )
            if relevant:
                reason = relevant.explanation
        if not reason:
            if run.failed_count == 0 and run.warning_count == 0 and run.unverified_count == 0 and run.unavailable_count == 0:
                reason = f"All {run.passed_count} checks passed. A reviewer still needs to record the final decision."
            else:
                reason = run.summary or "Checks are recorded. A human reviewer makes the final decision."

        items.append(
            ValidationRunHistoryItemResponse(
                id=run.id,
                application_id=application.id,
                application_reference=application.reference_number,
                vendor_name=application.legal_name,
                run_type=run.run_type,
                run_status=run.status,
                outcome=outcome,
                application_status=application.status,
                check_outcome=("INCOMPLETE" if run.status != "COMPLETED" else "NEEDS_REVIEW" if run.failed_count or run.warning_count or run.unverified_count or run.unavailable_count or any(f.is_stale for f in run.findings) else "CLEAR"),
                decision_at=application.reviewed_at,
                summary=run.summary,
                reason=reason,
                passed_count=run.passed_count,
                failed_count=run.failed_count,
                warning_count=run.warning_count,
                unverified_count=run.unverified_count,
                unavailable_count=run.unavailable_count,
                is_current=run.is_current,
                created_at=run.created_at,
            )
        )
    return items


@router.get(
    "/runs/{run_id}",
    response_model=ValidationRunResponse,
    summary="Get one validation run and its findings",
    description="Returns the exact saved execution selected from run history, scoped to the reviewer's organisation.",
)
def get_validation_run_history_detail(
    run_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([
        RoleEnum.REVIEWER,
        RoleEnum.PROCUREMENT_OFFICER,
        RoleEnum.ADMIN,
    ])),
) -> ValidationRunResponse:
    run = db.query(ValidationRun).filter(
        ValidationRun.id == run_id,
        ValidationRun.organisation_id == member.organisation_id,
    ).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation run not found.")
    get_scoped_application(run.application_id, member, db)
    return run


@router.post(
    "/{application_id}/validate",
    response_model=ValidationRunResponse,
    summary="Trigger Application Validation Run",
    description="Executes Layers A-D deterministic checks, cross-field matching, simulated verifications, and duplicate detection.",
)
def trigger_validation(
    application_id: str,
    payload: Optional[ValidationTriggerRequest] = None,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> ValidationRunResponse:
    app = get_scoped_application(application_id, member, db)

    orchestrator = ValidationOrchestrator(db)
    run_type = payload.run_type if payload else "FULL"
    trigger_reason = payload.trigger_reason if payload else "User triggered validation"

    validation_run = orchestrator.run_full_validation(
        application_id=app.id,
        user_id=member.user_id,
        run_type=run_type,
        trigger_reason=trigger_reason,
    )
    return validation_run


@router.get(
    "/{application_id}/validation",
    response_model=ValidationRunResponse,
    summary="Get Active Validation Run and Findings",
    description="Retrieves the current validation run with granular findings, evidence, and recommendations.",
)
def get_application_validation(
    application_id: str,
    auto_run: bool = True,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> ValidationRunResponse:
    app = get_scoped_application(application_id, member, db)

    current_run = (
        db.query(ValidationRun)
        .filter(
            ValidationRun.application_id == app.id,
            ValidationRun.is_current.is_(True),
        )
        .order_by(ValidationRun.created_at.desc())
        .first()
    )

    if not current_run and auto_run:
        orchestrator = ValidationOrchestrator(db)
        current_run = orchestrator.run_full_validation(
            application_id=app.id,
            user_id=member.user_id,
            run_type="INITIAL",
            trigger_reason="Automatic initial validation check",
        )

    if not current_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No validation run found for this application. Trigger validation first.",
        )

    return current_run


@router.get(
    "/{application_id}/verifications",
    response_model=List[ExternalVerificationResponse],
    summary="Get External Verification Records",
    description="Lists all simulated and authoritative external verification queries performed for the application.",
)
def get_external_verifications(
    application_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> List[ExternalVerificationResponse]:
    app = get_scoped_application(application_id, member, db)

    verifications = (
        db.query(ExternalVerificationRecord)
        .filter(
            ExternalVerificationRecord.application_id == app.id,
            ExternalVerificationRecord.organisation_id == member.organisation_id,
        )
        .order_by(ExternalVerificationRecord.created_at.desc())
        .all()
    )
    return verifications


@router.get(
    "/{application_id}/duplicates",
    response_model=List[DuplicateSignalResponse],
    summary="Get Organisation Duplicate Signals",
    description="Lists potential duplicate vendor/application signals detected within the organisation.",
)
def get_duplicate_signals(
    application_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([
        RoleEnum.REVIEWER,
        RoleEnum.PROCUREMENT_OFFICER,
        RoleEnum.ADMIN,
    ])),
) -> List[DuplicateSignalResponse]:
    app = get_scoped_application(application_id, member, db)

    signals = (
        db.query(DuplicateSignal)
        .filter(
            DuplicateSignal.application_id == app.id,
            DuplicateSignal.organisation_id == member.organisation_id,
        )
        .order_by(DuplicateSignal.created_at.desc())
        .all()
    )
    return signals


@router.post(
    "/{application_id}/duplicates/{signal_id}/dismiss",
    response_model=DuplicateSignalResponse,
    summary="Dismiss Duplicate Signal",
    description="Allows a reviewer or administrator to dismiss a duplicate candidate flag with explanation.",
)
def dismiss_duplicate_signal(
    application_id: str,
    signal_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([
        RoleEnum.REVIEWER,
        RoleEnum.ADMIN,
    ])),
) -> DuplicateSignalResponse:
    app = get_scoped_application(application_id, member, db)

    signal = (
        db.query(DuplicateSignal)
        .filter(
            DuplicateSignal.id == signal_id,
            DuplicateSignal.application_id == app.id,
            DuplicateSignal.organisation_id == member.organisation_id,
        )
        .first()
    )
    if not signal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Duplicate signal not found.")

    signal.is_dismissed = True

    # Audit log
    audit = AuditEvent(
        organisation_id=member.organisation_id,
        application_id=app.id,
        actor_user_id=member.user_id,
        actor_role=member.role,
        event_type="DUPLICATE_SIGNAL_DISMISSED",
        entity_type="DUPLICATE_SIGNAL",
        entity_id=signal.id,
        details_json=json.dumps({"dismissed_by": member.user.email}),
    )
    db.add(audit)
    db.commit()
    db.refresh(signal)
    return signal


@router.get(
    "/{application_id}/audit-trail",
    response_model=List[AuditEventResponse],
    summary="Get Application Audit Trail",
    description="Returns immutable structured audit trail of validation, verification, and decision events.",
)
def get_audit_trail(
    application_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([
        RoleEnum.REVIEWER,
        RoleEnum.PROCUREMENT_OFFICER,
        RoleEnum.ADMIN,
    ])),
) -> List[AuditEventResponse]:
    app = get_scoped_application(application_id, member, db)

    events = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.application_id == app.id,
            AuditEvent.organisation_id == member.organisation_id,
        )
        .order_by(AuditEvent.created_at.desc())
        .all()
    )
    return events
