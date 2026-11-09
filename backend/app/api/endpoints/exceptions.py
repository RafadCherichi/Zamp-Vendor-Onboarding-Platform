import json
import secrets
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_member, require_roles
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.vendor import Vendor
from app.models.application import Application
from app.models.exception import (
    OnboardingException,
    ExceptionTransition,
    ExceptionComment,
    ExceptionStatusEnum,
    ResolutionTypeEnum,
)
from app.models.audit import AuditEvent
from app.schemas.exception import (
    OnboardingExceptionResponse,
    ExceptionCreateRequest,
    ExceptionTransitionRequest,
    ExceptionAssignRequest,
    ExceptionCommentCreate,
    ExceptionCommentResponse,
    VendorCorrectionSubmitRequest,
)
from app.services.exceptions.state_machine import validate_transition
from app.services.exceptions.generator import ExceptionGenerator
from app.services.exceptions.revalidation import ExceptionResolutionService
from app.services.notifications.service import NotificationService
from app.api.endpoints.applications import get_scoped_application

router = APIRouter()


def sanitize_exception_for_vendor(exc: OnboardingException) -> OnboardingException:
    """
    Sanitizes an exception model before returning to a vendor,
    stripping internal reviewer comments and notes.
    """
    # Filter comments to only non-internal ones
    exc.comments = [c for c in exc.comments if not c.is_internal]
    return exc


