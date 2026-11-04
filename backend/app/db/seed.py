import io
import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.organization import Organization
from app.models.user import User
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.invitation import Invitation, InvitationStatusEnum
from app.models.vendor import Vendor
from app.models.application import Application, ApplicationStatusEnum, ConstitutionEnum
from app.models.document import Document, DocumentVersion
from app.core.security import hash_password, generate_invitation_token
from app.services.checklist import sync_application_documents
from app.storage.local import get_storage_adapter
from app.utils.synthetic_docs import generate_all_demo_documents
from app.services.extraction.pipeline import run_pipeline_for_document_version


def seed_document_for_slot(
    db: Session,
    app: Application,
    doc_type: str,
    file_path: str,
    content_type: str,
    filename: str,
    user_id: str,
):
    doc = db.query(Document).filter(Document.application_id == app.id, Document.document_type == doc_type).first()
    if not doc:
        return
    if doc.versions:
        # Already has version, ensure extraction pipeline has run
        latest = doc.versions[0]
        run_pipeline_for_document_version(latest.id, db)
        return

    if not Path(file_path).is_file():
        return

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


def seed_database():
    """
    Seed deterministic synthetic development/demo accounts, organisations,
    and two realistic vendor onboarding scenarios (Proprietorship & Private Limited).
    """
    db: Session = SessionLocal()
    try:
        # 1. Organisations
        apex_org = db.query(Organization).filter(Organization.slug == "apex-enterprises").first()
        if not apex_org:
            apex_org = Organization(
                id="org-apex-001",
                name="Apex Enterprises Ltd.",
                slug="apex-enterprises",
                is_active=True,
                policy_version="1.0.0",
                settings='{"industry": "Manufacturing", "jurisdiction": "IN"}',
            )
            db.add(apex_org)

        zenith_org = db.query(Organization).filter(Organization.slug == "zenith-global").first()
        if not zenith_org:
            zenith_org = Organization(
                id="org-zenith-002",
                name="Zenith Global Corp",
                slug="zenith-global",
                is_active=True,
                policy_version="1.0.0",
                settings='{"industry": "Distribution", "jurisdiction": "IN"}',
            )
            db.add(zenith_org)

        db.commit()

        default_hashed_pw = hash_password("Password123!")

        # 2. Staff Accounts
        staff_accounts = [
            {"email": "admin@apex.com", "name": "Aditya Sharma", "role": RoleEnum.ADMIN.value, "org_id": apex_org.id},
            {"email": "procurement@apex.com", "name": "Pooja Verma", "role": RoleEnum.PROCUREMENT_OFFICER.value, "org_id": apex_org.id},
            {"email": "reviewer@apex.com", "name": "Rajesh Iyer", "role": RoleEnum.REVIEWER.value, "org_id": apex_org.id},
            {"email": "procurement@zenith.com", "name": "Zoya Akhtar", "role": RoleEnum.PROCUREMENT_OFFICER.value, "org_id": zenith_org.id},
        ]

        for acc in staff_accounts:
            user = db.query(User).filter(User.email == acc["email"]).first()
            if not user:
                user = User(email=acc["email"], full_name=acc["name"], hashed_password=default_hashed_pw, is_active=True)
                db.add(user)
                db.flush()

            member = db.query(OrganisationMember).filter(
                OrganisationMember.user_id == user.id,
                OrganisationMember.organisation_id == acc["org_id"],
            ).first()
            if not member:
                member = OrganisationMember(user_id=user.id, organisation_id=acc["org_id"], role=acc["role"], is_active=True)
                db.add(member)

        db.commit()

        # 3. Seed Scenario A: Proprietorship (Apex Components)
        vendor_a_user = db.query(User).filter(User.email == "vendor@apexcomponents.com").first()
        if not vendor_a_user:
            vendor_a_user = User(
                email="vendor@apexcomponents.com",
                full_name="Vikram Malhotra",
                hashed_password=default_hashed_pw,
                is_active=True,
            )
            db.add(vendor_a_user)
            db.flush()

        member_a = db.query(OrganisationMember).filter(
            OrganisationMember.user_id == vendor_a_user.id,
            OrganisationMember.organisation_id == apex_org.id,
        ).first()
        if not member_a:
            member_a = OrganisationMember(
                user_id=vendor_a_user.id,
                organisation_id=apex_org.id,
                role=RoleEnum.VENDOR.value,
                is_active=True,
            )
            db.add(member_a)
            db.flush()

        vendor_a = db.query(Vendor).filter(
            Vendor.organisation_id == apex_org.id,
            Vendor.created_by_user_id == vendor_a_user.id,
        ).first()
        if not vendor_a:
            vendor_a = Vendor(
                organisation_id=apex_org.id,
                created_by_user_id=vendor_a_user.id,
                legal_name="Apex Components & Fasteners",
                trade_name="Apex Fasteners",
                constitution=ConstitutionEnum.PROPRIETORSHIP.value,
                pan="AAPFU0938L",
            )
            db.add(vendor_a)
            db.flush()

        app_a = db.query(Application).filter(Application.vendor_id == vendor_a.id).first()
        if not app_a:
            app_a = Application(
                reference_number="APP-2026-PROP-001",
                organisation_id=apex_org.id,
                vendor_id=vendor_a.id,
                created_by_user_id=vendor_a_user.id,
                status=ApplicationStatusEnum.IN_PROGRESS.value,
                legal_name="Apex Components & Fasteners",
                trade_name="Apex Fasteners",
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
                contact_name="Vikram Malhotra",
                contact_designation="Proprietor",
                contact_email="vendor@apexcomponents.com",
                contact_mobile="+91 98200 12345",
                authorised_signatory_name="Vikram Malhotra",
                bank_account_holder_name="Apex Components & Fasteners",
                bank_account_number="9876543210123",
                bank_ifsc="HDFC0000123",
                bank_account_type="CURRENT",
                bank_name="HDFC Bank Ltd",
                categories_json=json.dumps(["goods_supplier", "manufacturer"]),
                declaration_accurate_info=True,
                declaration_authorised_rep=True,
                declaration_verification_consent=True,
            )
            db.add(app_a)
            db.flush()
            sync_application_documents(db, app_a)

        # 4. Seed Scenario B: Private Limited Company (Zenith Cloud Systems)
        vendor_b_user = db.query(User).filter(User.email == "vendor@zenithsoft.in").first()
        if not vendor_b_user:
            vendor_b_user = User(
                email="vendor@zenithsoft.in",
                full_name="Karan Oberoi",
                hashed_password=default_hashed_pw,
                is_active=True,
            )
            db.add(vendor_b_user)
            db.flush()

        member_b = db.query(OrganisationMember).filter(
            OrganisationMember.user_id == vendor_b_user.id,
            OrganisationMember.organisation_id == apex_org.id,
        ).first()
        if not member_b:
            member_b = OrganisationMember(
                user_id=vendor_b_user.id,
                organisation_id=apex_org.id,
                role=RoleEnum.VENDOR.value,
                is_active=True,
            )
            db.add(member_b)
            db.flush()

        vendor_b = db.query(Vendor).filter(
            Vendor.organisation_id == apex_org.id,
            Vendor.created_by_user_id == vendor_b_user.id,
        ).first()
        if not vendor_b:
            vendor_b = Vendor(
                organisation_id=apex_org.id,
                created_by_user_id=vendor_b_user.id,
                legal_name="Zenith Cloud Systems Private Limited",
                trade_name="Zenith Cloud",
                constitution=ConstitutionEnum.PVT_LTD.value,
                pan="AAACZ1234K",
            )
            db.add(vendor_b)
            db.flush()

        app_b = db.query(Application).filter(Application.vendor_id == vendor_b.id).first()
        if not app_b:
            app_b = Application(
                reference_number="APP-2026-CORP-002",
                organisation_id=apex_org.id,
                vendor_id=vendor_b.id,
                created_by_user_id=vendor_b_user.id,
                status=ApplicationStatusEnum.IN_PROGRESS.value,
                legal_name="Zenith Cloud Systems Private Limited",
                trade_name="Zenith Cloud",
                constitution=ConstitutionEnum.PVT_LTD.value,
                date_of_establishment="2020-09-15",
                registered_address="Level 4, Tech Park Boulevard, Whitefield Main Road",
                operating_address="Level 4, Tech Park Boulevard, Whitefield Main Road",
                city="Bengaluru",
                state="Karnataka",
                pincode="560066",
                pan="AAACZ1234K",
                is_gst_registered=True,
                gstin="29AAACZ1234K1Z5",
                is_udyam_registered=False,
                cin_llpin="U72200KA2020PTC123456",
                contact_name="Karan Oberoi",
                contact_designation="Director",
                contact_email="vendor@zenithsoft.in",
                contact_mobile="+91 99887 65432",
                authorised_signatory_name="Karan Oberoi",
                bank_account_holder_name="Zenith Cloud Systems Private Limited",
                bank_account_number="50200012345678",
                bank_ifsc="ICIC0000002",
                bank_account_type="CURRENT",
                bank_name="ICICI Bank",
                categories_json=json.dumps(["it_services", "professional_services"]),
                declaration_accurate_info=True,
                declaration_authorised_rep=True,
                declaration_verification_consent=True,
            )
            db.add(app_b)
            db.flush()
            sync_application_documents(db, app_b)

        # 5. Pending invitation for testing token acceptance flow
        procurement_user = db.query(User).filter(User.email == "procurement@apex.com").first()
        test_inv = db.query(Invitation).filter(Invitation.vendor_email == "newvendor@testinv.in").first()
        if not test_inv:
            now = datetime.now(timezone.utc)
            _, token_hash = generate_invitation_token()
            test_inv = Invitation(
                organisation_id=apex_org.id,
                invited_by_user_id=procurement_user.id if procurement_user else None,
                vendor_name="Fresh Test Components LLP",
                vendor_email="newvendor@testinv.in",
                token_hash=token_hash,
                status=InvitationStatusEnum.PENDING.value,
                expires_at=now + timedelta(days=7),
                custom_message="Please join our supplier network.",
            )
            db.add(test_inv)

        db.commit()

        # 6. Generate and Seed Synthetic Compliance Documents for Live Demo
        demo_docs = generate_all_demo_documents("./demo_documents")

        # Scenario A compliance document uploads
        seed_document_for_slot(
            db, app_a, "PAN_PROOF", demo_docs["pan_pdf"], "application/pdf", "pan_card_apex.pdf", vendor_a_user.id
        )
        seed_document_for_slot(
            db, app_a, "GST_CERTIFICATE", demo_docs["gst_pdf"], "application/pdf", "form_gst_reg06_apex.pdf", vendor_a_user.id
        )
        seed_document_for_slot(
            db, app_a, "BANK_PROOF", demo_docs["bank_png"], "image/png", "cancelled_cheque_apex.png", vendor_a_user.id
        )
        seed_document_for_slot(
            db, app_a, "UDYAM_CERTIFICATE", demo_docs["udyam_pdf"], "application/pdf", "udyam_certificate_apex.pdf", vendor_a_user.id
        )

        # Scenario B compliance document uploads
        seed_document_for_slot(
            db, app_b, "CONSTITUTION_PROOF", demo_docs["coi_pdf"], "application/pdf", "coi_zenith.pdf", vendor_b_user.id
        )
        seed_document_for_slot(
            db, app_b, "BANK_PROOF", demo_docs["bank_png"], "image/png", "bank_proof_zenith.png", vendor_b_user.id
        )

        print("[Seed] Successfully seeded organisations, staff, Scenario A (Proprietorship), Scenario B (Company), demo compliance documents, and test invitations.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
