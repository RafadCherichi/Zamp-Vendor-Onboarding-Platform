from app.schemas.common import UTCResponseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class DocumentVersionResponse(UTCResponseModel):
    id: str
    version_number: int
    original_filename: str
    file_size_bytes: int
    content_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentSlotResponse(UTCResponseModel):
    id: str
    document_type: str
    title: str
    is_required: bool
    requirement_reason: Optional[str] = None
    status: str
    current_version: Optional[DocumentVersionResponse] = None
    versions_count: int = 0
    accepted_extensions: List[str] = [".pdf", ".jpg", ".jpeg", ".png"]
    max_size_mb: int = 15
    # Processing & Extraction Insights
    processing_status: Optional[str] = None
    detected_document_type: Optional[str] = None
    is_type_match: Optional[bool] = None
    review_flags: List[str] = []
    extracted_fields_summary: Dict[str, str] = {}

    model_config = {"from_attributes": True}


class ApplicationDraftUpdate(BaseModel):
    # Section 1: Business Identity
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    constitution: Optional[str] = None
    date_of_establishment: Optional[str] = None
    registered_address: Optional[str] = None
    operating_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    # Section 2: Tax & Registration
    pan: Optional[str] = None
    is_gst_registered: Optional[bool] = None
    gstin: Optional[str] = None
    is_udyam_registered: Optional[bool] = None
    udyam_number: Optional[str] = None
    cin_llpin: Optional[str] = None

    # Section 3: Authorised Contact
    contact_name: Optional[str] = None
    contact_designation: Optional[str] = None
    contact_email: Optional[str] = None
    contact_mobile: Optional[str] = None
    authorised_signatory_name: Optional[str] = None

    # Section 4: Banking Details
    bank_account_holder_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_account_type: Optional[str] = None
    bank_name: Optional[str] = None

    # Section 5: Business Classification
    categories: Optional[List[str]] = None
    other_business_activity_description: Optional[str] = None

    # Section 6: Declarations & Consent
    declaration_accurate_info: Optional[bool] = None
    declaration_authorised_rep: Optional[bool] = None
    declaration_verification_consent: Optional[bool] = None


class ApplicationResponse(UTCResponseModel):
    demo_profile_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    id: str
    reference_number: str
    organisation_id: str
    vendor_id: str
    status: str
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    rejection_reason: Optional[str] = None

    # Section 1
    legal_name: str
    trade_name: Optional[str] = None
    constitution: str
    date_of_establishment: Optional[str] = None
    registered_address: Optional[str] = None
    operating_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    # Section 2
    pan: Optional[str] = None
    is_gst_registered: bool
    gstin: Optional[str] = None
    is_udyam_registered: bool
    udyam_number: Optional[str] = None
    cin_llpin: Optional[str] = None

    # Section 3
    contact_name: Optional[str] = None
    contact_designation: Optional[str] = None
    contact_email: Optional[str] = None
    contact_mobile: Optional[str] = None
    authorised_signatory_name: Optional[str] = None

    # Section 4
    bank_account_holder_name: Optional[str] = None
    bank_account_number: Optional[str] = None  # Masked in response
    bank_ifsc: Optional[str] = None
    bank_account_type: Optional[str] = None
    bank_name: Optional[str] = None

    # Section 5
    categories: List[str] = []
    other_business_activity_description: Optional[str] = None

    # Section 6
    declaration_accurate_info: bool
    declaration_authorised_rep: bool
    declaration_verification_consent: bool
    declaration_timestamp: Optional[datetime] = None

    # Documents checklist
    documents: List[DocumentSlotResponse] = []


class ApplicationSubmitResponse(UTCResponseModel):
    success: bool
    reference_number: str
    status: str
    submitted_at: datetime
    message: str
