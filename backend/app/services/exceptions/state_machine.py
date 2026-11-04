from typing import Optional, Set
from fastapi import HTTPException, status
from app.models.exception import ExceptionStatusEnum
from app.models.role import RoleEnum

# Define valid status transition graph
VALID_TRANSITIONS = {
    ExceptionStatusEnum.OPEN.value: {
        ExceptionStatusEnum.ASSIGNED.value,
        ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
        ExceptionStatusEnum.UNDER_REVIEW.value,
        ExceptionStatusEnum.RESOLVED.value,
        ExceptionStatusEnum.ESCALATED.value,
        ExceptionStatusEnum.CLOSED.value,
    },
    ExceptionStatusEnum.ASSIGNED.value: {
        ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
        ExceptionStatusEnum.UNDER_REVIEW.value,
        ExceptionStatusEnum.RESOLVED.value,
        ExceptionStatusEnum.ESCALATED.value,
        ExceptionStatusEnum.CLOSED.value,
    },
    ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value: {
        ExceptionStatusEnum.RESPONSE_SUBMITTED.value,
        ExceptionStatusEnum.RESOLVED.value,  # Reviewer may waive or override
        ExceptionStatusEnum.ESCALATED.value,
        ExceptionStatusEnum.CLOSED.value,
    },
    ExceptionStatusEnum.RESPONSE_SUBMITTED.value: {
        ExceptionStatusEnum.UNDER_REVIEW.value,
        ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,  # Reviewer rejects correction & asks for re-submission
        ExceptionStatusEnum.RESOLVED.value,
        ExceptionStatusEnum.REJECTED.value,
        ExceptionStatusEnum.ESCALATED.value,
    },
    ExceptionStatusEnum.UNDER_REVIEW.value: {
        ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,
        ExceptionStatusEnum.RESOLVED.value,
        ExceptionStatusEnum.REJECTED.value,
        ExceptionStatusEnum.ESCALATED.value,
        ExceptionStatusEnum.CLOSED.value,
    },
    ExceptionStatusEnum.RESOLVED.value: {
        ExceptionStatusEnum.OPEN.value,  # Controlled reopening with mandatory reason
        ExceptionStatusEnum.CLOSED.value,
    },
    ExceptionStatusEnum.REJECTED.value: {
        ExceptionStatusEnum.OPEN.value,  # Reopened
        ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value,  # Request corrected submission
        ExceptionStatusEnum.UNDER_REVIEW.value,
        ExceptionStatusEnum.ESCALATED.value,
        ExceptionStatusEnum.CLOSED.value,
    },
    ExceptionStatusEnum.ESCALATED.value: {
        ExceptionStatusEnum.UNDER_REVIEW.value,
        ExceptionStatusEnum.RESOLVED.value,
        ExceptionStatusEnum.REJECTED.value,
        ExceptionStatusEnum.CLOSED.value,
    },
    ExceptionStatusEnum.CLOSED.value: {
        ExceptionStatusEnum.OPEN.value,  # Reopened with mandatory reason
    },
}


def validate_transition(
    current_status: str,
    target_status: str,
    actor_role: str,
    reason: Optional[str] = None,
) -> None:
    """
    Validates exception lifecycle transition against the statutory state machine
    and actor role permissions.
    """
    if current_status == target_status:
        return

    allowed_targets = VALID_TRANSITIONS.get(current_status, set())
    if target_status not in allowed_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid exception status transition from '{current_status}' to '{target_status}'. Allowed transitions: {sorted(allowed_targets)}",
        )

    # Vendor role guardrails:
    # Vendors can ONLY submit a correction response when action is requested from them.
    if actor_role == RoleEnum.VENDOR.value:
        if current_status != ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value or target_status != ExceptionStatusEnum.RESPONSE_SUBMITTED.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Vendors are only permitted to submit corrections for exceptions marked '{ExceptionStatusEnum.ACTION_REQUIRED_FROM_VENDOR.value}'.",
            )

    # Reopening resolved/closed exceptions requires a mandatory reason
    if current_status in [ExceptionStatusEnum.RESOLVED.value, ExceptionStatusEnum.CLOSED.value] and target_status == ExceptionStatusEnum.OPEN.value:
        if not reason or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A clear, reasoned justification is mandatory to reopen a resolved or closed exception.",
            )

    # Rejection or Escalation requires a mandatory reason
    if target_status in [ExceptionStatusEnum.REJECTED.value, ExceptionStatusEnum.ESCALATED.value]:
        if not reason or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A reason is required when transitioning an exception to '{target_status}'.",
            )
