from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# =========================================================
# Mentor Types
# =========================================================

MentorType = Literal[
    "general",
    "machine_learning",
    "business",
    "finance",
    "marketing",
    "research",
    "entrepreneurship",
    "cybersecurity",
    "product",
]


# =========================================================
# Original AI Mentor Chat
# =========================================================

class AIMentorChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
    )

    mentor_type: MentorType = "general"


class AIMentorChatResponse(BaseModel):
    mentor_type: MentorType
    message: str
    response: str
    is_premium: bool = False


class AIMentorTypeResponse(BaseModel):
    id: MentorType
    name: str
    description: str
    premium: bool


# =========================================================
# Conversation
# =========================================================

class AIConversationCreate(BaseModel):
    mentor_type: MentorType = "general"

    title: str | None = Field(
        default=None,
        max_length=255,
    )


class AIConversationResponse(BaseModel):
    id: UUID
    user_id: UUID
    mentor_type: str
    title: str | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


# =========================================================
# Messages
# =========================================================

class AIMessageCreate(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
    )


class AIMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender: str
    content: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


# =========================================================
# Conversation with Messages
# =========================================================

class AIConversationDetailResponse(
    AIConversationResponse
):
    messages: list[AIMessageResponse] = []


# =========================================================
# Send Message Response
# =========================================================

class AIMessageSendResponse(BaseModel):
    conversation_id: UUID
    user_message: AIMessageResponse
    assistant_message: AIMessageResponse