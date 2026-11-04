import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, field_validator


class ValidationFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    check_id: str
    layer: str
    check_name: str
    status: str
    severity: str
    source_document_id: Optional[str] = None
    source_version_id: Optional[str] = None
    submitted_value: Optional[str] = None
    extracted_value: Optional[str] = None
    external_value: Optional[str] = None
    evidence: Optional[str] = None
    explanation: str
    recommended_action: Optional[str] = None
    is_stale: bool = False
    stale_reason: Optional[str] = None
    created_at: datetime


class ExternalVerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    verification_type: str
    provider_name: str
    request_id: str
    submitted_identifier: str
    status: str
    is_simulated: bool
    returned_attributes_json: Optional[str] = None
    returned_attributes: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    duration_ms: int
    created_at: datetime

    @field_validator("returned_attributes", mode="before")
    @classmethod
    def parse_attributes(cls, v, values):
        if v is not None:
            return v
        raw = values.data.get("returned_attributes_json")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return {}
        return {}


class DuplicateSignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    candidate_application_id: str
    candidate_vendor_id: str
    match_strength: str
    matching_attributes_json: str
    matching_attributes: Optional[List[str]] = None
    explanation: str
    recommended_action: str
    is_dismissed: bool
    created_at: datetime

    @field_validator("matching_attributes", mode="before")
    @classmethod
    def parse_attrs(cls, v, values):
        if v is not None:
            return v
        raw = values.data.get("matching_attributes_json")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return []
        return []


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    entity_type: str
    entity_id: Optional[str] = None
    actor_role: Optional[str] = None
    details_json: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    @field_validator("details", mode="before")
    @classmethod
    def parse_details(cls, v, values):
        if v is not None:
            return v
        raw = values.data.get("details_json")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return {}
        return {}


class ValidationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    organisation_id: str
    run_type: str
    status: str
    summary: Optional[str] = None
    passed_count: int
    failed_count: int
    warning_count: int
    unverified_count: int
    unavailable_count: int
    is_current: bool
    trigger_reason: Optional[str] = None
    created_at: datetime
    findings: List[ValidationFindingResponse] = []


class ValidationTriggerRequest(BaseModel):
    run_type: Optional[str] = "FULL"
    trigger_reason: Optional[str] = "Manual validation trigger"
