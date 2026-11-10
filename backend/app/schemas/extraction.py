from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class ExtractedFieldResponse(BaseModel):
    id: str
    field_name: str
    extracted_value: str
    normalized_value: Optional[str] = None
    confidence_score: float
    page_number: int = 1
    evidence_text: Optional[str] = None
    extraction_method: str
    vendor_corrected_value: Optional[str] = None
    vendor_correction_reason: Optional[str] = None
    vendor_corrected_by_name: Optional[str] = None
    vendor_corrected_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VendorExtractionCorrectionRequest(BaseModel):
    corrected_value: str = Field(min_length=1, max_length=2000)
    reason: str = Field(min_length=3, max_length=1000)


class VendorExtractionCorrectionResponse(BaseModel):
    field: ExtractedFieldResponse
    message: str
    validation_rerun: bool = False


class DocumentExtractionResponse(BaseModel):
    id: str
    document_id: str
    document_version_id: str
    status: str
    detected_document_type: Optional[str] = None
    classification_confidence: Optional[float] = None
    classification_reason: Optional[str] = None
    is_type_match: bool
    page_count: int = 1
    provider_used: str
    review_flags: List[str] = []
    fields: List[ExtractedFieldResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
