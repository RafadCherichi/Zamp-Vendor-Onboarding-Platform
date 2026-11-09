from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import generate_invitation_token, hash_invitation_token
from app.core.deps import get_current_member, require_roles
from app.models.member import OrganisationMember
from app.models.role import RoleEnum
from app.models.invitation import Invitation, InvitationStatusEnum
from app.models.organization import Organization
from app.schemas.invitation import (
    InvitationCreate,
    InvitationResponse,
    InvitationPublicResponse,
    InvitationAcceptRequest,
)

router = APIRouter()


def claim_invitation(db, invitation):
    now = datetime.now(timezone.utc)
    changed = db.query(Invitation).filter(
        Invitation.id == invitation.id,
        Invitation.status == InvitationStatusEnum.PENDING.value,
        Invitation.expires_at > now,
    ).update({"status": InvitationStatusEnum.ACCEPTED.value, "accepted_at": now}, synchronize_session=False)
    if changed != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="This invitation changed or has already been used. Ask the buyer for a current invitation.")


def mask_email(email: str) -> str:
    """Mask email for safe public presentation (e.g., v***r@domain.com)."""
    try:
        user_part, domain = email.split("@")
        if len(user_part) <= 2:
            masked_user = user_part[0] + "*"
        else:
            masked_user = user_part[0] + ("*" * (len(user_part) - 2)) + user_part[-1]
        return f"{masked_user}@{domain}"
    except Exception:
        return email


@router.post(
    "",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Vendor Invitation",
    description="Generate a unique, cryptographically random vendor invitation token. Stoped only as SHA-256 hash.",
)
def create_invitation(
    data: InvitationCreate,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.PROCUREMENT_OFFICER])),
) -> InvitationResponse:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=data.days_valid)

    # Generate high-entropy token and its SHA-256 hash
    raw_token, token_hash = generate_invitation_token()

    # Expire any existing pending invitations for this vendor email in this organisation
    existing = (
        db.query(Invitation)
        .filter(
            Invitation.organisation_id == member.organisation_id,
            Invitation.vendor_email == data.vendor_email.lower(),
            Invitation.status == InvitationStatusEnum.PENDING.value,
        )
        .all()
    )
    for inv in existing:
        inv.status = InvitationStatusEnum.REVOKED.value
        inv.revoked_at = now

    invitation = Invitation(
        organisation_id=member.organisation_id,
        invited_by_user_id=member.user_id,
        vendor_name=data.vendor_name.strip(),
        vendor_email=data.vendor_email.lower().strip(),
        token_hash=token_hash,
        status=InvitationStatusEnum.PENDING.value,
        expires_at=expires_at,
        custom_message=data.custom_message,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    # For development/demo purposes, construct the direct link containing the raw token.
    # In production, this raw token would only be dispatched via transactional email and never stored.
    demo_url = f"/invite/{raw_token}"

    response_data = InvitationResponse.model_validate(invitation)
    response_data.demo_invitation_url = demo_url
    return response_data


@router.get(
    "",
    response_model=List[InvitationResponse],
    summary="List Organisation Invitations",
    description="Retrieve all vendor invitations scoped to the current user's organisation.",
)
def list_invitations(
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(
        require_roles([RoleEnum.ADMIN, RoleEnum.PROCUREMENT_OFFICER, RoleEnum.REVIEWER])
    ),
) -> List[InvitationResponse]:
    # Strictly scoped to current user's organisation
    invitations = (
        db.query(Invitation)
        .filter(Invitation.organisation_id == member.organisation_id)
        .order_by(Invitation.created_at.desc())
        .all()
    )

    now = datetime.now(timezone.utc)
    has_updates = False
    for inv in invitations:
        # Check and update expired status dynamically
        if inv.status == InvitationStatusEnum.PENDING.value and inv.is_expired:
            inv.status = InvitationStatusEnum.EXPIRED.value
            has_updates = True

    if has_updates:
        db.commit()

    return [InvitationResponse.model_validate(inv) for inv in invitations]


@router.post(
    "/{invitation_id}/revoke",
    response_model=InvitationResponse,
    summary="Revoke Vendor Invitation",
    description="Revoke an active invitation. Must belong to the current user's organisation.",
)
def revoke_invitation(
    invitation_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.PROCUREMENT_OFFICER])),
) -> InvitationResponse:
    # Organisation isolation: filter by both id and organisation_id
    invitation = (
        db.query(Invitation)
        .filter(
            Invitation.id == invitation_id,
            Invitation.organisation_id == member.organisation_id,
        )
        .first()
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found within your organisation.",
        )

    if invitation.status in [InvitationStatusEnum.REVOKED.value, InvitationStatusEnum.ACCEPTED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot revoke an invitation that is already {invitation.status}.",
        )

    invitation.status = InvitationStatusEnum.REVOKED.value
    invitation.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(invitation)

    return InvitationResponse.model_validate(invitation)


@router.get(
    "/token/{token}",
    response_model=InvitationPublicResponse,
    summary="Validate Invitation Token",
    description="Public endpoint for vendors to validate an invitation link and retrieve safe context.",
)
def validate_invitation_token(
    token: str,
    db: Session = Depends(get_db),
) -> InvitationPublicResponse:
    token_hash = hash_invitation_token(token)
    invitation = (
        db.query(Invitation)
        .join(Organization)
        .filter(Invitation.token_hash == token_hash)
        .first()
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The invitation link is invalid or has expired.",
        )

    # Check status and expiration
    if invitation.status == InvitationStatusEnum.REVOKED.value:
        return InvitationPublicResponse(
            is_valid=False,
            status=InvitationStatusEnum.REVOKED.value,
            vendor_name=invitation.vendor_name,
            vendor_email=mask_email(invitation.vendor_email),
            buyer_organisation_name=invitation.organization.name,
            expires_at=invitation.expires_at,
            message="This invitation has been revoked by the issuing buyer.",
        )

    if invitation.is_expired:
        if invitation.status == InvitationStatusEnum.PENDING.value:
            invitation.status = InvitationStatusEnum.EXPIRED.value
            db.commit()
        return InvitationPublicResponse(
            is_valid=False,
            status=InvitationStatusEnum.EXPIRED.value,
            vendor_name=invitation.vendor_name,
            vendor_email=mask_email(invitation.vendor_email),
            buyer_organisation_name=invitation.organization.name,
            expires_at=invitation.expires_at,
            message="This invitation link has expired. Please contact the buyer for a new invitation.",
        )

    if invitation.status == InvitationStatusEnum.ACCEPTED.value:
        return InvitationPublicResponse(
            is_valid=False,
            status=InvitationStatusEnum.ACCEPTED.value,
            vendor_name=invitation.vendor_name,
            vendor_email=mask_email(invitation.vendor_email),
            buyer_organisation_name=invitation.organization.name,
            expires_at=invitation.expires_at,
            message="This invitation has already been accepted and submitted.",
        )

    return InvitationPublicResponse(
        is_valid=True,
        status=InvitationStatusEnum.PENDING.value,
        vendor_name=invitation.vendor_name,
        vendor_email=mask_email(invitation.vendor_email),
        buyer_organisation_name=invitation.organization.name,
        expires_at=invitation.expires_at,
        message=invitation.custom_message,
    )


