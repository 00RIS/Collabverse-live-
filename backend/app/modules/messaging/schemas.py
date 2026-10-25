
import uuid
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.modules.messaging.models import ConversationType


# ============================================================
# BASE CONFIGURATION
# ============================================================

class ORMResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# CONVERSATION CREATION
# ============================================================

class ConversationCreate(BaseModel):
    recipient_user_id: uuid.UUID

    # Reserved for future implementation.
    # The current service does not send this automatically.
    initial_message: str | None = Field(
        default=None,
        min_length=1,
        max_length=5000,
    )


class MentorshipConversationCreate(BaseModel):
    mentorship_id: uuid.UUID


class ProjectConversationCreate(BaseModel):
    project_id: uuid.UUID

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )


class GroupConversationCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
    )

    participant_user_ids: list[uuid.UUID] = Field(
        min_length=1,
        max_length=100,
    )

    @model_validator(mode="after")
    def validate_participants(self):
        if len(set(self.participant_user_ids)) != len(
            self.participant_user_ids
        ):
            raise ValueError(
                "Duplicate participants are not allowed"
            )
        return self


# ============================================================
# PARTICIPANTS
# ============================================================

class ConversationParticipantResponse(ORMResponse):
    id: uuid.UUID
    conversation_id: uuid.UUID
    user_id: uuid.UUID
    joined_at: datetime
    last_read_at: datetime | None = None
    is_muted: bool


# ============================================================
# MESSAGES
# ============================================================

class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def validate_content(self):
        self.content = self.content.strip()
        if not self.content:
            raise ValueError("Message cannot be empty")
        return self


class MessageUpdate(MessageCreate):
    pass


class MessageResponse(ORMResponse):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    is_edited: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    total: int
    limit: int
    offset: int


# ============================================================
# CONVERSATIONS
# ============================================================

class ConversationResponse(ORMResponse):
    id: uuid.UUID
    conversation_type: ConversationType
    title: str | None = None
    mentorship_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    created_by: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    participants: list[ConversationParticipantResponse] = Field(
        default_factory=list
    )


class ConversationSummaryResponse(ConversationResponse):
    participants: list[ConversationParticipantResponse] = Field(
        default_factory=list
    )
    last_message: MessageResponse | None = None
    unread_count: int = 0


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummaryResponse]
    total: int
    limit: int
    offset: int


# ============================================================
# READ / UNREAD
# ============================================================

class MarkConversationReadResponse(BaseModel):
    conversation_id: uuid.UUID
    user_id: uuid.UUID
    last_read_at: datetime
    unread_count: int = 0


class UnreadCountResponse(BaseModel):
    total_unread_messages: int
    conversations_with_unread: int


# ============================================================
# PERMISSIONS
# ============================================================

class MessagingPermissionResponse(BaseModel):
    can_message: bool
    reason: str | None = None
    conversation_id: uuid.UUID | None = None


# ============================================================
# WEBSOCKET EVENT TYPES
# ============================================================

class WebSocketEventType(str, Enum):
    MESSAGE_SEND = "message.send"
    MESSAGE_NEW = "message.new"
    MESSAGE_UPDATED = "message.updated"
    MESSAGE_DELETED = "message.deleted"
    MESSAGE_DELIVERED = "message.delivered"
    MESSAGE_READ = "message.read"
    CONVERSATION_READ = "conversation.read"
    CONVERSATION_CREATED = "conversation.created"
    TYPING_START = "typing.start"
    TYPING_STOP = "typing.stop"
    ERROR = "error"


# ============================================================
# CLIENT -> SERVER EVENTS
# ============================================================

class WebSocketMessageSend(BaseModel):
    type: Literal["message.send"]
    content: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def validate_message(self):
        self.content = self.content.strip()
        if not self.content:
            raise ValueError("Message cannot be empty")
        return self


class WebSocketTypingStart(BaseModel):
    type: Literal["typing.start"]


class WebSocketTypingStop(BaseModel):
    type: Literal["typing.stop"]


class WebSocketConversationRead(BaseModel):
    type: Literal["conversation.read"]


class WebSocketMessageDelivered(BaseModel):
    type: Literal["message.delivered"]
    message_id: uuid.UUID


# ============================================================
# SERVER -> CLIENT EVENTS
# ============================================================

class WebSocketEvent(BaseModel):
    type: WebSocketEventType

    conversation_id: uuid.UUID | None = None
    message: MessageResponse | None = None

    message_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    actor_user_id: uuid.UUID | None = None

    last_read_at: datetime | None = None
    unread_count: int | None = None

    timestamp: datetime | None = None
    detail: str | None = None


# ============================================================
# GENERAL ACTION RESPONSES
# ============================================================

class MessagingActionResponse(BaseModel):
    success: bool
    message: str
