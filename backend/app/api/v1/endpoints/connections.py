import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.connection import Connection, ConnectionStatus
from app.models.user import User
from app.schemas.connection import ConnectionOut

from app.modules.notifications.models import NotificationType
from app.modules.notifications.repositories import NotificationRepository
from app.modules.notifications.service import NotificationService


router = APIRouter(
    prefix="/connections",
    tags=["connections"],
)


def get_notification_service(
    db: Session,
) -> NotificationService:
    return NotificationService(
        NotificationRepository(db)
    )


@router.get("", response_model=list[ConnectionOut])
def list_my_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Connection]:

    query = (
        select(Connection)
        .where(
            Connection.status == ConnectionStatus.ACCEPTED,
            or_(
                Connection.requester_id == current_user.id,
                Connection.recipient_id == current_user.id,
            ),
        )
        .order_by(Connection.updated_at.desc())
    )

    return list(db.scalars(query))


@router.get("/requests/incoming", response_model=list[ConnectionOut])
def incoming_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Connection]:

    query = (
        select(Connection)
        .where(
            Connection.recipient_id == current_user.id,
            Connection.status == ConnectionStatus.PENDING,
        )
        .order_by(Connection.created_at.desc())
    )

    return list(db.scalars(query))


@router.get("/requests/outgoing", response_model=list[ConnectionOut])
def outgoing_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Connection]:

    query = (
        select(Connection)
        .where(
            Connection.requester_id == current_user.id,
            Connection.status == ConnectionStatus.PENDING,
        )
        .order_by(Connection.created_at.desc())
    )

    return list(db.scalars(query))


@router.post(
    "/{user_id}",
    response_model=ConnectionOut,
    status_code=status.HTTP_201_CREATED,
)
def send_connection_request(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Connection:

    if user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot connect with yourself",
        )

    target_user = db.get(User, user_id)

    if target_user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if not target_user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot connect with an inactive user",
        )

    existing = db.scalar(
        select(Connection).where(
            or_(
                and_(
                    Connection.requester_id == current_user.id,
                    Connection.recipient_id == user_id,
                ),
                and_(
                    Connection.requester_id == user_id,
                    Connection.recipient_id == current_user.id,
                ),
            )
        )
    )

    notification_service = get_notification_service(db)

    if existing is not None:
        if existing.status == ConnectionStatus.PENDING:
            raise HTTPException(
                status_code=409,
                detail="A connection request already exists",
            )

        if existing.status == ConnectionStatus.ACCEPTED:
            raise HTTPException(
                status_code=409,
                detail="You are already connected",
            )

        existing.requester_id = current_user.id
        existing.recipient_id = user_id
        existing.status = ConnectionStatus.PENDING

        db.commit()
        db.refresh(existing)

        notification_service.create_notification(
            user_id=user_id,
            actor_id=current_user.id,
            notification_type=NotificationType.CONNECTION_REQUEST,
            title="New connection request",
            message="Someone sent you a connection request.",
            entity_type="connection",
            entity_id=existing.id,
        )

        return existing

    connection = Connection(
        requester_id=current_user.id,
        recipient_id=user_id,
        status=ConnectionStatus.PENDING,
    )

    db.add(connection)
    db.commit()
    db.refresh(connection)

    notification_service.create_notification(
        user_id=user_id,
        actor_id=current_user.id,
        notification_type=NotificationType.CONNECTION_REQUEST,
        title="New connection request",
        message="Someone sent you a connection request.",
        entity_type="connection",
        entity_id=connection.id,
    )

    return connection


@router.patch("/{connection_id}/accept", response_model=ConnectionOut)
def accept_connection_request(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Connection:

    connection = db.get(Connection, connection_id)

    if connection is None:
        raise HTTPException(
            status_code=404,
            detail="Connection request not found",
        )

    if connection.recipient_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the recipient can accept this request",
        )

    if connection.status != ConnectionStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail="This connection request is no longer pending",
        )

    connection.status = ConnectionStatus.ACCEPTED

    db.commit()
    db.refresh(connection)

    notification_service = get_notification_service(db)

    notification_service.create_notification(
        user_id=connection.requester_id,
        actor_id=current_user.id,
        notification_type=NotificationType.CONNECTION_ACCEPTED,
        title="Connection request accepted",
        message="Your connection request was accepted.",
        entity_type="connection",
        entity_id=connection.id,
    )

    return connection


@router.patch("/{connection_id}/reject", response_model=ConnectionOut)
def reject_connection_request(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Connection:

    connection = db.get(Connection, connection_id)

    if connection is None:
        raise HTTPException(
            status_code=404,
            detail="Connection request not found",
        )

    if connection.recipient_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the recipient can reject this request",
        )

    if connection.status != ConnectionStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail="This connection request is no longer pending",
        )

    connection.status = ConnectionStatus.REJECTED

    db.commit()
    db.refresh(connection)

    return connection


@router.delete(
    "/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:

    connection = db.get(Connection, connection_id)

    if connection is None:
        raise HTTPException(
            status_code=404,
            detail="Connection not found",
        )

    is_participant = (
        connection.requester_id == current_user.id
        or connection.recipient_id == current_user.id
    )

    if not is_participant:
        raise HTTPException(
            status_code=403,
            detail="You cannot modify this connection",
        )

    if (
        connection.status == ConnectionStatus.PENDING
        and connection.recipient_id == current_user.id
    ):
        raise HTTPException(
            status_code=400,
            detail="Use the reject endpoint for incoming requests",
        )

    db.delete(connection)
    db.commit()