@router.post(
    "/token/{token}/accept",
    response_model=dict,
    summary="Accept Vendor Invitation",
    description="Accept an invitation, establish the vendor user account, and initialize the onboarding application.",
)
def accept_invitation(
    token: str,
    data: InvitationAcceptRequest,
    db: Session = Depends(get_db),
):
    import secrets
    from app.core.security import hash_password, create_access_token, verify_password
    from app.models.user import User
    from app.models.vendor import Vendor
    from app.models.application import Application, ApplicationStatusEnum, ConstitutionEnum
    from app.services.checklist import sync_application_documents

    token_hash = hash_invitation_token(token)
    invitation = (
        db.query(Invitation)
        .join(Organization)
        .filter(Invitation.token_hash == token_hash)
        .first()
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation token not recognized or invalid.",
        )

    if invitation.status == InvitationStatusEnum.REVOKED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has been revoked by the issuing buyer.",
        )

    if invitation.is_expired:
        invitation.status = InvitationStatusEnum.EXPIRED.value
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation link has expired. Please contact the buyer for a new invitation.",
        )

    if invitation.status == InvitationStatusEnum.ACCEPTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has already been accepted.",
        )

    now = datetime.now(timezone.utc)

    # Prove ownership before claiming a link for an existing account.
    user = db.query(User).filter(User.email == invitation.vendor_email.lower()).first()
    if user and (not user.is_active or not verify_password(data.password, user.hashed_password)):
        raise HTTPException(status_code=401, detail="This email already has an account. Enter its existing password to accept the invitation.")
    claim_invitation(db, invitation)
    if not user:
        user = User(email=invitation.vendor_email.lower(), hashed_password=hash_password(data.password), full_name=data.full_name or invitation.vendor_name, is_active=True)
        db.add(user)
        db.flush()

    # 2. Establish Organisation Membership as Vendor
    member = (
        db.query(OrganisationMember)
        .filter(
            OrganisationMember.user_id == user.id,
            OrganisationMember.organisation_id == invitation.organisation_id,
        )
        .first()
    )
    if not member:
        member = OrganisationMember(
            user_id=user.id,
            organisation_id=invitation.organisation_id,
            role=RoleEnum.VENDOR.value,
            is_active=True,
        )
        db.add(member)
        db.flush()

    if member.role != RoleEnum.VENDOR.value or not member.is_active:
        raise HTTPException(status_code=403, detail="This account cannot accept a vendor invitation for this organisation.")

    # 3. Mark Invitation Accepted
    invitation.status = InvitationStatusEnum.ACCEPTED.value
    invitation.accepted_at = now

    # 4. Create or retrieve Vendor legal identity
    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.organisation_id == invitation.organisation_id,
            Vendor.created_by_user_id == user.id,
        )
        .first()
    )
    if not vendor:
        vendor = Vendor(
            organisation_id=invitation.organisation_id,
            created_by_user_id=user.id,
            legal_name=invitation.vendor_name,
            constitution=ConstitutionEnum.PROPRIETORSHIP.value,
        )
        db.add(vendor)
        db.flush()

    # 5. Create or retrieve active Application draft
    application = (
        db.query(Application)
        .filter(
            Application.vendor_id == vendor.id,
            Application.organisation_id == invitation.organisation_id,
            Application.status.in_([ApplicationStatusEnum.DRAFT.value, ApplicationStatusEnum.IN_PROGRESS.value]),
        )
        .first()
    )
    if not application:
        ref_num = f"APP-{now.year}-{secrets.token_hex(3).upper()}"
        application = Application(
            organisation_id=invitation.organisation_id,
            vendor_id=vendor.id,
            invitation_id=invitation.id,
            created_by_user_id=user.id,
            reference_number=ref_num,
            legal_name=invitation.vendor_name,
            contact_email=invitation.vendor_email,
            status=ApplicationStatusEnum.IN_PROGRESS.value,
            categories_json="[]",
        )
        db.add(application)
        db.flush()
        sync_application_documents(db, application)

    db.commit()

    # Issue JWT token for immediate authenticated login
    token_payload = {
        "sub": user.id,
        "email": user.email,
        "org_id": invitation.organisation_id,
        "role": RoleEnum.VENDOR.value,
    }
    access_token = create_access_token(token_payload)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": RoleEnum.VENDOR.value,
            "organisation": {
                "id": invitation.organization.id,
                "name": invitation.organization.name,
                "slug": invitation.organization.slug,
            },
        },
        "application_id": application.id,
        "reference_number": application.reference_number,
    }
