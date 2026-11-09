import io
import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models.organization import Organization
from app.models.user import User
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.invitation import Invitation, InvitationStatusEnum
from app.models.vendor import Vendor
from app.models.application import Application, ApplicationStatusEnum, ConstitutionEnum
from app.models.document import Document, DocumentVersion
from app.models.extraction import (
    DocumentExtractionResult,
    ExtractedField,
    ProcessingStatusEnum,
)
from app.models.validation import (
    ValidationRun,
    ValidationFinding,
    ExternalVerificationRecord,
    DuplicateSignal,
    ValidationStatusEnum,
    ValidationSeverityEnum,
    ValidationLayerEnum,
)
from app.models.exception import (
    OnboardingException,
    ExceptionTransition,
    ExceptionComment,
    FieldCorrectionRecord,
    ExceptionStatusEnum,
    ExceptionSeverityEnum,
    ExceptionCategoryEnum,
)
from app.models.notification import Notification
from app.models.audit import AuditEvent
from app.core.security import hash_password, generate_invitation_token
from app.services.checklist import sync_application_documents
from app.storage.local import get_storage_adapter
from app.utils.synthetic_docs import generate_all_demo_documents
from app.services.extraction.pipeline import run_pipeline_for_document_version
from app.services.validation.orchestrator import ValidationOrchestrator


def clean_database(db: Session):
    """
    Cleans all operational tables in reverse dependency order.
    """
    tables = [
        AuditEvent,
        Notification,
        FieldCorrectionRecord,
        ExceptionTransition,
        ExceptionComment,
        OnboardingException,
        DuplicateSignal,
        ExternalVerificationRecord,
        ValidationFinding,
        ValidationRun,
        ExtractedField,
        DocumentExtractionResult,
        DocumentVersion,
        Document,
        Application,
        Vendor,
        Invitation,
        OrganisationMember,
        User,
        Organization,
    ]
    for table in tables:
        try:
            db.query(table).delete()
        except Exception:
            pass
    db.commit()


def seed_document(
    db: Session,
    app: Application,
    doc_type: str,
    file_path: str,
    content_type: str,
    filename: str,
    user_id: str,
) -> DocumentVersion:
    doc = db.query(Document).filter(
        Document.application_id == app.id,
        Document.document_type == doc_type,
    ).first()
    if not doc:
        doc = Document(
            application_id=app.id,
            organisation_id=app.organisation_id,
            document_type=doc_type,
            title=doc_type.replace("_", " ").title(),
            is_required=True,
            status="PENDING",
        )
        db.add(doc)
        db.flush()

    with open(file_path, "rb") as f:
        content = f.read()

    checksum = hashlib.sha256(content).hexdigest()
    storage = get_storage_adapter()
    dest_path = f"org_{app.organisation_id}/app_{app.id}/{doc_type}_v1_{secrets.token_hex(4)}{Path(file_path).suffix}"
    storage_key = storage.save_file(io.BytesIO(content), dest_path, content_type)

    version = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        storage_key=storage_key,
        original_filename=filename,
        file_size_bytes=len(content),
        content_type=content_type,
        file_checksum=checksum,
        uploaded_by_user_id=user_id,
    )
    db.add(version)
    db.flush()

    doc.status = "UPLOADED"
    doc.current_version_id = version.id
    db.commit()

    run_pipeline_for_document_version(version.id, db)
    return version


