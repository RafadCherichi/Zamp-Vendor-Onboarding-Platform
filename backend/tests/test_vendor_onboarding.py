import io
import secrets
from datetime import datetime, timedelta, timezone
import pytest
from app.core.security import generate_invitation_token
from app.database import SessionLocal
from app.models.invitation import Invitation, InvitationStatusEnum
from app.models.organization import Organization
from app.models.user import User
from app.models.vendor import Vendor
from app.models.application import Application, ConstitutionEnum, ApplicationStatusEnum


@pytest.fixture(autouse=True)
def ensure_clean_test_state():
    """Ensure seeded demo vendor application is in IN_PROGRESS state before each test."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "vendor@apexcomponents.com").first()
        if user:
            vendor = db.query(Vendor).filter(Vendor.created_by_user_id == user.id).first()
            if vendor:
                app = db.query(Application).filter(Application.vendor_id == vendor.id).first()
                if app:
                    app.status = ApplicationStatusEnum.IN_PROGRESS.value
                    app.submitted_at = None
                    app.constitution = ConstitutionEnum.PROPRIETORSHIP.value
                    db.commit()
    finally:
        db.close()


def get_token(client, email, password="Password123!"):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


# ---------------------------------------------------------
# 1. Invitation Acceptance Tests
# ---------------------------------------------------------

def test_invitation_acceptance_creates_vendor_account(client):
    # Create fresh invitation via procurement
    proc_token = get_token(client, "procurement@apex.com")
    create_resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {proc_token}"},
        json={
            "vendor_name": "Sunrise Fabrication Works",
            "vendor_email": "sunrise@fabrication.in",
            "days_valid": 5,
        },
    )
    assert create_resp.status_code == 201
    raw_token = create_resp.json()["demo_invitation_url"].replace("/invite/", "")

    # Accept invitation as vendor
    accept_resp = client.post(
        f"/api/invitations/token/{raw_token}/accept",
        json={"password": "SecurePassword123!", "full_name": "Suresh Gupta"},
    )
    assert accept_resp.status_code == 200
    data = accept_resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "sunrise@fabrication.in"
    assert data["user"]["role"] == "vendor"
    assert data["user"]["organisation"]["name"] == "Apex Enterprises Ltd."
    assert "application_id" in data
    assert "reference_number" in data


def test_cannot_reuse_accepted_invitation(client):
    proc_token = get_token(client, "procurement@apex.com")
    create_resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {proc_token}"},
        json={
            "vendor_name": "Duplicate Test Co",
            "vendor_email": "dup@testco.in",
            "days_valid": 5,
        },
    )
    raw_token = create_resp.json()["demo_invitation_url"].replace("/invite/", "")

    # First accept
    r1 = client.post(
        f"/api/invitations/token/{raw_token}/accept",
        json={"password": "Password123!", "full_name": "Ramesh"},
    )
    assert r1.status_code == 200

    # Second accept must fail
    r2 = client.post(
        f"/api/invitations/token/{raw_token}/accept",
        json={"password": "Password123!", "full_name": "Ramesh"},
    )
    assert r2.status_code == 400
    assert "already been accepted" in r2.json()["detail"]


def test_cannot_accept_expired_or_revoked_invitation(client):
    proc_token = get_token(client, "procurement@apex.com")
    create_resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {proc_token}"},
        json={"vendor_name": "Revoke Inv Vendor", "vendor_email": "revoked@vendor.in", "days_valid": 5},
    )
    inv_id = create_resp.json()["id"]
    raw_token = create_resp.json()["demo_invitation_url"].replace("/invite/", "")

    # Revoke
    client.post(f"/api/invitations/{inv_id}/revoke", headers={"Authorization": f"Bearer {proc_token}"})

    # Attempt accept
    rev_accept = client.post(
        f"/api/invitations/token/{raw_token}/accept",
        json={"password": "Password123!"},
    )
    assert rev_accept.status_code == 400
    assert "revoked" in rev_accept.json()["detail"]


# ---------------------------------------------------------
# 2. Application Draft & Update Tests
# ---------------------------------------------------------

def test_vendor_can_fetch_and_update_draft(client):
    vendor_token = get_token(client, "vendor@apexcomponents.com")

    # Fetch current draft
    get_resp = client.get("/api/applications/current", headers={"Authorization": f"Bearer {vendor_token}"})
    assert get_resp.status_code == 200
    app_data = get_resp.json()
    app_id = app_data["id"]
    assert app_data["constitution"] == "PROPRIETORSHIP"

    # Update draft
    patch_resp = client.patch(
        f"/api/applications/{app_id}",
        headers={"Authorization": f"Bearer {vendor_token}"},
        json={
            "trade_name": "Apex Precision Components",
            "city": "Thane",
            "state": "Maharashtra",
            "pincode": "400604",
            "is_gst_registered": True,
            "gstin": "27AAPFU0938L1ZV",
        },
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["trade_name"] == "Apex Precision Components"
    assert updated["is_gst_registered"] is True
    assert updated["gstin"] == "27AAPFU0938L1ZV"


def test_cross_vendor_isolation(client):
    # Vendor A: Apex Components
    vendor_a_token = get_token(client, "vendor@apexcomponents.com")
    app_a = client.get("/api/applications/current", headers={"Authorization": f"Bearer {vendor_a_token}"}).json()

    # Vendor B: Zenith Cloud Systems
    vendor_b_token = get_token(client, "vendor@zenithsoft.in")

    # Vendor B attempts to access Vendor A's application by ID -> 404/403
    cross_resp = client.get(
        f"/api/applications/{app_a['id']}",
        headers={"Authorization": f"Bearer {vendor_b_token}"},
    )
    assert cross_resp.status_code == 404


# ---------------------------------------------------------
# 3. Dynamic Checklist Rules Tests
# ---------------------------------------------------------

def test_dynamic_checklist_rules_across_constitutions(client):
    vendor_token = get_token(client, "vendor@apexcomponents.com")
    app_resp = client.get("/api/applications/current", headers={"Authorization": f"Bearer {vendor_token}"})
    app_id = app_resp.json()["id"]

    # Scenario 1: Proprietorship with GST and Udyam
    client.patch(
        f"/api/applications/{app_id}",
        headers={"Authorization": f"Bearer {vendor_token}"},
        json={"constitution": "PROPRIETORSHIP", "is_gst_registered": True, "is_udyam_registered": True},
    )
    cl_resp = client.get(f"/api/applications/{app_id}/checklist", headers={"Authorization": f"Bearer {vendor_token}"})
    assert cl_resp.status_code == 200
    docs = {d["document_type"]: d for d in cl_resp.json()}

    assert docs["PAN_PROOF"]["is_required"] is True
    assert "Proprietor" in docs["PAN_PROOF"]["title"]
    assert docs["CONSTITUTION_PROOF"]["is_required"] is True
    assert "Establishment" in docs["CONSTITUTION_PROOF"]["title"]
    assert docs["BANK_PROOF"]["is_required"] is True
    assert docs["GST_CERTIFICATE"]["is_required"] is True
    assert docs["UDYAM_CERTIFICATE"]["is_required"] is True
    # Signatory proof optional for proprietorship
    assert docs["SIGNATORY_PROOF"]["is_required"] is False

    # Scenario 2: Uncheck GST and Udyam
    client.patch(
        f"/api/applications/{app_id}",
        headers={"Authorization": f"Bearer {vendor_token}"},
        json={"is_gst_registered": False, "is_udyam_registered": False},
    )
    cl_resp2 = client.get(f"/api/applications/{app_id}/checklist", headers={"Authorization": f"Bearer {vendor_token}"})
    docs2 = {d["document_type"]: d for d in cl_resp2.json()}
    assert docs2["GST_CERTIFICATE"]["is_required"] is False
    assert docs2["UDYAM_CERTIFICATE"]["is_required"] is False

    # Scenario 3: Private Limited Company with Board Resolution
    client.patch(
        f"/api/applications/{app_id}",
        headers={"Authorization": f"Bearer {vendor_token}"},
        json={"constitution": "PVT_LTD", "is_gst_registered": True},
    )
    cl_resp3 = client.get(f"/api/applications/{app_id}/checklist", headers={"Authorization": f"Bearer {vendor_token}"})
    docs3 = {d["document_type"]: d for d in cl_resp3.json()}
    assert "MOA" in docs3["CONSTITUTION_PROOF"]["title"]
    # Board resolution / signatory proof is mandatory for company
    assert docs3["SIGNATORY_PROOF"]["is_required"] is True

    # Scenario 4: Activity specific licence (Food Catering)
    client.patch(
        f"/api/applications/{app_id}",
        headers={"Authorization": f"Bearer {vendor_token}"},
        json={"categories": ["food_catering"]},
    )
    cl_resp4 = client.get(f"/api/applications/{app_id}/checklist", headers={"Authorization": f"Bearer {vendor_token}"})
    docs4 = {d["document_type"]: d for d in cl_resp4.json()}
    assert "INDUSTRY_LICENCE" in docs4
    assert docs4["INDUSTRY_LICENCE"]["is_required"] is True
    assert "FSSAI" in docs4["INDUSTRY_LICENCE"]["title"]


# ---------------------------------------------------------
# 4. Document Upload, Replacement & Preview Tests
# ---------------------------------------------------------

def test_document_upload_and_replacement_versioning(client):
    proc_token = get_token(client, "procurement@apex.com")
    unique_email = f"uploadtest_{secrets.token_hex(4)}@vendor.in"
    create_resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {proc_token}"},
        json={"vendor_name": "Upload Test Vendor", "vendor_email": unique_email, "days_valid": 5},
    )
    raw_token = create_resp.json()["demo_invitation_url"].replace("/invite/", "")
    acc_resp = client.post(f"/api/invitations/token/{raw_token}/accept", json={"password": "Password123!"})
    vendor_token = acc_resp.json()["access_token"]
    app_id = acc_resp.json()["application_id"]

    # 1. Valid PDF upload
    pdf_content = b"%PDF-1.4\n%Fake PDF content for test\n%%EOF"
    upload_resp = client.post(
        f"/api/applications/{app_id}/documents/PAN_PROOF/upload",
        headers={"Authorization": f"Bearer {vendor_token}"},
        files={"file": ("pan_card.pdf", pdf_content, "application/pdf")},
    )
    assert upload_resp.status_code == 200
    doc_data = upload_resp.json()
    assert doc_data["status"] == "UPLOADED"
    assert doc_data["current_version"]["version_number"] == 1
    assert doc_data["current_version"]["original_filename"] == "pan_card.pdf"

    # 2. Preview endpoint
    preview_resp = client.get(
        f"/api/applications/{app_id}/documents/{doc_data['id']}/preview",
        headers={"Authorization": f"Bearer {vendor_token}"},
    )
    assert preview_resp.status_code == 200
    assert preview_resp.headers["content-type"] == "application/pdf"

    # 3. Replace document (Upload Version 2)
    png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRFakePNGContent"
    replace_resp = client.post(
        f"/api/applications/{app_id}/documents/PAN_PROOF/upload",
        headers={"Authorization": f"Bearer {vendor_token}"},
        files={"file": ("pan_card_v2.png", png_content, "image/png")},
    )
    assert replace_resp.status_code == 200
    rep_data = replace_resp.json()
    assert rep_data["current_version"]["version_number"] == 2
    assert rep_data["current_version"]["original_filename"] == "pan_card_v2.png"
    assert rep_data["versions_count"] == 2


def test_untrusted_file_rejected(client):
    vendor_token = get_token(client, "vendor@apexcomponents.com")
    app_id = client.get("/api/applications/current", headers={"Authorization": f"Bearer {vendor_token}"}).json()["id"]

    # Executable disguised as pdf
    malicious_content = b"MZ\x90\x00\x03\x00\x00\x00FakeExecutableData"
    bad_resp = client.post(
        f"/api/applications/{app_id}/documents/BANK_PROOF/upload",
        headers={"Authorization": f"Bearer {vendor_token}"},
        files={"file": ("cheque.pdf", malicious_content, "application/pdf")},
    )
    # Magic bytes do not match %PDF
    assert bad_resp.status_code == 400
    assert "Untrusted file rejected" in bad_resp.json()["detail"]


# ---------------------------------------------------------
# 5. Application Submission Tests
# ---------------------------------------------------------

def test_submission_blocked_when_requirements_missing(client):
    # Create fresh invitation and user
    proc_token = get_token(client, "procurement@apex.com")
    create_resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {proc_token}"},
        json={"vendor_name": "Incomplete Vendor", "vendor_email": "incomplete@vendor.in", "days_valid": 5},
    )
    raw_token = create_resp.json()["demo_invitation_url"].replace("/invite/", "")
    acc_resp = client.post(f"/api/invitations/token/{raw_token}/accept", json={"password": "Password123!"})
    new_vendor_token = acc_resp.json()["access_token"]
    app_id = acc_resp.json()["application_id"]

    # Attempt to submit empty draft
    sub_resp = client.post(f"/api/applications/{app_id}/submit", headers={"Authorization": f"Bearer {new_vendor_token}"})
    assert sub_resp.status_code == 400
    detail = sub_resp.json()["detail"]
    assert "mandatory requirement(s) missing" in detail["message"]
    assert len(detail["errors"]) > 0


def test_full_application_submission_and_locking(client):
    proc_token = get_token(client, "procurement@apex.com")
    create_resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {proc_token}"},
        json={"vendor_name": "Full Submit Vendor", "vendor_email": "fullsubmit@vendor.in", "days_valid": 5},
    )
    raw_token = create_resp.json()["demo_invitation_url"].replace("/invite/", "")
    acc_resp = client.post(f"/api/invitations/token/{raw_token}/accept", json={"password": "Password123!"})
    vendor_token = acc_resp.json()["access_token"]
    app_id = acc_resp.json()["application_id"]

    # 1. Fill all required fields
    client.patch(
        f"/api/applications/{app_id}",
        headers={"Authorization": f"Bearer {vendor_token}"},
        json={
            "legal_name": "Apex Components & Fasteners",
            "constitution": "PROPRIETORSHIP",
            "registered_address": "Plot 42, Wagle Industrial Estate",
            "city": "Thane",
            "state": "Maharashtra",
            "pincode": "400604",
            "pan": "AAPFU0938L",
            "is_gst_registered": True,
            "gstin": "27AAPFU0938L1ZV",
            "is_udyam_registered": True,
            "udyam_number": "UDYAM-MH-02-0012345",
            "contact_name": "Vikram Malhotra",
            "contact_email": "vendor@apexcomponents.com",
            "contact_mobile": "+91 98200 12345",
            "bank_account_holder_name": "Apex Components & Fasteners",
            "bank_account_number": "9876543210123",
            "bank_ifsc": "HDFC0000123",
            "declaration_accurate_info": True,
            "declaration_authorised_rep": True,
            "declaration_verification_consent": True,
            "categories": ["goods_supplier"],
        },
    )

    # 2. Upload dummy files for all required documents
    pdf_content = b"%PDF-1.4\nDummy content for automated test\n%%EOF"
    checklist = client.get(f"/api/applications/{app_id}/checklist", headers={"Authorization": f"Bearer {vendor_token}"}).json()
    for doc in checklist:
        if doc["is_required"]:
            client.post(
                f"/api/applications/{app_id}/documents/{doc['document_type']}/upload",
                headers={"Authorization": f"Bearer {vendor_token}"},
                files={"file": (f"{doc['document_type'].lower()}.pdf", pdf_content, "application/pdf")},
            )

    # 3. Submit application
    submit_resp = client.post(
        f"/api/applications/{app_id}/submit",
        headers={"Authorization": f"Bearer {vendor_token}"},
    )
    assert submit_resp.status_code == 200
    res = submit_resp.json()
    assert res["success"] is True
    # The dummy documents trigger immediate correction requests after submission.
    assert res["status"] == "ACTION_REQUIRED"
    assert "reference_number" in res

    # 4. Locking test: After submission, edits must be blocked
    locked_patch = client.patch(
        f"/api/applications/{app_id}",
        headers={"Authorization": f"Bearer {vendor_token}"},
        json={"trade_name": "New Name After Submit"},
    )
    assert locked_patch.status_code == 400
    assert "already been submitted" in locked_patch.json()["detail"]
