from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.models.member import OrganisationMember
from app.models.user import User


class NotificationService:
    @staticmethod
    def create_notification(
        db: Session,
        organisation_id: str,
        recipient_user_id: str,
        title: str,
        message: str,
        notification_type: str,
        entity_type: str,
        entity_id: str,
    ) -> Notification:
        notif = Notification(
            organisation_id=organisation_id,
            recipient_user_id=recipient_user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            entity_type=entity_type,
            entity_id=entity_id,
            is_read=False,
        )
        db.add(notif)
        db.flush()
        return notif

    @staticmethod
    def notify_organisation_role(
        db: Session,
        organisation_id: str,
        role: str,
        title: str,
        message: str,
        notification_type: str,
        entity_type: str,
        entity_id: str,
    ) -> List[Notification]:
        members = (
            db.query(OrganisationMember)
            .filter(
                OrganisationMember.organisation_id == organisation_id,
                OrganisationMember.role == role,
            )
            .all()
        )
        created = []
        for m in members:
            notif = Notification(
                organisation_id=organisation_id,
                recipient_user_id=m.user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                entity_type=entity_type,
                entity_id=entity_id,
                is_read=False,
            )
            db.add(notif)
            created.append(notif)
        db.flush()
        return created
