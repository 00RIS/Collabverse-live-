from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Response,
    status,
)
from sqlalchemy.orm import Session

from .schemas import (
    AIMentorTypeResponse,
    AIConversationCreate,
    AIConversationResponse,
    AIConversationDetailResponse,
    AIMessageCreate,
    AIMessageSendResponse,
)

from .service import ai_mentor_service

# CHANGE THESE TWO IMPORTS
# TO MATCH YOUR EXISTING PROJECT
from app.db.session import get_db
from app.api.deps import get_current_user


router = APIRouter(
    prefix="/ai/mentor",
    tags=["AI Mentor"]
)


MENTOR_TYPES = [
    {
        "id": "general",
        "name": "AI Mentor",
        "description":
            "General learning, career and project guidance.",
        "premium": False,
    },
    {
        "id": "machine_learning",
        "name": "AI & Machine Learning Mentor",
        "description":
            "Machine learning, AI, data science and ML project guidance.",
        "premium": True,
    },
    {
        "id": "business",
        "name": "Business & Strategy Mentor",
        "description":
            "Business strategy, analytics and consulting guidance.",
        "premium": True,
    },
    {
        "id": "finance",
        "name": "Finance Mentor",
        "description":
            "Finance, investment and financial analysis guidance.",
        "premium": True,
    },
    {
        "id": "marketing",
        "name": "Marketing Mentor",
        "description":
            "Marketing, branding and growth guidance.",
        "premium": True,
    },
    {
        "id": "research",
        "name": "Research Mentor",
        "description":
            "Research methodology and academic project guidance.",
        "premium": True,
    },
    {
        "id": "entrepreneurship",
        "name": "Entrepreneurship Mentor",
        "description":
            "Startup, MVP and business-building guidance.",
        "premium": True,
    },
    {
        "id": "cybersecurity",
        "name": "Cybersecurity Mentor",
        "description":
            "Cybersecurity learning and career guidance.",
        "premium": True,
    },
    {
        "id": "product",
        "name": "Product Management Mentor",
        "description":
            "Product strategy, MVP and product management guidance.",
        "premium": True,
    },
]


@router.get(
    "/types",
    response_model=list[AIMentorTypeResponse],
)
async def get_mentor_types():
    return MENTOR_TYPES


@router.post(
    "/conversations",
    response_model=AIConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    request: AIConversationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ai_mentor_service.create_conversation(
        db=db,
        user=current_user,
        mentor_type=request.mentor_type,
        title=request.title,
    )


@router.get(
    "/conversations",
    response_model=list[AIConversationResponse],
)
async def get_conversations(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ai_mentor_service.get_conversations(
        db=db,
        user=current_user,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=AIConversationDetailResponse,
)
async def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ai_mentor_service.get_conversation(
        db=db,
        user=current_user,
        conversation_id=conversation_id,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=AIMessageSendResponse,
)
async def send_message(
    conversation_id: UUID,
    request: AIMessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_message, assistant_message = (
        await ai_mentor_service.send_message(
            db=db,
            user=current_user,
            conversation_id=conversation_id,
            message=request.message,
        )
    )

    return AIMessageSendResponse(
        conversation_id=conversation_id,
        user_message=user_message,
        assistant_message=assistant_message,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ai_mentor_service.delete_conversation(
        db=db,
        user=current_user,
        conversation_id=conversation_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )