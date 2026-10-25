import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User

from app.modules.preferences.models import (
    UserGoal,
    UserInterest,
    UserLearningSkill,
)

from app.modules.preferences.repositories import (
    PreferenceRepository,
)

from app.modules.preferences.schemas import (
    MyPreferencesResponse,
    UserGoalCreate,
    UserGoalResponse,
    UserGoalUpdate,
    UserInterestCreate,
    UserInterestResponse,
    UserLearningSkillCreate,
    UserLearningSkillResponse,
    UserLearningSkillUpdate,
    UserPreferenceResponse,
    UserPreferenceUpdate,
)


class PreferenceService:

    # =========================================================
    # COMPLETE USER PREFERENCES
    # =========================================================

    def get_my_preferences(
        self,
        db: Session,
        current_user: User,
    ) -> MyPreferencesResponse:
        repository = PreferenceRepository(db)

        interests = repository.list_interests(
            current_user.id
        )

        goals = repository.list_goals(
            current_user.id
        )

        learning_skills = (
            repository.list_learning_skills(
                current_user.id
            )
        )

        settings = (
            repository.get_or_create_settings(
                current_user.id
            )
        )

        return MyPreferencesResponse(
            interests=[
                UserInterestResponse.model_validate(
                    interest
                )
                for interest in interests
            ],
            goals=[
                UserGoalResponse.model_validate(
                    goal
                )
                for goal in goals
            ],
            skills_to_learn=[
                UserLearningSkillResponse.model_validate(
                    learning_skill
                )
                for learning_skill
                in learning_skills
            ],
            settings=(
                UserPreferenceResponse.model_validate(
                    settings
                )
            ),
        )

    # =========================================================
    # INTERESTS
    # =========================================================

    def create_interest(
        self,
        db: Session,
        current_user: User,
        data: UserInterestCreate,
    ) -> UserInterest:
        repository = PreferenceRepository(db)

        clean_name = data.name.strip()

        existing = (
            repository.get_interest_by_name(
                user_id=current_user.id,
                name=clean_name,
            )
        )

        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Interest already added",
            )

        interest = UserInterest(
            user_id=current_user.id,
            name=clean_name,
            category=data.category,
        )

        return repository.create_interest(
            interest
        )

    def delete_interest(
        self,
        db: Session,
        current_user: User,
        interest_id: uuid.UUID,
    ) -> None:
        repository = PreferenceRepository(db)

        interest = repository.get_interest(
            interest_id
        )

        if (
            interest is None
            or interest.user_id
            != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interest not found",
            )

        repository.delete_interest(
            interest
        )

    # =========================================================
    # GOALS
    # =========================================================

    def create_goal(
        self,
        db: Session,
        current_user: User,
        data: UserGoalCreate,
    ) -> UserGoal:
        repository = PreferenceRepository(db)

        goal = UserGoal(
            user_id=current_user.id,
            title=data.title.strip(),
            description=data.description,
            goal_type=data.goal_type,
            target_date=data.target_date,
            priority=data.priority,
        )

        return repository.create_goal(
            goal
        )

    def update_goal(
        self,
        db: Session,
        current_user: User,
        goal_id: uuid.UUID,
        data: UserGoalUpdate,
    ) -> UserGoal:
        repository = PreferenceRepository(db)

        goal = repository.get_goal(
            goal_id
        )

        if (
            goal is None
            or goal.user_id
            != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found",
            )

        update_data = data.model_dump(
            exclude_unset=True
        )

        if (
            "title" in update_data
            and update_data["title"] is not None
        ):
            update_data["title"] = (
                update_data["title"].strip()
            )

        return repository.update_goal(
            goal=goal,
            update_data=update_data,
        )

    def delete_goal(
        self,
        db: Session,
        current_user: User,
        goal_id: uuid.UUID,
    ) -> None:
        repository = PreferenceRepository(db)

        goal = repository.get_goal(
            goal_id
        )

        if (
            goal is None
            or goal.user_id
            != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Goal not found",
            )

        repository.delete_goal(
            goal
        )

    # =========================================================
    # SKILLS TO LEARN
    # =========================================================

    def create_learning_skill(
        self,
        db: Session,
        current_user: User,
        data: UserLearningSkillCreate,
    ) -> UserLearningSkill:
        repository = PreferenceRepository(db)

        skill = repository.get_skill(
            data.skill_id
        )

        if skill is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skill not found",
            )

        existing = (
            repository
            .get_learning_skill_by_skill_id(
                user_id=current_user.id,
                skill_id=data.skill_id,
            )
        )

        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Skill is already in your learning list",
            )

        learning_skill = UserLearningSkill(
            user_id=current_user.id,
            skill_id=data.skill_id,
            target_level=data.target_level,
            priority=data.priority,
            reason=data.reason,
        )

        return repository.create_learning_skill(
            learning_skill
        )

    def update_learning_skill(
        self,
        db: Session,
        current_user: User,
        learning_skill_id: uuid.UUID,
        data: UserLearningSkillUpdate,
    ) -> UserLearningSkill:
        repository = PreferenceRepository(db)

        learning_skill = (
            repository.get_learning_skill(
                learning_skill_id
            )
        )

        if (
            learning_skill is None
            or learning_skill.user_id
            != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning skill not found",
            )

        update_data = data.model_dump(
            exclude_unset=True
        )

        return repository.update_learning_skill(
            learning_skill=learning_skill,
            update_data=update_data,
        )

    def delete_learning_skill(
        self,
        db: Session,
        current_user: User,
        learning_skill_id: uuid.UUID,
    ) -> None:
        repository = PreferenceRepository(db)

        learning_skill = (
            repository.get_learning_skill(
                learning_skill_id
            )
        )

        if (
            learning_skill is None
            or learning_skill.user_id
            != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning skill not found",
            )

        repository.delete_learning_skill(
            learning_skill
        )

    # =========================================================
    # SETTINGS
    # =========================================================

    def update_settings(
        self,
        db: Session,
        current_user: User,
        data: UserPreferenceUpdate,
    ):
        repository = PreferenceRepository(db)

        settings = (
            repository.get_or_create_settings(
                current_user.id
            )
        )

        update_data = data.model_dump(
            exclude_unset=True
        )

        return repository.update_settings(
            settings=settings,
            update_data=update_data,
        )


preference_service = PreferenceService()