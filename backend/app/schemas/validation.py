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


CHECK_ORDER_WEIGHTS: Dict[str, int] = {
    # 1. Business Identity
    "A_LEGAL_NAME_VALIDITY": 101,
    "A_CONSTITUTION_RULE": 102,
    "A_PINCODE_FORMAT": 103,
    "A_CITY_STATE_MATCH": 104,
    "B_NAME_PAN_DOC_MATCH": 105,
    "B_NAME_GST_DOC_MATCH": 106,
    "B_NAME_COI_DOC_MATCH": 107,

    # 2. Tax Registration
    "A_PAN_FORMAT_AND_CONSTITUTION": 201,
    "A_GSTIN_FORMAT_AND_CHECKSUM": 202,
    "A_UDYAM_FORMAT": 203,
    "A_CIN_LLPIN_STRUCTURE": 204,
    "B_GSTIN_EMBEDDED_PAN_MATCH": 205,

    # 3. Contact Details
    "A_CONTACT_EMAIL_FORMAT": 301,
    "A_CONTACT_MOBILE_FORMAT": 302,
    "A_AUTHORISED_SIGNATORY_RULE": 303,

    # 4. Banking Details
    "A_BANK_IFSC_STRUCTURE": 401,
    "A_BANK_ACCOUNT_NUM_STRUCTURE": 402,
    "B_BANK_ACCOUNT_NUM_MATCH": 403,
    "B_BANK_IFSC_MATCH": 404,
    "C_BANK_PENNY_DROP_VERIF": 405,

    # 5. Document Matching
    "B_PAN_DOC_CROSS_MATCH": 501,
    "B_GST_DOC_CROSS_MATCH": 502,
    "B_COI_DOC_CROSS_MATCH": 503,
    "B_BANK_DOC_CROSS_MATCH": 504,
    "B_UDYAM_DOC_CROSS_MATCH": 505,

    # 6. External Verification
    "C_PAN_EXTERNAL_VERIF": 601,
    "C_GSTIN_EXTERNAL_VERIF": 602,
    "C_MCA_EXTERNAL_VERIF": 603,
    "C_UDYAM_EXTERNAL_VERIF": 604,

    # 7. Duplicate Candidate Detection
    "D_DUPLICATE_PAN": 701,
    "D_DUPLICATE_GSTIN": 702,
    "D_DUPLICATE_BANK_ACCOUNT": 703,
    "D_DUPLICATE_NAME_CITY": 704,
}


def get_check_order_weight(check_id: Optional[str], check_name: Optional[str] = None) -> int:
    if not check_id:
        return 999
    if check_id in CHECK_ORDER_WEIGHTS:
        return CHECK_ORDER_WEIGHTS[check_id]
    cid = (check_id or "").upper()
    cname = (check_name or "").upper()
    combo = f"{cid} {cname}"

    # Group 7: Duplicates (check first so 'Duplicate PAN' doesn't match Tax group)
    if "DUP" in cid or "DUPLICATE" in cname or cid.startswith("D_"):
        return 705
    # Group 6: External Registry Checks
    if "EXT" in cid or "EXTERNAL" in cname or cid.startswith("C_"):
        return 605
    # Group 5: Document & Cross-Checks
    if "DOC" in cid or "CROSS" in cname or cid.startswith("B_"):
        return 505
    # Group 4: Banking & Payments
    if "BANK" in combo or "IFSC" in combo or "ACCOUNT" in combo:
        return 405
    # Group 3: Contact Details
    if "CONTACT" in combo or "EMAIL" in combo or "MOBILE" in combo:
        return 305
    # Group 2: Tax Registration
    if "PAN" in combo or "GST" in combo or "TAX" in combo or "UDYAM" in combo or "CIN" in combo:
        return 205
    # Group 1: Business Identity & Constitution
    if "CON" in combo or "LEGAL_NAME" in combo or "ENTITY" in combo or "IDENTITY" in combo:
        return 105
    if cid.startswith("A_"):
        return 150
    return 999


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

    @field_validator("findings", mode="before")
    @classmethod
    def sort_findings(cls, v):
        if not v:
            return []
        def get_key(item):
            cid = getattr(item, "check_id", None) or (item.get("check_id") if isinstance(item, dict) else "")
            cname = getattr(item, "check_name", None) or (item.get("check_name") if isinstance(item, dict) else "")
            return (get_check_order_weight(cid, cname), cid or "")
        return sorted(v, key=get_key)


class ValidationRunHistoryItemResponse(BaseModel):
    """A compact, human-readable record of one real validation execution."""

    id: str
    application_id: str
    application_reference: str
    vendor_name: str
    run_type: str
    run_status: str
    outcome: str
    application_status: str
    summary: Optional[str] = None
    reason: str
    passed_count: int
    failed_count: int
    warning_count: int
    unverified_count: int
    unavailable_count: int
    is_current: bool
    created_at: datetime


class ValidationTriggerRequest(BaseModel):
    run_type: Optional[str] = "FULL"
    trigger_reason: Optional[str] = "Manual validation trigger"