@router.get(
    "/",
    response_model=List[OnboardingExceptionResponse],
    summary="List Exceptions",
    description="Lists exceptions scoped to the user's organisation with role-based filtering.",
)
def list_exceptions(
    application_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    severity: Optional[str] = None,
    assigned_role: Optional[str] = None,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> List[OnboardingExceptionResponse]:
    query = (
        db.query(OnboardingException)
        .filter(OnboardingException.organisation_id == member.organisation_id)
    )

    if member.role == RoleEnum.REVIEWER.value:
        query = query.filter(OnboardingException.application_id.in_(db.query(Application.id).filter(Application.organisation_id == member.organisation_id, Application.assigned_reviewer_id == member.user_id)))

    # Vendor scoping: Only own applications and only non-internal comments
    if member.role == RoleEnum.VENDOR.value:
        vendor_apps = (
            db.query(Application.id)
            .join(Vendor, Application.vendor_id == Vendor.id, isouter=True)
            .filter(
                Application.organisation_id == member.organisation_id,
                (Application.created_by_user_id == member.user_id) | (Vendor.created_by_user_id == member.user_id),
            )
            .all()
        )
        vendor_app_ids = [a[0] for a in vendor_apps]
        query = query.filter(OnboardingException.application_id.in_(vendor_app_ids))

    if application_id:
        query = query.filter(OnboardingException.application_id == application_id)
    if status_filter:
        query = query.filter(OnboardingException.status == status_filter)
    if category:
        query = query.filter(OnboardingException.category == category)
    if severity:
        query = query.filter(OnboardingException.severity == severity)
    if assigned_role:
        query = query.filter(OnboardingException.assigned_role == assigned_role)

    exceptions = query.order_by(OnboardingException.created_at.desc()).all()

    if member.role == RoleEnum.VENDOR.value:
        for exc in exceptions:
            sanitize_exception_for_vendor(exc)

    return exceptions


@router.get(
    "/{exception_id}",
    response_model=OnboardingExceptionResponse,
    summary="Get Exception by ID",
    description="Retrieves a single exception with complete transition history and comments.",
)
def get_exception(
    exception_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> OnboardingExceptionResponse:
    exc = (
        db.query(OnboardingException)
        .filter(
            OnboardingException.id == exception_id,
            OnboardingException.organisation_id == member.organisation_id,
        )
        .first()
    )
    if not exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")
    get_scoped_application(exc.application_id, member, db)

    # If vendor, ensure ownership
    if member.role == RoleEnum.VENDOR.value:
        if exc.application.created_by_user_id != member.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        sanitize_exception_for_vendor(exc)

    return exc


@router.post(
    "/sync-from-validation/{application_id}",
    response_model=List[OnboardingExceptionResponse],
    summary="Synchronize Exceptions from Validation Run",
    description="Evaluates the latest validation findings and creates or updates non-duplicate actionable exceptions.",
)
def sync_exceptions(
    application_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([
        RoleEnum.PROCUREMENT_OFFICER,
        RoleEnum.REVIEWER,
        RoleEnum.ADMIN,
    ])),
) -> List[OnboardingExceptionResponse]:
    app = get_scoped_application(application_id, member, db)
    generator = ExceptionGenerator(db)
    created = generator.sync_exceptions_for_application(
        application_id=app.id,
        actor_user_id=member.user_id,
        actor_role=member.role,
    )
    return created


@router.post(
    "/",
    response_model=OnboardingExceptionResponse,
    summary="Create Manual Exception",
    description="Allows a reviewer or procurement officer to raise a new exception on an application.",
)
def create_manual_exception(
    payload: ExceptionCreateRequest,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([
        RoleEnum.PROCUREMENT_OFFICER,
        RoleEnum.REVIEWER,
        RoleEnum.ADMIN,
    ])),
) -> OnboardingExceptionResponse:
    app = get_scoped_application(payload.application_id, member, db)

    ref_no = f"EXC-{datetime.now(timezone.utc).year}-{secrets.token_hex(3).upper()}"
    new_exc = OnboardingException(
        reference_number=ref_no,
        organisation_id=app.organisation_id,
        application_id=app.id,
        vendor_id=app.vendor_id,
        category=payload.category,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        source_check_ids_json=json.dumps(payload.source_check_ids or []),
        related_document_id=payload.related_document_id,
        related_field_name=payload.related_field_name,
        assigned_user_id=payload.assigned_user_id,
        assigned_role=payload.assigned_role or RoleEnum.REVIEWER.value,
        status=payload.initial_status or ExceptionStatusEnum.OPEN.value,
        vendor_action_instruction=payload.vendor_action_instruction,
        created_by_user_id=member.user_id,
        created_by_role=member.role,
    )
    db.add(new_exc)
    db.flush()

    # Initial transition
    trans = ExceptionTransition(
        exception_id=new_exc.id,
        from_status="NONE",
        to_status=new_exc.status,
        actor_user_id=member.user_id,
        actor_role=member.role,
        reason="Manually raised by reviewer/procurement",
        notes=payload.description,
    )
    db.add(trans)

    # Notify vendor if action required
    if new_exc.status == ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value and app.created_by_user_id:
        NotificationService.create_notification(
            db=db,
            organisation_id=app.organisation_id,
            recipient_user_id=app.created_by_user_id,
            title=f"Clarification Required: {new_exc.title}",
            message=new_exc.vendor_action_instruction or new_exc.description,
            notification_type="ACTION_REQUIRED",
            entity_type="EXCEPTION",
            entity_id=new_exc.id,
        )

    db.commit()
    db.refresh(new_exc)
    return new_exc


