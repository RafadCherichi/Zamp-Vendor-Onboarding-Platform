import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator


class ExceptionTransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    from_status: str
    to_status: str
    actor_role: str
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class ExceptionCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author_role: str
    is_internal: bool
    message: str
    created_at: datetime


class FieldCorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    field_name: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by_role: str
    vendor_explanation: Optional[str] = None
    created_at: datetime


class OnboardingExceptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference_number: str
    application_id: str
    organisation_id: str
    vendor_id: str
    category: str
    title: str
    description: str
    severity: str
    source_check_ids_json: Optional[str] = "[]"
    source_check_ids: Optional[List[str]] = None
    source_finding_id: Optional[str] = None
    related_document_id: Optional[str] = None
    related_version_id: Optional[str] = None
    related_field_name: Optional[str] = None
    assigned_user_id: Optional[str] = None
    assigned_role: Optional[str] = None
    status: str
    vendor_action_instruction: Optional[str] = None
    resolution_type: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_by_role: str
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    transitions: List[ExceptionTransitionResponse] = []
    comments: List[ExceptionCommentResponse] = []
    field_corrections: List[FieldCorrectionResponse] = []

    @field_validator("source_check_ids", mode="before")
    @classmethod
    def parse_check_ids(cls, v, values):
        if v is not None:
            return v
        raw = values.data.get("source_check_ids_json")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return []
        return []


class ExceptionCreateRequest(BaseModel):
    application_id: str
    category: str
    title: str
    description: str
    severity: str = "MEDIUM"
    source_check_ids: Optional[List[str]] = []
    related_document_id: Optional[str] = None
    related_field_name: Optional[str] = None
    vendor_action_instruction: Optional[str] = None
    assigned_user_id: Optional[str] = None
    assigned_role: Optional[str] = None
    initial_status: Optional[str] = "OPEN"


class ExceptionTransitionRequest(BaseModel):
    target_status: str
    reason: Optional[str] = None
    notes: Optional[str] = None
    resolution_type: Optional[str] = None
    resolution_notes: Optional[str] = None
    vendor_action_instruction: Optional[str] = None


class ExceptionAssignRequest(BaseModel):
    assigned_user_id: Optional[str] = None
    assigned_role: Optional[str] = None
    reason: Optional[str] = None


class ExceptionCommentCreate(BaseModel):
    message: str
    is_internal: bool = False


class VendorCorrectionSubmitRequest(BaseModel):
    field_name: Optional[str] = None
    new_field_value: Optional[str] = None
    explanation: Optional[str] = None
