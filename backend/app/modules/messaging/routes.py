
import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)

from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import SessionLocal, get_db
from app.models.user import User

from app.modules.messaging.repositories import MessagingRepository
from app.modules.messaging.schemas import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    GroupConversationCreate,
    MarkConversationReadResponse,
    MentorshipConversationCreate,
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    MessageUpdate,
    MessagingActionResponse,
    MessagingPermissionResponse,
    ProjectConversationCreate,
    UnreadCountResponse,
)

from app.modules.messaging.service import MessagingService
from app.modules.messaging.websocket import manager


router = APIRouter(
    prefix="/messaging",
    tags=["messaging"],
)


# ============================================================
# HELPERS
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def get_messaging_service(
    db: Session = Depends(get_db),
) -> MessagingService:
    return MessagingService(
        MessagingRepository(db)
    )


def save_rest_message(
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    payload: MessageCreate,
):
    """
    Create, use, and close the database session
    within the same worker thread.
    """

    with SessionLocal() as db:
        user = db.get(User, user_id)

        if user is None or not user.is_active:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=403,
                detail="User account unavailable",
            )

        service = MessagingService(
            MessagingRepository(db)
        )

        message = service.send_message(
            current_user=user,
            conversation_id=conversation_id,
            payload=payload,
        )

        return MessageResponse.model_validate(
            message
        )


def mark_rest_conversation_read(
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
):
    """
    Mark read using a database session created
    and closed inside the same worker thread.
    """

    with SessionLocal() as db:
        user = db.get(User, user_id)

        if user is None or not user.is_active:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=403,
                detail="User account unavailable",
            )

        service = MessagingService(
            MessagingRepository(db)
        )

        result = service.mark_conversation_read(
            current_user=user,
            conversation_id=conversation_id,
        )

        return MarkConversationReadResponse.model_validate(
            result
        )


# ============================================================
# CREATE DIRECT CONVERSATION
# ============================================================

@router.post(
    "/conversations/direct",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
)
def create_direct_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    service: MessagingService = Depends(get_messaging_service),
):
    return service.create_direct_conversation(
        current_user=current_user,
        payload=payload,
    )


# ============================================================
# CREATE MENTORSHIP CONVERSATION
# ============================================================

@router.post(
    "/conversations/mentorship",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
)
def create_mentorship_conversation(
    payload: MentorshipConversationCreate,
    current_user: User = Depends(get_current_user),
    service: MessagingService = Depends(get_messaging_service),
):
    return service.create_mentorship_conversation(
        current_user=current_user,
        payload=payload,
    )


# ============================================================
# PROJECT CONVERSATIONS
# ============================================================

@router.post(
    "/conversations/project",
    response_model=ConversationDetailResponse,
)
def create_project_conversation(
    payload: ProjectConversationCreate,
    current_user: User = Depends(get_current_user),
    service: MessagingService = Depends(get_messaging_service),
):
    return service.create_project_conversation(
        current_user=current_user,
        payload=payload,
    )


# ============================================================
# GROUP CONVERSATIONS
# ============================================================

@router.post(
    "/conversations/group",
    response_model=ConversationDetailResponse,
)
def create_group_conversation(
    payload: GroupConversationCreate,
    current_user: User = Depends(get_current_user),
    service: MessagingService = Depends(get_messaging_service),
):
    return service.create_group_conversation(
        current_user=current_user,
        payload=payload,
    )


# ============================================================
# CONVERSATION LIST
# ============================================================

@router.get(
    "/conversations",
    response_model=ConversationListResponse,
)
def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    service: MessagingService = Depends(get_messaging_service),
):
    return service.list_conversations(
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


# ============================================================
# UNREAD COUNTS
# ============================================================

@router.get(
    "/unread",
    response_model=UnreadCountResponse,
)
def get_unread_counts(
    current_user: User = Depends(get_current_user),
    service: MessagingService = Depends(get_messaging_service),
):
    return service.get_unread_counts(
        current_user=current_user,
    )


# ============================================================
# MESSAGING PERMISSION
# ============================================================

@router.get(
    "/permissions/{recipient_user_id}",
    response_model=MessagingPermissionResponse,
)
def check_messaging_permission(
    recipient_user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: MessagingService = Depends(get_messaging_service),
):
    return service.check_messaging_permission(
        current_user=current_user,
        recipient_user_id=recipient_user_id,
    )


# ============================================================
# CONVERSATION DETAILS
# ============================================================

@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: MessagingService = Depends(get_messaging_service),
):
    return service.get_conversation(
        current_user=current_user,
        conversation_id=conversation_id,
    )


# ============================================================
# MESSAGE HISTORY
# ============================================================

@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
)
def list_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    service: MessagingService = Depends(get_messaging_service),
):
    return service.list_messages(
        current_user=current_user,
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
    )


# ============================================================
# REST MESSAGE + LIVE BROADCAST
# ============================================================

@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id

    # Database work is performed in one worker thread.
    # The service commits before returning.
    message = await asyncio.to_thread(
        save_rest_message,
        user_id,
        conversation_id,
        payload,
    )

    # Broadcast the committed message.
    await manager.broadcast(
        conversation_id,
        {
            "type": "message.new",
            "conversation_id": str(conversation_id),
            "message": message.model_dump(mode="json"),
            "timestamp": utc_now(),
        },
    )

    return message


# ============================================================
# REST MARK READ + LIVE BROADCAST
# ============================================================

@router.post(
    "/conversations/{conversation_id}/read",
    response_model=MarkConversationReadResponse,
)
async def mark_conversation_read(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id

    result = await asyncio.to_thread(
        mark_rest_conversation_read,
        user_id,
        conversation_id,
    )

    await manager.broadcast(
        conversation_id,
        {
            "type": "conversation.read",
            "conversation_id": str(result.conversation_id),
            "user_id": str(result.user_id),
            "last_read_at": result.last_read_at.isoformat(),
            "unread_count": result.unread_count,
            "timestamp": utc_now(),
        },
    )

    return result


# ============================================================
# EDIT MESSAGE
# ============================================================

@router.patch(
    "/messages/{message_id}",
    response_model=MessageResponse,
)
def edit_message(
    message_id: uuid.UUID,
    payload: MessageUpdate,
    current_user: User = Depends(get_current_user),
    service: MessagingService = Depends(get_messaging_service),
):
    return service.edit_message(
        current_user=current_user,
        message_id=message_id,
        payload=payload,
    )


# ============================================================
# DELETE MESSAGE
# ============================================================

@router.delete(
    "/messages/{message_id}",
    response_model=MessagingActionResponse,
)
def delete_message(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: MessagingService = Depends(get_messaging_service),
):
    return service.delete_message(
        current_user=current_user,
        message_id=message_id,
    )
