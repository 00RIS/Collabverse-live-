import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.notifications.models import NotificationType


class NotificationCreate(BaseModel):
    user_id: uuid.UUID

    actor_id: uuid.UUID | None = None

    notification_type: NotificationType

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    message: str | None = Field(
        default=None,
        max_length=2000,
    )

    entity_type: str | None = Field(
        default=None,
        max_length=50,
    )

    entity_id: uuid.UUID | None = None


class NotificationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: uuid.UUID

    user_id: uuid.UUID

    actor_id: uuid.UUID | None

    notification_type: NotificationType

    title: str

    message: str | None

    entity_type: str | None

    entity_id: uuid.UUID | None

    is_read: bool

    created_at: datetime


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]

    total: int

    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkReadResponse(BaseModel):
    id: uuid.UUID

    is_read: bool


class MarkAllReadResponse(BaseModel):
    updated_count: int