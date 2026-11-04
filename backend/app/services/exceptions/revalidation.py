import json
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.application import Application
from app.models.exception import (
    OnboardingException,
    ExceptionTransition,
    ExceptionStatusEnum,
    FieldCorrectionRecord,
)
from app.models.validation import ValidationFinding, ValidationRun
from app.models.user import User
from app.models.role import RoleEnum
from app.models.audit import AuditEvent
from app.services.exceptions.state_machine import validate_transition
from app.services.validation.orchestrator import ValidationOrchestrator
from app.services.notifications.service import NotificationService
from app.services.verification.simulated import mask_id

logger = logging.getLogger(__name__)

# Permitted vendor-correctable fields
PERMITTED_VENDOR_FIELDS = {
    "legal_name",
    "trade_name",
    "constitution",
    "pan",
    "gstin",
    "cin_llpin",
    "udyam_number",
    "contact_name",
    "contact_email",
    "contact_mobile",
    "bank_account_holder_name",
    "bank_account_number",
    "bank_ifsc",
    "registered_address",
    "city",
    "state",
    "pincode",
}


class ExceptionResolutionService:
    def __init__(self, db: Session):
        self.db = db

    def submit_vendor_correction(
        self,
        exception_id: str,
        user: User,
        field_name: Optional[str] = None,
        new_field_value: Optional[str] = None,
        explanation: Optional[str] = None,
    ) -> OnboardingException:
        """
        Processes a vendor correction on an exception, preserving previous field values,
        invalidating stale validation findings, executing selective revalidation,
        and notifying reviewers.
        """
        exc = self.db.query(OnboardingException).filter(OnboardingException.id == exception_id).first()
        if not exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")

        # Validate transition
        validate_transition(
            current_status=exc.status,
            target_status=ExceptionStatusEnum.RESPONSE_SUBMITTED.value,
            actor_role=RoleEnum.VENDOR.value,
            reason=explanation,
        )

        app = exc.application

        # 1. Handle Field Correction if provided
        target_field = field_name or exc.related_field_name
        if new_field_value is not None and target_field:
            if target_field not in PERMITTED_VENDOR_FIELDS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Field '{target_field}' cannot be modified directly by vendor.",
                )

            prev_val = getattr(app, target_field, None)
            setattr(app, target_field, new_field_value)

            # Record historical field correction
            correction_record = FieldCorrectionRecord(
                exception_id=exc.id,
                application_id=app.id,
                field_name=target_field,
                previous_value=mask_id(str(prev_val)) if "pan" in target_field or "bank" in target_field else str(prev_val) if prev_val else None,
                new_value=mask_id(str(new_field_value)) if "pan" in target_field or "bank" in target_field else str(new_field_value),
                changed_by_user_id=user.id,
                changed_by_role=RoleEnum.VENDOR.value,
                vendor_explanation=explanation,
            )
            self.db.add(correction_record)

        # 2. Transition Exception Status
        prev_status = exc.status
        exc.status = ExceptionStatusEnum.RESPONSE_SUBMITTED.value

        # If application was in ACTION_REQUIRED, return it to UNDER_REVIEW for reviewer reassessment
        if app.status == "ACTION_REQUIRED":
            app.status = "UNDER_REVIEW"

        transition = ExceptionTransition(
            exception_id=exc.id,
            from_status=prev_status,
            to_status=exc.status,
            actor_user_id=user.id,
            actor_role=RoleEnum.VENDOR.value,
            reason="Vendor submitted correction / clarification",
            notes=explanation,
        )
        self.db.add(transition)

        # 3. Mark dependent validation findings stale
        try:
            check_ids = json.loads(exc.source_check_ids_json)
        except Exception:
            check_ids = []

        if check_ids:
            findings = (
                self.db.query(ValidationFinding)
                .filter(
                    ValidationFinding.application_id == app.id,
                    ValidationFinding.check_id.in_(check_ids),
                    ValidationFinding.is_stale.is_(False),
                )
                .all()
            )
            for f in findings:
                f.is_stale = True
                f.stale_reason = f"Vendor submitted correction for exception {exc.reference_number}"

        self.db.flush()

        # 4. Trigger selective / full revalidation
        orchestrator = ValidationOrchestrator(self.db)
        new_run = orchestrator.run_full_validation(
            application_id=app.id,
            user_id=user.id,
            run_type="CORRECTION_REVALIDATION",
            trigger_reason=f"Vendor correction on exception {exc.reference_number}",
        )

        # Update exception source_finding_id to new run's finding if available
        for f in new_run.findings:
            if f.check_id in check_ids:
                exc.source_finding_id = f.id
                break

        # 5. Audit Logging
        audit = AuditEvent(
            organisation_id=app.organisation_id,
            application_id=app.id,
            actor_user_id=user.id,
            actor_role=RoleEnum.VENDOR.value,
            event_type="EXCEPTION_CORRECTION_SUBMITTED",
            entity_type="ONBOARDING_EXCEPTION",
            entity_id=exc.id,
            details_json=json.dumps({
                "exception_ref": exc.reference_number,
                "field_name": exc.related_field_name,
                "has_explanation": bool(explanation),
                "revalidation_run_id": new_run.id,
            }),
        )
        self.db.add(audit)

        # 6. Notify Reviewers
        NotificationService.notify_organisation_role(
            db=self.db,
            organisation_id=app.organisation_id,
            role=RoleEnum.REVIEWER.value,
            title=f"Vendor Correction Submitted: {exc.reference_number}",
            message=f"Vendor submitted a correction for application {app.reference_number} regarding '{exc.title}'.",
            notification_type="CORRECTION_SUBMITTED",
            entity_type="EXCEPTION",
            entity_id=exc.id,
        )

        self.db.commit()
        self.db.refresh(exc)
        return exc

    def link_document_replacement(
        self,
        exception_id: str,
        document_version_id: str,
        user: User,
        explanation: Optional[str] = None,
    ) -> OnboardingException:
        """
        Links a newly uploaded replacement DocumentVersion to the exception,
        marks prior findings stale, reruns validation, and updates exception state.
        """
        exc = self.db.query(OnboardingException).filter(OnboardingException.id == exception_id).first()
        if not exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")

        prev_status = exc.status
        exc.related_version_id = document_version_id
        exc.status = ExceptionStatusEnum.RESPONSE_SUBMITTED.value

        if exc.application and exc.application.status == "ACTION_REQUIRED":
            exc.application.status = "UNDER_REVIEW"

        trans = ExceptionTransition(
            exception_id=exc.id,
            from_status=prev_status,
            to_status=exc.status,
            actor_user_id=user.id,
            actor_role=RoleEnum.VENDOR.value,
            reason="Replacement statutory document uploaded",
            notes=explanation,
        )
        self.db.add(trans)

        # Rerun validation
        orchestrator = ValidationOrchestrator(self.db)
        new_run = orchestrator.run_full_validation(
            application_id=exc.application_id,
            user_id=user.id,
            run_type="DOCUMENT_REPLACEMENT_REVALIDATION",
            trigger_reason=f"Replacement document uploaded for {exc.reference_number}",
        )

        try:
            check_ids = json.loads(exc.source_check_ids_json)
            for f in new_run.findings:
                if f.check_id in check_ids:
                    exc.source_finding_id = f.id
                    break
        except Exception:
            pass

        # Audit event
        audit = AuditEvent(
            organisation_id=exc.organisation_id,
            application_id=exc.application_id,
            actor_user_id=user.id,
            actor_role=RoleEnum.VENDOR.value,
            event_type="EXCEPTION_DOCUMENT_REPLACED",
            entity_type="ONBOARDING_EXCEPTION",
            entity_id=exc.id,
            details_json=json.dumps({
                "exception_ref": exc.reference_number,
                "version_id": document_version_id,
                "new_run_id": new_run.id,
            }),
        )
        self.db.add(audit)

        # Notify reviewers
        NotificationService.notify_organisation_role(
            db=self.db,
            organisation_id=exc.organisation_id,
            role=RoleEnum.REVIEWER.value,
            title=f"Replacement Document Uploaded: {exc.reference_number}",
            message=f"Vendor uploaded a replacement document for application {exc.application.reference_number}.",
            notification_type="CORRECTION_SUBMITTED",
            entity_type="EXCEPTION",
            entity_id=exc.id,
        )

        self.db.commit()
        self.db.refresh(exc)
        return exc
