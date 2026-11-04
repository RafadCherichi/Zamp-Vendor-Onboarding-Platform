import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import or_, and_, func, desc, asc
from sqlalchemy.orm import Session, joinedload

from app.models.application import Application, ApplicationStatusEnum
from app.models.vendor import Vendor
from app.models.user import User
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.document import Document, DocumentVersion
from app.models.extraction import DocumentExtractionResult, ExtractedField
from app.models.exception import (
    OnboardingException,
    ExceptionStatusEnum,
    ExceptionSeverityEnum,
    FieldCorrectionRecord,
)
from app.models.validation import (
    ValidationRun,
    ValidationFinding,
    ValidationStatusEnum,
    ValidationLayerEnum,
    ExternalVerificationRecord,
    DuplicateSignal,
)
from app.models.audit import AuditEvent
from app.services.review.decision_service import ReviewerDecisionService


def mask_identifier(field_name: str, val: Optional[str]) -> Optional[str]:
    if not val:
        return val
    s = str(val).strip()
    if "pan" in field_name.lower() and len(s) >= 5:
        return s[:2] + "*****" + s[-2:]
    if "bank" in field_name.lower() or "account" in field_name.lower():
        if len(s) <= 4:
            return "****"
        return ("*" * (len(s) - 4)) + s[-4:]
    return s


