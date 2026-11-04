from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class InvitationCreate(BaseModel):
    vendor_name: str = Field(..., min_length=2, max_length=255, description="Legal or trade name of the vendor")
    vendor_email: EmailStr = Field(..., description="Business email of the vendor contact")
    days_valid: int = Field(7, ge=1, le=90, description="Number of days until the invitation expires")
    custom_message: Optional[str] = Field(None, max_length=1000, description="Optional note to the vendor")


class InvitationResponse(BaseModel):
    id: str
    organisation_id: str
    vendor_name: str
    vendor_email: str
    status: str
    expires_at: datetime
    created_at: datetime
    accepted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    custom_message: Optional[str] = None
    # Safe demo link generated only upon creation or dev retrieval for testing
    demo_invitation_url: Optional[str] = Field(None, description="[DEMO ONLY] Simulated direct link without real email dispatch")

    model_config = {"from_attributes": True}


class InvitationPublicResponse(BaseModel):
    """
    Vendor-safe context returned when a vendor opens an invitation link.
    Contains no internal buyer operational notes or raw secrets.
    """
    is_valid: bool
    status: str
    vendor_name: str
    vendor_email: str
    buyer_organisation_name: str
    expires_at: datetime
    message: Optional[str] = None
