
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.models.user import User
from app.models.connection import Connection, ConnectionStatus
from app.modules.messaging.models import (
    Conversation,
    ConversationParticipant,
    ConversationType,
    Message,
)
from app.modules.mentorship.models import (
    MentorProfile,
    Mentorship,
    MentorshipStatus,
)


class MessagingRepository:
    """
    Database access layer for CollabVerse Messaging.

    Important:
    - Authorization belongs in MessagingService.
    - Public API routes must never call repository
      methods directly without permission checks.
    - Database writes are flushed by default.
      The service controls transaction commits.
    """

    def __init__(self, db: Session):
        self.db = db

    # ========================================================
    # USERS
    # ========================================================

    def get_user(self, user_id: uuid.UUID):
        return self.db.get(User, user_id)

    def get_accepted_connection_between_users(self, first_user_id: uuid.UUID, second_user_id: uuid.UUID):
        return self.db.scalar(select(Connection).where(
            Connection.status == ConnectionStatus.ACCEPTED,
            or_(
                and_(Connection.requester_id == first_user_id, Connection.recipient_id == second_user_id),
                and_(Connection.requester_id == second_user_id, Connection.recipient_id == first_user_id),
            ),
        ))

    def get_users(self, user_ids: list[uuid.UUID]):
        if not user_ids:
            return []

        return list(
            self.db.scalars(
                select(User).where(User.id.in_(user_ids))
            ).all()
        )

    # ========================================================
    # CONVERSATIONS
    # ========================================================

    def get_conversation(
        self,
        conversation_id: uuid.UUID,
    ):
        statement = (
            select(Conversation)
            .options(
                selectinload(Conversation.participants)
            )
            .where(Conversation.id == conversation_id)
        )

        return self.db.scalar(statement)

    def create_conversation(
        self,
        *,
        conversation_type: ConversationType,
        created_by: uuid.UUID,
        title: str | None = None,
        mentorship_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        is_active: bool = True,
    ):
        conversation = Conversation(
            conversation_type=conversation_type,
            created_by=created_by,
            title=title,
            mentorship_id=mentorship_id,
            project_id=project_id,
            is_active=is_active,
        )

        self.db.add(conversation)
        self.db.flush()

        return conversation

    def get_conversation_by_mentorship(
        self,
        mentorship_id: uuid.UUID,
    ):
        return self.db.scalar(
            select(Conversation)
            .options(
                selectinload(Conversation.participants)
            )
            .where(
                Conversation.mentorship_id == mentorship_id
            )
        )

    def get_direct_conversation(
        self,
        first_user_id: uuid.UUID,
        second_user_id: uuid.UUID,
    ):
        """
        Find a direct conversation containing exactly
        the two specified users.

        This excludes group and mentorship conversations.
        """

        participant_count = (
            select(
                ConversationParticipant.conversation_id
            )
            .group_by(
                ConversationParticipant.conversation_id
            )
            .having(
                func.count(
                    ConversationParticipant.user_id
                ) == 2
            )
            .having(
                func.count(
                    func.distinct(
                        ConversationParticipant.user_id
                    )
                ) == 2
            )
            .having(
                func.count(
                    func.distinct(
                        ConversationParticipant.user_id
                    )
                ).filter(
                    ConversationParticipant.user_id.in_(
                        [first_user_id, second_user_id]
                    )
                ) == 2
            )
            .subquery()
        )

        statement = (
            select(Conversation)
            .options(
                selectinload(Conversation.participants)
            )
            .join(
                participant_count,
                participant_count.c.conversation_id
                == Conversation.id,
            )
            .where(
                Conversation.conversation_type
                == ConversationType.DIRECT
            )
            .order_by(
                Conversation.created_at.desc()
            )
        )

        return self.db.scalar(statement)

    def get_project_conversation(
        self,
        project_id: uuid.UUID,
    ):
        return self.db.scalar(
            select(Conversation)
            .options(
                selectinload(Conversation.participants)
            )
            .where(
                Conversation.project_id == project_id,
                Conversation.conversation_type
                == ConversationType.PROJECT,
            )
        )

    def list_user_conversations(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ):
        statement = (
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id
                == Conversation.id,
            )
            .where(
                ConversationParticipant.user_id == user_id
            )
            .options(
                selectinload(Conversation.participants)
            )
            .order_by(
                Conversation.updated_at.desc(),
                Conversation.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        return list(
            self.db.scalars(statement).all()
        )

    def count_user_conversations(
        self,
        user_id: uuid.UUID,
    ) -> int:
        statement = (
            select(func.count(Conversation.id))
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id
                == Conversation.id,
            )
            .where(
                ConversationParticipant.user_id == user_id
            )
        )

        return int(
            self.db.scalar(statement) or 0
        )

    def touch_conversation(
        self,
        conversation: Conversation,
    ):
        conversation.updated_at = datetime.now(
            timezone.utc
        )

        self.db.flush()

        return conversation

    # ========================================================
    # PARTICIPANTS
    # ========================================================

    def add_participant(
        self,
        *,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        existing = self.get_participant(
            conversation_id,
            user_id,
        )

        if existing is not None:
            return existing

        participant = ConversationParticipant(
            conversation_id=conversation_id,
            user_id=user_id,
        )

        self.db.add(participant)
        self.db.flush()

        return participant

    def get_participant(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        return self.db.scalar(
            select(ConversationParticipant)
            .where(
                ConversationParticipant.conversation_id
                == conversation_id,
                ConversationParticipant.user_id
                == user_id,
            )
        )

    def is_participant(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        return (
            self.get_participant(
                conversation_id,
                user_id,
            )
            is not None
        )

    def list_participants(
        self,
        conversation_id: uuid.UUID,
    ):
        statement = (
            select(ConversationParticipant)
            .where(
                ConversationParticipant.conversation_id
                == conversation_id
            )
            .order_by(
                ConversationParticipant.joined_at.asc()
            )
        )

        return list(
            self.db.scalars(statement).all()
        )

    def set_participant_muted(
        self,
        participant: ConversationParticipant,
        muted: bool,
    ):
        participant.is_muted = muted
        self.db.flush()

        return participant

    # ========================================================
    # MESSAGES
    # ========================================================

    def create_message(
        self,
        *,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        content: str,
    ):
        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
        )

        self.db.add(message)
        self.db.flush()

        return message

    def get_message(
        self,
        message_id: uuid.UUID,
    ):
        return self.db.get(Message, message_id)

    def list_messages(
        self,
        conversation_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ):
        """
        Returns newest messages first.

        Frontend can reverse the returned page
        when displaying chronological chat bubbles.
        """

        statement = (
            select(Message)
            .where(
                Message.conversation_id
                == conversation_id
            )
            .order_by(
                Message.created_at.desc(),
                Message.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        return list(
            self.db.scalars(statement).all()
        )

    def count_messages(
        self,
        conversation_id: uuid.UUID,
    ) -> int:
        return int(
            self.db.scalar(
                select(func.count(Message.id))
                .where(
                    Message.conversation_id
                    == conversation_id
                )
            )
            or 0
        )

    def get_last_message(
        self,
        conversation_id: uuid.UUID,
    ):
        return self.db.scalar(
            select(Message)
            .where(
                Message.conversation_id
                == conversation_id
            )
            .order_by(
                Message.created_at.desc(),
                Message.id.desc(),
            )
            .limit(1)
        )

    def update_message(
        self,
        message: Message,
        content: str,
    ):
        message.content = content
        message.is_edited = True
        message.updated_at = datetime.now(
            timezone.utc
        )

        self.db.flush()

        return message

    def soft_delete_message(
        self,
        message: Message,
    ):
        """
        Preserve the message record but remove
        its visible text.
        """

        message.content = ""
        message.is_deleted = True
        message.updated_at = datetime.now(
            timezone.utc
        )

        self.db.flush()

        return message

    # ========================================================
    # READ / UNREAD TRACKING
    # ========================================================

    def mark_conversation_read(
        self,
        participant: ConversationParticipant,
    ):
        """
        Update read timestamp.

        This must be called only after checking
        that the user belongs to the conversation.
        """

        participant.last_read_at = datetime.now(
            timezone.utc
        )

        self.db.flush()

        return participant

    def count_unread_messages(
        self,
        *,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> int:
        participant = self.get_participant(
            conversation_id,
            user_id,
        )

        if participant is None:
            return 0

        conditions = [
            Message.conversation_id == conversation_id,
            Message.sender_id != user_id,
            Message.is_deleted.is_(False),
        ]

        if participant.last_read_at is not None:
            conditions.append(
                Message.created_at
                > participant.last_read_at
            )
        else:
            conditions.append(
                Message.created_at
                >= participant.joined_at
            )

        statement = (
            select(func.count(Message.id))
            .where(*conditions)
        )

        return int(
            self.db.scalar(statement) or 0
        )

    def count_all_unread_messages(
        self,
        user_id: uuid.UUID,
    ) -> int:
        """
        Count unread messages across all conversations.

        Uses a single aggregate query.
        """

        participant = ConversationParticipant

        unread_condition = or_(
            and_(
                participant.last_read_at.is_not(None),
                Message.created_at
                > participant.last_read_at,
            ),
            and_(
                participant.last_read_at.is_(None),
                Message.created_at
                >= participant.joined_at,
            ),
        )

        statement = (
            select(func.count(Message.id))
            .join(
                participant,
                participant.conversation_id
                == Message.conversation_id,
            )
            .where(
                participant.user_id == user_id,
                Message.sender_id != user_id,
                Message.is_deleted.is_(False),
                unread_condition,
            )
        )

        return int(
            self.db.scalar(statement) or 0
        )

    def count_conversations_with_unread(
        self,
        user_id: uuid.UUID,
    ) -> int:
        participant = ConversationParticipant

        unread_condition = or_(
            and_(
                participant.last_read_at.is_not(None),
                Message.created_at
                > participant.last_read_at,
            ),
            and_(
                participant.last_read_at.is_(None),
                Message.created_at
                >= participant.joined_at,
            ),
        )

        statement = (
            select(
                func.count(
                    func.distinct(
                        Message.conversation_id
                    )
                )
            )
            .join(
                participant,
                participant.conversation_id
                == Message.conversation_id,
            )
            .where(
                participant.user_id == user_id,
                Message.sender_id != user_id,
                Message.is_deleted.is_(False),
                unread_condition,
            )
        )

        return int(
            self.db.scalar(statement) or 0
        )

    # ========================================================
    # MENTORSHIP INTEGRATION
    # ========================================================

    def get_mentorship(
        self,
        mentorship_id: uuid.UUID,
    ):
        return self.db.scalar(
            select(Mentorship)
            .options(
                selectinload(
                    Mentorship.mentor_profile
                )
            )
            .where(
                Mentorship.id == mentorship_id
            )
        )

    def get_accepted_mentorship_between_users(
        self,
        first_user_id: uuid.UUID,
        second_user_id: uuid.UUID,
    ):
        """
        Find an accepted mentorship connecting
        the specified users in either direction.
        """

        statement = (
            select(Mentorship)
            .join(
                MentorProfile,
                MentorProfile.id
                == Mentorship.mentor_profile_id,
            )
            .where(
                Mentorship.status
                == MentorshipStatus.ACCEPTED,
                or_(
                    and_(
                        Mentorship.mentee_user_id
                        == first_user_id,
                        MentorProfile.user_id
                        == second_user_id,
                    ),
                    and_(
                        Mentorship.mentee_user_id
                        == second_user_id,
                        MentorProfile.user_id
                        == first_user_id,
                    ),
                ),
            )
            .order_by(
                Mentorship.started_at.desc()
            )
        )

        return self.db.scalar(statement)

    # ========================================================
    # TRANSACTIONS
    # ========================================================

    def flush(self):
        self.db.flush()

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    def refresh(self, instance):
        self.db.refresh(instance)
        return instance
