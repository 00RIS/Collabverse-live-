import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.modules.notifications.models import (
    Notification,
    NotificationType,
)


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        actor_id: uuid.UUID | None = None,
        message: str | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> Notification:

        notification = Notification(
            user_id=user_id,
            actor_id=actor_id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
        )

        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        return notification

    def get_notification(
        self,
        notification_id: uuid.UUID,
    ) -> Notification | None:

        return self.db.get(
            Notification,
            notification_id,
        )

    def get_user_notifications(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[Notification]:

        query = select(Notification).where(
            Notification.user_id == user_id
        )

        if unread_only:
            query = query.where(
                Notification.is_read.is_(False)
            )

        query = (
            query
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        return list(
            self.db.scalars(query).all()
        )

    def count_user_notifications(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
    ) -> int:

        query = select(
            func.count(Notification.id)
        ).where(
            Notification.user_id == user_id
        )

        if unread_only:
            query = query.where(
                Notification.is_read.is_(False)
            )

        result = self.db.scalar(query)

        return result or 0

    def count_unread(
        self,
        user_id: uuid.UUID,
    ) -> int:

        return self.count_user_notifications(
            user_id=user_id,
            unread_only=True,
        )

    def mark_read(
        self,
        notification: Notification,
    ) -> Notification:

        notification.is_read = True

        self.db.commit()
        self.db.refresh(notification)

        return notification

    def mark_unread(
        self,
        notification: Notification,
    ) -> Notification:

        notification.is_read = False

        self.db.commit()
        self.db.refresh(notification)

        return notification

    def mark_all_read(
        self,
        user_id: uuid.UUID,
    ) -> int:

        statement = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )

        result = self.db.execute(statement)
        self.db.commit()

        return result.rowcount or 0

    def delete_notification(
        self,
        notification: Notification,
    ) -> None:

        self.db.delete(notification)
        self.db.commit()

    def delete_all_for_user(
        self,
        user_id: uuid.UUID,
    ) -> int:

        count = self.count_user_notifications(
            user_id=user_id
        )

        self.db.execute(
            delete(Notification).where(
                Notification.user_id == user_id
            )
        )

        self.db.commit()

        return count