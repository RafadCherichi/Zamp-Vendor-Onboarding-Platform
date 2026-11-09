from typing import Generator, List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

from app.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.member import OrganisationMember
from app.models.organization import Organization
from app.models.role import RoleEnum

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate JWT token and retrieve the current active user."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or are malformed.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload is missing subject identity.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or has been deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_member(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganisationMember:
    """
    Retrieve the active organisation membership context for the current user.
    Enforces organisation-level data scoping and role assignment.
    """
    # Check if a specific organisation was selected in the token claims
    token = credentials.credentials
    payload = decode_access_token(token)
    token_org_id = payload.get("org_id")

    query = db.query(OrganisationMember).join(Organization).filter(
        OrganisationMember.user_id == user.id,
        OrganisationMember.is_active == True,
        Organization.is_active == True,
    )

    if token_org_id:
        member = query.filter(OrganisationMember.organisation_id == token_org_id).first()
    else:
        member = query.first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have an active membership in any organisation.",
        )

    return member


def require_roles(allowed_roles: List[RoleEnum]):
    """
    Factory creating a role-enforcing dependency.
    Rejects unauthorized roles with HTTP 403 Forbidden.
    """
    role_values = [r.value if isinstance(r, RoleEnum) else r for r in allowed_roles]

    def role_checker(member: OrganisationMember = Depends(get_current_member)) -> OrganisationMember:
        if member.role not in role_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(role_values)}. Current role: {member.role}",
            )
        return member

    return role_checker


def scope_applications(query, member):
    """Apply organisation and case ownership before returning application data."""
    from app.models.application import Application
    from app.models.vendor import Vendor
    from sqlalchemy import or_
    query = query.filter(Application.organisation_id == member.organisation_id)
    if member.role == RoleEnum.REVIEWER.value:
        query = query.filter(Application.assigned_reviewer_id == member.user_id)
    elif member.role == RoleEnum.VENDOR.value:
        query = query.filter(or_(Application.created_by_user_id == member.user_id, Application.vendor.has(Vendor.created_by_user_id == member.user_id)))
    return query


def require_case_access(application, member):
    if application is None or application.organisation_id != member.organisation_id or (
        member.role == RoleEnum.REVIEWER.value and application.assigned_reviewer_id != member.user_id
    ):
        raise HTTPException(status_code=404, detail="Application not found or no longer assigned to you.")
