import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.validation import (
    ValidationRun,
    ValidationFinding,
    ExternalVerificationRecord,
    DuplicateSignal,
    ValidationStatusEnum,
    ValidationSeverityEnum,
    ValidationLayerEnum,
    VerificationStatusEnum,
)
from app.models.audit import AuditEvent
from app.services.validation.layer_a_input import run_layer_a_checks
from app.services.validation.layer_b_consistency import run_layer_b_checks
from app.services.validation.duplicate_detector import detect_duplicates_for_application
from app.services.validation.name_matching import compare_names, MatchTier
from app.services.verification.simulated import (
    SimulatedPanAdapter,
    SimulatedGstAdapter,
    SimulatedMcaAdapter,
    SimulatedUdyamAdapter,
    SimulatedBankAccountAdapter,
    mask_id,
)

logger = logging.getLogger(__name__)


def map_verification_status(verif_status: str) -> str:
    if verif_status == VerificationStatusEnum.VERIFIED.value:
        return ValidationStatusEnum.PASSED.value
    elif verif_status == VerificationStatusEnum.FAILED.value:
        return ValidationStatusEnum.FAILED.value
    elif verif_status == VerificationStatusEnum.UNAVAILABLE.value:
        return ValidationStatusEnum.UNAVAILABLE.value
    return ValidationStatusEnum.UNVERIFIED.value


