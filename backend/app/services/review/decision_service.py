import json
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStatusEnum
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.user import User
from app.models.document import Document
from app.models.exception import OnboardingException, ExceptionStatusEnum, ExceptionSeverityEnum
from app.models.validation import ValidationRun, ValidationFinding, ValidationStatusEnum
from app.models.audit import AuditEvent
from app.services.notifications.service import NotificationService
from app.services.exceptions.state_machine import validate_transition


class ReviewerDecisionService:
    """
    Enforces policy compliance gates, reviewer assignments, and application lifecycle
    decisions (Approval, Rejection, Clarification Request, Escalation).
    """

    def __init__(self, db: Session):
        self.db = db

    def check_approval_eligibility(self, app: Application) -> Tuple[bool, List[str]]:
        """
        Evaluates whether an application satisfies all statutory and organizational
        policy prerequisites for formal approval.
        """
        blocking_reasons: List[str] = []

        # 1. State check: Cannot approve draft or terminal state
        if app.status in [ApplicationStatusEnum.DRAFT.value, ApplicationStatusEnum.IN_PROGRESS.value]:
            blocking_reasons.append("Application has not been formally submitted by the vendor.")
        if app.status == ApplicationStatusEnum.APPROVED.value:
            blocking_reasons.append("Application is already approved.")
        if app.status == ApplicationStatusEnum.REJECTED.value:
            blocking_reasons.append("Application has already been rejected and cannot be directly approved.")

        # 2. Mandatory Documents check
        for doc in app.documents:
            if doc.is_required and doc.status != "UPLOADED":
                blocking_reasons.append(f"Mandatory document missing: {doc.title}")

        # 3. Unresolved Exceptions check (Critical and High strictly block approval)
        unresolved_exceptions = (
            self.db.query(OnboardingException)
            .filter(
                OnboardingException.application_id == app.id,
                OnboardingException.status.notin_([
                    ExceptionStatusEnum.RESOLVED.value,
                    ExceptionStatusEnum.CLOSED.value,
                ]),
            )
            .all()
        )

        for exc in unresolved_exceptions:
            if exc.severity in [ExceptionSeverityEnum.CRITICAL.value, ExceptionSeverityEnum.HIGH.value]:
                blocking_reasons.append(
                    f"Unresolved {exc.severity} exception: {exc.reference_number} ({exc.title})"
                )
            elif exc.status == ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value:
                blocking_reasons.append(
                    f"Pending vendor clarification: {exc.reference_number} ({exc.title})"
                )

        # 4. Current Validation Run check
        current_run = (
            self.db.query(ValidationRun)
            .filter(
                ValidationRun.application_id == app.id,
                ValidationRun.is_current.is_(True),
            )
            .first()
        )
        if not current_run:
            blocking_reasons.append("No completed validation evaluation on file for this application.")
        else:
            # Check for unaddressed failed checks that have no corresponding exception or resolution
            unaddressed_failures = [
                f for f in current_run.findings
                if f.status == ValidationStatusEnum.FAILED.value and not f.is_stale
            ]
            # If there are failed checks and no exceptions were raised/resolved for them
            if unaddressed_failures and not unresolved_exceptions:
                # Any active failures should be investigated
                for uf in unaddressed_failures[:3]:
                    blocking_reasons.append(f"Validation failure unaddressed: {uf.check_name}")

        is_eligible = len(blocking_reasons) == 0
        return is_eligible, blocking_reasons

    def approve_application(
        self,
        application_id: str,
        actor_member: OrganisationMember,
        notes: Optional[str] = None,
    ) -> Application:
        """
        Approves an application if all policy requirements are met.
        """
        app = self._get_scoped_app(application_id, actor_member)
        self._require_review_role(actor_member)

        is_eligible, blocking_reasons = self.check_approval_eligibility(app)
        if not is_eligible:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Cannot approve application. Mandatory policy requirements not met.",
                    "reasons": blocking_reasons,
                },
            )

        now = datetime.now(timezone.utc)
        prev_status = app.status
        app.status = ApplicationStatusEnum.APPROVED.value
        app.reviewed_by_user_id = actor_member.user_id
        app.reviewed_at = now
        app.decision_notes = notes

        # Audit event
        audit = AuditEvent(
            organisation_id=app.organisation_id,
            application_id=app.id,
            actor_user_id=actor_member.user_id,
            actor_role=actor_member.role,
            event_type="APPLICATION_APPROVED",
            entity_type="APPLICATION",
            entity_id=app.id,
            details_json=json.dumps({
                "from_status": prev_status,
                "to_status": app.status,
                "notes": notes,
                "reviewer_name": actor_member.user.full_name if actor_member.user else "Reviewer",
            }),
        )
        self.db.add(audit)

        # Notify vendor
        if app.created_by_user_id:
            NotificationService.create_notification(
                db=self.db,
                organisation_id=app.organisation_id,
                recipient_user_id=app.created_by_user_id,
                title=f"Application Approved: {app.reference_number}",
                message=f"Congratulations! Your onboarding application for {app.legal_name} has been officially approved.",
                notification_type="STATUS_CHANGE",
                entity_type="APPLICATION",
                entity_id=app.id,
            )

        self.db.commit()
        self.db.refresh(app)
        return app

    def reject_application(
        self,
        application_id: str,
        actor_member: OrganisationMember,
        reason: str,
        notes: Optional[str] = None,
    ) -> Application:
        """
        Rejects an application with a mandatory rejection explanation.
        """
        if not reason or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A clear, reasoned rejection explanation is mandatory.",
            )

        app = self._get_scoped_app(application_id, actor_member)
        self._require_review_role(actor_member)

        if app.status in [ApplicationStatusEnum.DRAFT.value, ApplicationStatusEnum.IN_PROGRESS.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reject an application that has not been submitted.",
            )
        if app.status == ApplicationStatusEnum.REJECTED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Application is already in rejected state.",
            )

        now = datetime.now(timezone.utc)
        prev_status = app.status
        app.status = ApplicationStatusEnum.REJECTED.value
        app.reviewed_by_user_id = actor_member.user_id
        app.reviewed_at = now
        app.rejection_reason = reason.strip()
        app.decision_notes = notes

        # Audit event
        audit = AuditEvent(
            organisation_id=app.organisation_id,
            application_id=app.id,
            actor_user_id=actor_member.user_id,
            actor_role=actor_member.role,
            event_type="APPLICATION_REJECTED",
            entity_type="APPLICATION",
            entity_id=app.id,
            details_json=json.dumps({
                "from_status": prev_status,
                "to_status": app.status,
                "rejection_reason": reason.strip(),
                "notes": notes,
                "reviewer_name": actor_member.user.full_name if actor_member.user else "Reviewer",
            }),
        )
        self.db.add(audit)

        # Notify vendor
        if app.created_by_user_id:
            NotificationService.create_notification(
                db=self.db,
                organisation_id=app.organisation_id,
                recipient_user_id=app.created_by_user_id,
                title=f"Application Rejected: {app.reference_number}",
                message=f"Your onboarding application for {app.legal_name} was not approved. Reason: {reason.strip()}",
                notification_type="STATUS_CHANGE",
                entity_type="APPLICATION",
                entity_id=app.id,
            )

        self.db.commit()
        self.db.refresh(app)
        return app

    def request_clarification(
        self,
        application_id: str,
        actor_member: OrganisationMember,
        instructions: str,
        related_exception_id: Optional[str] = None,
        related_field: Optional[str] = None,
    ) -> Application:
        """
        Transitions application to ACTION_REQUIRED and alerts vendor with specific instructions.
        """
        if not instructions or not instructions.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specific clarification instructions for the vendor are mandatory.",
            )

        app = self._get_scoped_app(application_id, actor_member)
        self._require_review_role(actor_member)

        prev_status = app.status
        app.status = ApplicationStatusEnum.ACTION_REQUIRED.value
        app.clarification_requested_at = datetime.now(timezone.utc)

        # If linked to an existing exception, transition that exception
        if related_exception_id:
            exc = (
                self.db.query(OnboardingException)
                .filter(
                    OnboardingException.id == related_exception_id,
                    OnboardingException.application_id == app.id,
                )
                .first()
            )
            if exc:
                validate_transition(
                    current_status=exc.status,
                    target_status=ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
                    actor_role=actor_member.role,
                    reason=instructions.strip(),
                )
                exc.status = ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value
                exc.vendor_action_instruction = instructions.strip()

        # Audit event
        audit = AuditEvent(
            organisation_id=app.organisation_id,
            application_id=app.id,
            actor_user_id=actor_member.user_id,
            actor_role=actor_member.role,
            event_type="APPLICATION_CLARIFICATION_REQUESTED",
            entity_type="APPLICATION",
            entity_id=app.id,
            details_json=json.dumps({
                "from_status": prev_status,
                "to_status": app.status,
                "instructions": instructions.strip(),
                "related_exception_id": related_exception_id,
                "related_field": related_field,
            }),
        )
        self.db.add(audit)

        # Notify vendor
        if app.created_by_user_id:
            NotificationService.create_notification(
                db=self.db,
                organisation_id=app.organisation_id,
                recipient_user_id=app.created_by_user_id,
                title=f"Action Required: Clarification for {app.reference_number}",
                message=instructions.strip(),
                notification_type="ACTION_REQUIRED",
                entity_type="APPLICATION",
                entity_id=app.id,
            )

        self.db.commit()
        self.db.refresh(app)
        return app

    def escalate_application(
        self,
        application_id: str,
        actor_member: OrganisationMember,
        reason: str,
        target_role: str = "ADMIN",
    ) -> Application:
        """
        Escalates an application for higher-level administrative or policy review.
        """
        if not reason or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A clear escalation justification is mandatory.",
            )

        app = self._get_scoped_app(application_id, actor_member)
        self._require_review_role(actor_member)

        prev_status = app.status
        app.status = ApplicationStatusEnum.ESCALATED.value

        # Audit event
        audit = AuditEvent(
            organisation_id=app.organisation_id,
            application_id=app.id,
            actor_user_id=actor_member.user_id,
            actor_role=actor_member.role,
            event_type="APPLICATION_ESCALATED",
            entity_type="APPLICATION",
            entity_id=app.id,
            details_json=json.dumps({
                "from_status": prev_status,
                "to_status": app.status,
                "reason": reason.strip(),
                "target_role": target_role,
            }),
        )
        self.db.add(audit)

        # Notify target role in organization
        NotificationService.notify_organisation_role(
            db=self.db,
            organisation_id=app.organisation_id,
            target_role=target_role,
            title=f"Escalation Alert: Application {app.reference_number}",
            message=f"Application for {app.legal_name} has been escalated: {reason.strip()}",
            notification_type="ESCALATION",
            entity_type="APPLICATION",
            entity_id=app.id,
        )

        self.db.commit()
        self.db.refresh(app)
        return app

    def assign_reviewer(
        self,
        application_id: str,
        reviewer_user_id: Optional[str],
        actor_member: OrganisationMember,
    ) -> Application:
        """
        Assigns or reassigns an application to an internal reviewer within the same organisation.
        """
        app = self._get_scoped_app(application_id, actor_member)
        self._require_review_role(actor_member)

        prev_reviewer_id = app.assigned_reviewer_id

        if reviewer_user_id:
            # Verify reviewer belongs to same organisation and has permissible role
            target_member = (
                self.db.query(OrganisationMember)
                .filter(
                    OrganisationMember.user_id == reviewer_user_id,
                    OrganisationMember.organisation_id == app.organisation_id,
                )
                .first()
            )
            if not target_member or target_member.role not in [
                RoleEnum.REVIEWER.value,
                RoleEnum.PROCUREMENT_OFFICER.value,
                RoleEnum.ADMIN.value,
            ]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assigned user must belong to this organisation with Reviewer, Procurement, or Admin authority.",
                )

        now = datetime.now(timezone.utc)
        app.assigned_reviewer_id = reviewer_user_id
        app.assigned_at = now if reviewer_user_id else None

        # If currently SUBMITTED and assigned, transition to UNDER_REVIEW
        if app.status == ApplicationStatusEnum.SUBMITTED.value and reviewer_user_id:
            app.status = ApplicationStatusEnum.UNDER_REVIEW.value

        # Audit event
        audit = AuditEvent(
            organisation_id=app.organisation_id,
            application_id=app.id,
            actor_user_id=actor_member.user_id,
            actor_role=actor_member.role,
            event_type="REVIEWER_ASSIGNED",
            entity_type="APPLICATION",
            entity_id=app.id,
            details_json=json.dumps({
                "previous_reviewer_id": prev_reviewer_id,
                "new_reviewer_id": reviewer_user_id,
                "assigned_by_user_id": actor_member.user_id,
            }),
        )
        self.db.add(audit)

        # Notify assigned reviewer
        if reviewer_user_id and reviewer_user_id != actor_member.user_id:
            NotificationService.create_notification(
                db=self.db,
                organisation_id=app.organisation_id,
                recipient_user_id=reviewer_user_id,
                title=f"Application Assigned: {app.reference_number}",
                message=f"You have been assigned to review application for {app.legal_name}.",
                notification_type="ASSIGNMENT",
                entity_type="APPLICATION",
                entity_id=app.id,
            )

        self.db.commit()
        self.db.refresh(app)
        return app

    def _get_scoped_app(self, application_id: str, member: OrganisationMember) -> Application:
        app = (
            self.db.query(Application)
            .filter(
                Application.id == application_id,
                Application.organisation_id == member.organisation_id,
            )
            .first()
        )
        if not app:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
        return app

    def _require_review_role(self, member: OrganisationMember):
        if member.role not in [
            RoleEnum.REVIEWER.value,
            RoleEnum.PROCUREMENT_OFFICER.value,
            RoleEnum.ADMIN.value,
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Reviewer, Procurement, or Admin role required.",
            )
