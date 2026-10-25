import uuid

from fastapi import HTTPException

from app.models.user import User
from app.modules.notifications.models import (
    Notification,
    NotificationType,
)
from app.modules.notifications.repositories import (
    NotificationRepository,
)
from app.modules.notifications.schemas import (
    NotificationListResponse,
    NotificationResponse,
)


class NotificationService:
    def __init__(
        self,
        repository: NotificationRepository,
    ):
        self.repository = repository

    # ---------------------------------------------------------
    # CREATE NOTIFICATION
    # ---------------------------------------------------------

    def create_notification(
        self,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        actor_id: uuid.UUID | None = None,
        message: str | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> Notification | None:

        # Prevent normal social notifications
        # from being sent to the same user.
        if (
            actor_id is not None
            and actor_id == user_id
            and notification_type != NotificationType.SYSTEM
        ):
            return None

        return self.repository.create_notification(
            user_id=user_id,
            actor_id=actor_id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
        )

    # ---------------------------------------------------------
    # GET NOTIFICATION
    # ---------------------------------------------------------

    def get_notification_or_404(
        self,
        notification_id: uuid.UUID,
        current_user: User,
    ) -> Notification:

        notification = (
            self.repository.get_notification(
                notification_id
            )
        )

        if notification is None:
            raise HTTPException(
                status_code=404,
                detail="Notification not found",
            )

        # Do not expose another user's notification.
        if notification.user_id != current_user.id:
            raise HTTPException(
                status_code=404,
                detail="Notification not found",
            )

        return notification

    # ---------------------------------------------------------
    # LIST NOTIFICATIONS
    # ---------------------------------------------------------

    def get_notifications(
        self,
        current_user: User,
        limit: int,
        offset: int,
        unread_only: bool,
    ) -> NotificationListResponse:

        notifications = (
            self.repository.get_user_notifications(
                user_id=current_user.id,
                limit=limit,
                offset=offset,
                unread_only=unread_only,
            )
        )

        total = (
            self.repository.count_user_notifications(
                user_id=current_user.id,
                unread_only=unread_only,
            )
        )

        unread_count = (
            self.repository.count_unread(
                current_user.id
            )
        )

        return NotificationListResponse(
            notifications=[
                NotificationResponse.model_validate(
                    notification
                )
                for notification in notifications
            ],
            total=total,
            unread_count=unread_count,
        )

    # ---------------------------------------------------------
    # UNREAD COUNT
    # ---------------------------------------------------------

    def get_unread_count(
        self,
        current_user: User,
    ) -> int:

        return self.repository.count_unread(
            current_user.id
        )

    # ---------------------------------------------------------
    # MARK ONE READ
    # ---------------------------------------------------------

    def mark_read(
        self,
        notification_id: uuid.UUID,
        current_user: User,
    ) -> Notification:

        notification = (
            self.get_notification_or_404(
                notification_id,
                current_user,
            )
        )

        return self.repository.mark_read(
            notification
        )

    # ---------------------------------------------------------
    # MARK ONE UNREAD
    # ---------------------------------------------------------

    def mark_unread(
        self,
        notification_id: uuid.UUID,
        current_user: User,
    ) -> Notification:

        notification = (
            self.get_notification_or_404(
                notification_id,
                current_user,
            )
        )

        return self.repository.mark_unread(
            notification
        )

    # ---------------------------------------------------------
    # MARK ALL READ
    # ---------------------------------------------------------

    def mark_all_read(
        self,
        current_user: User,
    ) -> int:

        return self.repository.mark_all_read(
            current_user.id
        )

    # ---------------------------------------------------------
    # DELETE ONE
    # ---------------------------------------------------------

    def delete_notification(
        self,
        notification_id: uuid.UUID,
        current_user: User,
    ) -> None:

        notification = (
            self.get_notification_or_404(
                notification_id,
                current_user,
            )
        )

        self.repository.delete_notification(
            notification
        )

    # ---------------------------------------------------------
    # DELETE ALL
    # ---------------------------------------------------------

    def delete_all(
        self,
        current_user: User,
    ) -> int:

        return self.repository.delete_all_for_user(
            current_user.id
        )