class QueueAndDashboardService:
    """
    High-performance, organization-scoped queries for procurement dashboards,
    application queues, and comprehensive evidence inspection.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_metrics(self, organisation_id: str) -> Dict[str, Any]:
        """
        Derives operational dashboard metrics strictly from persisted database records.
        """
        # Applications query
        apps_query = self.db.query(Application).filter(Application.organisation_id == organisation_id)
        all_apps = apps_query.all()
        total_apps = len(all_apps)

        in_progress_count = sum(1 for a in all_apps if a.status in [ApplicationStatusEnum.DRAFT.value, ApplicationStatusEnum.IN_PROGRESS.value])
        awaiting_vendor_count = sum(1 for a in all_apps if a.status == ApplicationStatusEnum.ACTION_REQUIRED.value)
        submitted_count = sum(1 for a in all_apps if a.status == ApplicationStatusEnum.SUBMITTED.value)
        under_review_count = sum(1 for a in all_apps if a.status == ApplicationStatusEnum.UNDER_REVIEW.value)
        approved_count = sum(1 for a in all_apps if a.status == ApplicationStatusEnum.APPROVED.value)
        rejected_count = sum(1 for a in all_apps if a.status == ApplicationStatusEnum.REJECTED.value)
        escalated_count = sum(1 for a in all_apps if a.status == ApplicationStatusEnum.ESCALATED.value)

        awaiting_review_count = submitted_count + under_review_count + escalated_count

        # Exceptions query
        exceptions_query = self.db.query(OnboardingException).filter(OnboardingException.organisation_id == organisation_id)
        all_exceptions = exceptions_query.all()

        open_exceptions = [
            e for e in all_exceptions
            if e.status not in [ExceptionStatusEnum.RESOLVED.value, ExceptionStatusEnum.CLOSED.value]
        ]
        open_exceptions_count = len(open_exceptions)
        high_severity_exceptions_count = sum(
            1 for e in open_exceptions
            if e.severity in [ExceptionSeverityEnum.CRITICAL.value, ExceptionSeverityEnum.HIGH.value]
        )

        # Ready for approval count: submitted or under_review applications with zero open exceptions
        app_open_exc_map: Dict[str, int] = {}
        for e in open_exceptions:
            app_open_exc_map[e.application_id] = app_open_exc_map.get(e.application_id, 0) + 1

        ready_for_approval_count = sum(
            1 for a in all_apps
            if a.status in [ApplicationStatusEnum.SUBMITTED.value, ApplicationStatusEnum.UNDER_REVIEW.value]
            and app_open_exc_map.get(a.id, 0) == 0
        )

        # Extended review wait: submitted > 3 days ago still awaiting review
        three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
        stale_review_count = sum(
            1 for a in all_apps
            if a.status in [ApplicationStatusEnum.SUBMITTED.value, ApplicationStatusEnum.UNDER_REVIEW.value]
            and a.submitted_at and (a.submitted_at.tzinfo is not None and a.submitted_at <= three_days_ago)
        )

        # Processing count: applications having documents in processing
        processing_count = sum(
            1 for a in all_apps
            if any(d.status == "PENDING" for d in a.documents)
        )

        # Exception category breakdown
        cat_breakdown: Dict[str, int] = {}
        for e in open_exceptions:
            cat_breakdown[e.category] = cat_breakdown.get(e.category, 0) + 1

        # Exception severity breakdown
        sev_breakdown: Dict[str, int] = {}
        for e in open_exceptions:
            sev_breakdown[e.severity] = sev_breakdown.get(e.severity, 0) + 1

        # Recent application activity (last 8 audit events)
        recent_audits = (
            self.db.query(AuditEvent)
            .filter(AuditEvent.organisation_id == organisation_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(8)
            .all()
        )
        activity_list = []
        for audit in recent_audits:
            details = {}
            if audit.details_json:
                try:
                    details = json.loads(audit.details_json)
                except Exception:
                    pass
            activity_list.append({
                "id": audit.id,
                "event_type": audit.event_type,
                "actor_role": audit.actor_role or "SYSTEM",
                "application_id": audit.application_id,
                "details": details,
                "created_at": audit.created_at.isoformat() if audit.created_at else None,
            })

        # Recently submitted applications (last 5)
        recent_submits = (
            self.db.query(Application)
            .filter(
                Application.organisation_id == organisation_id,
                Application.status.notin_([ApplicationStatusEnum.DRAFT.value, ApplicationStatusEnum.IN_PROGRESS.value]),
            )
            .order_by(Application.submitted_at.desc().nullslast(), Application.updated_at.desc())
            .limit(5)
            .all()
        )
        recent_submit_list = [
            {
                "id": a.id,
                "reference_number": a.reference_number,
                "legal_name": a.legal_name,
                "constitution": a.constitution,
                "status": a.status,
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
                "open_exceptions_count": app_open_exc_map.get(a.id, 0),
            }
            for a in recent_submits
        ]

        return {
            "total_applications": total_apps,
            "in_progress_count": in_progress_count,
            "awaiting_vendor_count": awaiting_vendor_count,
            "processing_count": processing_count,
            "awaiting_review_count": awaiting_review_count,
            "ready_for_approval_count": ready_for_approval_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "escalated_count": escalated_count,
            "open_exceptions_count": open_exceptions_count,
            "high_severity_exceptions_count": high_severity_exceptions_count,
            "stale_review_count": stale_review_count,
            "exception_breakdown_by_category": cat_breakdown,
            "exception_breakdown_by_severity": sev_breakdown,
            "recent_activity": activity_list,
            "recently_submitted": recent_submit_list,
        }

    def query_queue(
        self,
        organisation_id: str,
        search: Optional[str] = None,
        status: Optional[str] = None,
        exception_severity: Optional[str] = None,
        exception_category: Optional[str] = None,
        assigned_reviewer_id: Optional[str] = None,
        unassigned_only: bool = False,
        ready_for_approval_only: bool = False,
        submitted_from: Optional[datetime] = None,
        submitted_to: Optional[datetime] = None,
        sort_by: str = "submitted_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """
        Paginated, multi-filtered query for internal reviewer and procurement queues.
        """
        query = self.db.query(Application).filter(Application.organisation_id == organisation_id)

        # 1. Search term (matches vendor legal name, trade name, reference number, contact email)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Application.legal_name.ilike(term),
                    Application.trade_name.ilike(term),
                    Application.reference_number.ilike(term),
                    Application.contact_email.ilike(term),
                )
            )

        # 2. Lifecycle Status filter
        if status and status.strip() and status != "ALL":
            query = query.filter(Application.status == status.strip())

        # 3. Assigned Reviewer filter
        if unassigned_only:
            query = query.filter(Application.assigned_reviewer_id.is_(None))
        elif assigned_reviewer_id and assigned_reviewer_id != "ALL":
            query = query.filter(Application.assigned_reviewer_id == assigned_reviewer_id)

        # 4. Date ranges
        if submitted_from:
            query = query.filter(Application.submitted_at >= submitted_from)
        if submitted_to:
            query = query.filter(Application.submitted_at <= submitted_to)

        # 5. Exception Severity / Category filtering
        if (exception_severity and exception_severity != "ALL") or (exception_category and exception_category != "ALL"):
            exc_filter = [
                OnboardingException.status.notin_([
                    ExceptionStatusEnum.RESOLVED.value,
                    ExceptionStatusEnum.CLOSED.value,
                ])
            ]
            if exception_severity and exception_severity != "ALL":
                exc_filter.append(OnboardingException.severity == exception_severity)
            if exception_category and exception_category != "ALL":
                exc_filter.append(OnboardingException.category == exception_category)

            matching_app_ids = (
                self.db.query(OnboardingException.application_id)
                .filter(and_(*exc_filter))
                .distinct()
                .subquery()
            )
            query = query.filter(Application.id.in_(matching_app_ids))

        # 6. Ready for approval filter (has 0 active open exceptions and status in SUBMITTED or UNDER_REVIEW)
        if ready_for_approval_only:
            active_exc_app_ids = (
                self.db.query(OnboardingException.application_id)
                .filter(
                    OnboardingException.status.notin_([
                        ExceptionStatusEnum.RESOLVED.value,
                        ExceptionStatusEnum.CLOSED.value,
                    ])
                )
                .distinct()
                .subquery()
            )
            query = query.filter(
                Application.status.in_([
                    ApplicationStatusEnum.SUBMITTED.value,
                    ApplicationStatusEnum.UNDER_REVIEW.value,
                ]),
                Application.id.notin_(active_exc_app_ids),
            )

        # Count total
        total = query.count()

        # 7. Sorting
        sort_col = getattr(Application, sort_by, Application.submitted_at)
        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_col).nullslast())
        else:
            query = query.order_by(desc(sort_col).nullslast())

        # 8. Pagination
        offset = max(0, (page - 1) * page_size)
        applications = query.offset(offset).limit(page_size).all()

        # Batch load active exceptions and reviewer names for items
        app_ids = [a.id for a in applications]
        exceptions = (
            self.db.query(OnboardingException)
            .filter(
                OnboardingException.application_id.in_(app_ids),
                OnboardingException.status.notin_([
                    ExceptionStatusEnum.RESOLVED.value,
                    ExceptionStatusEnum.CLOSED.value,
                ]),
            )
            .all()
        )
        exc_by_app: Dict[str, List[OnboardingException]] = {}
        for e in exceptions:
            exc_by_app.setdefault(e.application_id, []).append(e)

        reviewer_ids = list({a.assigned_reviewer_id for a in applications if a.assigned_reviewer_id})
        reviewers = (
            self.db.query(User)
            .filter(User.id.in_(reviewer_ids))
            .all()
        ) if reviewer_ids else []
        reviewer_map = {r.id: r.full_name for r in reviewers}

        items = []
        for app in applications:
            app_excs = exc_by_app.get(app.id, [])
            open_count = len(app_excs)
            crit_count = sum(1 for e in app_excs if e.severity in ["CRITICAL", "HIGH"])
            is_ready = (
                app.status in [ApplicationStatusEnum.SUBMITTED.value, ApplicationStatusEnum.UNDER_REVIEW.value]
                and open_count == 0
            )

            items.append({
                "id": app.id,
                "reference_number": app.reference_number,
                "legal_name": app.legal_name,
                "trade_name": app.trade_name,
                "constitution": app.constitution,
                "status": app.status,
                "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
                "created_at": app.created_at.isoformat() if app.created_at else None,
                "updated_at": app.updated_at.isoformat() if app.updated_at else None,
                "assigned_reviewer_id": app.assigned_reviewer_id,
                "assigned_reviewer_name": reviewer_map.get(app.assigned_reviewer_id) if app.assigned_reviewer_id else None,
                "open_exceptions_count": open_count,
                "critical_exceptions_count": crit_count,
                "ready_for_approval": is_ready,
            })

        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "items": items,
        }

    def get_application_details_comprehensive(
        self,
        application_id: str,
        actor_member: OrganisationMember,
    ) -> Dict[str, Any]:
        """
        Constructs the comprehensive 7-section evidence workspace payload with security sanitization.
        """
        app = (
            self.db.query(Application)
            .filter(
                Application.id == application_id,
                Application.organisation_id == actor_member.organisation_id,
            )
            .first()
        )
        if not app:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

        is_vendor = (actor_member.role == RoleEnum.VENDOR.value)
        decision_service = ReviewerDecisionService(self.db)
        is_eligible, blocking_reasons = decision_service.check_approval_eligibility(app)

        # 1. Overview Section
        overview = {
            "id": app.id,
            "reference_number": app.reference_number,
            "legal_name": app.legal_name,
            "trade_name": app.trade_name,
            "constitution": app.constitution,
            "status": app.status,
            "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
            "assigned_reviewer_id": app.assigned_reviewer_id,
            "assigned_reviewer_name": app.assigned_reviewer.full_name if app.assigned_reviewer else None,
            "assigned_at": app.assigned_at.isoformat() if app.assigned_at else None,
            "reviewed_by_name": app.reviewed_by.full_name if app.reviewed_by else None,
            "reviewed_at": app.reviewed_at.isoformat() if app.reviewed_at else None,
            "decision_notes": app.decision_notes,
            "rejection_reason": app.rejection_reason,
            "is_approval_eligible": is_eligible,
            "blocking_reasons": blocking_reasons,
        }

        # 2. Business Details (Mask sensitive compliance fields)
        business_details = {
            "identity": {
                "legal_name": app.legal_name,
                "trade_name": app.trade_name,
                "constitution": app.constitution,
                "date_of_establishment": app.date_of_establishment,
                "registered_address": app.registered_address,
                "operating_address": app.operating_address,
                "city": app.city,
                "state": app.state,
                "pincode": app.pincode,
            },
            "tax_and_registrations": {
                "pan": mask_identifier("pan", app.pan),
                "is_gst_registered": app.is_gst_registered,
                "gstin": app.gstin,
                "is_udyam_registered": app.is_udyam_registered,
                "udyam_number": app.udyam_number,
                "cin_llpin": app.cin_llpin,
            },
            "contact": {
                "contact_name": app.contact_name,
                "contact_designation": app.contact_designation,
                "contact_email": app.contact_email,
                "contact_mobile": app.contact_mobile,
                "authorised_signatory_name": app.authorised_signatory_name,
            },
            "banking": {
                "bank_account_holder_name": app.bank_account_holder_name,
                "bank_account_number": mask_identifier("bank", app.bank_account_number),
                "bank_ifsc": app.bank_ifsc,
                "bank_account_type": app.bank_account_type,
                "bank_name": app.bank_name,
            },
            "classification": {
                "categories": json.loads(app.categories_json) if app.categories_json else [],
            },
            "declarations": {
                "declaration_accurate_info": app.declaration_accurate_info,
                "declaration_authorised_rep": app.declaration_authorised_rep,
                "declaration_verification_consent": app.declaration_verification_consent,
                "declaration_timestamp": app.declaration_timestamp.isoformat() if app.declaration_timestamp else None,
            },
        }

        # 3. Documents & Versions
        docs_list = []
        for d in app.documents:
            versions_list = []
            for v in d.versions:
                ext_res = (
                    self.db.query(DocumentExtractionResult)
                    .filter(DocumentExtractionResult.document_version_id == v.id)
                    .first()
                )
                fields_data = []
                if ext_res:
                    for f in ext_res.fields:
                        fields_data.append({
                            "field_name": f.field_name,
                            "extracted_value": mask_identifier(f.field_name, f.extracted_value),
                            "confidence_score": f.confidence_score,
                            "evidence_text": f.evidence_text,
                        })

                versions_list.append({
                    "id": v.id,
                    "version_number": v.version_number,
                    "filename": v.original_filename,
                    "file_size": v.file_size_bytes,
                    "content_type": v.content_type,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                    "preview_url": f"/api/applications/{app.id}/documents/{d.id}/preview",
                    "extraction": {
                        "status": ext_res.status if ext_res else "QUEUED",
                        "detected_document_type": ext_res.detected_document_type if ext_res else None,
                        "classification_confidence": ext_res.classification_confidence if ext_res else None,
                        "is_type_match": ext_res.is_type_match if ext_res else None,
                        "fields": fields_data,
                    } if ext_res else None,
                })

            docs_list.append({
                "id": d.id,
                "document_type": d.document_type,
                "title": d.title,
                "is_required": d.is_required,
                "status": d.status,
                "current_version_id": d.current_version_id,
                "versions": versions_list,
            })

        # 4. Validation Engine Findings Grouped by Layer
        val_run = (
            self.db.query(ValidationRun)
            .filter(
                ValidationRun.application_id == app.id,
                ValidationRun.is_current.is_(True),
            )
            .first()
        )
        validation_data = None
        if val_run:
            grouped_findings: Dict[str, List[Dict[str, Any]]] = {
                ValidationLayerEnum.LAYER_A_INPUT.value: [],
                ValidationLayerEnum.LAYER_B_CONSISTENCY.value: [],
                ValidationLayerEnum.LAYER_C_EXTERNAL.value: [],
                ValidationLayerEnum.LAYER_D_DUPLICATE.value: [],
            }
            for f in val_run.findings:
                finding_item = {
                    "id": f.id,
                    "check_id": f.check_id,
                    "layer": f.layer,
                    "check_name": f.check_name,
                    "status": f.status,
                    "severity": f.severity,
                    "submitted_value": mask_identifier("submitted", f.submitted_value),
                    "extracted_value": mask_identifier("extracted", f.extracted_value),
                    "external_value": mask_identifier("external", f.external_value),
                    "evidence": f.evidence,
                    "explanation": f.explanation,
                    "recommended_action": f.recommended_action,
                    "is_stale": f.is_stale,
                    "stale_reason": f.stale_reason,
                }
                grouped_findings.setdefault(f.layer, []).append(finding_item)

            validation_data = {
                "id": val_run.id,
                "run_type": val_run.run_type,
                "status": val_run.status,
                "summary": val_run.summary,
                "passed_count": val_run.passed_count,
                "failed_count": val_run.failed_count,
                "warning_count": val_run.warning_count,
                "unverified_count": val_run.unverified_count,
                "unavailable_count": val_run.unavailable_count,
                "created_at": val_run.created_at.isoformat() if val_run.created_at else None,
                "layers": grouped_findings,
            }

        # 5. Exceptions & State Machine History
        exceptions = (
            self.db.query(OnboardingException)
            .filter(OnboardingException.application_id == app.id)
            .order_by(OnboardingException.created_at.desc())
            .all()
        )
        exceptions_list = []
        for exc in exceptions:
            comments_list = []
            for c in exc.comments:
                if is_vendor and c.is_internal:
                    continue  # Purge confidential internal notes for vendors
                comments_list.append({
                    "id": c.id,
                    "author_role": c.author_role,
                    "is_internal": c.is_internal,
                    "message": c.message,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                })

            corrections_list = [
                {
                    "id": fc.id,
                    "field_name": fc.field_name,
                    "previous_value": fc.previous_value,
                    "new_value": fc.new_value,
                    "vendor_explanation": fc.vendor_explanation,
                    "created_at": fc.created_at.isoformat() if fc.created_at else None,
                }
                for fc in exc.field_corrections
            ]

            transitions_list = [
                {
                    "id": t.id,
                    "from_status": t.from_status,
                    "to_status": t.to_status,
                    "actor_role": t.actor_role,
                    "reason": t.reason,
                    "notes": t.notes,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in exc.transitions
            ]

            exceptions_list.append({
                "id": exc.id,
                "reference_number": exc.reference_number,
                "category": exc.category,
                "title": exc.title,
                "description": exc.description,
                "severity": exc.severity,
                "status": exc.status,
                "assigned_role": exc.assigned_role,
                "related_field_name": exc.related_field_name,
                "related_document_id": exc.related_document_id,
                "vendor_action_instruction": exc.vendor_action_instruction,
                "resolution_type": exc.resolution_type,
                "resolution_notes": exc.resolution_notes,
                "resolved_at": exc.resolved_at.isoformat() if exc.resolved_at else None,
                "created_at": exc.created_at.isoformat() if exc.created_at else None,
                "comments": comments_list,
                "field_corrections": corrections_list,
                "transitions": transitions_list,
            })

        # 6. External Verification Logs (Clearly labeled simulated)
        verifications = (
            self.db.query(ExternalVerificationRecord)
            .filter(ExternalVerificationRecord.application_id == app.id)
            .order_by(ExternalVerificationRecord.created_at.desc())
            .all()
        )
        verifications_list = [
            {
                "id": v.id,
                "verification_type": v.verification_type,
                "provider_name": v.provider_name,
                "request_id": v.request_id,
                "submitted_identifier": mask_identifier(v.verification_type, v.submitted_identifier),
                "status": v.status,
                "is_simulated": v.is_simulated,
                "environment_label": "SIMULATED SANDBOX",
                "returned_attributes": json.loads(v.returned_attributes_json) if v.returned_attributes_json else {},
                "reason": v.reason,
                "duration_ms": v.duration_ms,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in verifications
        ]

        # 7. Chronological Activity & Audit Trail
        audits = (
            self.db.query(AuditEvent)
            .filter(AuditEvent.application_id == app.id)
            .order_by(AuditEvent.created_at.asc())
            .all()
        )
        activity_trail = []
        for a in audits:
            details = {}
            if a.details_json:
                try:
                    details = json.loads(a.details_json)
                except Exception:
                    pass
            activity_trail.append({
                "id": a.id,
                "event_type": a.event_type,
                "actor_role": a.actor_role or "SYSTEM",
                "details": details,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

        return {
            "overview": overview,
            "business_details": business_details,
            "documents": docs_list,
            "validation": validation_data,
            "exceptions": exceptions_list,
            "external_verifications": verifications_list,
            "activity_trail": activity_trail,
        }
