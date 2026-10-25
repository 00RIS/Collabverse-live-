from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .context import AIMentorContextBuilder
from .prompts import get_mentor_prompt
from .provider import GeminiAIProvider
from .repositories import AIMentorRepository


class AIMentorService:

    def __init__(self):
        self.provider = GeminiAIProvider()

    def _build_history(
        self,
        messages,
    ) -> list[dict]:

        return [
            {
                "role": (
                    "user"
                    if message.sender == "user"
                    else "assistant"
                ),
                "content": message.content,
            }
            for message in messages
        ]

    def _generate_title(
        self,
        message: str,
    ) -> str:

        message = message.strip()

        if len(message) <= 60:
            return message

        return message[:57] + "..."

    def create_conversation(
        self,
        db: Session,
        user,
        mentor_type: str,
        title: str | None = None,
    ):

        repository = AIMentorRepository(db)

        return repository.create_conversation(
            user_id=user.id,
            mentor_type=mentor_type,
            title=title,
        )

    def get_conversations(
        self,
        db: Session,
        user,
    ):

        repository = AIMentorRepository(db)

        return repository.get_user_conversations(
            user.id
        )

    def get_conversation(
        self,
        db: Session,
        user,
        conversation_id: UUID,
    ):

        repository = AIMentorRepository(db)

        conversation = repository.get_conversation(
            conversation_id=conversation_id,
            user_id=user.id,
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        return conversation

    async def send_message(
        self,
        db: Session,
        user,
        conversation_id: UUID,
        message: str,
    ):

        repository = AIMentorRepository(db)

        # Ownership check
        conversation = repository.get_conversation(
            conversation_id=conversation_id,
            user_id=user.id,
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        if conversation.is_archived:
            raise HTTPException(
                status_code=400,
                detail="Conversation is archived",
            )

        # Load history only from the verified conversation
        previous_messages = repository.get_messages(
            conversation
        )

        history = self._build_history(
            previous_messages
        )

        # Save user's message
        user_message = repository.save_message(
            conversation=conversation,
            sender="user",
            content=message,
        )

        # Build user context
        context = (
            AIMentorContextBuilder
            .build_basic_context(user)
        )

        context_text = (
            AIMentorContextBuilder
            .context_to_text(context)
        )

        # Pick mentor prompt
        system_prompt = get_mentor_prompt(
            conversation.mentor_type
        )

        # Generate Gemini response
        ai_response = await self.provider.generate(
            system_prompt=system_prompt,
            user_message=message,
            context=context_text,
            history=history,
        )

        # Save assistant response
        assistant_message = repository.save_message(
            conversation=conversation,
            sender="assistant",
            content=ai_response,
        )

        # Auto-generate title if missing
        if not conversation.title:
            repository.update_title(
                conversation,
                self._generate_title(message),
            )

        return (
            user_message,
            assistant_message,
        )

    def delete_conversation(
        self,
        db: Session,
        user,
        conversation_id: UUID,
    ):

        repository = AIMentorRepository(db)

        # Ownership check
        conversation = repository.get_conversation(
            conversation_id=conversation_id,
            user_id=user.id,
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        repository.delete_conversation(
            conversation
        )


ai_mentor_service = AIMentorService()