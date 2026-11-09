from app.schemas.common import UTCResponseModel
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NotificationResponse(UTCResponseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    message: str
    notification_type: str
    entity_type: str
    entity_id: str
    is_read: bool
    created_at: datetime
