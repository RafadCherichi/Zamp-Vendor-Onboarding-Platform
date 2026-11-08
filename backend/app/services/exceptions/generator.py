import json
import secrets
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.validation import ValidationRun, ValidationFinding, ValidationStatusEnum, ValidationSeverityEnum
from app.models.exception import (
    OnboardingException,
    ExceptionTransition,
    ExceptionCategoryEnum,
    ExceptionSeverityEnum,
    ExceptionStatusEnum,
)
from app.models.role import RoleEnum


class ExceptionGenerator:
    """
    Evaluates validation findings and application state to create or update
    actionable exceptions without generating duplicate open issues.
    """

    def __init__(self, db: Session):
        self.db = db

    def sync_exceptions_for_application(
        self,
        application_id: str,
        actor_user_id: Optional[str] = None,
        actor_role: str = "SYSTEM",
        validation_run: Optional[ValidationRun] = None,
    ) -> List[OnboardingException]:
        app = self.db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found")

        # Get current validation run
        current_run = validation_run
        if not current_run:
            current_run = (
                self.db.query(ValidationRun)
                .filter(
                    ValidationRun.application_id == app.id,
                    ValidationRun.is_current.is_(True),
                )
                .order_by(ValidationRun.created_at.desc())
                .first()
            )
        if not current_run:
            return []

        # Get existing open/active exceptions for this application
        existing_active_exceptions = (
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

        active_by_check_id = {}
        for exc in existing_active_exceptions:
            try:
                check_ids = json.loads(exc.source_check_ids_json)
                for cid in check_ids:
                    active_by_check_id[cid] = exc
            except Exception:
                pass

        created_exceptions: List[OnboardingException] = []

        # Inspect current findings
        for finding in current_run.findings:
            if finding.is_stale:
                continue

            # A missing readable bank account must also create an actionable issue.
            if finding.status not in [
                ValidationStatusEnum.FAILED.value,
                ValidationStatusEnum.WARNING.value,
                ValidationStatusEnum.UNAVAILABLE.value,
            ] and not (
                finding.check_id == "B_BANK_ACCOUNT_NUM_MATCH"
                and finding.status == ValidationStatusEnum.UNVERIFIED.value
            ):
                continue

            check_id = finding.check_id

            # Deduplication: If an open exception already covers this check ID, update finding ref and skip
            if check_id in active_by_check_id:
                existing_exc = active_by_check_id[check_id]
                existing_exc.source_finding_id = finding.id
                continue

            mapped = self._map_finding_to_exception(app, finding)
            if not mapped:
                continue

            ref_no = f"EXC-{datetime.now(timezone.utc).year}-{secrets.token_hex(3).upper()}"
            new_exc = OnboardingException(
                reference_number=ref_no,
                organisation_id=app.organisation_id,
                application_id=app.id,
                vendor_id=app.vendor_id,
                category=mapped["category"],
                title=mapped["title"],
                description=mapped["description"],
                severity=mapped["severity"],
                source_check_ids_json=json.dumps([check_id]),
                source_finding_id=finding.id,
                related_document_id=mapped.get("related_document_id"),
                related_version_id=mapped.get("related_version_id"),
                related_field_name=mapped.get("related_field_name"),
                assigned_user_id=None,
                assigned_role=mapped["assigned_role"],
                status=mapped["initial_status"],
                vendor_action_instruction=mapped.get("vendor_action_instruction"),
                created_by_user_id=actor_user_id,
                created_by_role=actor_role,
            )
            self.db.add(new_exc)
            self.db.flush()

            # Record initial transition in history
            trans = ExceptionTransition(
                exception_id=new_exc.id,
                from_status="NONE",
                to_status=new_exc.status,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                reason="Generated from validation engine findings",
                notes=f"Source check: {check_id}",
            )
            self.db.add(trans)
            created_exceptions.append(new_exc)
            active_by_check_id[check_id] = new_exc

        self.db.commit()
        return created_exceptions

    def _map_finding_to_exception(self, app: Application, finding: ValidationFinding) -> Optional[dict]:
        cid = finding.check_id
        status = finding.status

        # 1. PAN Input & Constitution
        if cid == "A_PAN_FORMAT_AND_CONSTITUTION":
            return {
                "category": ExceptionCategoryEnum.PAN_MISMATCH.value,
                "title": "Permanent Account Number (PAN) Discrepancy",
                "description": finding.explanation,
                "severity": ExceptionSeverityEnum.CRITICAL.value,
                "related_field_name": "pan",
                "assigned_role": RoleEnum.VENDOR.value,
                "initial_status": ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
                "vendor_action_instruction": "Your PAN does not match your declared business constitution. Please provide a valid 10-character PAN or correct your business constitution.",
            }

        # 2. GSTIN Format & Mod-36 Checksum
        if cid == "A_GSTIN_FORMAT_AND_CHECKSUM":
            return {
                "category": ExceptionCategoryEnum.GST_MISMATCH.value,
                "title": "GSTIN Statutory Checksum / State Code Failure",
                "description": finding.explanation,
                "severity": ExceptionSeverityEnum.HIGH.value,
                "related_field_name": "gstin",
                "assigned_role": RoleEnum.VENDOR.value,
                "initial_status": ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
                "vendor_action_instruction": "The provided GSTIN failed statutory Mod-36 verification. Please enter the exact 15-character statutory GSTIN from your GST Registration Certificate.",
            }

        # 3. CIN / LLPIN
        if cid == "A_CIN_LLPIN_STRUCTURE":
            return {
                "category": ExceptionCategoryEnum.INVALID_IDENTIFIER_FORMAT.value,
                "title": "MCA Corporate Registration Identifier Invalid",
                "description": finding.explanation,
                "severity": ExceptionSeverityEnum.HIGH.value,
                "related_field_name": "cin_llpin",
                "assigned_role": RoleEnum.VENDOR.value,
                "initial_status": ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
                "vendor_action_instruction": "Please provide a valid 21-character MCA CIN (for Companies) or valid LLPIN (for LLPs) as issued on the Certificate of Incorporation.",
            }

        # 4. Bank IFSC Format
        if cid == "A_BANK_IFSC_STRUCTURE":
            return {
                "category": ExceptionCategoryEnum.BANK_DETAIL_MISMATCH.value,
                "title": "Invalid Bank IFSC Format",
                "description": finding.explanation,
                "severity": ExceptionSeverityEnum.HIGH.value,
                "related_field_name": "bank_ifsc",
                "assigned_role": RoleEnum.VENDOR.value,
                "initial_status": ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
                "vendor_action_instruction": "Please enter a valid 11-character RBI IFSC code printed on your bank cheque book or passbook.",
            }

        # 5. GSTIN Embedded PAN Mismatch
        if cid == "B_GSTIN_EMBEDDED_PAN_MATCH":
            return {
                "category": ExceptionCategoryEnum.GST_MISMATCH.value,
                "title": "GSTIN Embedded PAN Differs from Declared Business PAN",
                "description": finding.explanation,
                "severity": ExceptionSeverityEnum.CRITICAL.value,
                "related_field_name": "gstin",
                "assigned_role": RoleEnum.VENDOR.value,
                "initial_status": ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
                "vendor_action_instruction": "The PAN embedded within your GSTIN does not match your business PAN. If you operate multiple legal entities, please ensure the correct entity's PAN and GSTIN are provided.",
            }

        # 6. PAN Document Cross-Match
        if cid == "B_PAN_DOC_CROSS_MATCH":
            return {
                "category": ExceptionCategoryEnum.PAN_MISMATCH.value,
                "title": "PAN Document OCR Discrepancy",
                "description": finding.explanation,
                "severity": ExceptionSeverityEnum.CRITICAL.value,
                "related_document_id": finding.source_document_id,
                "related_version_id": finding.source_version_id,
                "related_field_name": "pan",
                "assigned_role": RoleEnum.VENDOR.value,
                "initial_status": ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
                "vendor_action_instruction": "The PAN extracted from your uploaded PAN card proof differs from the PAN entered in your profile. Please upload the correct PAN card document or correct the application profile.",
            }

        # 7. Name Matches
        if cid in ["B_NAME_PAN_DOC_MATCH", "B_NAME_GST_DOC_MATCH"]:
            if status == ValidationStatusEnum.WARNING.value:
                # Reviewer investigative issue, not direct vendor correction
                return {
                    "category": ExceptionCategoryEnum.LEGAL_NAME_MISMATCH.value,
                    "title": f"Name Match Review: {finding.check_name}",
                    "description": finding.explanation,
                    "severity": ExceptionSeverityEnum.MEDIUM.value,
                    "related_document_id": finding.source_document_id,
                    "related_version_id": finding.source_version_id,
                    "related_field_name": "legal_name",
                    "assigned_role": RoleEnum.REVIEWER.value,
                    "initial_status": ExceptionStatusEnum.UNDER_REVIEW.value,
                    "vendor_action_instruction": None,
                }
            else:
                return {
                    "category": ExceptionCategoryEnum.LEGAL_NAME_MISMATCH.value,
                    "title": "Significant Legal Name Discrepancy",
                    "description": finding.explanation,
                    "severity": ExceptionSeverityEnum.HIGH.value,
                    "related_document_id": finding.source_document_id,
                    "related_version_id": finding.source_version_id,
                    "related_field_name": "legal_name",
                    "assigned_role": RoleEnum.REVIEWER.value,
                    "initial_status": ExceptionStatusEnum.OPEN.value,
                    "vendor_action_instruction": "The legal name on your statutory document differs from the application name. Please clarify the discrepancy or upload an amended certificate.",
                }

        # 8. Bank Account Number / IFSC Match with Document
        if cid in ["B_BANK_ACCOUNT_NUM_MATCH", "B_BANK_IFSC_MATCH"]:
            unreadable_account = (
                cid == "B_BANK_ACCOUNT_NUM_MATCH"
                and status == ValidationStatusEnum.UNVERIFIED.value
            )
            return {
                "category": ExceptionCategoryEnum.BANK_DETAIL_MISMATCH.value,
                "title": "Bank Account Number Could Not Be Read" if unreadable_account else "Bank Account Details Differ from Cancelled Cheque / Statement",
                "description": finding.explanation,
                "severity": ExceptionSeverityEnum.CRITICAL.value,
                "related_document_id": finding.source_document_id,
                "related_version_id": finding.source_version_id,
                "related_field_name": "bank_account_number" if "ACCOUNT_NUM" in cid else "bank_ifsc",
                "assigned_role": RoleEnum.VENDOR.value,
                "initial_status": ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
                "vendor_action_instruction": "Please upload a clearer bank proof that shows the full account number." if unreadable_account else "The bank account details extracted from your bank document do not match the form input. Please re-check the account number/IFSC or upload a legible cancelled cheque.",
            }

        # 9. External Verification Provider Unavailable
        if status == ValidationStatusEnum.UNAVAILABLE.value:
            return {
                "category": ExceptionCategoryEnum.EXTERNAL_VERIFICATION_UNAVAILABLE.value,
                "title": f"Registry Service Unavailable: {finding.check_name}",
                "description": finding.explanation,
                "severity": ExceptionSeverityEnum.MEDIUM.value,
                "assigned_role": RoleEnum.PROCUREMENT_OFFICER.value,
                "initial_status": ExceptionStatusEnum.OPEN.value,
                "vendor_action_instruction": None,  # NOT asking vendor to resubmit
            }

        # 10. External Verification Failure
        if cid.startswith("C_") and status == ValidationStatusEnum.FAILED.value:
            return {
                "category": ExceptionCategoryEnum.EXTERNAL_VERIFICATION_FAILURE.value,
                "title": f"External Statutory Verification Failed: {finding.check_name}",
                "description": finding.explanation,
                "severity": ExceptionSeverityEnum.HIGH.value,
                "assigned_role": RoleEnum.REVIEWER.value,
                "initial_status": ExceptionStatusEnum.UNDER_REVIEW.value,
                "vendor_action_instruction": None,
            }

        # 11. Potential Duplicate Vendor
        if cid == "D_DUPLICATE_DETECTION_CHECK":
            return {
                "category": ExceptionCategoryEnum.POTENTIAL_DUPLICATE_VENDOR.value,
                "title": "Potential Duplicate Vendor Candidate in Organisation",
                "description": finding.explanation,
                "severity": ExceptionSeverityEnum.HIGH.value,
                "assigned_role": RoleEnum.REVIEWER.value,
                "initial_status": ExceptionStatusEnum.UNDER_REVIEW.value,
                "vendor_action_instruction": None,  # Strictly internal investigation
            }

        return None
