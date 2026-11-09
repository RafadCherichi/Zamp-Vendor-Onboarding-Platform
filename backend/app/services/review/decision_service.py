from app.core.deps import require_case_access
import json
import secrets
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.application import Application, ApplicationStatusEnum
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.user import User
from app.models.document import Document
from app.models.extraction import DocumentExtractionResult
from app.models.exception import OnboardingException, ExceptionStatusEnum, ExceptionSeverityEnum, ExceptionTransition
from app.models.validation import ValidationRun, ValidationFinding, ValidationStatusEnum
from app.models.audit import AuditEvent
from app.services.notifications.service import NotificationService
from app.services.exceptions.state_machine import validate_transition
from app.services.validation.document_slot import mismatched_required_document_slots


class ReviewerDecisionService:
    """
    Enforces policy compliance gates, reviewer assignments, and application lifecycle
    decisions (Approval, Rejection, Clarification Request, Escalation).
    """

    def __init__(self, db: Session):
        self.db = db

    def prepare_eligibility(self, applications):
        """Request-local evidence snapshot for read-only queues; never used to approve."""
        ids = [app.id for app in applications]
        exceptions = {}
        runs = {}
        if not ids:
            return {"exceptions": exceptions, "runs": runs, "extractions": {}}
        for exc in self.db.query(OnboardingException).filter(OnboardingException.application_id.in_(ids)).all():
            exceptions.setdefault(exc.application_id, []).append(exc)
        for run in self.db.query(ValidationRun).options(selectinload(ValidationRun.findings)).filter(
            ValidationRun.application_id.in_(ids), ValidationRun.is_current.is_(True)
        ).all():
            runs.setdefault(run.application_id, run)
        version_ids = [doc.versions[0].id for app in applications for doc in app.documents if doc.versions]
        extractions = {
            item.document_version_id: item
            for item in self.db.query(DocumentExtractionResult).filter(
                DocumentExtractionResult.document_version_id.in_(version_ids)
            ).all()
        } if version_ids else {}
        return {"exceptions": exceptions, "runs": runs, "extractions": extractions}

    def check_approval_eligibility(self, app: Application, *, evidence=None) -> Tuple[bool, List[str]]:
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
        for doc, extraction in mismatched_required_document_slots(
            self.db, app, extractions=evidence["extractions"] if evidence is not None else None
        ):
            blocking_reasons.append(
                f"Required document has the wrong file type: {doc.title}. "
                f"The latest upload appears to be {extraction.detected_document_type.replace('_', ' ')}."
            )

        # 3. Unresolved Exceptions check (Critical and High strictly block approval)
        unresolved_exceptions = [
            exc for exc in evidence["exceptions"].get(app.id, [])
            if exc.status not in [ExceptionStatusEnum.RESOLVED.value, ExceptionStatusEnum.CLOSED.value]
        ] if evidence is not None else (
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
        current_run = evidence["runs"].get(app.id) if evidence is not None else (
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
            if current_run.status != "COMPLETED":
                blocking_reasons.append("Automated checks are incomplete. Retry checks before deciding.")
            if any(finding.is_stale for finding in current_run.findings):
                blocking_reasons.append("Evidence changed after checks. Run checks again before deciding.")
            # A provider timeout is unknown evidence, not a clean verification.
            # Staff can retry or document a policy path before approval.
            unavailable_checks = [
                finding for finding in current_run.findings
                if finding.status in [ValidationStatusEnum.UNAVAILABLE.value, ValidationStatusEnum.UNVERIFIED.value]
                and finding.check_id.startswith("C_")
                and not finding.is_stale
            ]
            for finding in unavailable_checks:
                blocking_reasons.append(
                    f"Verification incomplete: {finding.check_name}. Procurement must verify the evidence or escalate before approval."
                )
            # A different open exception must not mask an unaddressed failed check.
            # Match exceptions by finding ID or check ID and accept only an explicit
            # manual disposition; a vendor correction needs a fresh passing run.
            application_exceptions = evidence["exceptions"].get(app.id, []) if evidence is not None else self.db.query(OnboardingException).filter(
                OnboardingException.application_id == app.id
            ).all()
            manually_disposed = {
                ExceptionStatusEnum.RESOLVED.value,
                ExceptionStatusEnum.CLOSED.value,
            }
            accepted_dispositions = {
                "VERIFIED_MANUALLY",
                "WAIVED_WITH_JUSTIFICATION",
                "OVERRIDDEN_BY_ADMIN",
                "DISMISSED_AS_FALSE_POSITIVE",
            }
            for finding in [
                item for item in current_run.findings
                if not item.is_stale and (
                    item.status == ValidationStatusEnum.FAILED.value
                    or (item.status == ValidationStatusEnum.UNVERIFIED.value and item.check_id in {
                        "B_PAN_DOC_CROSS_MATCH", "B_BANK_ACCOUNT_NUM_MATCH"
                    })
                )
            ]:
                linked_exceptions = []
                for exception in application_exceptions:
                    try:
                        source_check_ids = json.loads(exception.source_check_ids_json or "[]")
                    except (TypeError, json.JSONDecodeError):
                        source_check_ids = []
                    if exception.source_finding_id == finding.id:
                        linked_exceptions.append(exception)

                has_active_exception = any(exc.status not in manually_disposed for exc in linked_exceptions)
                has_manual_disposition = any(
                    exc.status in manually_disposed
                    and exc.resolution_type in accepted_dispositions
                    and bool((exc.resolution_notes or "").strip())
                    for exc in linked_exceptions
                )
                if not has_manual_disposition:
                    blocking_reasons.append(
                        f"Validation failure needs review: {finding.check_name}. "
                        "Open its linked issue, document a manual finding, or rerun the check after correction."
                    )

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
        self._require_decision_authority(app, actor_member)

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
        self._claim_transition(app, ApplicationStatusEnum.APPROVED.value)
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
        self._require_decision_authority(app, actor_member)

        if app.status in [ApplicationStatusEnum.DRAFT.value, ApplicationStatusEnum.IN_PROGRESS.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reject an application that has not been submitted.",
            )
        if app.status in [ApplicationStatusEnum.REJECTED.value, ApplicationStatusEnum.APPROVED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A final decision has already been recorded.",
            )

        now = datetime.now(timezone.utc)
        prev_status = app.status
        self._claim_transition(app, ApplicationStatusEnum.REJECTED.value)
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
        related_document_id: Optional[str] = None,
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
        self._require_decision_authority(app, actor_member)

        if related_document_id:
            related_document = self.db.query(Document).filter(
                Document.id == related_document_id,
                Document.application_id == app.id,
            ).first()
            if not related_document:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The selected document does not belong to this application.")

        prev_status = app.status
        self._claim_transition(app, ApplicationStatusEnum.ACTION_REQUIRED.value)
        app.clarification_requested_at = datetime.now(timezone.utc)

        clarification_exception = None
        # If linked to an existing exception, transition that exception.
        if related_exception_id:
            clarification_exception = (
                self.db.query(OnboardingException)
                .filter(
                    OnboardingException.id == related_exception_id,
                    OnboardingException.application_id == app.id,
                )
                .first()
            )
            if not clarification_exception:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The selected issue was not found for this application.")
            validate_transition(
                current_status=clarification_exception.status,
                target_status=ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
                actor_role=actor_member.role,
                reason=instructions.strip(),
            )
            clarification_exception.status = ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value
            clarification_exception.vendor_action_instruction = instructions.strip()

        # General clarification requests also need a durable, answerable vendor
        # task. An audit entry alone leaves the vendor with nothing to respond to.
        if not clarification_exception:
            clarification_exception = OnboardingException(
                reference_number=f"EXC-{datetime.now(timezone.utc).year}-{secrets.token_hex(3).upper()}",
                organisation_id=app.organisation_id,
                application_id=app.id,
                vendor_id=app.vendor_id,
                category="MISSING_INFORMATION",
                title="Additional information requested",
                description=instructions.strip(),
                severity=ExceptionSeverityEnum.MEDIUM.value,
                source_check_ids_json="[]",
                related_document_id=related_document_id,
                related_field_name=related_field,
                assigned_role=RoleEnum.VENDOR.value,
                status=ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
                vendor_action_instruction=instructions.strip(),
                created_by_user_id=actor_member.user_id,
                created_by_role=actor_member.role,
            )
            self.db.add(clarification_exception)
            self.db.flush()
            self.db.add(ExceptionTransition(
                exception_id=clarification_exception.id,
                from_status="OPEN",
                to_status=ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
                actor_user_id=actor_member.user_id,
                actor_role=actor_member.role,
                reason=instructions.strip()[:255],
                notes="Clarification request created for the vendor.",
            ))

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
                "related_document_id": related_document_id,
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
        self._require_decision_authority(app, actor_member)

        prev_status = app.status
        self._claim_transition(app, ApplicationStatusEnum.ESCALATED.value)

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
            role=target_role.lower(),
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
        reason: Optional[str] = None,
    ) -> Application:
        """
        Assigns or reassigns an application to an internal reviewer within the same organisation.
        """
        app = self._get_scoped_app(application_id, actor_member)
        if actor_member.role not in [RoleEnum.ADMIN.value, RoleEnum.PROCUREMENT_OFFICER.value]:
            raise HTTPException(status_code=403, detail="Procurement or an administrator must assign the decision maker.")

        if actor_member.role == RoleEnum.ADMIN.value and not (reason or "").strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators must record a reason when changing case ownership.",
            )

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
            if not target_member or not target_member.is_active or target_member.role not in [
                RoleEnum.REVIEWER.value,
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
                "reason": reason.strip() if reason else None,
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
        require_case_access(app, member)
        return app

    def _claim_transition(self, app, target_status):
        # Compare and write in one statement so concurrent decisions cannot both win.
        query = self.db.query(Application).filter(
            Application.id == app.id,
            Application.organisation_id == app.organisation_id,
            Application.status == app.status,
            Application.assigned_reviewer_id == app.assigned_reviewer_id,
            Application.updated_at == app.updated_at,
        )
        changed = query.update({"status": target_status, "updated_at": datetime.now(timezone.utc)}, synchronize_session=False)
        if changed != 1:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="This case changed while you were reviewing it. Refresh the case before deciding.")
        app.status = target_status

    def _require_decision_authority(self, app, member):
        if member.role not in [RoleEnum.REVIEWER.value, RoleEnum.ADMIN.value]:
            raise HTTPException(status_code=403, detail="A reviewer must record this decision.")
        if app.status not in ["SUBMITTED", "UNDER_REVIEW", "ACTION_REQUIRED", "ESCALATED"]:
            raise HTTPException(status_code=409, detail="This application is not awaiting a decision.")
        if app.assigned_reviewer_id != member.user_id:
            raise HTTPException(status_code=403, detail="Assign this case to the decision maker before recording a decision.")

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
