from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DashboardMetricsResponse(BaseModel):
    total_applications: int
    in_progress_count: int
    awaiting_vendor_count: int
    processing_count: int
    awaiting_review_count: int
    ready_for_approval_count: int
    approved_count: int
    rejected_count: int
    escalated_count: int
    open_exceptions_count: int
    high_severity_exceptions_count: int
    stale_review_count: int
    exception_breakdown_by_category: Dict[str, int]
    exception_breakdown_by_severity: Dict[str, int]
    recent_activity: List[Dict[str, Any]]
    recently_submitted: List[Dict[str, Any]]


class QueueItemResponse(BaseModel):
    id: str
    reference_number: str
    legal_name: str
    trade_name: Optional[str] = None
    constitution: str
    status: str
    submitted_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    assigned_reviewer_id: Optional[str] = None
    assigned_reviewer_name: Optional[str] = None
    open_exceptions_count: int
    critical_exceptions_count: int
    ready_for_approval: bool


class QueueResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[QueueItemResponse]


class ReviewerUserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    role: str


class ReviewerAssignRequest(BaseModel):
    reviewer_user_id: Optional[str] = None


class DecisionApproveRequest(BaseModel):
    notes: Optional[str] = None


class DecisionRejectRequest(BaseModel):
    reason: str
    notes: Optional[str] = None


class DecisionClarificationRequest(BaseModel):
    instructions: str
    related_exception_id: Optional[str] = None
    related_field: Optional[str] = None


class DecisionEscalateRequest(BaseModel):
    reason: str
    target_role: Optional[str] = "ADMIN"