@router.post(
    "/{exception_id}/transition",
    response_model=OnboardingExceptionResponse,
    summary="Transition Exception Status",
    description="Transitions an exception through its lifecycle with backend validation rules.",
)
def transition_exception(
    exception_id: str,
    payload: ExceptionTransitionRequest,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([
        RoleEnum.PROCUREMENT_OFFICER,
        RoleEnum.REVIEWER,
        RoleEnum.ADMIN,
    ])),
) -> OnboardingExceptionResponse:
    exc = (
        db.query(OnboardingException)
        .filter(
            OnboardingException.id == exception_id,
            OnboardingException.organisation_id == member.organisation_id,
        )
        .first()
    )
    if not exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")
    get_scoped_application(exc.application_id, member, db)

    if (
        payload.target_status in [ExceptionStatusEnum.RESOLVED.value, ExceptionStatusEnum.CLOSED.value]
        and payload.resolution_type in {
            "VERIFIED_MANUALLY",
            "WAIVED_WITH_JUSTIFICATION",
            "OVERRIDDEN_BY_ADMIN",
            "DISMISSED_AS_FALSE_POSITIVE",
        }
        and not (payload.resolution_notes or payload.notes or "").strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add the evidence or reason that supports this manual resolution.",
        )

    validate_transition(
        current_status=exc.status,
        target_status=payload.target_status,
        actor_role=member.role,
        reason=payload.reason or payload.notes,
    )

    prev_status = exc.status
    exc.status = payload.target_status

    if payload.resolution_type:
        exc.resolution_type = payload.resolution_type
    if payload.resolution_notes:
        exc.resolution_notes = payload.resolution_notes
    if payload.vendor_action_instruction:
        exc.vendor_action_instruction = payload.vendor_action_instruction

    if payload.target_status in [ExceptionStatusEnum.RESOLVED.value, ExceptionStatusEnum.CLOSED.value]:
        exc.resolved_at = datetime.now(timezone.utc)
        exc.resolved_by_user_id = member.user_id

    trans = ExceptionTransition(
        exception_id=exc.id,
        from_status=prev_status,
        to_status=exc.status,
        actor_user_id=member.user_id,
        actor_role=member.role,
        reason=payload.reason,
        notes=payload.notes,
    )
    db.add(trans)

    # Notify vendor if action required
    if exc.status == ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value and exc.application.created_by_user_id:
        NotificationService.create_notification(
            db=db,
            organisation_id=exc.organisation_id,
            recipient_user_id=exc.application.created_by_user_id,
            title=f"Action Required: {exc.title}",
            message=exc.vendor_action_instruction or payload.notes or "Please review requested clarification.",
            notification_type="ACTION_REQUIRED",
            entity_type="EXCEPTION",
            entity_id=exc.id,
        )

    # Audit log
    audit = AuditEvent(
        organisation_id=exc.organisation_id,
        application_id=exc.application_id,
        actor_user_id=member.user_id,
        actor_role=member.role,
        event_type="EXCEPTION_STATUS_TRANSITIONED",
        entity_type="ONBOARDING_EXCEPTION",
        entity_id=exc.id,
        details_json=json.dumps({
            "from_status": prev_status,
            "to_status": exc.status,
            "reason": payload.reason,
        }),
    )
    db.add(audit)

    db.commit()
    db.refresh(exc)
    return exc


@router.post(
    "/{exception_id}/assign",
    response_model=OnboardingExceptionResponse,
    summary="Assign Exception",
    description="Assigns or reassigns an exception to a specific user or role.",
)
def assign_exception(
    exception_id: str,
    payload: ExceptionAssignRequest,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([
        RoleEnum.PROCUREMENT_OFFICER,
        RoleEnum.REVIEWER,
        RoleEnum.ADMIN,
    ])),
) -> OnboardingExceptionResponse:
    exc = (
        db.query(OnboardingException)
        .filter(
            OnboardingException.id == exception_id,
            OnboardingException.organisation_id == member.organisation_id,
        )
        .first()
    )
    if not exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")
    get_scoped_application(exc.application_id, member, db)

    exc.assigned_user_id = payload.assigned_user_id
    if payload.assigned_role:
        exc.assigned_role = payload.assigned_role

    if exc.status == ExceptionStatusEnum.OPEN.value:
        exc.status = ExceptionStatusEnum.ASSIGNED.value

    trans = ExceptionTransition(
        exception_id=exc.id,
        from_status=exc.status,
        to_status=exc.status,
        actor_user_id=member.user_id,
        actor_role=member.role,
        reason="Reassigned responsibility",
        notes=payload.reason or f"Assigned to user {payload.assigned_user_id or payload.assigned_role}",
    )
    db.add(trans)

    if payload.assigned_user_id:
        NotificationService.create_notification(
            db=db,
            organisation_id=exc.organisation_id,
            recipient_user_id=payload.assigned_user_id,
            title=f"Exception Assigned: {exc.reference_number}",
            message=f"You have been assigned exception '{exc.title}' for application {exc.application.reference_number}.",
            notification_type="ASSIGNMENT",
            entity_type="EXCEPTION",
            entity_id=exc.id,
        )

    db.commit()
    db.refresh(exc)
    return exc


