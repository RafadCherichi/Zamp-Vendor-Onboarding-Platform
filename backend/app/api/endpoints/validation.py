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
