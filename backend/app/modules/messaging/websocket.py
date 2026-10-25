
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.user import User

from app.modules.messaging.repositories import MessagingRepository
from app.modules.messaging.schemas import (
    MessageCreate,
    MessageResponse,
    WebSocketMessageSend,
    WebSocketTypingStart,
    WebSocketTypingStop,
    WebSocketConversationRead,
    WebSocketMessageDelivered,
)
from app.modules.messaging.service import MessagingService


router = APIRouter(tags=["messaging-websocket"])
logger = logging.getLogger(__name__)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# AUTHENTICATION
# ============================================================

def authenticate_user(token: str):
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        return None

    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        return None

    with SessionLocal() as db:
        user = db.get(User, user_id)

        if user is None or not user.is_active:
            return None

        return user.id


# ============================================================
# AUTHORIZATION
# ============================================================

def authorize_conversation(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
):
    with SessionLocal() as db:
        user = db.get(User, user_id)

        if user is None or not user.is_active:
            return False

        repository = MessagingRepository(db)
        service = MessagingService(repository)

        conversation = repository.get_conversation(
            conversation_id
        )

        if conversation is None:
            return False

        try:
            service._require_can_send(
                conversation,
                user_id,
            )
        except HTTPException:
            return False

        return True


# ============================================================
# CONNECTION MANAGER
# ============================================================

class ConnectionManager:

    def __init__(self):
        self.active_connections = {}
        self.lock = asyncio.Lock()

    async def connect(
        self,
        conversation_id,
        user_id,
        websocket,
    ):
        await websocket.accept(
            subprotocol="collabverse"
        )

        async with self.lock:
            users = self.active_connections.setdefault(
                conversation_id,
                {},
            )

            sockets = users.setdefault(
                user_id,
                set(),
            )

            sockets.add(websocket)

    async def disconnect(
        self,
        conversation_id,
        user_id,
        websocket,
    ):
        async with self.lock:
            users = self.active_connections.get(
                conversation_id
            )

            if not users:
                return

            sockets = users.get(user_id)

            if sockets is not None:
                sockets.discard(websocket)

                if not sockets:
                    users.pop(user_id, None)

            if not users:
                self.active_connections.pop(
                    conversation_id,
                    None,
                )

    async def broadcast(
        self,
        conversation_id,
        event,
        exclude_user_id=None,
    ):
        async with self.lock:
            users = self.active_connections.get(
                conversation_id,
                {},
            )

            recipients = [
                (user_id, socket)
                for user_id, sockets in users.items()
                if user_id != exclude_user_id
                for socket in sockets
            ]

        # Check permissions before delivering events.
        checked = {}

        for user_id, socket in recipients:
            if user_id not in checked:
                checked[user_id] = await asyncio.to_thread(
                    authorize_conversation,
                    conversation_id,
                    user_id,
                )

            if not checked[user_id]:
                try:
                    await socket.close(
                        code=1008,
                        reason="Conversation access revoked",
                    )
                except Exception:
                    pass

                await self.disconnect(
                    conversation_id,
                    user_id,
                    socket,
                )
                continue

            try:
                await socket.send_json(event)
            except Exception:
                await self.disconnect(
                    conversation_id,
                    user_id,
                    socket,
                )


manager = ConnectionManager()


# ============================================================
# DATABASE OPERATIONS
# ============================================================

def save_message(
    conversation_id,
    user_id,
    content,
):
    with SessionLocal() as db:
        user = db.get(User, user_id)

        if user is None or not user.is_active:
            raise ValueError("User unavailable")

        service = MessagingService(
            MessagingRepository(db)
        )

        message = service.send_message(
            current_user=user,
            conversation_id=conversation_id,
            payload=MessageCreate(content=content),
        )

        return MessageResponse.model_validate(
            message
        ).model_dump(mode="json")


def mark_read(
    conversation_id,
    user_id,
):
    with SessionLocal() as db:
        user = db.get(User, user_id)

        if user is None or not user.is_active:
            raise ValueError("User unavailable")

        service = MessagingService(
            MessagingRepository(db)
        )

        result = service.mark_conversation_read(
            current_user=user,
            conversation_id=conversation_id,
        )

        return {
            "conversation_id": str(result.conversation_id),
            "user_id": str(result.user_id),
            "last_read_at": result.last_read_at.isoformat(),
            "unread_count": result.unread_count,
        }


def verify_delivery(
    conversation_id,
    user_id,
    message_id,
):
    with SessionLocal() as db:
        repository = MessagingRepository(db)

        message = repository.get_message(message_id)

        if message is None:
            return False

        if message.conversation_id != conversation_id:
            return False

        if message.sender_id == user_id:
            return False

        if message.is_deleted:
            return False

        return authorize_delivery_in_session(
            db,
            conversation_id,
            user_id,
        )


