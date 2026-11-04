from datetime import datetime, timedelta, timezone
import pytest
from app.core.security import generate_invitation_token
from app.models.invitation import Invitation, InvitationStatusEnum
from app.models.organization import Organization
from app.models.user import User


def get_token(client, email, password="Password123!"):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


def test_login_success(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "procurement@apex.com", "password": "Password123!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "procurement@apex.com"
    assert data["user"]["role"] == "procurement_officer"
    assert data["user"]["organisation"]["slug"] == "apex-enterprises"


def test_login_invalid_password(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "procurement@apex.com", "password": "WrongPassword!"},
    )
    assert resp.status_code == 401
    assert "Incorrect email or password" in resp.json()["detail"]


def test_login_nonexistent_user(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "ghost@unknown.com", "password": "Password123!"},
    )
    assert resp.status_code == 401
    assert "Incorrect email or password" in resp.json()["detail"]


def test_auth_me_endpoint(client):
    token = get_token(client, "reviewer@apex.com")
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "reviewer@apex.com"
    assert data["role"] == "reviewer"
    assert data["organisation"]["name"] == "Apex Enterprises Ltd."


def test_auth_me_unauthorized_without_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_invitation_creation_by_procurement(client):
    token = get_token(client, "procurement@apex.com")
    resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "vendor_name": "Kavita Machining Works",
            "vendor_email": "kavita@machiningworks.in",
            "days_valid": 10,
            "custom_message": "Please onboard for precision casting supply.",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["vendor_name"] == "Kavita Machining Works"
    assert data["vendor_email"] == "kavita@machiningworks.in"
    assert data["status"] == "PENDING"
    assert "demo_invitation_url" in data
    assert data["demo_invitation_url"].startswith("/invite/")


def test_vendor_cannot_create_invitation(client):
    vendor_token = get_token(client, "vendor@apexcomponents.com")
    resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {vendor_token}"},
        json={
            "vendor_name": "Unauthorized Vendor",
            "vendor_email": "unauth@vendor.com",
            "days_valid": 5,
        },
    )
    # Backend-enforced RBAC: Vendor forbidden
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_reviewer_cannot_create_invitation(client):
    reviewer_token = get_token(client, "reviewer@apex.com")
    resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={
            "vendor_name": "Another Vendor",
            "vendor_email": "another@vendor.com",
            "days_valid": 5,
        },
    )
    # Backend-enforced RBAC: Reviewer forbidden from invitation creation
    assert resp.status_code == 403


def test_invitation_token_validation_workflow(client):
    # 1. Procurement creates invitation
    token = get_token(client, "procurement@apex.com")
    create_resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "vendor_name": "Sahara Agro Components",
            "vendor_email": "contact@saharaagro.in",
            "days_valid": 7,
        },
    )
    assert create_resp.status_code == 201
    invite_url = create_resp.json()["demo_invitation_url"]
    raw_token = invite_url.replace("/invite/", "")

    # 2. Public token validation
    pub_resp = client.get(f"/api/invitations/token/{raw_token}")
    assert pub_resp.status_code == 200
    pub_data = pub_resp.json()
    assert pub_data["is_valid"] is True
    assert pub_data["status"] == "PENDING"
    assert pub_data["vendor_name"] == "Sahara Agro Components"
    assert pub_data["buyer_organisation_name"] == "Apex Enterprises Ltd."

    # 3. Invalid token returns 404
    inv_resp = client.get("/api/invitations/token/nonexistent_fake_token_12345")
    assert inv_resp.status_code == 404


def test_invitation_revocation(client):
    token = get_token(client, "procurement@apex.com")
    # Create invitation
    create_resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "vendor_name": "Revoke Test Corp",
            "vendor_email": "revoke@testcorp.in",
            "days_valid": 7,
        },
    )
    inv_id = create_resp.json()["id"]
    raw_token = create_resp.json()["demo_invitation_url"].replace("/invite/", "")

    # Revoke invitation
    rev_resp = client.post(
        f"/api/invitations/{inv_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json()["status"] == "REVOKED"

    # Now validate via public token: must indicate revoked
    pub_resp = client.get(f"/api/invitations/token/{raw_token}")
    assert pub_resp.status_code == 200
    assert pub_resp.json()["is_valid"] is False
    assert pub_resp.json()["status"] == "REVOKED"


def test_cross_organisation_data_isolation(client):
    """
    Verify organisation data isolation:
    User in Zenith Global Corp CANNOT access or revoke an invitation created in Apex Enterprises.
    """
    apex_token = get_token(client, "procurement@apex.com")
    zenith_token = get_token(client, "procurement@zenith.com")

    # Apex creates an invitation
    create_resp = client.post(
        "/api/invitations",
        headers={"Authorization": f"Bearer {apex_token}"},
        json={
            "vendor_name": "Apex Only Vendor",
            "vendor_email": "isolated@apexvendor.in",
            "days_valid": 7,
        },
    )
    apex_invitation_id = create_resp.json()["id"]

    # Zenith procurement attempts to view list of invitations
    zenith_list_resp = client.get(
        "/api/invitations",
        headers={"Authorization": f"Bearer {zenith_token}"},
    )
    assert zenith_list_resp.status_code == 200
    zenith_invites = zenith_list_resp.json()
    # Zenith's list must NOT include the Apex invitation
    assert all(inv["id"] != apex_invitation_id for inv in zenith_invites)

    # Zenith procurement attempts to revoke Apex's invitation by ID -> 404 (isolation enforced)
    zenith_revoke_resp = client.post(
        f"/api/invitations/{apex_invitation_id}/revoke",
        headers={"Authorization": f"Bearer {zenith_token}"},
    )
    assert zenith_revoke_resp.status_code == 404
    assert "not found within your organisation" in zenith_revoke_resp.json()["detail"]
