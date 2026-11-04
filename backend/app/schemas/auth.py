from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class OrganisationInfo(BaseModel):
    id: str
    name: str
    slug: str


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    organisation: OrganisationInfo


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile
