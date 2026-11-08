from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_member
from app.models.member import OrganisationMember
from app.models.notification import Notification
from app.schemas.notification import NotificationResponse

router = APIRouter()


@router.get(
    "/count",
    summary="Get unread notification count",
)
def get_unread_notification_count(
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> dict:
    unread_count = db.query(Notification.id).filter(
        Notification.organisation_id == member.organisation_id,
        Notification.recipient_user_id == member.user_id,
        Notification.is_read.is_(False),
    ).count()
    return {"unread_count": unread_count}


@router.get(
    "/",
    response_model=List[NotificationResponse],
    summary="Get User Notifications",
    description="Retrieves notifications for the current user in this organisation.",
)
def get_user_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> List[NotificationResponse]:
    query = db.query(Notification).filter(
        Notification.organisation_id == member.organisation_id,
        Notification.recipient_user_id == member.user_id,
    )
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    return query.order_by(Notification.created_at.desc()).limit(50).all()


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark Notification as Read",
)
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
) -> NotificationResponse:
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.organisation_id == member.organisation_id,
        Notification.recipient_user_id == member.user_id,
    ).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.post(
    "/read-all",
    summary="Mark All Notifications as Read",
)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    member: OrganisationMember = Depends(get_current_member),
):
    db.query(Notification).filter(
        Notification.organisation_id == member.organisation_id,
        Notification.recipient_user_id == member.user_id,
        Notification.is_read.is_(False),
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}
