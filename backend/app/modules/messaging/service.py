
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.modules.messaging.models import (
    Conversation,
    ConversationType,
    Message,
)
from app.modules.messaging.repositories import MessagingRepository
from app.modules.messaging.schemas import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummaryResponse,
    GroupConversationCreate,
    MarkConversationReadResponse,
    MentorshipConversationCreate,
    MessageCreate,
    MessageListResponse,
    MessageUpdate,
    MessagingActionResponse,
    MessagingPermissionResponse,
    ProjectConversationCreate,
    UnreadCountResponse,
)
from app.modules.mentorship.models import MentorshipStatus


class MessagingService:
    """
    Business logic for CollabVerse messaging.

    V1 rules:
    - Users may message through accepted mentorships.
    - Existing direct conversations remain accessible
      only to their participants.
    - New unrestricted direct chats are disabled.
    - Project/group creation is reserved until
      membership permissions are integrated.
    - Mentorship messages require an active,
      accepted mentorship.
    """

    def __init__(self, repository: MessagingRepository):
        self.repository = repository

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _error(
        code: int,
        message: str,
    ):
        raise HTTPException(
            status_code=code,
            detail=message,
        )

    @staticmethod
    def _utcnow():
        return datetime.now(timezone.utc)

    def _get_conversation(
        self,
        conversation_id: uuid.UUID,
    ) -> Conversation:
        conversation = self.repository.get_conversation(
            conversation_id
        )

        if conversation is None:
            self._error(
                status.HTTP_404_NOT_FOUND,
                "Conversation not found",
            )

        return conversation

    def _require_participant(
        self,
        conversation: Conversation,
        user_id: uuid.UUID,
    ):
        participant = self.repository.get_participant(
            conversation.id,
            user_id,
        )

        if participant is None:
            self._error(
                status.HTTP_404_NOT_FOUND,
                "Conversation not found",
            )

        return participant

    def _require_active_mentorship(
        self,
        conversation: Conversation,
    ):
        if conversation.conversation_type != ConversationType.MENTORSHIP:
            return

        if conversation.mentorship_id is None:
            self._error(
                status.HTTP_403_FORBIDDEN,
                "Mentorship conversation has no linked mentorship",
            )

        mentorship = self.repository.get_mentorship(
            conversation.mentorship_id
        )

        if (
            mentorship is None
            or mentorship.status != MentorshipStatus.ACCEPTED
        ):
            self._error(
                status.HTTP_403_FORBIDDEN,
                "Messaging is available only for active mentorships",
            )

        return mentorship

    def _require_can_send(
        self,
        conversation: Conversation,
        user_id: uuid.UUID,
    ):
        self._require_participant(
            conversation,
            user_id,
        )

        if not conversation.is_active:
            self._error(
                status.HTTP_403_FORBIDDEN,
                "This conversation is inactive",
            )

        if conversation.conversation_type == ConversationType.MENTORSHIP:
            self._require_active_mentorship(conversation)

        elif conversation.conversation_type == ConversationType.DIRECT:
            # Direct chats require an accepted connection or mentorship.
            participants = self.repository.list_participants(
                conversation.id
            )

            if len(participants) != 2:
                self._error(
                    status.HTTP_403_FORBIDDEN,
                    "Direct conversation is not configured correctly",
                )

            first_id = participants[0].user_id
            second_id = participants[1].user_id

            relationship = (
                self.repository.get_accepted_mentorship_between_users(
                    first_id,
                    second_id,
                )
            )

            connection = self.repository.get_accepted_connection_between_users(
                first_id,
                second_id,
            )

            if relationship is None and connection is None:
                self._error(
                    status.HTTP_403_FORBIDDEN,
                    "An accepted connection or mentorship is required to send messages",
                )

        else:
            # Project and group permissions will be added
            # when their membership workflows are connected.
            self._error(
                status.HTTP_403_FORBIDDEN,
                "Messaging for this conversation type is not enabled yet",
            )

    @staticmethod
    def _conversation_detail(conversation):
        return ConversationDetailResponse.model_validate(
            conversation
        )

    def _conversation_summary(
        self,
        conversation: Conversation,
        user_id: uuid.UUID,
    ):
        summary = ConversationSummaryResponse.model_validate(
            conversation
        )

        last_message = self.repository.get_last_message(
            conversation.id
        )

        if last_message is not None:
            from app.modules.messaging.schemas import MessageResponse

            summary.last_message = MessageResponse.model_validate(
                last_message
            )

        summary.unread_count = (
            self.repository.count_unread_messages(
                conversation_id=conversation.id,
                user_id=user_id,
            )
        )

        return summary

    # ========================================================
    # CREATE DIRECT CONVERSATION
    # ========================================================

    def create_direct_conversation(
        self,
        *,
        current_user: User,
        payload: ConversationCreate,
    ):
        if current_user.id == payload.recipient_user_id:
            self._error(
                status.HTTP_400_BAD_REQUEST,
                "You cannot start a conversation with yourself",
            )

        recipient = self.repository.get_user(
            payload.recipient_user_id
        )

        if recipient is None:
            self._error(
                status.HTTP_404_NOT_FOUND,
                "Recipient not found",
            )

        relationship = (
            self.repository.get_accepted_mentorship_between_users(
                current_user.id,
                recipient.id,
            )
        )

        accepted_connection = self.repository.get_accepted_connection_between_users(
            current_user.id,
            recipient.id,
        )

        if relationship is None and accepted_connection is None:
            self._error(
                status.HTTP_403_FORBIDDEN,
                "You must be connected or have an accepted mentorship to start a conversation",
            )

        if relationship is None:
            existing = self.repository.get_direct_conversation(current_user.id, recipient.id)
            if existing is not None:
                self._require_participant(existing, current_user.id)
                return self._conversation_detail(existing)
            try:
                conversation = self.repository.create_conversation(
                    conversation_type=ConversationType.DIRECT,
                    created_by=current_user.id,
                )
                self.repository.add_participant(conversation_id=conversation.id, user_id=current_user.id)
                self.repository.add_participant(conversation_id=conversation.id, user_id=recipient.id)
                self.repository.commit()
                return self._conversation_detail(self.repository.get_conversation(conversation.id))
            except IntegrityError:
                self.repository.rollback()
                existing = self.repository.get_direct_conversation(current_user.id, recipient.id)
                if existing is not None:
                    return self._conversation_detail(existing)
                raise

        # Reuse the mentorship-linked conversation rather
        # than creating a second chat for the same relationship.
        existing = self.repository.get_conversation_by_mentorship(
            relationship.id
        )

        if existing is not None:
            self._require_participant(
                existing,
                current_user.id,
            )

            return self._conversation_detail(existing)

        return self.create_mentorship_conversation(
            current_user=current_user,
            payload=MentorshipConversationCreate(
                mentorship_id=relationship.id
            ),
        )

    # ========================================================
    # CREATE MENTORSHIP CONVERSATION
    # ========================================================

    def create_mentorship_conversation(
        self,
        *,
        current_user: User,
        payload: MentorshipConversationCreate,
    ):
        mentorship = self.repository.get_mentorship(
            payload.mentorship_id
        )

        if mentorship is None:
            self._error(
                status.HTTP_404_NOT_FOUND,
                "Mentorship not found",
            )

        mentor_user_id = mentorship.mentor_profile.user_id
        mentee_user_id = mentorship.mentee_user_id

        if current_user.id not in {
            mentor_user_id,
            mentee_user_id,
        }:
            self._error(
                status.HTTP_404_NOT_FOUND,
                "Mentorship not found",
            )

        if mentorship.status != MentorshipStatus.ACCEPTED:
            self._error(
                status.HTTP_403_FORBIDDEN,
                "Mentorship must be accepted before messaging",
            )

        existing = self.repository.get_conversation_by_mentorship(
            mentorship.id
        )

        if existing is not None:
            self._require_participant(
                existing,
                current_user.id,
            )

            return self._conversation_detail(existing)

        try:
            conversation = self.repository.create_conversation(
                conversation_type=ConversationType.MENTORSHIP,
                created_by=current_user.id,
                mentorship_id=mentorship.id,
            )

            self.repository.add_participant(
                conversation_id=conversation.id,
                user_id=mentor_user_id,
            )

            self.repository.add_participant(
                conversation_id=conversation.id,
                user_id=mentee_user_id,
            )

            self.repository.commit()

        except IntegrityError:
            self.repository.rollback()

            # Another request may have created the same
            # mentorship conversation concurrently.
            existing = self.repository.get_conversation_by_mentorship(
                mentorship.id
            )

            if existing is not None:
                self._require_participant(
                    existing,
                    current_user.id,
                )

                return self._conversation_detail(existing)

            raise

        except Exception:
            self.repository.rollback()
            raise

        conversation = self.repository.get_conversation(
            conversation.id
        )

        return self._conversation_detail(conversation)

    # ========================================================
    # PROJECT / GROUP CONVERSATIONS
    # ========================================================

    def create_project_conversation(
        self,
        *,
        current_user: User,
        payload: ProjectConversationCreate,
    ):
        self._error(
            status.HTTP_501_NOT_IMPLEMENTED,
            "Project messaging will be enabled after project membership integration",
        )

    def create_group_conversation(
        self,
        *,
        current_user: User,
        payload: GroupConversationCreate,
    ):
        self._error(
            status.HTTP_501_NOT_IMPLEMENTED,
            "Group messaging is not enabled yet",
        )

    # ========================================================
    # CONVERSATION DISCOVERY
    # ========================================================

    def get_conversation(
        self,
        *,
        current_user: User,
        conversation_id: uuid.UUID,
    ):
        conversation = self._get_conversation(
            conversation_id
        )

        self._require_participant(
            conversation,
            current_user.id,
        )

        return self._conversation_detail(
            conversation
        )

    def list_conversations(
        self,
        *,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
    ):
        conversations = (
            self.repository.list_user_conversations(
                current_user.id,
                limit=limit,
                offset=offset,
            )
        )

        total = self.repository.count_user_conversations(
            current_user.id
        )

        summaries = [
            self._conversation_summary(
                conversation,
                current_user.id,
            )
            for conversation in conversations
        ]

        return ConversationListResponse(
            conversations=summaries,
            total=total,
            limit=limit,
            offset=offset,
        )

    # ========================================================
    # SEND MESSAGE
    # ========================================================

    def send_message(
        self,
        *,
        current_user: User,
        conversation_id: uuid.UUID,
        payload: MessageCreate,
    ):
        conversation = self._get_conversation(
            conversation_id
        )

        self._require_can_send(
            conversation,
            current_user.id,
        )

        try:
            message = self.repository.create_message(
                conversation_id=conversation.id,
                sender_id=current_user.id,
                content=payload.content,
            )

            self.repository.touch_conversation(
                conversation
            )

            self.repository.commit()
            self.repository.refresh(message)

        except Exception:
            self.repository.rollback()
            raise

        return message

    # ========================================================
    # MESSAGE HISTORY
    # ========================================================

    def list_messages(
        self,
        *,
        current_user: User,
        conversation_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ):
        conversation = self._get_conversation(
            conversation_id
        )

        self._require_participant(
            conversation,
            current_user.id,
        )

        messages = self.repository.list_messages(
            conversation.id,
            limit=limit,
            offset=offset,
        )

        total = self.repository.count_messages(
            conversation.id
        )

        return MessageListResponse(
            messages=messages,
            total=total,
            limit=limit,
            offset=offset,
        )

    # ========================================================
    # EDIT MESSAGE
    # ========================================================

    def edit_message(
        self,
        *,
        current_user: User,
        message_id: uuid.UUID,
        payload: MessageUpdate,
    ):
        message = self.repository.get_message(
            message_id
        )

        if message is None:
            self._error(
                status.HTTP_404_NOT_FOUND,
                "Message not found",
            )

        conversation = self._get_conversation(
            message.conversation_id
        )

        self._require_can_send(
            conversation,
            current_user.id,
        )

        if message.sender_id != current_user.id:
            self._error(
                status.HTTP_403_FORBIDDEN,
                "You can edit only your own messages",
            )

        if message.is_deleted:
            self._error(
                status.HTTP_409_CONFLICT,
                "Deleted messages cannot be edited",
            )

        try:
            updated = self.repository.update_message(
                message,
                payload.content,
            )

            self.repository.commit()
            self.repository.refresh(updated)

        except Exception:
            self.repository.rollback()
            raise

        return updated

    # ========================================================
    # DELETE MESSAGE
    # ========================================================

    def delete_message(
        self,
        *,
        current_user: User,
        message_id: uuid.UUID,
    ):
        message = self.repository.get_message(
            message_id
        )

        if message is None:
            self._error(
                status.HTTP_404_NOT_FOUND,
                "Message not found",
            )

        conversation = self._get_conversation(
            message.conversation_id
        )

        self._require_participant(
            conversation,
            current_user.id,
        )

        if message.sender_id != current_user.id:
            self._error(
                status.HTTP_403_FORBIDDEN,
                "You can delete only your own messages",
            )

        if message.is_deleted:
            return MessagingActionResponse(
                success=True,
                message="Message already deleted",
            )

        try:
            self.repository.soft_delete_message(
                message
            )
            self.repository.commit()

        except Exception:
            self.repository.rollback()
            raise

        return MessagingActionResponse(
            success=True,
            message="Message deleted",
        )

    # ========================================================
    # MARK CONVERSATION READ
    # ========================================================

    def mark_conversation_read(
        self,
        *,
        current_user: User,
        conversation_id: uuid.UUID,
    ):
        conversation = self._get_conversation(
            conversation_id
        )

        participant = self._require_participant(
            conversation,
            current_user.id,
        )

        try:
            updated = self.repository.mark_conversation_read(
                participant
            )

            self.repository.commit()

        except Exception:
            self.repository.rollback()
            raise

        return MarkConversationReadResponse(
            conversation_id=conversation.id,
            user_id=current_user.id,
            last_read_at=updated.last_read_at,
            unread_count=self.repository.count_unread_messages(
                conversation_id=conversation.id,
                user_id=current_user.id,
            ),
        )

    # ========================================================
    # UNREAD COUNTS
    # ========================================================

    def get_unread_counts(
        self,
        *,
        current_user: User,
    ):
        return UnreadCountResponse(
            total_unread_messages=(
                self.repository.count_all_unread_messages(
                    current_user.id
                )
            ),
            conversations_with_unread=(
                self.repository.count_conversations_with_unread(
                    current_user.id
                )
            ),
        )

    # ========================================================
    # MESSAGING PERMISSION CHECK
    # ========================================================

    def check_messaging_permission(
        self,
        *,
        current_user: User,
        recipient_user_id: uuid.UUID,
    ):
        if current_user.id == recipient_user_id:
            return MessagingPermissionResponse(
                can_message=False,
                reason="You cannot message yourself",
            )

        recipient = self.repository.get_user(
            recipient_user_id
        )

        if recipient is None:
            return MessagingPermissionResponse(
                can_message=False,
                reason="Recipient not found",
            )

        mentorship = (
            self.repository.get_accepted_mentorship_between_users(
                current_user.id,
                recipient_user_id,
            )
        )

        if mentorship is None:
            connection = self.repository.get_accepted_connection_between_users(
                current_user.id,
                recipient_user_id,
            )
            if connection is None:
                return MessagingPermissionResponse(
                    can_message=False,
                    reason="Connect with this member or accept a mentorship before messaging",
                )
            conversation = self.repository.get_direct_conversation(current_user.id, recipient_user_id)
            return MessagingPermissionResponse(
                can_message=True,
                reason=None,
                conversation_id=conversation.id if conversation is not None else None,
            )

        conversation = self.repository.get_conversation_by_mentorship(
            mentorship.id
        )

        return MessagingPermissionResponse(
            can_message=True,
            reason=None,
            conversation_id=(
                conversation.id
                if conversation is not None
                else None
            ),
        )
