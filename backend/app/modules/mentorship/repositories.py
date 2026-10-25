import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.institution import Institution
from app.models.organization import Organization
from app.models.skill import Skill
from app.modules.mentorship.models import (
    MentorProfile,
    MentorSkill,
    Mentorship,
    MentorshipStatus,
)


class MentorRepository:
    def __init__(self, db: Session):
        self.db = db

    # ========================================================
    # MENTOR PROFILE
    # ========================================================

    def get_by_user_id(
        self,
        user_id: uuid.UUID,
    ) -> MentorProfile | None:
        return self.db.scalar(
            select(MentorProfile)
            .options(
                selectinload(MentorProfile.skills),
            )
            .where(
                MentorProfile.user_id == user_id
            )
        )

    def get_by_id(
        self,
        mentor_id: uuid.UUID,
    ) -> MentorProfile | None:
        return self.db.scalar(
            select(MentorProfile)
            .options(
                selectinload(MentorProfile.skills),
            )
            .where(
                MentorProfile.id == mentor_id
            )
        )

    def create(
        self,
        user_id: uuid.UUID,
        **data,
    ) -> MentorProfile:
        skill_ids = data.pop(
            "skill_ids",
            [],
        )

        mentor = MentorProfile(
            user_id=user_id,
            **data,
        )

        self.db.add(mentor)
        self.db.flush()

        self.set_skills(
            mentor=mentor,
            skill_ids=skill_ids,
            commit=False,
        )

        self.db.commit()

        return self.get_by_id(
            mentor.id
        )

    def update(
        self,
        mentor: MentorProfile,
        data: dict,
    ) -> MentorProfile:
        skill_ids = data.pop(
            "skill_ids",
            None,
        )

        for field, value in data.items():
            setattr(
                mentor,
                field,
                value,
            )

        if skill_ids is not None:
            self.set_skills(
                mentor=mentor,
                skill_ids=skill_ids,
                commit=False,
            )

        self.db.commit()

        return self.get_by_id(
            mentor.id
        )

    # ========================================================
    # MENTOR SKILLS
    # ========================================================

    def set_skills(
        self,
        mentor: MentorProfile,
        skill_ids: list[uuid.UUID],
        commit: bool = True,
    ) -> None:
        self.db.execute(
            delete(MentorSkill).where(
                MentorSkill.mentor_profile_id
                == mentor.id
            )
        )

        unique_skill_ids = set(
            skill_ids
        )

        for skill_id in unique_skill_ids:
            self.db.add(
                MentorSkill(
                    mentor_profile_id=mentor.id,
                    skill_id=skill_id,
                )
            )

        if commit:
            self.db.commit()

    def get_skill(
        self,
        skill_id: uuid.UUID,
    ) -> Skill | None:
        return self.db.get(
            Skill,
            skill_id,
        )

    # ========================================================
    # ORGANIZATION / INSTITUTION REFERENCES
    # ========================================================

    def get_organization(
        self,
        organization_id: uuid.UUID,
    ) -> Organization | None:
        return self.db.get(
            Organization,
            organization_id,
        )

    def get_institution(
        self,
        institution_id: uuid.UUID,
    ) -> Institution | None:
        return self.db.get(
            Institution,
            institution_id,
        )

    # ========================================================
    # MENTOR DISCOVERY
    # ========================================================

    def list_mentors(
        self,
        limit: int = 20,
        offset: int = 0,
        accepting_only: bool = True,
    ) -> list[MentorProfile]:
        query = (
            select(MentorProfile)
            .options(
                selectinload(MentorProfile.skills),
            )
        )

        if accepting_only:
            query = query.where(
                MentorProfile.is_accepting_mentees.is_(True)
            )

        query = (
            query
            .order_by(
                MentorProfile.is_verified.desc(),
                MentorProfile.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        return list(
            self.db.scalars(
                query
            ).all()
        )

    def count_mentors(
        self,
        accepting_only: bool = True,
    ) -> int:
        query = select(
            func.count(
                MentorProfile.id
            )
        )

        if accepting_only:
            query = query.where(
                MentorProfile.is_accepting_mentees.is_(True)
            )

        return (
            self.db.scalar(query)
            or 0
        )

    # ========================================================
    # MENTORSHIP GETTERS
    # ========================================================

    def get_mentorship(
        self,
        mentorship_id: uuid.UUID,
    ) -> Mentorship | None:
        return self.db.scalar(
            select(Mentorship)
            .options(
                selectinload(
                    Mentorship.mentor_profile
                ).selectinload(
                    MentorProfile.skills
                ),
            )
            .where(
                Mentorship.id
                == mentorship_id
            )
        )

    def get_existing_open_mentorship(
        self,
        mentor_profile_id: uuid.UUID,
        mentee_user_id: uuid.UUID,
    ) -> Mentorship | None:
        """
        Find an existing pending or accepted mentorship
        between the same mentor and mentee.

        Historical rejected, cancelled and completed
        relationships do not block a future request.
        """

        return self.db.scalar(
            select(Mentorship)
            .where(
                Mentorship.mentor_profile_id
                == mentor_profile_id,
                Mentorship.mentee_user_id
                == mentee_user_id,
                Mentorship.status.in_(
                    [
                        MentorshipStatus.PENDING,
                        MentorshipStatus.ACCEPTED,
                    ]
                ),
            )
            .order_by(
                Mentorship.created_at.desc()
            )
        )

    # ========================================================
    # CREATE MENTORSHIP REQUEST
    # ========================================================

    def create_mentorship_request(
        self,
        mentor_profile_id: uuid.UUID,
        mentee_user_id: uuid.UUID,
        request_message: str | None = None,
        goals: str | None = None,
    ) -> Mentorship:
        mentorship = Mentorship(
            mentor_profile_id=mentor_profile_id,
            mentee_user_id=mentee_user_id,
            request_message=request_message,
            goals=goals,
            status=MentorshipStatus.PENDING,
        )

        self.db.add(
            mentorship
        )

        self.db.commit()

        return self.get_mentorship(
            mentorship.id
        )

    # ========================================================
    # ACTIVE MENTEE COUNT / CAPACITY
    # ========================================================

    def count_active_mentees(
        self,
        mentor_profile_id: uuid.UUID,
    ) -> int:
        count = self.db.scalar(
            select(
                func.count(
                    Mentorship.id
                )
            ).where(
                Mentorship.mentor_profile_id
                == mentor_profile_id,
                Mentorship.status
                == MentorshipStatus.ACCEPTED,
            )
        )

        return count or 0

    # ========================================================
    # SENT REQUESTS
    # ========================================================

    def get_sent_requests(
        self,
        mentee_user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Mentorship]:
        return list(
            self.db.scalars(
                select(Mentorship)
                .options(
                    selectinload(
                        Mentorship.mentor_profile
                    ).selectinload(
                        MentorProfile.skills
                    ),
                )
                .where(
                    Mentorship.mentee_user_id
                    == mentee_user_id
                )
                .order_by(
                    Mentorship.created_at.desc()
                )
                .offset(offset)
                .limit(limit)
            ).all()
        )

    def count_sent_requests(
        self,
        mentee_user_id: uuid.UUID,
    ) -> int:
        count = self.db.scalar(
            select(
                func.count(
                    Mentorship.id
                )
            ).where(
                Mentorship.mentee_user_id
                == mentee_user_id
            )
        )

        return count or 0

    # ========================================================
    # RECEIVED REQUESTS
    # ========================================================

    def get_received_requests(
        self,
        mentor_profile_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        pending_only: bool = False,
    ) -> list[Mentorship]:
        query = (
            select(Mentorship)
            .options(
                selectinload(
                    Mentorship.mentor_profile
                ).selectinload(
                    MentorProfile.skills
                ),
            )
            .where(
                Mentorship.mentor_profile_id
                == mentor_profile_id
            )
        )

        if pending_only:
            query = query.where(
                Mentorship.status
                == MentorshipStatus.PENDING
            )

        query = (
            query
            .order_by(
                Mentorship.created_at.desc()
            )
            .offset(offset)
            .limit(limit)
        )

        return list(
            self.db.scalars(
                query
            ).all()
        )

    def count_received_requests(
        self,
        mentor_profile_id: uuid.UUID,
        pending_only: bool = False,
    ) -> int:
        query = select(
            func.count(
                Mentorship.id
            )
        ).where(
            Mentorship.mentor_profile_id
            == mentor_profile_id
        )

        if pending_only:
            query = query.where(
                Mentorship.status
                == MentorshipStatus.PENDING
            )

        count = self.db.scalar(
            query
        )

        return count or 0

    # ========================================================
    # MY ACTIVE MENTORS
    # ========================================================

    def get_active_mentors_for_user(
        self,
        mentee_user_id: uuid.UUID,
    ) -> list[Mentorship]:
        return list(
            self.db.scalars(
                select(Mentorship)
                .options(
                    selectinload(
                        Mentorship.mentor_profile
                    ).selectinload(
                        MentorProfile.skills
                    ),
                )
                .where(
                    Mentorship.mentee_user_id
                    == mentee_user_id,
                    Mentorship.status
                    == MentorshipStatus.ACCEPTED,
                )
                .order_by(
                    Mentorship.started_at.desc()
                )
            ).all()
        )

    # ========================================================
    # MY ACTIVE MENTEES
    # ========================================================

    def get_active_mentees_for_mentor(
        self,
        mentor_profile_id: uuid.UUID,
    ) -> list[Mentorship]:
        return list(
            self.db.scalars(
                select(Mentorship)
                .where(
                    Mentorship.mentor_profile_id
                    == mentor_profile_id,
                    Mentorship.status
                    == MentorshipStatus.ACCEPTED,
                )
                .order_by(
                    Mentorship.started_at.desc()
                )
            ).all()
        )

    # ========================================================
    # ACCEPT REQUEST
    # ========================================================

    def accept_mentorship(
        self,
        mentorship: Mentorship,
        response_message: str | None = None,
    ) -> Mentorship:
        now = datetime.now(
            timezone.utc
        )

        mentorship.status = (
            MentorshipStatus.ACCEPTED
        )

        mentorship.response_message = (
            response_message
        )

        mentorship.responded_at = now
        mentorship.started_at = now

        self.db.commit()

        return self.get_mentorship(
            mentorship.id
        )

    # ========================================================
    # REJECT REQUEST
    # ========================================================

    def reject_mentorship(
        self,
        mentorship: Mentorship,
        response_message: str | None = None,
    ) -> Mentorship:
        mentorship.status = (
            MentorshipStatus.REJECTED
        )

        mentorship.response_message = (
            response_message
        )

        mentorship.responded_at = datetime.now(
            timezone.utc
        )

        self.db.commit()

        return self.get_mentorship(
            mentorship.id
        )

    # ========================================================
    # CANCEL MENTORSHIP
    # ========================================================

    def cancel_mentorship(
        self,
        mentorship: Mentorship,
        cancellation_reason: str | None = None,
    ) -> Mentorship:
        now = datetime.now(
            timezone.utc
        )

        mentorship.status = (
            MentorshipStatus.CANCELLED
        )

        mentorship.cancellation_reason = (
            cancellation_reason
        )

        mentorship.cancelled_at = now

        # If a pending request is cancelled, it has effectively
        # received its final response at this point.
        if mentorship.responded_at is None:
            mentorship.responded_at = now

        self.db.commit()

        return self.get_mentorship(
            mentorship.id
        )

    # ========================================================
    # COMPLETE MENTORSHIP
    # ========================================================

    def complete_mentorship(
        self,
        mentorship: Mentorship,
        completion_note: str | None = None,
    ) -> Mentorship:
        mentorship.status = (
            MentorshipStatus.COMPLETED
        )

        mentorship.completion_note = (
            completion_note
        )

        mentorship.completed_at = datetime.now(
            timezone.utc
        )

        self.db.commit()

        return self.get_mentorship(
            mentorship.id
        )

    # ========================================================
    # PARTICIPANT HISTORY
    # ========================================================

    def get_user_mentorship_history(
        self,
        user_id: uuid.UUID,
        mentor_profile_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Mentorship]:
        """
        Return mentorships where the user is either:

        1. The mentee.
        2. The owner of the supplied mentor profile.

        The mentor_profile_id should only be supplied by the
        service after confirming that it belongs to user_id.
        """

        conditions = [
            Mentorship.mentee_user_id
            == user_id
        ]

        if mentor_profile_id is not None:
            conditions.append(
                Mentorship.mentor_profile_id
                == mentor_profile_id
            )

        return list(
            self.db.scalars(
                select(Mentorship)
                .options(
                    selectinload(
                        Mentorship.mentor_profile
                    ).selectinload(
                        MentorProfile.skills
                    ),
                )
                .where(
                    or_(
                        *conditions
                    )
                )
                .order_by(
                    Mentorship.created_at.desc()
                )
                .offset(offset)
                .limit(limit)
            ).all()
        )

    # ========================================================
    # TRANSACTION HELPERS
    # ========================================================

    def commit(
        self,
    ) -> None:
        self.db.commit()

    def rollback(
        self,
    ) -> None:
        self.db.rollback()

    def flush(
        self,
    ) -> None:
        self.db.flush()