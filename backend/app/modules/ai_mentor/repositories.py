from uuid import UUID

from sqlalchemy.orm import Session

from .models import AIConversation, AIMessage


class AIMentorRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_conversation(
        self,
        user_id: UUID,
        mentor_type: str,
        title: str | None = None,
    ) -> AIConversation:

        conversation = AIConversation(
            user_id=user_id,
            mentor_type=mentor_type,
            title=title,
        )

        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)

        return conversation

    def get_user_conversations(
        self,
        user_id: UUID,
    ) -> list[AIConversation]:

        return (
            self.db.query(AIConversation)
            .filter(
                AIConversation.user_id == user_id,
                AIConversation.is_archived.is_(False),
            )
            .order_by(AIConversation.updated_at.desc())
            .all()
        )

    def get_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> AIConversation | None:

        return (
            self.db.query(AIConversation)
            .filter(
                AIConversation.id == conversation_id,
                AIConversation.user_id == user_id,
            )
            .first()
        )

    def save_message(
        self,
        conversation: AIConversation,
        sender: str,
        content: str,
    ) -> AIMessage:

        message = AIMessage(
            conversation_id=conversation.id,
            sender=sender,
            content=content,
        )

        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        return message

    def get_messages(
        self,
        conversation: AIConversation,
    ) -> list[AIMessage]:

        return (
            self.db.query(AIMessage)
            .filter(
                AIMessage.conversation_id == conversation.id
            )
            .order_by(AIMessage.created_at.asc())
            .all()
        )

    def update_title(
        self,
        conversation: AIConversation,
        title: str,
    ) -> AIConversation:

        conversation.title = title

        self.db.commit()
        self.db.refresh(conversation)

        return conversation

    def archive_conversation(
        self,
        conversation: AIConversation,
    ) -> AIConversation:

        conversation.is_archived = True

        self.db.commit()
        self.db.refresh(conversation)

        return conversation

    def delete_conversation(
        self,
        conversation: AIConversation,
    ) -> None:

        self.db.delete(conversation)
        self.db.commit()