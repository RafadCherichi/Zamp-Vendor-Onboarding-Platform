from datetime import datetime, timezone
from pydantic import BaseModel, field_serializer


def as_utc(value):
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def iso_utc(value):
    return as_utc(value).isoformat() if value else None


class UTCResponseModel(BaseModel):
    """SQLite drops timezone offsets; persisted timestamps in this app are UTC."""
    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_timestamp(self, value):
        return as_utc(value)
