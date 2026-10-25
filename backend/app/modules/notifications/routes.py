import uuid

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

from app.modules.notifications.repositories import (
    NotificationRepository,
)
from app.modules.notifications.schemas import (
    MarkAllReadResponse,
    MarkReadResponse,
    NotificationListResponse,
    UnreadCountResponse,
)
from app.modules.notifications.service import (
    NotificationService,
)


router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


def get_notification_service(
    db: Session = Depends(get_db),
) -> NotificationService:
    repository = NotificationRepository(db)

    return NotificationService(
        repository
    )


@router.get(
    "",
    response_model=NotificationListResponse,
)
def get_notifications(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    unread_only: bool = Query(
        default=False,
    ),
    current_user: User = Depends(
        get_current_user
    ),
    service: NotificationService = Depends(
        get_notification_service
    ),
):
    return service.get_notifications(
        current_user=current_user,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
)
def get_unread_count(
    current_user: User = Depends(
        get_current_user
    ),
    service: NotificationService = Depends(
        get_notification_service
    ),
):
    count = service.get_unread_count(
        current_user
    )

    return UnreadCountResponse(
        unread_count=count
    )


@router.patch(
    "/read-all",
    response_model=MarkAllReadResponse,
)
def mark_all_read(
    current_user: User = Depends(
        get_current_user
    ),
    service: NotificationService = Depends(
        get_notification_service
    ),
):
    count = service.mark_all_read(
        current_user
    )

    return MarkAllReadResponse(
        updated_count=count
    )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_all_notifications(
    current_user: User = Depends(
        get_current_user
    ),
    service: NotificationService = Depends(
        get_notification_service
    ),
):
    service.delete_all(
        current_user
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


@router.patch(
    "/{notification_id}/read",
    response_model=MarkReadResponse,
)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(
        get_current_user
    ),
    service: NotificationService = Depends(
        get_notification_service
    ),
):
    notification = service.mark_read(
        notification_id,
        current_user,
    )

    return MarkReadResponse(
        id=notification.id,
        is_read=notification.is_read,
    )


@router.patch(
    "/{notification_id}/unread",
    response_model=MarkReadResponse,
)
def mark_notification_unread(
    notification_id: uuid.UUID,
    current_user: User = Depends(
        get_current_user
    ),
    service: NotificationService = Depends(
        get_notification_service
    ),
):
    notification = service.mark_unread(
        notification_id,
        current_user,
    )

    return MarkReadResponse(
        id=notification.id,
        is_read=notification.is_read,
    )


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(
        get_current_user
    ),
    service: NotificationService = Depends(
        get_notification_service
    ),
):
    service.delete_notification(
        notification_id,
        current_user,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )