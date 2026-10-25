import uuid
from datetime import datetime, timezone

from sqlalchemy import select, or_
from sqlalchemy.orm import Session, selectinload

from app.models.profile import StudentProfile
from app.models.project import (
    Project,
    ProjectStatus,
)
from app.models.skill import Skill
from app.models.student_skill import StudentSkill
from app.models.internship import (
    Internship,
    InternshipStatus,
)

from app.modules.preferences.models import (
    UserGoal,
    UserInterest,
    UserLearningSkill,
)

from app.modules.hackathons.models import (
    Hackathon,
    HackathonStatus,
)


class RecommendationRepository:
    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    # =========================================================
    # STUDENT PROFILE
    # =========================================================

    def get_student_profile(
        self,
        user_id: uuid.UUID,
    ) -> StudentProfile | None:

        return self.db.scalar(
            select(StudentProfile).where(
                StudentProfile.user_id
                == user_id
            )
        )

    # =========================================================
    # STUDENT SKILLS
    # =========================================================

    def get_student_skills(
        self,
        student: StudentProfile,
    ) -> list[StudentSkill]:

        return list(
            student.student_skills
        )

    # =========================================================
    # LEARNING SKILLS
    # =========================================================

    def get_learning_skills(
        self,
        user_id: uuid.UUID,
    ) -> list[UserLearningSkill]:

        return list(
            self.db.scalars(
                select(UserLearningSkill)
                .options(
                    selectinload(
                        UserLearningSkill.skill
                    )
                )
                .where(
                    UserLearningSkill.user_id
                    == user_id
                )
            ).all()
        )

    # =========================================================
    # INTERESTS
    # =========================================================

    def get_interests(
        self,
        user_id: uuid.UUID,
    ) -> list[UserInterest]:

        return list(
            self.db.scalars(
                select(UserInterest)
                .where(
                    UserInterest.user_id
                    == user_id
                )
            ).all()
        )

    # =========================================================
    # GOALS
    # =========================================================

    def get_goals(
        self,
        user_id: uuid.UUID,
    ) -> list[UserGoal]:

        return list(
            self.db.scalars(
                select(UserGoal)
                .where(
                    UserGoal.user_id
                    == user_id
                )
            ).all()
        )

    # =========================================================
    # SKILL
    # =========================================================

    def get_skill(
        self,
        skill_id: uuid.UUID,
    ) -> Skill | None:

        return self.db.get(
            Skill,
            skill_id,
        )

    # =========================================================
    # OPEN PROJECTS
    # =========================================================

    def get_open_projects(
        self,
        user_id: uuid.UUID,
        limit: int = 100,
    ) -> list[Project]:

        return list(
            self.db.scalars(
                select(Project)
                .options(
                    selectinload(
                        Project.skills
                    )
                )
                .where(
                    Project.status
                    == ProjectStatus.OPEN,

                    Project.is_accepting_members.is_(
                        True
                    ),

                    Project.creator_id
                    != user_id,
                )
                .order_by(
                    Project.created_at.desc()
                )
                .limit(limit)
            ).all()
        )

    # =========================================================
    # OPEN INTERNSHIPS
    # =========================================================

    def get_open_internships(
        self,
        user_id: uuid.UUID,
        limit: int = 100,
    ) -> list[Internship]:

        return list(
            self.db.scalars(
                select(Internship)
                .options(
                    selectinload(
                        Internship.skills
                    )
                )
                .where(
                    Internship.status
                    == InternshipStatus.OPEN,

                    Internship.posted_by
                    != user_id,
                )
                .order_by(
                    Internship.created_at.desc()
                )
                .limit(limit)
            ).all()
        )

    # =========================================================
    # OPEN HACKATHONS
    # =========================================================

    def get_open_hackathons(
        self,
        limit: int = 1000,
    ) -> list[Hackathon]:

        """
        Return hackathons that are actually usable as
        recommendation candidates.

        Rules:
        - Must be active.
        - Registration must still be open.
        - Registration deadline must not have passed.
        - If deadline is missing, we still allow the record
          because some external opportunities may not provide
          a deadline.
        - Load skills eagerly for recommendation scoring.
        - Prefer recently discovered/updated opportunities
          rather than filling the candidate pool with the
          oldest deadlines.
        """

        now = datetime.now(
            timezone.utc
        )

        return list(
            self.db.scalars(
                select(Hackathon)
                .options(
                    selectinload(
                        Hackathon.skills
                    )
                )
                .where(
                    # -----------------------------------------
                    # ACTIVE RECORD ONLY
                    # -----------------------------------------

                    Hackathon.is_active.is_(
                        True
                    ),

                    # -----------------------------------------
                    # REGISTRATION MUST BE OPEN
                    #
                    # Do NOT include ONGOING here.
                    #
                    # An ongoing hackathon may already have
                    # closed registration, so it should not
                    # normally appear as something the user
                    # can still apply/register for.
                    # -----------------------------------------

                    Hackathon.status
                    == HackathonStatus.REGISTRATION_OPEN,

                    # -----------------------------------------
                    # DEADLINE MUST NOT BE EXPIRED
                    #
                    # NULL is allowed because some external
                    # records may legitimately have no
                    # registration deadline.
                    # -----------------------------------------

                    or_(
                        Hackathon.registration_deadline
                        .is_(None),

                        Hackathon.registration_deadline
                        > now,
                    ),
                )

                # ---------------------------------------------
                # CANDIDATE ORDER
                #
                # We are NOT ranking recommendations here.
                #
                # The service layer does personalization.
                #
                # We simply want a broad, fresh candidate
                # pool rather than the 300 opportunities with
                # the earliest deadlines.
                # ---------------------------------------------

                .order_by(
                    Hackathon.created_at.desc(),
                    Hackathon.registration_deadline.asc(),
                )

                .limit(limit)
            ).all()
        )