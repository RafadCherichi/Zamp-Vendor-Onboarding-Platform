from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.deps import get_current_user, get_current_member
from app.models.user import User
from app.models.member import OrganisationMember
from app.models.organization import Organization
from app.schemas.auth import LoginRequest, TokenResponse, UserProfile, OrganisationInfo

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate User",
    description="Authenticate with email and password. Returns a signed JWT token with organisation scoping.",
)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email_clean = request.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact your administrator.",
        )

    # Resolve active membership and organisation
    member = (
        db.query(OrganisationMember)
        .join(Organization)
        .filter(
            OrganisationMember.user_id == user.id,
            OrganisationMember.is_active == True,
            Organization.is_active == True,
        )
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active organisation membership found for this user.",
        )

    token_payload = {
        "sub": user.id,
        "email": user.email,
        "org_id": member.organisation_id,
        "role": member.role,
    }
    access_token = create_access_token(token_payload)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserProfile(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=member.role,
            organisation=OrganisationInfo(
                id=member.organization.id,
                name=member.organization.name,
                slug=member.organization.slug,
            ),
        ),
    )


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get Current User Profile",
    description="Returns the profile and active organisation membership of the currently authenticated user.",
)
def get_me(member: OrganisationMember = Depends(get_current_member)) -> UserProfile:
    return UserProfile(
        id=member.user.id,
        email=member.user.email,
        full_name=member.user.full_name,
        role=member.role,
        organisation=OrganisationInfo(
            id=member.organization.id,
            name=member.organization.name,
            slug=member.organization.slug,
        ),
    )


@router.post(
    "/logout",
    summary="Logout User",
    description="Stateless logout hook. Frontend discards stored credentials.",
)
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Successfully logged out."}