def reset_and_seed_demo(db: Session = None) -> dict:
    """
    Main seed function creating 3 repeatable demo cases:
    1. Clean Application Ready for Reviewer Approval (APP-2026-CLEAN-001)
    2. Application Requiring Vendor Correction Due to Mismatch (APP-2026-MISM-002)
    3. Application with Unresolved Verification or Review Issue (APP-2026-WARN-003)
    """
    owns_db = False
    if db is None:
        db = SessionLocal()
        owns_db = True

    try:
        clean_database(db)

        now = datetime.now(timezone.utc)
        default_pw = hash_password("Password123!")

        # 1. Seed Organisations
        apex_org = Organization(
            id="org-apex-001",
            name="Apex Enterprises Ltd.",
            slug="apex-enterprises",
            is_active=True,
            policy_version="1.0.0",
            settings=json.dumps({"industry": "Manufacturing", "jurisdiction": "IN"}),
        )
        db.add(apex_org)

        zenith_org = Organization(
            id="org-zenith-002",
            name="Zenith Global Corp",
            slug="zenith-global",
            is_active=True,
            policy_version="1.0.0",
            settings=json.dumps({"industry": "Distribution", "jurisdiction": "IN"}),
        )
        db.add(zenith_org)
        db.commit()

        # 2. Staff Accounts
        admin_user = User(
            id="usr-apex-admin-01",
            email="admin@apex.com",
            full_name="Aditya Sharma",
            hashed_password=default_pw,
            is_active=True,
        )
        db.add(admin_user)

        proc_user = User(
            id="usr-apex-proc-01",
            email="procurement@apex.com",
            full_name="Pooja Verma",
            hashed_password=default_pw,
            is_active=True,
        )
        db.add(proc_user)

        rev_user = User(
            id="usr-apex-rev-01",
            email="reviewer@apex.com",
            full_name="Rajesh Iyer",
            hashed_password=default_pw,
            is_active=True,
        )
        db.add(rev_user)

        zenith_proc_user = User(
            id="usr-zenith-proc-01",
            email="procurement@zenith.com",
            full_name="Zoya Akhtar",
            hashed_password=default_pw,
            is_active=True,
        )
        db.add(zenith_proc_user)
        db.flush()

        # Memberships
        db.add(OrganisationMember(user_id=admin_user.id, organisation_id=apex_org.id, role=RoleEnum.ADMIN.value, is_active=True))
        db.add(OrganisationMember(user_id=proc_user.id, organisation_id=apex_org.id, role=RoleEnum.PROCUREMENT_OFFICER.value, is_active=True))
        db.add(OrganisationMember(user_id=rev_user.id, organisation_id=apex_org.id, role=RoleEnum.REVIEWER.value, is_active=True))
        db.add(OrganisationMember(user_id=zenith_proc_user.id, organisation_id=zenith_org.id, role=RoleEnum.PROCUREMENT_OFFICER.value, is_active=True))
        db.commit()

        # Baseline vendor accounts for test harness continuity
        vendor_baseline = User(
            id="usr-vendor-apex-01",
            email="vendor@apexcomponents.com",
            full_name="Vikram Malhotra",
            hashed_password=default_pw,
            is_active=True,
        )
        db.add(vendor_baseline)
        db.flush()
        db.add(OrganisationMember(user_id=vendor_baseline.id, organisation_id=apex_org.id, role=RoleEnum.VENDOR.value, is_active=True))

        v_base = Vendor(
            id="vnd-apex-base-01",
            organisation_id=apex_org.id,
            created_by_user_id=vendor_baseline.id,
            legal_name="Apex Components & Fasteners",
            trade_name="Apex Fasteners",
            constitution=ConstitutionEnum.PROPRIETORSHIP.value,
            pan="ABCPV1234F",
        )
        db.add(v_base)
        db.flush()

        app_base = Application(
            id="app-apex-base-01",
            reference_number="APP-2026-PROP-001",
            organisation_id=apex_org.id,
            vendor_id=v_base.id,
            created_by_user_id=vendor_baseline.id,
            status=ApplicationStatusEnum.IN_PROGRESS.value,
            legal_name="Apex Components & Fasteners",
            trade_name="Apex Fasteners",
            constitution=ConstitutionEnum.PROPRIETORSHIP.value,
            contact_email="vendor@apexcomponents.com",
            categories_json="[]",
        )
        db.add(app_base)
        db.flush()
        sync_application_documents(db, app_base)

        vendor_b_user = User(
            id="usr-vendor-zenith-01",
            email="vendor@zenithsoft.in",
            full_name="Karan Oberoi",
            hashed_password=default_pw,
            is_active=True,
        )
        db.add(vendor_b_user)
        db.flush()
        db.add(OrganisationMember(user_id=vendor_b_user.id, organisation_id=apex_org.id, role=RoleEnum.VENDOR.value, is_active=True))
        db.commit()

        # Synthetic Docs
        demo_docs = generate_all_demo_documents("./demo_documents")

        # ---------------------------------------------------------------------
        # Case 1: Clean Application Ready for Reviewer Approval
        # ---------------------------------------------------------------------
        vendor1_user = User(
            id="usr-vendor-clean-01",
            email="vendor.clean@tatasupply.in",
            full_name="Ratan Verma",
            hashed_password=default_pw,
            is_active=True,
        )
        db.add(vendor1_user)
        db.flush()

        db.add(OrganisationMember(user_id=vendor1_user.id, organisation_id=apex_org.id, role=RoleEnum.VENDOR.value, is_active=True))

        vendor1 = Vendor(
            id="vnd-clean-001",
            organisation_id=apex_org.id,
            created_by_user_id=vendor1_user.id,
            legal_name="Tata Industrial Supplies Private Limited",
            trade_name="Tata Supplies",
            constitution=ConstitutionEnum.PVT_LTD.value,
            pan="AAACZ1234K",
        )
        db.add(vendor1)
        db.flush()

        app1 = Application(
            id="app-clean-001",
            reference_number="APP-2026-CLEAN-001",
            organisation_id=apex_org.id,
            vendor_id=vendor1.id,
            created_by_user_id=vendor1_user.id,
            status=ApplicationStatusEnum.UNDER_REVIEW.value,
            assigned_reviewer_id=rev_user.id,
            assigned_at=now - timedelta(hours=2),
            legal_name="Tata Industrial Supplies Private Limited",
            trade_name="Tata Supplies",
            constitution=ConstitutionEnum.PVT_LTD.value,
            date_of_establishment="2020-09-15",
            registered_address="Plot 10, Industrial Hub, Electronic City Phase 1",
            operating_address="Plot 10, Industrial Hub, Electronic City Phase 1",
            city="Bengaluru",
            state="Karnataka",
            pincode="560100",
            pan="AAACZ1234K",
            is_gst_registered=True,
            gstin="29AAACZ1234K1Z5",
            is_udyam_registered=False,
            cin_llpin="U72200KA2020PTC123456",
            contact_name="Ratan Verma",
            contact_designation="Director",
            contact_email="vendor.clean@tatasupply.in",
            contact_mobile="+91 98450 12345",
            authorised_signatory_name="Ratan Verma",
            bank_account_holder_name="Tata Industrial Supplies Private Limited",
            bank_account_number="50200012345678",
            bank_ifsc="ICIC0000002",
            bank_account_type="CURRENT",
            bank_name="ICICI Bank",
            categories_json=json.dumps(["goods_supplier", "it_services"]),
            declaration_accurate_info=True,
            declaration_authorised_rep=True,
            declaration_verification_consent=True,
            submitted_at=now - timedelta(hours=3),
        )
        db.add(app1)
        db.flush()
        sync_application_documents(db, app1)

        # Upload and extract compliance docs for Case 1
        seed_document(db, app1, "PAN_PROOF", demo_docs["pan_tata_pdf"], "application/pdf", "pan_tata_supplies.pdf", vendor1_user.id)
        seed_document(db, app1, "GST_CERTIFICATE", demo_docs["gst_tata_pdf"], "application/pdf", "gst_reg06_tata.pdf", vendor1_user.id)
        seed_document(db, app1, "BANK_PROOF", demo_docs["bank_tata_pdf"], "application/pdf", "cancelled_cheque_tata.pdf", vendor1_user.id)
        seed_document(db, app1, "CONSTITUTION_PROOF", demo_docs["coi_tata_pdf"], "application/pdf", "coi_certificate_tata.pdf", vendor1_user.id)
        seed_document(db, app1, "SIGNATORY_PROOF", demo_docs["board_res_tata_pdf"], "application/pdf", "board_resolution_tata.pdf", vendor1_user.id)

        # Run validation for Case 1
        orchestrator = ValidationOrchestrator(db)
        orchestrator.run_full_validation(
            application_id=app1.id,
            user_id=vendor1_user.id,
            run_type="INITIAL",
            trigger_reason="Application submission automated validation",
        )

        # Audit events for Case 1
        db.add(AuditEvent(
            organisation_id=apex_org.id,
            application_id=app1.id,
            actor_user_id=vendor1_user.id,
            actor_role=RoleEnum.VENDOR.value,
            event_type="APPLICATION_SUBMITTED",
            entity_type="APPLICATION",
            entity_id=app1.id,
            details_json=json.dumps({"reference": app1.reference_number}),
        ))
        db.add(AuditEvent(
            organisation_id=apex_org.id,
            application_id=app1.id,
            actor_user_id=admin_user.id,
            actor_role=RoleEnum.ADMIN.value,
            event_type="REVIEWER_ASSIGNED",
            entity_type="APPLICATION",
            entity_id=app1.id,
            details_json=json.dumps({"reviewer_id": rev_user.id, "reviewer_name": rev_user.full_name}),
        ))
        db.commit()

        # ---------------------------------------------------------------------
        # Case 2: Application Requiring Vendor Correction Due to Mismatch
        # ---------------------------------------------------------------------
        vendor2_user = User(
            id="usr-vendor-mism-02",
            email="vendor.mismatch@sharmaworks.in",
            full_name="Ramesh Sharma",
            hashed_password=default_pw,
            is_active=True,
        )
        db.add(vendor2_user)
        db.flush()

        db.add(OrganisationMember(user_id=vendor2_user.id, organisation_id=apex_org.id, role=RoleEnum.VENDOR.value, is_active=True))

        vendor2 = Vendor(
            id="vnd-mism-002",
            organisation_id=apex_org.id,
            created_by_user_id=vendor2_user.id,
            legal_name="Sharma Engineering Works",
            trade_name="Sharma Engineering",
            constitution=ConstitutionEnum.PROPRIETORSHIP.value,
            pan="AAPFU0938L",
        )
        db.add(vendor2)
        db.flush()

        app2 = Application(
            id="app-mism-002",
            reference_number="APP-2026-MISM-002",
            organisation_id=apex_org.id,
            vendor_id=vendor2.id,
            created_by_user_id=vendor2_user.id,
            status=ApplicationStatusEnum.ACTION_REQUIRED.value,
            assigned_reviewer_id=rev_user.id,
            assigned_at=now - timedelta(days=1),
            clarification_requested_at=now - timedelta(hours=5),
            legal_name="Sharma Engineering Works",
            trade_name="Sharma Engineering",
            constitution=ConstitutionEnum.PROPRIETORSHIP.value,
            date_of_establishment="2018-04-12",
            registered_address="Plot 42, Wagle Industrial Estate, Road No. 16",
            operating_address="Plot 42, Wagle Industrial Estate, Road No. 16",
            city="Thane",
            state="Maharashtra",
            pincode="400604",
            pan="AAPFU0938L",
            is_gst_registered=True,
            gstin="27AAPFU0938L1ZV",
            is_udyam_registered=True,
            udyam_number="UDYAM-MH-02-0012345",
            contact_name="Ramesh Sharma",
            contact_designation="Proprietor",
            contact_email="vendor.mismatch@sharmaworks.in",
            contact_mobile="+91 98200 54321",
            authorised_signatory_name="Ramesh Sharma",
            bank_account_holder_name="Sharma Engineering Works",
            # Mismatch: form specifies 9876543210123 while cheque image extracts 50200012345678
            bank_account_number="9876543210123",
            bank_ifsc="HDFC0000123",
            bank_account_type="CURRENT",
            bank_name="HDFC Bank",
            categories_json=json.dumps(["manufacturer", "goods_supplier"]),
            declaration_accurate_info=True,
            declaration_authorised_rep=True,
            declaration_verification_consent=True,
            submitted_at=now - timedelta(days=1),
        )
        db.add(app2)
        db.flush()
        sync_application_documents(db, app2)

        # Upload docs for Case 2
        seed_document(db, app2, "PAN_PROOF", demo_docs["pan_sharma_pdf"], "application/pdf", "pan_card_sharma.pdf", vendor2_user.id)
        seed_document(db, app2, "GST_CERTIFICATE", demo_docs["gst_sharma_pdf"], "application/pdf", "gst_certificate_sharma.pdf", vendor2_user.id)
        bank_v2 = seed_document(db, app2, "BANK_PROOF", demo_docs["bank_sharma_pdf"], "application/pdf", "cheque_sharma.pdf", vendor2_user.id)
        seed_document(db, app2, "UDYAM_CERTIFICATE", demo_docs["udyam_sharma_pdf"], "application/pdf", "udyam_cert_sharma.pdf", vendor2_user.id)
        seed_document(db, app2, "CONSTITUTION_PROOF", demo_docs["udyam_sharma_pdf"], "application/pdf", "establishment_sharma.pdf", vendor2_user.id)

        # Run validation
        run2 = orchestrator.run_full_validation(
            application_id=app2.id,
            user_id=vendor2_user.id,
            run_type="INITIAL",
            trigger_reason="Initial validation finding bank mismatch",
        )

        bank_doc = db.query(Document).filter(Document.application_id == app2.id, Document.document_type == "BANK_PROOF").first()

        # Reuse the exception generated from the real validation finding.
        # A second manually inserted bank issue would ask the vendor twice.
        exc2 = db.query(OnboardingException).filter(
            OnboardingException.application_id == app2.id,
            OnboardingException.related_field_name == "bank_account_number",
        ).first()
        if exc2 is None:
            raise RuntimeError("Seeded bank mismatch did not produce an exception")
        exc2.reference_number = "EXC-2026-0001"
        exc2.title = "Bank Account Number Mismatch between Form and Cancelled Cheque"
        exc2.description = "The registered bank account number '9876543210123' does not match the account number '60200012345678' extracted from the uploaded cheque."
        exc2.severity = ExceptionSeverityEnum.HIGH.value
        exc2.status = ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value
        exc2.related_document_id = bank_doc.id if bank_doc else None
        exc2.related_version_id = bank_v2.id if bank_v2 else None
        exc2.source_check_ids_json = json.dumps(["B_BANK_ACCOUNT_NUM_MATCH"])
        exc2.assigned_user_id = rev_user.id
        exc2.assigned_role = RoleEnum.REVIEWER.value
        exc2.vendor_action_instruction = "Please check your bank account number. The form shows 9876543210123, while your cheque shows 60200012345678. Update the number or upload a matching cheque."
        db.flush()

        # Transitions & Comments
        db.add(ExceptionTransition(
            exception_id=exc2.id,
            from_status=ExceptionStatusEnum.OPEN.value,
            to_status=ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
            actor_user_id=rev_user.id,
            actor_role=RoleEnum.REVIEWER.value,
            reason="Reviewer requested vendor correction for bank account number discrepancy.",
        ))
        db.add(ExceptionComment(
            exception_id=exc2.id,
            author_user_id=rev_user.id,
            author_role=RoleEnum.REVIEWER.value,
            message="Vendor account number does not match image MICR band. Sent clarification request.",
            is_internal=False,
        ))

        # Notifications
        db.add(Notification(
            organisation_id=apex_org.id,
            recipient_user_id=vendor2_user.id,
            title="Action Required: Bank Account Number Clarification",
            message=exc2.vendor_action_instruction,
            notification_type="ACTION_REQUIRED",
            entity_type="EXCEPTION",
            entity_id=exc2.id,
        ))

        # Audit event
        db.add(AuditEvent(
            organisation_id=apex_org.id,
            application_id=app2.id,
            actor_user_id=rev_user.id,
            actor_role=RoleEnum.REVIEWER.value,
            event_type="CLARIFICATION_REQUESTED",
            entity_type="APPLICATION",
            entity_id=app2.id,
            details_json=json.dumps({"instructions": exc2.vendor_action_instruction, "exception_ref": exc2.reference_number}),
        ))
        db.commit()

        # ---------------------------------------------------------------------
        # Case 3: Application with Unresolved Verification or Review Issue
        # ---------------------------------------------------------------------
        vendor3_user = User(
            id="usr-vendor-warn-03",
            email="vendor.issue@apexlogistics.in",
            full_name="Anand Mehta",
            hashed_password=default_pw,
            is_active=True,
        )
        db.add(vendor3_user)
        db.flush()

        db.add(OrganisationMember(user_id=vendor3_user.id, organisation_id=apex_org.id, role=RoleEnum.VENDOR.value, is_active=True))

        vendor3 = Vendor(
            id="vnd-warn-003",
            organisation_id=apex_org.id,
            created_by_user_id=vendor3_user.id,
            legal_name="Apex Logistics & Cargo LLP",
            trade_name="Apex Cargo",
            constitution=ConstitutionEnum.LLP.value,
            pan="AABFA1234F",
        )
        db.add(vendor3)
        db.flush()

        app3 = Application(
            id="app-warn-003",
            reference_number="APP-2026-WARN-003",
            organisation_id=apex_org.id,
            vendor_id=vendor3.id,
            created_by_user_id=vendor3_user.id,
            status=ApplicationStatusEnum.UNDER_REVIEW.value,
            assigned_reviewer_id=rev_user.id,
            assigned_at=now - timedelta(hours=6),
            legal_name="Apex Logistics & Cargo LLP",
            trade_name="Apex Cargo",
            constitution=ConstitutionEnum.LLP.value,
            date_of_establishment="2021-03-20",
            registered_address="Unit 5, Transport Nagar, Sion East",
            operating_address="Unit 5, Transport Nagar, Sion East",
            city="Mumbai",
            state="Maharashtra",
            pincode="400037",
            pan="AABFA1234F",
            is_gst_registered=False,
            cin_llpin="AAA-1234",
            contact_name="Anand Mehta",
            contact_designation="Partner",
            contact_email="vendor.issue@apexlogistics.in",
            contact_mobile="+91 97654 32100",
            authorised_signatory_name="Anand Mehta",
            bank_account_holder_name="Apex Logistics & Cargo LLP",
            bank_account_number="123456789012",
            bank_ifsc="SBIN0001234",
            bank_account_type="CURRENT",
            bank_name="State Bank of India",
            categories_json=json.dumps(["logistics", "freight_forwarder"]),
            declaration_accurate_info=True,
            declaration_authorised_rep=True,
            declaration_verification_consent=True,
            submitted_at=now - timedelta(hours=8),
        )
        db.add(app3)
        db.flush()
        sync_application_documents(db, app3)

        # Upload docs for Case 3
        seed_document(db, app3, "PAN_PROOF", demo_docs["pan_logistics_pdf"], "application/pdf", "pan_card_apex_logistics.pdf", vendor3_user.id)
        seed_document(db, app3, "BANK_PROOF", demo_docs["bank_logistics_pdf"], "application/pdf", "cheque_apex_logistics.pdf", vendor3_user.id)

        seed_document(db, app3, "CONSTITUTION_PROOF", demo_docs["llp_logistics_pdf"], "application/pdf", "llp_logistics.pdf", vendor3_user.id)

        seed_document(db, app3, "SIGNATORY_PROOF", demo_docs["authority_logistics_pdf"], "application/pdf", "authority_logistics.pdf", vendor3_user.id)
        seed_document(db, app3, "INDUSTRY_LICENCE", demo_docs["permit_logistics_pdf"], "application/pdf", "permit_logistics.pdf", vendor3_user.id)

        # Run validation for Case 3
        orchestrator.run_full_validation(
            application_id=app3.id,
            user_id=vendor3_user.id,
            run_type="INITIAL",
            trigger_reason="Initial validation run for Case 3",
        )

        # Duplicate signal candidate with Case 2
        dup_signal = DuplicateSignal(
            application_id=app3.id,
            organisation_id=apex_org.id,
            candidate_application_id=app2.id,
            candidate_vendor_id=app2.vendor_id,
            match_strength="STRONG",
            explanation="Synthetic demonstration: procurement designated this existing supplier as a candidate for manual duplicate review. This is a seeded concern, not a measured similarity result.",
            matching_attributes_json=json.dumps(["trade_name_similarity", "geographic_zone"]),
            recommended_action="Reviewer manual inspection required: verify corporate filings to confirm distinct entity ownership.",
            is_dismissed=False,
        )
        db.add(dup_signal)

        # Route the real unavailable-check issue to reviewer oversight without duplicating it.
        exc3 = db.query(OnboardingException).filter(
            OnboardingException.application_id == app3.id,
            OnboardingException.source_check_ids_json.contains("C_MCA_EXTERNAL_VERIFICATION"),
        ).first()
        if not exc3:
            raise RuntimeError("Seeded logistics timeout did not produce an issue")
        exc3.severity = ExceptionSeverityEnum.HIGH.value
        exc3.assigned_user_id = rev_user.id
        exc3.assigned_role = RoleEnum.REVIEWER.value

        # Audit events for Case 3
        db.add(AuditEvent(
            organisation_id=apex_org.id,
            application_id=app3.id,
            actor_user_id=vendor3_user.id,
            actor_role=RoleEnum.VENDOR.value,
            event_type="APPLICATION_SUBMITTED",
            entity_type="APPLICATION",
            entity_id=app3.id,
            details_json=json.dumps({"reference": app3.reference_number}),
        ))
        db.add(AuditEvent(
            organisation_id=apex_org.id,
            application_id=app3.id,
            actor_user_id=rev_user.id,
            actor_role=RoleEnum.REVIEWER.value,
            event_type="EXCEPTION_CREATED",
            entity_type="ONBOARDING_EXCEPTION",
            entity_id=exc3.id,
            details_json=json.dumps({"reference": exc3.reference_number, "reason": "MCA Provider Timeout"}),
        ))
        db.commit()

        # ---------------------------------------------------------------------
        # 7. Live Demo Invitation (Pending Token Acceptance)
        # ---------------------------------------------------------------------
        raw_inv_token = "demo-invitation-token-apex-2026"
        inv_token_hash = hashlib.sha256(raw_inv_token.encode("utf-8")).hexdigest()
        live_inv = Invitation(
            id="inv-live-demo-001",
            organisation_id=apex_org.id,
            invited_by_user_id=proc_user.id,
            vendor_name="National Industrial Supplies LLP",
            vendor_email="invite.national@suppliernet.in",
            token_hash=inv_token_hash,
            status=InvitationStatusEnum.PENDING.value,
            expires_at=now + timedelta(days=7),
            custom_message="Please complete your official vendor onboarding and statutory compliance registration with Apex Enterprises Ltd.",
            metadata_json=json.dumps({"raw_token": raw_inv_token}),
        )
        db.add(live_inv)
        db.commit()

        result_summary = {
            "success": True,
            "message": "Deterministic demo environment seeded successfully.",
            "organisation": apex_org.name,
            "accounts": {
                "admin": {"email": admin_user.email, "password": "Password123!"},
                "procurement": {"email": proc_user.email, "password": "Password123!"},
                "reviewer": {"email": rev_user.email, "password": "Password123!"},
                "clean_vendor": {"email": vendor1_user.email, "password": "Password123!", "ref": app1.reference_number},
                "mismatch_vendor": {"email": vendor2_user.email, "password": "Password123!", "ref": app2.reference_number},
                "issue_vendor": {"email": vendor3_user.email, "password": "Password123!", "ref": app3.reference_number},
            },
            "cases": [
                {
                    "case": 1,
                    "title": "Clean Application Ready for Reviewer Approval",
                    "ref": app1.reference_number,
                    "vendor": app1.legal_name,
                    "status": app1.status,
                    "approval_gate": "PASS",
                },
                {
                    "case": 2,
                    "title": "Application Requiring Vendor Correction Due to Mismatch",
                    "ref": app2.reference_number,
                    "vendor": app2.legal_name,
                    "status": app2.status,
                    "exception": exc2.title,
                    "approval_gate": "BLOCKED (High Severity Exception)",
                },
                {
                    "case": 3,
                    "title": "Application with Unresolved Verification / Review Issue",
                    "ref": app3.reference_number,
                    "vendor": app3.legal_name,
                    "status": app3.status,
                    "issue": "External Registry Timeout (UNAVAILABLE) & Duplicate Signal",
                    "approval_gate": "BLOCKED (Unresolved High Exception)",
                },
            ],
            "demo_invitation": {
                "vendor_name": live_inv.vendor_name,
                "vendor_email": live_inv.vendor_email,
                "token": raw_inv_token,
                "url": f"/invite/{raw_inv_token}",
            },
        }

        print("[Seed Demo] Successfully seeded deterministic demo environment:")
        print(json.dumps(result_summary, indent=2))
        return result_summary

    finally:
        if owns_db:
            db.close()


if __name__ == "__main__":
    reset_and_seed_demo()
