from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models.organization import Organization
from app.models.user import User
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.invitation import Invitation, InvitationStatusEnum
from app.core.security import hash_password, generate_invitation_token


def seed_database():
    """
    Seed deterministic synthetic development/demo accounts and organisations.
    Safe for local testing and demonstration.
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

        # 2. Users and Memberships
        demo_accounts = [
            {
                "email": "admin@apex.com",
                "name": "Aditya Sharma",
                "role": RoleEnum.ADMIN.value,
                "org_id": apex_org.id,
            },
            {
                "email": "procurement@apex.com",
                "name": "Pooja Verma",
                "role": RoleEnum.PROCUREMENT_OFFICER.value,
                "org_id": apex_org.id,
            },
            {
                "email": "reviewer@apex.com",
                "name": "Rajesh Iyer",
                "role": RoleEnum.REVIEWER.value,
                "org_id": apex_org.id,
            },
            {
                "email": "vendor@apexcomponents.com",
                "name": "Vikram Malhotra",
                "role": RoleEnum.VENDOR.value,
                "org_id": apex_org.id,
            },
            # Secondary organisation user for cross-tenant testing
            {
                "email": "procurement@zenith.com",
                "name": "Zoya Akhtar",
                "role": RoleEnum.PROCUREMENT_OFFICER.value,
                "org_id": zenith_org.id,
            },
        ]

        default_hashed_pw = hash_password("Password123!")

        for acc in demo_accounts:
            user = db.query(User).filter(User.email == acc["email"]).first()
            if not user:
                user = User(
                    email=acc["email"],
                    full_name=acc["name"],
                    hashed_password=default_hashed_pw,
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)

            # Ensure membership
            member = (
                db.query(OrganisationMember)
                .filter(
                    OrganisationMember.user_id == user.id,
                    OrganisationMember.organisation_id == acc["org_id"],
                )
                .first()
            )
            if not member:
                member = OrganisationMember(
                    user_id=user.id,
                    organisation_id=acc["org_id"],
                    role=acc["role"],
                    is_active=True,
                )
                db.add(member)

        db.commit()

        # 3. Seed Sample Invitations for Apex Enterprises (if none exist)
        apex_invites_count = db.query(Invitation).filter(Invitation.organisation_id == apex_org.id).count()
        if apex_invites_count == 0:
            procurement_user = db.query(User).filter(User.email == "procurement@apex.com").first()
            now = datetime.now(timezone.utc)

            # Pending invitation
            raw_token_pending, hash_pending = generate_invitation_token()
            inv_pending = Invitation(
                organisation_id=apex_org.id,
                invited_by_user_id=procurement_user.id if procurement_user else None,
                vendor_name="Apex Precision Fasteners Pvt Ltd",
                vendor_email="onboarding@apexprecision.in",
                token_hash=hash_pending,
                status=InvitationStatusEnum.PENDING.value,
                expires_at=now + timedelta(days=7),
                custom_message="Please complete your GST, PAN and Bank details for our annual vendor panel.",
            )
            db.add(inv_pending)

            # Expired invitation
            _, hash_expired = generate_invitation_token()
            inv_expired = Invitation(
                organisation_id=apex_org.id,
                invited_by_user_id=procurement_user.id if procurement_user else None,
                vendor_name="Southern Logistics Express",
                vendor_email="contact@southernlogistics.co.in",
                token_hash=hash_expired,
                status=InvitationStatusEnum.EXPIRED.value,
                expires_at=now - timedelta(days=2),
                custom_message="Expedited onboarding for Q3 transport contract.",
            )
            db.add(inv_expired)

            # Revoked invitation
            _, hash_revoked = generate_invitation_token()
            inv_revoked = Invitation(
                organisation_id=apex_org.id,
                invited_by_user_id=procurement_user.id if procurement_user else None,
                vendor_name="Delta Heavy Tools Corp",
                vendor_email="accounts@deltaheavy.com",
                token_hash=hash_revoked,
                status=InvitationStatusEnum.REVOKED.value,
                expires_at=now + timedelta(days=5),
                revoked_at=now - timedelta(hours=6),
                custom_message="Revoked due to change in vendor entity.",
            )
            db.add(inv_revoked)

            db.commit()

        print("[Seed] Successfully seeded organisations, demo accounts, and sample invitations.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