class ValidationOrchestrator:
    """
    Orchestrates deterministic validation across Layers A, B, C, and D.
    Supports change-aware revalidation, stale marking, and audit logging.
    """

    def __init__(self, db: Session):
        self.db = db
        self.pan_adapter = SimulatedPanAdapter()
        self.gst_adapter = SimulatedGstAdapter()
        self.mca_adapter = SimulatedMcaAdapter()
        self.udyam_adapter = SimulatedUdyamAdapter()
        self.bank_adapter = SimulatedBankAccountAdapter()

    def run_layer_c_verifications(self, app: Application) -> List[Dict[str, Any]]:
        """
        Executes simulated authoritative external verifications, records results in
        external_verification_records, and outputs Layer C validation findings.
        """
        findings: List[Dict[str, Any]] = []

        # 1. PAN External Verification
        if app.pan:
            res = self.pan_adapter.verify(app.pan, {"declared_name": app.legal_name})
            rec = ExternalVerificationRecord(
                application_id=app.id,
                organisation_id=app.organisation_id,
                verification_type=res.verification_type,
                provider_name=res.provider_name,
                request_id=res.request_id,
                submitted_identifier=res.submitted_identifier,
                status=res.status.value,
                is_simulated=res.is_simulated,
                returned_attributes_json=json.dumps(res.returned_attributes),
                reason=res.reason,
                duration_ms=res.duration_ms,
            )
            self.db.add(rec)

            val_status = map_verification_status(res.status.value)
            sev = ValidationSeverityEnum.CRITICAL.value
            taxpayer_name = res.returned_attributes.get("taxpayer_name") or ""
            
            # Cross check name if verified
            if val_status == ValidationStatusEnum.PASSED.value and taxpayer_name:
                tier, score, reason_txt = compare_names(app.legal_name, taxpayer_name, entity_type=app.constitution)
                if tier == MatchTier.PROBABLE_MATCH:
                    val_status = ValidationStatusEnum.WARNING.value
                    sev = ValidationSeverityEnum.MEDIUM.value
                    explanation = f"Simulated PAN registry verified active status. Taxpayer name '{taxpayer_name}' is a probable match ({score:.0%}) with application legal name '{app.legal_name}': {reason_txt}."
                elif tier == MatchTier.SIGNIFICANT_MISMATCH:
                    val_status = ValidationStatusEnum.FAILED.value
                    sev = ValidationSeverityEnum.HIGH.value
                    explanation = f"Simulated PAN verified, but registered taxpayer name '{taxpayer_name}' significantly mismatches application name '{app.legal_name}'."
                else:
                    explanation = f"Simulated PAN verified active with Income Tax Department sandbox. Registered taxpayer: '{taxpayer_name}'."
            elif val_status == ValidationStatusEnum.UNAVAILABLE.value:
                sev = ValidationSeverityEnum.MEDIUM.value
                explanation = f"Simulated external PAN registry was temporarily unavailable: {res.reason}. This is an infrastructure availability flag, not a verification failure."
            elif val_status == ValidationStatusEnum.PASSED.value:
                explanation = "Simulated PAN registry reported the PAN as active. No registered taxpayer name was returned for comparison."
            else:
                explanation = f"Simulated PAN verification failed: {res.reason}."

            findings.append({
                "check_id": "C_PAN_EXTERNAL_VERIFICATION",
                "layer": ValidationLayerEnum.LAYER_C_EXTERNAL.value,
                "check_name": "PAN Registry Verification (Simulated ITD)",
                "status": val_status,
                "severity": sev,
                "submitted_value": mask_id(app.pan),
                "extracted_value": None,
                "external_value": taxpayer_name or ("UNAVAILABLE" if val_status == ValidationStatusEnum.UNAVAILABLE.value else ("VERIFIED; name not returned" if val_status == ValidationStatusEnum.PASSED.value else "INVALID")),
                "evidence": f"Provider: {res.provider_name} | ReqId: {res.request_id} | Status: {res.status.value}",
                "explanation": f"[SIMULATED] {explanation}",
                "recommended_action": "Retry verification later when provider recovers." if val_status == ValidationStatusEnum.UNAVAILABLE.value else ("No action required." if val_status == ValidationStatusEnum.PASSED.value else "Verify PAN details with vendor."),
            })

        # 2. GSTIN External Verification
        if app.is_gst_registered and app.gstin:
            res = self.gst_adapter.verify(app.gstin, {"declared_name": app.legal_name})
            rec = ExternalVerificationRecord(
                application_id=app.id,
                organisation_id=app.organisation_id,
                verification_type=res.verification_type,
                provider_name=res.provider_name,
                request_id=res.request_id,
                submitted_identifier=res.submitted_identifier,
                status=res.status.value,
                is_simulated=res.is_simulated,
                returned_attributes_json=json.dumps(res.returned_attributes),
                reason=res.reason,
                duration_ms=res.duration_ms,
            )
            self.db.add(rec)

            val_status = map_verification_status(res.status.value)
            sev = ValidationSeverityEnum.HIGH.value
            legal_name = res.returned_attributes.get("legal_name") or ""
            trade_name = res.returned_attributes.get("trade_name") or ""
            reg_status = res.returned_attributes.get("gst_status") or ""

            if val_status == ValidationStatusEnum.PASSED.value:
                explanation = f"Simulated GSTN verified active. Legal: '{legal_name}', Trade: '{trade_name}', Status: '{reg_status}'."
            elif val_status == ValidationStatusEnum.UNAVAILABLE.value:
                sev = ValidationSeverityEnum.MEDIUM.value
                explanation = f"Simulated GST portal temporarily unavailable: {res.reason}."
            else:
                explanation = f"Simulated GSTN verification failed: {res.reason}."

            findings.append({
                "check_id": "C_GST_EXTERNAL_VERIFICATION",
                "layer": ValidationLayerEnum.LAYER_C_EXTERNAL.value,
                "check_name": "GSTN Portal Verification (Simulated GSTN)",
                "status": val_status,
                "severity": sev,
                "submitted_value": mask_id(app.gstin),
                "extracted_value": None,
                "external_value": f"{legal_name} ({reg_status})" if legal_name else ("UNAVAILABLE" if val_status == ValidationStatusEnum.UNAVAILABLE.value else "INVALID"),
                "evidence": f"Provider: {res.provider_name} | ReqId: {res.request_id} | Status: {res.status.value}",
                "explanation": f"[SIMULATED] {explanation}",
                "recommended_action": "Retry verification later." if val_status == ValidationStatusEnum.UNAVAILABLE.value else ("No action required." if val_status == ValidationStatusEnum.PASSED.value else "Review GST registration certificate."),
            })

        # 3. MCA External Verification
        const_upper = (app.constitution or "").upper()
        if const_upper in ["PVT_LTD", "PUB_LTD", "LLP"] and app.cin_llpin:
            res = self.mca_adapter.verify(app.cin_llpin, {"constitution": const_upper})
            rec = ExternalVerificationRecord(
                application_id=app.id,
                organisation_id=app.organisation_id,
                verification_type=res.verification_type,
                provider_name=res.provider_name,
                request_id=res.request_id,
                submitted_identifier=res.submitted_identifier,
                status=res.status.value,
                is_simulated=res.is_simulated,
                returned_attributes_json=json.dumps(res.returned_attributes),
                reason=res.reason,
                duration_ms=res.duration_ms,
            )
            self.db.add(rec)

            val_status = map_verification_status(res.status.value)
            sev = ValidationSeverityEnum.HIGH.value
            comp_name = res.returned_attributes.get("company_name") or ""
            comp_status = res.returned_attributes.get("company_status") or ""

            if val_status == ValidationStatusEnum.PASSED.value:
                explanation = f"Simulated MCA registry confirmed active corporate entity '{comp_name}' (Status: '{comp_status}')."
            elif val_status == ValidationStatusEnum.UNAVAILABLE.value:
                sev = ValidationSeverityEnum.MEDIUM.value
                explanation = f"Simulated MCA registry service unavailable: {res.reason}."
            elif val_status == ValidationStatusEnum.UNVERIFIED.value:
                sev = ValidationSeverityEnum.MEDIUM.value
                explanation = (
                    "The limited MCA sample registry returned no record for this identifier. "
                    "This demo result cannot confirm whether the entity is officially registered."
                )
            else:
                explanation = f"Simulated MCA registry verification failed: {res.reason}."

            findings.append({
                "check_id": "C_MCA_EXTERNAL_VERIFICATION",
                "layer": ValidationLayerEnum.LAYER_C_EXTERNAL.value,
                "check_name": "MCA Registry Verification (Simulated MCA-21)",
                "status": val_status,
                "severity": sev,
                "submitted_value": app.cin_llpin,
                "extracted_value": None,
                "external_value": f"{comp_name} ({comp_status})" if comp_name else (
                    "UNAVAILABLE" if val_status == ValidationStatusEnum.UNAVAILABLE.value else
                    "NO SAMPLE MATCH" if val_status == ValidationStatusEnum.UNVERIFIED.value else "INVALID"
                ),
                "evidence": f"Provider: {res.provider_name} | ReqId: {res.request_id} | Status: {res.status.value}",
                "explanation": f"[SIMULATED] {explanation}",
                "recommended_action": (
                    "Compare the CIN/LLPIN with the incorporation documents or verify through an official source."
                    if val_status == ValidationStatusEnum.UNVERIFIED.value else
                    "Review incorporation details." if val_status != ValidationStatusEnum.PASSED.value else
                    "No action required."
                ),
            })

        # 4. Bank Account Penny-Drop Verification
        if app.bank_account_number and app.bank_ifsc:
            res = self.bank_adapter.verify(
                app.bank_account_number,
                {"ifsc": app.bank_ifsc, "account_holder_name": app.bank_account_holder_name or app.legal_name},
            )
            rec = ExternalVerificationRecord(
                application_id=app.id,
                organisation_id=app.organisation_id,
                verification_type=res.verification_type,
                provider_name=res.provider_name,
                request_id=res.request_id,
                submitted_identifier=res.submitted_identifier,
                status=res.status.value,
                is_simulated=res.is_simulated,
                returned_attributes_json=json.dumps(res.returned_attributes),
                reason=res.reason,
                duration_ms=res.duration_ms,
            )
            self.db.add(rec)

            val_status = map_verification_status(res.status.value)
            sev = ValidationSeverityEnum.CRITICAL.value
            ben_name = res.returned_attributes.get("registered_name") or ""
            bank_status = res.returned_attributes.get("account_status") or ""

            if val_status == ValidationStatusEnum.PASSED.value:
                # Compare registered name with application holder name
                target_holder = app.bank_account_holder_name or app.legal_name
                tier, score, reason_txt = compare_names(target_holder, ben_name, entity_type=app.constitution)
                if tier == MatchTier.PROBABLE_MATCH:
                    val_status = ValidationStatusEnum.WARNING.value
                    sev = ValidationSeverityEnum.MEDIUM.value
                    explanation = f"Simulated penny-drop succeeded. Bank registered beneficiary '{ben_name}' is a probable match with '{target_holder}': {reason_txt}."
                elif tier == MatchTier.SIGNIFICANT_MISMATCH:
                    val_status = ValidationStatusEnum.FAILED.value
                    sev = ValidationSeverityEnum.HIGH.value
                    explanation = f"Simulated penny-drop succeeded, but registered beneficiary name '{ben_name}' does not match declared holder '{target_holder}'."
                else:
                    explanation = f"Simulated penny-drop successful. Active bank account verified. Beneficiary: '{ben_name}'."
            elif val_status == ValidationStatusEnum.UNAVAILABLE.value:
                sev = ValidationSeverityEnum.MEDIUM.value
                explanation = f"Simulated banking payment gateway timeout: {res.reason}."
            else:
                explanation = f"Simulated penny-drop failed: {res.reason}."

            findings.append({
                "check_id": "C_BANK_PENNY_DROP_VERIFICATION",
                "layer": ValidationLayerEnum.LAYER_C_EXTERNAL.value,
                "check_name": "Bank Account Penny-Drop Verification (Simulated NPCI/IMPS)",
                "status": val_status,
                "severity": sev,
                "submitted_value": f"{mask_id(app.bank_account_number)} ({app.bank_ifsc})",
                "extracted_value": None,
                "external_value": ben_name or ("UNAVAILABLE" if val_status == ValidationStatusEnum.UNAVAILABLE.value else "INVALID"),
                "evidence": f"Provider: {res.provider_name} | ReqId: {res.request_id} | Status: {res.status.value}",
                "explanation": f"[SIMULATED] {explanation}",
                "recommended_action": "Verify bank passbook / cancelled cheque and re-verify." if val_status != ValidationStatusEnum.PASSED.value else "No action required.",
            })

        # 5. Udyam MSME External Verification
        if app.is_udyam_registered and app.udyam_number:
            res = self.udyam_adapter.verify(app.udyam_number, {"declared_name": app.legal_name})
            rec = ExternalVerificationRecord(
                application_id=app.id,
                organisation_id=app.organisation_id,
                verification_type=res.verification_type,
                provider_name=res.provider_name,
                request_id=res.request_id,
                submitted_identifier=res.submitted_identifier,
                status=res.status.value,
                is_simulated=res.is_simulated,
                returned_attributes_json=json.dumps(res.returned_attributes),
                reason=res.reason,
                duration_ms=res.duration_ms,
            )
            self.db.add(rec)

            val_status = map_verification_status(res.status.value)
            sev = ValidationSeverityEnum.MEDIUM.value
            ent_name = res.returned_attributes.get("enterprise_name") or ""
            ent_type = res.returned_attributes.get("enterprise_type") or ""

            if val_status == ValidationStatusEnum.PASSED.value:
                explanation = f"Simulated Udyam portal verified active registration for '{ent_name}' (Classification: {ent_type})."
            elif val_status == ValidationStatusEnum.UNAVAILABLE.value:
                sev = ValidationSeverityEnum.MEDIUM.value
                explanation = f"Simulated Udyam portal unavailable: {res.reason}."
            else:
                explanation = f"Simulated Udyam verification failed: {res.reason}."

            findings.append({
                "check_id": "C_UDYAM_EXTERNAL_VERIFICATION",
                "layer": ValidationLayerEnum.LAYER_C_EXTERNAL.value,
                "check_name": "MSME Udyam Portal Verification (Simulated MSME Registry)",
                "status": val_status,
                "severity": sev,
                "submitted_value": app.udyam_number,
                "extracted_value": None,
                "external_value": f"{ent_name} ({ent_type})" if ent_name else ("UNAVAILABLE" if val_status == ValidationStatusEnum.UNAVAILABLE.value else "INVALID"),
                "evidence": f"Provider: {res.provider_name} | ReqId: {res.request_id} | Status: {res.status.value}",
                "explanation": f"[SIMULATED] {explanation}",
                "recommended_action": "Review Udyam certificate." if val_status != ValidationStatusEnum.PASSED.value else "No action required.",
            })

        return findings

    def run_full_validation(
        self,
        application_id: str,
        user_id: Optional[str] = None,
        run_type: str = "FULL",
        trigger_reason: Optional[str] = "Manual validation trigger",
    ) -> ValidationRun:
        """
        Executes a complete validation run across Layers A, B, C, and D.
        Invalidates previous runs, persists findings, records duplicate signals,
        and creates an immutable audit event.
        """
        app = self.db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found")

        # 1. Mark previous active runs as non-current
        previous_runs = (
            self.db.query(ValidationRun)
            .filter(ValidationRun.application_id == app.id, ValidationRun.is_current.is_(True))
            .all()
        )

        # 2. Initialize new ValidationRun
        new_run = ValidationRun(
            application_id=app.id,
            organisation_id=app.organisation_id,
            run_type=run_type,
            status="IN_PROGRESS",
            is_current=False,
            triggered_by_user_id=user_id,
            trigger_reason=trigger_reason,
        )
        self.db.add(new_run)
        self.db.flush()

        # 3. Execute Layers
        all_finding_dicts: List[Dict[str, Any]] = []

        # Layer A
        layer_a_findings = run_layer_a_checks(app)
        all_finding_dicts.extend(layer_a_findings)

        # Layer B
        layer_b_findings = run_layer_b_checks(app)
        all_finding_dicts.extend(layer_b_findings)

        # Layer C
        layer_c_findings = self.run_layer_c_verifications(app)
        all_finding_dicts.extend(layer_c_findings)

        # Layer D: Duplicate Detection
        dup_signals, layer_d_findings = detect_duplicates_for_application(self.db, app)
        for sig in dup_signals:
            self.db.add(sig)
        all_finding_dicts.extend(layer_d_findings)

        # 4. Instantiate and persist ValidationFinding records
        passed = 0
        failed = 0
        warning = 0
        unverified = 0
        unavailable = 0

        for f_data in all_finding_dicts:
            status_val = f_data.get("status")
            if status_val == ValidationStatusEnum.PASSED.value:
                passed += 1
            elif status_val == ValidationStatusEnum.FAILED.value:
                failed += 1
            elif status_val == ValidationStatusEnum.WARNING.value:
                warning += 1
            elif status_val == ValidationStatusEnum.UNVERIFIED.value:
                unverified += 1
            elif status_val == ValidationStatusEnum.UNAVAILABLE.value:
                unavailable += 1

            finding = ValidationFinding(
                validation_run_id=new_run.id,
                application_id=app.id,
                check_id=f_data["check_id"],
                layer=f_data["layer"],
                check_name=f_data["check_name"],
                status=f_data["status"],
                severity=f_data["severity"],
                source_document_id=f_data.get("source_document_id"),
                source_version_id=f_data.get("source_version_id"),
                submitted_value=f_data.get("submitted_value"),
                extracted_value=f_data.get("extracted_value"),
                external_value=f_data.get("external_value"),
                evidence=f_data.get("evidence"),
                explanation=f_data["explanation"],
                recommended_action=f_data.get("recommended_action"),
                is_stale=False,
            )
            self.db.add(finding)

        # 5. Finalize ValidationRun summary and counts
        new_run.status = "COMPLETED"
        new_run.passed_count = passed
        new_run.failed_count = failed
        new_run.warning_count = warning
        new_run.unverified_count = unverified
        new_run.unavailable_count = unavailable
        new_run.summary = (
            f"Validation completed: {passed} passed, {failed} failed, {warning} warnings, "
            f"{unverified} unverified, {unavailable} unavailable."
        )

        # 6. Immutable Audit Log Event
        audit_event = AuditEvent(
            organisation_id=app.organisation_id,
            application_id=app.id,
            actor_user_id=user_id,
            actor_role="SYSTEM" if not user_id else "USER",
            event_type="VALIDATION_RUN_COMPLETED",
            entity_type="VALIDATION_RUN",
            entity_id=new_run.id,
            details_json=json.dumps({
                "run_id": new_run.id,
                "run_type": run_type,
                "passed": passed,
                "failed": failed,
                "warnings": warning,
                "unverified": unverified,
                "unavailable": unavailable,
                "duplicate_signals_count": len(dup_signals),
            }),
        )
        self.db.add(audit_event)

        if dup_signals:
            dup_audit = AuditEvent(
                organisation_id=app.organisation_id,
                application_id=app.id,
                actor_user_id=user_id,
                actor_role="SYSTEM",
                event_type="DUPLICATE_SIGNAL_DETECTED",
                entity_type="DUPLICATE_SIGNAL",
                entity_id=dup_signals[0].id,
                details_json=json.dumps({
                    "signals_count": len(dup_signals),
                    "candidates": [s.candidate_application_id for s in dup_signals],
                }),
            )
            self.db.add(dup_audit)

        self.db.flush()

        # 7. Automatically synchronize non-duplicate exceptions for actionable findings
        try:
            from app.services.exceptions.generator import ExceptionGenerator
            ExceptionGenerator(self.db).sync_exceptions_for_application(
                application_id=app.id,
                actor_user_id=user_id,
                actor_role="SYSTEM" if not user_id else "USER",
                validation_run=new_run,
                commit=False,
            )
        except Exception as e:
            logger.exception(f"Error syncing exceptions after validation run: {e}")
            self.db.rollback()
            raise

        for prev in previous_runs:
            prev.is_current = False
        new_run.is_current = True
        self.db.commit()
        self.db.refresh(new_run)
        return new_run

    def mark_stale_findings_for_document(self, document_id: str, reason: str = "Document re-uploaded") -> int:
        """
        Marks any active findings that depended on this document as stale.
        """
        findings = (
            self.db.query(ValidationFinding)
            .join(ValidationRun, ValidationFinding.validation_run_id == ValidationRun.id)
            .filter(
                ValidationFinding.source_document_id == document_id,
                ValidationRun.is_current.is_(True),
                ValidationFinding.is_stale.is_(False),
            )
            .all()
        )
        for f in findings:
            f.is_stale = True
            f.stale_reason = reason

        self.db.commit()
        return len(findings)
