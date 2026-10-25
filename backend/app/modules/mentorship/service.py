import uuid

from fastapi import HTTPException

from app.models.user import User, UserRole
from app.modules.mentorship.models import (
    MentorProfile,
    Mentorship,
    MentorshipStatus,
)
from app.modules.mentorship.repositories import MentorRepository
from app.modules.mentorship.schemas import (
    MentorCapacityResponse,
    MentorProfileCreate,
    MentorProfileUpdate,
    MentorshipAcceptRequest,
    MentorshipCancelRequest,
    MentorshipCompleteRequest,
    MentorshipListResponse,
    MentorshipRejectRequest,
    MentorshipRequestCreate,
    MentorshipResponse,
    MyMenteeResponse,
    MyMentorResponse,
)
from app.modules.notifications.models import NotificationType
from app.modules.notifications.repositories import NotificationRepository
from app.modules.notifications.service import NotificationService


class MentorService:
    def __init__(
        self,
        repository: MentorRepository,
    ):
        self.repository = repository

        # The mentorship repository and notification repository
        # use the same SQLAlchemy session.
        self.notification_service = NotificationService(
            NotificationRepository(
                repository.db
            )
        )

    # ========================================================
    # ROLE / PERMISSION HELPERS
    # ========================================================

    def _check_mentor_eligibility(
        self,
        current_user: User,
    ) -> None:
        """
        Only academicians and professionals can create
        and manage mentor profiles.
        """

        allowed_roles = {
            UserRole.ACADEMICIAN,
            UserRole.PROFESSIONAL,
        }

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only academicians and professionals "
                    "can create a mentor profile"
                ),
            )

    def _get_current_user_mentor_profile(
        self,
        current_user: User,
    ) -> MentorProfile:
        """
        Return the current user's mentor profile.

        Used for mentor-only operations such as viewing
        incoming requests or accepting mentorships.
        """

        self._check_mentor_eligibility(
            current_user
        )

        mentor = self.repository.get_by_user_id(
            current_user.id
        )

        if mentor is None:
            raise HTTPException(
                status_code=404,
                detail="Mentor profile not found",
            )

        return mentor

    def _get_mentorship_or_404(
        self,
        mentorship_id: uuid.UUID,
    ) -> Mentorship:
        mentorship = self.repository.get_mentorship(
            mentorship_id
        )

        if mentorship is None:
            raise HTTPException(
                status_code=404,
                detail="Mentorship not found",
            )

        return mentorship

    def _is_mentor_owner(
        self,
        mentorship: Mentorship,
        current_user: User,
    ) -> bool:
        return (
            mentorship.mentor_profile.user_id
            == current_user.id
        )

    def _is_mentee(
        self,
        mentorship: Mentorship,
        current_user: User,
    ) -> bool:
        return (
            mentorship.mentee_user_id
            == current_user.id
        )

    def _check_participant(
        self,
        mentorship: Mentorship,
        current_user: User,
    ) -> None:
        if not (
            self._is_mentor_owner(
                mentorship,
                current_user,
            )
            or self._is_mentee(
                mentorship,
                current_user,
            )
        ):
            # Return 404 rather than exposing that another
            # user's mentorship exists.
            raise HTTPException(
                status_code=404,
                detail="Mentorship not found",
            )

    # ========================================================
    # REFERENCE VALIDATION
    # ========================================================

    def validate_references(
        self,
        organization_id: uuid.UUID | None,
        institution_id: uuid.UUID | None,
        skill_ids: list[uuid.UUID] | None,
    ) -> None:
        if organization_id is not None:
            organization = (
                self.repository.get_organization(
                    organization_id
                )
            )

            if organization is None:
                raise HTTPException(
                    status_code=404,
                    detail="Organization not found",
                )

        if institution_id is not None:
            institution = (
                self.repository.get_institution(
                    institution_id
                )
            )

            if institution is None:
                raise HTTPException(
                    status_code=404,
                    detail="Institution not found",
                )

        if skill_ids is not None:
            for skill_id in set(
                skill_ids
            ):
                skill = self.repository.get_skill(
                    skill_id
                )

                if skill is None:
                    raise HTTPException(
                        status_code=404,
                        detail=(
                            f"Skill {skill_id} not found"
                        ),
                    )

    # ========================================================
    # MENTOR PROFILE
    # ========================================================

    def create_profile(
        self,
        current_user: User,
        payload: MentorProfileCreate,
    ) -> MentorProfile:
        self._check_mentor_eligibility(
            current_user
        )

        existing = (
            self.repository.get_by_user_id(
                current_user.id
            )
        )

        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Mentor profile already exists"
                ),
            )

        self.validate_references(
            payload.organization_id,
            payload.institution_id,
            payload.skill_ids,
        )

        data = payload.model_dump()

        return self.repository.create(
            user_id=current_user.id,
            **data,
        )

    def get_my_profile(
        self,
        current_user: User,
    ) -> MentorProfile:
        return self._get_current_user_mentor_profile(
            current_user
        )

    def get_public_profile(
        self,
        mentor_id: uuid.UUID,
    ) -> MentorProfile:
        mentor = self.repository.get_by_id(
            mentor_id
        )

        if mentor is None:
            raise HTTPException(
                status_code=404,
                detail="Mentor profile not found",
            )

        return mentor

    def update_profile(
        self,
        current_user: User,
        payload: MentorProfileUpdate,
    ) -> MentorProfile:
        self._check_mentor_eligibility(
            current_user
        )

        mentor = self.get_my_profile(
            current_user
        )

        update_data = payload.model_dump(
            exclude_unset=True
        )

        organization_id = update_data.get(
            "organization_id",
            mentor.organization_id,
        )

        institution_id = update_data.get(
            "institution_id",
            mentor.institution_id,
        )

        skill_ids = update_data.get(
            "skill_ids",
            None,
        )

        self.validate_references(
            organization_id,
            institution_id,
            skill_ids,
        )

        return self.repository.update(
            mentor,
            update_data,
        )

    # ========================================================
    # MENTOR DISCOVERY
    # ========================================================

    def list_mentors(
        self,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
        accepting_only: bool = True,
    ) -> list[MentorProfile]:
        """
        Browse mentor profiles.

        The current user's own mentor profile is removed
        from discovery results.
        """

        mentors = self.repository.list_mentors(
            limit=limit + 1,
            offset=offset,
            accepting_only=accepting_only,
        )

        filtered = [
            mentor
            for mentor in mentors
            if mentor.user_id != current_user.id
        ]

        return filtered[:limit]

    # ========================================================
    # MENTOR CAPACITY
    # ========================================================

    def get_mentor_capacity(
        self,
        mentor_profile_id: uuid.UUID,
    ) -> MentorCapacityResponse:
        mentor = self.repository.get_by_id(
            mentor_profile_id
        )

        if mentor is None:
            raise HTTPException(
                status_code=404,
                detail="Mentor profile not found",
            )

        active_mentees = (
            self.repository.count_active_mentees(
                mentor.id
            )
        )

        if mentor.max_mentees is None:
            available_slots = None
            is_full = False
        else:
            available_slots = max(
                mentor.max_mentees
                - active_mentees,
                0,
            )

            is_full = (
                active_mentees
                >= mentor.max_mentees
            )

        return MentorCapacityResponse(
            mentor_profile_id=mentor.id,
            is_accepting_mentees=(
                mentor.is_accepting_mentees
            ),
            max_mentees=mentor.max_mentees,
            active_mentees=active_mentees,
            available_slots=available_slots,
            is_full=is_full,
        )

    def _check_mentor_available(
        self,
        mentor: MentorProfile,
    ) -> None:
        if not mentor.is_accepting_mentees:
            raise HTTPException(
                status_code=409,
                detail=(
                    "This mentor is not currently "
                    "accepting mentees"
                ),
            )

        if mentor.max_mentees is None:
            return

        active_mentees = (
            self.repository.count_active_mentees(
                mentor.id
            )
        )

        if (
            active_mentees
            >= mentor.max_mentees
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "This mentor has reached their "
                    "maximum mentee capacity"
                ),
            )

    # ========================================================
    # CREATE MENTORSHIP REQUEST
    # ========================================================

    def create_mentorship_request(
        self,
        current_user: User,
        payload: MentorshipRequestCreate,
    ) -> Mentorship:
        mentor = self.repository.get_by_id(
            payload.mentor_profile_id
        )

        if mentor is None:
            raise HTTPException(
                status_code=404,
                detail="Mentor profile not found",
            )

        # ----------------------------------------------------
        # NO SELF-MENTORSHIP
        # ----------------------------------------------------

        if mentor.user_id == current_user.id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "You cannot request mentorship "
                    "from yourself"
                ),
            )

        # ----------------------------------------------------
        # MENTOR AVAILABILITY
        # ----------------------------------------------------

        self._check_mentor_available(
            mentor
        )

        # ----------------------------------------------------
        # DUPLICATE PENDING / ACTIVE RELATIONSHIP
        # ----------------------------------------------------

        existing = (
            self.repository
            .get_existing_open_mentorship(
                mentor_profile_id=mentor.id,
                mentee_user_id=current_user.id,
            )
        )

        if existing is not None:
            if (
                existing.status
                == MentorshipStatus.PENDING
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "You already have a pending "
                        "mentorship request with this mentor"
                    ),
                )

            if (
                existing.status
                == MentorshipStatus.ACCEPTED
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "You already have an active "
                        "mentorship with this mentor"
                    ),
                )

        mentorship = (
            self.repository
            .create_mentorship_request(
                mentor_profile_id=mentor.id,
                mentee_user_id=current_user.id,
                request_message=(
                    payload.request_message
                ),
                goals=payload.goals,
            )
        )

        # ----------------------------------------------------
        # NOTIFY MENTOR
        # ----------------------------------------------------

        self.notification_service.create_notification(
            user_id=mentor.user_id,
            actor_id=current_user.id,
            notification_type=(
                NotificationType.MENTOR_REQUEST
            ),
            title="New mentorship request",
            message=(
                "You received a new mentorship request."
            ),
            entity_type="mentorship",
            entity_id=mentorship.id,
        )

        return mentorship

    # ========================================================
    # SENT REQUESTS
    # ========================================================

    def get_sent_requests(
        self,
        current_user: User,
        limit: int = 50,
        offset: int = 0,
    ) -> MentorshipListResponse:
        mentorships = (
            self.repository.get_sent_requests(
                mentee_user_id=current_user.id,
                limit=limit,
                offset=offset,
            )
        )

        total = (
            self.repository.count_sent_requests(
                current_user.id
            )
        )

        return MentorshipListResponse(
            mentorships=[
                MentorshipResponse.model_validate(
                    mentorship
                )
                for mentorship in mentorships
            ],
            total=total,
        )

    # ========================================================
    # RECEIVED REQUESTS
    # ========================================================

    def get_received_requests(
        self,
        current_user: User,
        limit: int = 50,
        offset: int = 0,
        pending_only: bool = False,
    ) -> MentorshipListResponse:
        mentor = (
            self._get_current_user_mentor_profile(
                current_user
            )
        )

        mentorships = (
            self.repository.get_received_requests(
                mentor_profile_id=mentor.id,
                limit=limit,
                offset=offset,
                pending_only=pending_only,
            )
        )

        total = (
            self.repository.count_received_requests(
                mentor_profile_id=mentor.id,
                pending_only=pending_only,
            )
        )

        return MentorshipListResponse(
            mentorships=[
                MentorshipResponse.model_validate(
                    mentorship
                )
                for mentorship in mentorships
            ],
            total=total,
        )

    # ========================================================
    # GET INDIVIDUAL MENTORSHIP
    # ========================================================

    def get_mentorship(
        self,
        mentorship_id: uuid.UUID,
        current_user: User,
    ) -> Mentorship:
        mentorship = self._get_mentorship_or_404(
            mentorship_id
        )

        self._check_participant(
            mentorship,
            current_user,
        )

        return mentorship

    # ========================================================
    # ACCEPT REQUEST
    # ========================================================

    def accept_request(
        self,
        mentorship_id: uuid.UUID,
        current_user: User,
        payload: MentorshipAcceptRequest,
    ) -> Mentorship:
        mentorship = self._get_mentorship_or_404(
            mentorship_id
        )

        if not self._is_mentor_owner(
            mentorship,
            current_user,
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only the requested mentor can "
                    "accept this mentorship request"
                ),
            )

        if (
            mentorship.status
            != MentorshipStatus.PENDING
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Only pending mentorship requests "
                    "can be accepted"
                ),
            )

        # Check again at acceptance time because mentor
        # capacity may have changed after the student
        # originally submitted the request.
        self._check_mentor_available(
            mentorship.mentor_profile
        )

        mentorship = (
            self.repository.accept_mentorship(
                mentorship=mentorship,
                response_message=(
                    payload.response_message
                ),
            )
        )

        self.notification_service.create_notification(
            user_id=mentorship.mentee_user_id,
            actor_id=current_user.id,
            notification_type=(
                NotificationType.MENTOR_ACCEPTED
            ),
            title="Mentorship request accepted",
            message=(
                "Your mentorship request has been accepted."
            ),
            entity_type="mentorship",
            entity_id=mentorship.id,
        )

        return mentorship

    # ========================================================
    # REJECT REQUEST
    # ========================================================

    def reject_request(
        self,
        mentorship_id: uuid.UUID,
        current_user: User,
        payload: MentorshipRejectRequest,
    ) -> Mentorship:
        mentorship = self._get_mentorship_or_404(
            mentorship_id
        )

        if not self._is_mentor_owner(
            mentorship,
            current_user,
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Only the requested mentor can "
                    "reject this mentorship request"
                ),
            )

        if (
            mentorship.status
            != MentorshipStatus.PENDING
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Only pending mentorship requests "
                    "can be rejected"
                ),
            )

        mentorship = (
            self.repository.reject_mentorship(
                mentorship=mentorship,
                response_message=(
                    payload.response_message
                ),
            )
        )

        # We currently only have MENTOR_REQUEST and
        # MENTOR_ACCEPTED notification types.
        # SYSTEM is used temporarily for rejection until
        # dedicated mentorship lifecycle notification
        # types are added.
        self.notification_service.create_notification(
            user_id=mentorship.mentee_user_id,
            actor_id=current_user.id,
            notification_type=(
                NotificationType.SYSTEM
            ),
            title="Mentorship request update",
            message=(
                "Your mentorship request was declined."
            ),
            entity_type="mentorship",
            entity_id=mentorship.id,
        )

        return mentorship

    # ========================================================
    # CANCEL REQUEST / ACTIVE MENTORSHIP
    # ========================================================

    def cancel_mentorship(
        self,
        mentorship_id: uuid.UUID,
        current_user: User,
        payload: MentorshipCancelRequest,
    ) -> Mentorship:
        mentorship = self._get_mentorship_or_404(
            mentorship_id
        )

        self._check_participant(
            mentorship,
            current_user,
        )

        if mentorship.status not in {
            MentorshipStatus.PENDING,
            MentorshipStatus.ACCEPTED,
        }:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Only pending or active mentorships "
                    "can be cancelled"
                ),
            )

        previous_status = mentorship.status

        mentor_user_id = (
            mentorship.mentor_profile.user_id
        )

        mentee_user_id = (
            mentorship.mentee_user_id
        )

        mentorship = (
            self.repository.cancel_mentorship(
                mentorship=mentorship,
                cancellation_reason=(
                    payload.cancellation_reason
                ),
            )
        )

        # Notify the other participant.
        if current_user.id == mentee_user_id:
            recipient_id = mentor_user_id
        else:
            recipient_id = mentee_user_id

        if (
            previous_status
            == MentorshipStatus.PENDING
        ):
            message = (
                "A mentorship request was cancelled."
            )
        else:
            message = (
                "An active mentorship was cancelled."
            )

        self.notification_service.create_notification(
            user_id=recipient_id,
            actor_id=current_user.id,
            notification_type=(
                NotificationType.SYSTEM
            ),
            title="Mentorship cancelled",
            message=message,
            entity_type="mentorship",
            entity_id=mentorship.id,
        )

        return mentorship

    # ========================================================
    # COMPLETE ACTIVE MENTORSHIP
    # ========================================================

    def complete_mentorship(
        self,
        mentorship_id: uuid.UUID,
        current_user: User,
        payload: MentorshipCompleteRequest,
    ) -> Mentorship:
        mentorship = self._get_mentorship_or_404(
            mentorship_id
        )

        self._check_participant(
            mentorship,
            current_user,
        )

        if (
            mentorship.status
            != MentorshipStatus.ACCEPTED
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Only active mentorships "
                    "can be completed"
                ),
            )

        mentor_user_id = (
            mentorship.mentor_profile.user_id
        )

        mentee_user_id = (
            mentorship.mentee_user_id
        )

        mentorship = (
            self.repository.complete_mentorship(
                mentorship=mentorship,
                completion_note=(
                    payload.completion_note
                ),
            )
        )

        if current_user.id == mentee_user_id:
            recipient_id = mentor_user_id
        else:
            recipient_id = mentee_user_id

        self.notification_service.create_notification(
            user_id=recipient_id,
            actor_id=current_user.id,
            notification_type=(
                NotificationType.SYSTEM
            ),
            title="Mentorship completed",
            message=(
                "Your mentorship has been marked as completed."
            ),
            entity_type="mentorship",
            entity_id=mentorship.id,
        )

        return mentorship

    # ========================================================
    # MY ACTIVE MENTORS
    # ========================================================

    def get_my_mentors(
        self,
        current_user: User,
    ) -> list[MyMentorResponse]:
        mentorships = (
            self.repository
            .get_active_mentors_for_user(
                current_user.id
            )
        )

        return [
            MyMentorResponse(
                mentorship_id=mentorship.id,
                mentor=mentorship.mentor_profile,
                status=mentorship.status,
                goals=mentorship.goals,
                started_at=mentorship.started_at,
                created_at=mentorship.created_at,
            )
            for mentorship in mentorships
        ]

    # ========================================================
    # MY ACTIVE MENTEES
    # ========================================================

    def get_my_mentees(
        self,
        current_user: User,
    ) -> list[MyMenteeResponse]:
        mentor = (
            self._get_current_user_mentor_profile(
                current_user
            )
        )

        mentorships = (
            self.repository
            .get_active_mentees_for_mentor(
                mentor.id
            )
        )

        return [
            MyMenteeResponse(
                mentorship_id=mentorship.id,
                mentee_user_id=(
                    mentorship.mentee_user_id
                ),
                status=mentorship.status,
                request_message=(
                    mentorship.request_message
                ),
                goals=mentorship.goals,
                started_at=mentorship.started_at,
                created_at=mentorship.created_at,
            )
            for mentorship in mentorships
        ]

    # ========================================================
    # MENTORSHIP HISTORY
    # ========================================================

    def get_history(
        self,
        current_user: User,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MentorshipResponse]:
        mentor = self.repository.get_by_user_id(
            current_user.id
        )

        mentor_profile_id = (
            mentor.id
            if mentor is not None
            else None
        )

        mentorships = (
            self.repository
            .get_user_mentorship_history(
                user_id=current_user.id,
                mentor_profile_id=(
                    mentor_profile_id
                ),
                limit=limit,
                offset=offset,
            )
        )

        return [
            MentorshipResponse.model_validate(
                mentorship
            )
            for mentorship in mentorships
        ]