@router.post(
    "/{exception_id}/comments",
    response_model=ExceptionCommentResponse,
    summary="Add Exception Comment",
    description="Adds a comment to the exception thread. Vendors cannot post internal notes.",
)
def add_comment(
    exception_id: str,
    payload: ExceptionCommentCreate,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> ExceptionCommentResponse:
    exc = (
        db.query(OnboardingException)
        .filter(
            OnboardingException.id == exception_id,
            OnboardingException.organisation_id == member.organisation_id,
        )
        .first()
    )
    if not exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")
    get_scoped_application(exc.application_id, member, db)

    is_internal = payload.is_internal
    if member.role == RoleEnum.VENDOR.value:
        if exc.application.created_by_user_id != member.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        is_internal = False  # Vendors can never post internal notes

    comment = ExceptionComment(
        exception_id=exc.id,
        author_user_id=member.user_id,
        author_role=member.role,
        is_internal=is_internal,
        message=payload.message,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.post(
    "/{exception_id}/correct",
    response_model=OnboardingExceptionResponse,
    summary="Submit Vendor Correction",
    description="Allows a vendor to submit a corrected field value or response for an exception requiring action.",
)
def submit_correction(
    exception_id: str,
    payload: VendorCorrectionSubmitRequest,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([RoleEnum.VENDOR])),
) -> OnboardingExceptionResponse:
    exc = (
        db.query(OnboardingException)
        .filter(
            OnboardingException.id == exception_id,
            OnboardingException.organisation_id == member.organisation_id,
        )
        .first()
    )
    if not exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")
    get_scoped_application(exc.application_id, member, db)

    # Authorisation: Vendors can only correct their own applications
    if exc.application.created_by_user_id != member.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if payload.field_name and payload.field_name != exc.related_field_name:
        raise HTTPException(status_code=400, detail="Only the field requested by the reviewer can be corrected.")

    service = ExceptionResolutionService(db)
    updated_exc = service.submit_vendor_correction(
        exception_id=exc.id,
        user=member.user,
        field_name=payload.field_name,
        new_field_value=payload.new_field_value,
        explanation=payload.explanation,
    )

    if member.role == RoleEnum.VENDOR.value:
        sanitize_exception_for_vendor(updated_exc)

    return updated_exc


@router.post(
    "/{exception_id}/resolve",
    response_model=OnboardingExceptionResponse,
    summary="Resolve Exception",
    description="Resolves an exception with a specific resolution type and justification notes.",
)
def resolve_exception(
    exception_id: str,
    payload: ExceptionTransitionRequest,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([
        RoleEnum.REVIEWER,
        RoleEnum.ADMIN,
    ])),
) -> OnboardingExceptionResponse:
    payload.target_status = ExceptionStatusEnum.RESOLVED.value
    if not payload.resolution_type:
        payload.resolution_type = ResolutionTypeEnum.VERIFIED_MANUALLY.value
    return transition_exception(exception_id, payload, db, member)


@router.post(
    "/{exception_id}/reopen",
    response_model=OnboardingExceptionResponse,
    summary="Reopen Exception",
    description="Reopens a resolved or closed exception with mandatory justification reason.",
)
def reopen_exception(
    exception_id: str,
    payload: ExceptionTransitionRequest,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([
        RoleEnum.REVIEWER,
        RoleEnum.ADMIN,
    ])),
) -> OnboardingExceptionResponse:
    payload.target_status = ExceptionStatusEnum.OPEN.value
    return transition_exception(exception_id, payload, db, member)