def authorize_delivery_in_session(
    db,
    conversation_id,
    user_id,
):
    user = db.get(User, user_id)

    if user is None or not user.is_active:
        return False

    repository = MessagingRepository(db)
    service = MessagingService(repository)

    conversation = repository.get_conversation(
        conversation_id
    )

    if conversation is None:
        return False

    try:
        service._require_can_send(
            conversation,
            user_id,
        )
    except HTTPException:
        return False

    return True


# ============================================================
# EVENT VALIDATION
# ============================================================

def validate_incoming_event(data):
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")

    event_type = data.get("type")

    event_models = {
        "message.send": WebSocketMessageSend,
        "typing.start": WebSocketTypingStart,
        "typing.stop": WebSocketTypingStop,
        "conversation.read": WebSocketConversationRead,
        "message.delivered": WebSocketMessageDelivered,
    }

    model = event_models.get(event_type)

    if model is None:
        raise ValueError("Unsupported event type")

    return model.model_validate(data)


# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================

@router.websocket("/ws/messaging/{conversation_id}")
async def messaging_websocket(
    websocket: WebSocket,
    conversation_id: uuid.UUID,
):
    token = None

    for protocol in websocket.scope.get(
        "subprotocols",
        [],
    ):
        if protocol.startswith("bearer."):
            token = protocol[len("bearer."):]

    if not token:
        await websocket.close(
            code=1008,
            reason="Authentication required",
        )
        return

    user_id = await asyncio.to_thread(
        authenticate_user,
        token,
    )

    if user_id is None:
        await websocket.close(
            code=1008,
            reason="Invalid access token",
        )
        return

    authorized = await asyncio.to_thread(
        authorize_conversation,
        conversation_id,
        user_id,
    )

    if not authorized:
        await websocket.close(
            code=1008,
            reason="Conversation access denied",
        )
        return

    await manager.connect(
        conversation_id,
        user_id,
        websocket,
    )

    try:
        while True:
            try:
                data = await websocket.receive_json()

                incoming = validate_incoming_event(
                    data
                )

                event_type = incoming.type

                # Recheck authentication and permissions
                # before handling every incoming event.
                authorized = await asyncio.to_thread(
                    authorize_conversation,
                    conversation_id,
                    user_id,
                )

                if not authorized:
                    await websocket.close(
                        code=1008,
                        reason="Conversation access revoked",
                    )
                    break

                # ----------------------------------------
                # SEND MESSAGE
                # ----------------------------------------

                if event_type == "message.send":
                    message = await asyncio.to_thread(
                        save_message,
                        conversation_id,
                        user_id,
                        incoming.content,
                    )

                    await manager.broadcast(
                        conversation_id,
                        {
                            "type": "message.new",
                            "conversation_id": str(
                                conversation_id
                            ),
                            "message": message,
                            "timestamp": utc_now(),
                        },
                    )

                # ----------------------------------------
                # TYPING START / STOP
                # ----------------------------------------

                elif event_type in (
                    "typing.start",
                    "typing.stop",
                ):
                    await manager.broadcast(
                        conversation_id,
                        {
                            "type": event_type,
                            "conversation_id": str(
                                conversation_id
                            ),
                            "user_id": str(user_id),
                            "timestamp": utc_now(),
                        },
                        exclude_user_id=user_id,
                    )

                # ----------------------------------------
                # CONVERSATION READ
                # ----------------------------------------

                elif event_type == "conversation.read":
                    result = await asyncio.to_thread(
                        mark_read,
                        conversation_id,
                        user_id,
                    )

                    await manager.broadcast(
                        conversation_id,
                        {
                            "type": "conversation.read",
                            **result,
                            "timestamp": utc_now(),
                        },
                    )

                # ----------------------------------------
                # DELIVERY ACKNOWLEDGEMENT
                # ----------------------------------------

                elif event_type == "message.delivered":
                    valid = await asyncio.to_thread(
                        verify_delivery,
                        conversation_id,
                        user_id,
                        incoming.message_id,
                    )

                    if not valid:
                        raise ValueError(
                            "Message cannot be acknowledged"
                        )

                    await manager.broadcast(
                        conversation_id,
                        {
                            "type": "message.delivered",
                            "conversation_id": str(
                                conversation_id
                            ),
                            "message_id": str(
                                incoming.message_id
                            ),
                            "user_id": str(user_id),
                            "timestamp": utc_now(),
                        },
                        exclude_user_id=user_id,
                    )

            except (ValidationError, ValueError) as exc:
                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": str(exc),
                    }
                )

            except HTTPException as exc:
                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": str(exc.detail),
                    }
                )

            except WebSocketDisconnect:
                raise

            except Exception:
                logger.exception(
                    "Messaging WebSocket event failed"
                )

                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": "Unable to process event",
                    }
                )

    except WebSocketDisconnect:
        pass

    finally:
        await manager.disconnect(
            conversation_id,
            user_id,
            websocket,
        )
