import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.skill import Skill

from app.modules.preferences.models import (
    UserGoal,
    UserInterest,
    UserLearningSkill,
    UserPreference,
)


class PreferenceRepository:
    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    # =========================================================
    # INTERESTS
    # =========================================================

    def list_interests(
        self,
        user_id: uuid.UUID,
    ) -> list[UserInterest]:
        stmt = (
            select(UserInterest)
            .where(
                UserInterest.user_id == user_id
            )
            .order_by(
                UserInterest.created_at.asc()
            )
        )

        return list(
            self.db.scalars(stmt).all()
        )

    def get_interest(
        self,
        interest_id: uuid.UUID,
    ) -> UserInterest | None:
        return self.db.get(
            UserInterest,
            interest_id,
        )

    def get_interest_by_name(
        self,
        user_id: uuid.UUID,
        name: str,
    ) -> UserInterest | None:
        stmt = select(UserInterest).where(
            UserInterest.user_id == user_id,
            func.lower(UserInterest.name)
            == name.strip().lower(),
        )

        return self.db.scalar(stmt)

    def create_interest(
        self,
        interest: UserInterest,
    ) -> UserInterest:
        self.db.add(interest)
        self.db.commit()
        self.db.refresh(interest)

        return interest

    def delete_interest(
        self,
        interest: UserInterest,
    ) -> None:
        self.db.delete(interest)
        self.db.commit()

    # =========================================================
    # GOALS
    # =========================================================

    def list_goals(
        self,
        user_id: uuid.UUID,
    ) -> list[UserGoal]:
        stmt = (
            select(UserGoal)
            .where(
                UserGoal.user_id == user_id
            )
            .order_by(
                UserGoal.priority.desc(),
                UserGoal.created_at.desc(),
            )
        )

        return list(
            self.db.scalars(stmt).all()
        )

    def get_goal(
        self,
        goal_id: uuid.UUID,
    ) -> UserGoal | None:
        return self.db.get(
            UserGoal,
            goal_id,
        )

    def create_goal(
        self,
        goal: UserGoal,
    ) -> UserGoal:
        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)

        return goal

    def update_goal(
        self,
        goal: UserGoal,
        update_data: dict,
    ) -> UserGoal:
        for field, value in update_data.items():
            setattr(
                goal,
                field,
                value,
            )

        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)

        return goal

    def delete_goal(
        self,
        goal: UserGoal,
    ) -> None:
        self.db.delete(goal)
        self.db.commit()

    # =========================================================
    # SKILLS TO LEARN
    # =========================================================

    def get_skill(
        self,
        skill_id: uuid.UUID,
    ) -> Skill | None:
        return self.db.get(
            Skill,
            skill_id,
        )

    def list_learning_skills(
        self,
        user_id: uuid.UUID,
    ) -> list[UserLearningSkill]:
        stmt = (
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
            .order_by(
                UserLearningSkill.created_at.desc()
            )
        )

        return list(
            self.db.scalars(stmt).all()
        )

    def get_learning_skill(
        self,
        learning_skill_id: uuid.UUID,
    ) -> UserLearningSkill | None:
        stmt = (
            select(UserLearningSkill)
            .options(
                selectinload(
                    UserLearningSkill.skill
                )
            )
            .where(
                UserLearningSkill.id
                == learning_skill_id
            )
        )

        return self.db.scalar(stmt)

    def get_learning_skill_by_skill_id(
        self,
        user_id: uuid.UUID,
        skill_id: uuid.UUID,
    ) -> UserLearningSkill | None:
        stmt = (
            select(UserLearningSkill)
            .options(
                selectinload(
                    UserLearningSkill.skill
                )
            )
            .where(
                UserLearningSkill.user_id
                == user_id,
                UserLearningSkill.skill_id
                == skill_id,
            )
        )

        return self.db.scalar(stmt)

    def create_learning_skill(
        self,
        learning_skill: UserLearningSkill,
    ) -> UserLearningSkill:
        self.db.add(learning_skill)
        self.db.commit()
        self.db.refresh(learning_skill)

        return self.get_learning_skill(
            learning_skill.id
        )

    def update_learning_skill(
        self,
        learning_skill: UserLearningSkill,
        update_data: dict,
    ) -> UserLearningSkill:
        for field, value in update_data.items():
            setattr(
                learning_skill,
                field,
                value,
            )

        self.db.add(learning_skill)
        self.db.commit()
        self.db.refresh(learning_skill)

        return self.get_learning_skill(
            learning_skill.id
        )

    def delete_learning_skill(
        self,
        learning_skill: UserLearningSkill,
    ) -> None:
        self.db.delete(learning_skill)
        self.db.commit()

    # =========================================================
    # SETTINGS
    # =========================================================

    def get_settings(
        self,
        user_id: uuid.UUID,
    ) -> UserPreference | None:
        stmt = select(UserPreference).where(
            UserPreference.user_id == user_id
        )

        return self.db.scalar(stmt)

    def create_settings(
        self,
        user_id: uuid.UUID,
    ) -> UserPreference:
        settings = UserPreference(
            user_id=user_id,
        )

        self.db.add(settings)
        self.db.commit()
        self.db.refresh(settings)

        return settings

    def get_or_create_settings(
        self,
        user_id: uuid.UUID,
    ) -> UserPreference:
        settings = self.get_settings(
            user_id
        )

        if settings is not None:
            return settings

        return self.create_settings(
            user_id
        )

    def update_settings(
        self,
        settings: UserPreference,
        update_data: dict,
    ) -> UserPreference:
        for field, value in update_data.items():
            setattr(
                settings,
                field,
                value,
            )

        self.db.add(settings)
        self.db.commit()
        self.db.refresh(settings)

        return settings