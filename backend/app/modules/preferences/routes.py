import uuid

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

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

from app.modules.preferences.service import (
    preference_service,
)


router = APIRouter(
    prefix="/preferences",
    tags=["Preferences"],
)


# =========================================================
# COMPLETE PREFERENCE PROFILE
# =========================================================

@router.get(
    "/me",
    response_model=MyPreferencesResponse,
)
def get_my_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    return preference_service.get_my_preferences(
        db=db,
        current_user=current_user,
    )


# =========================================================
# INTERESTS
# =========================================================

@router.post(
    "/interests",
    response_model=UserInterestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_interest(
    data: UserInterestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    return preference_service.create_interest(
        db=db,
        current_user=current_user,
        data=data,
    )


@router.delete(
    "/interests/{interest_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_interest(
    interest_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    preference_service.delete_interest(
        db=db,
        current_user=current_user,
        interest_id=interest_id,
    )

    return None


# =========================================================
# GOALS
# =========================================================

@router.post(
    "/goals",
    response_model=UserGoalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_goal(
    data: UserGoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    return preference_service.create_goal(
        db=db,
        current_user=current_user,
        data=data,
    )


@router.patch(
    "/goals/{goal_id}",
    response_model=UserGoalResponse,
)
def update_goal(
    goal_id: uuid.UUID,
    data: UserGoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    return preference_service.update_goal(
        db=db,
        current_user=current_user,
        goal_id=goal_id,
        data=data,
    )


@router.delete(
    "/goals/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_goal(
    goal_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    preference_service.delete_goal(
        db=db,
        current_user=current_user,
        goal_id=goal_id,
    )

    return None


# =========================================================
# SKILLS TO LEARN
# =========================================================

@router.post(
    "/learning-skills",
    response_model=UserLearningSkillResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_learning_skill(
    data: UserLearningSkillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    return preference_service.create_learning_skill(
        db=db,
        current_user=current_user,
        data=data,
    )


@router.patch(
    "/learning-skills/{learning_skill_id}",
    response_model=UserLearningSkillResponse,
)
def update_learning_skill(
    learning_skill_id: uuid.UUID,
    data: UserLearningSkillUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    return (
        preference_service.update_learning_skill(
            db=db,
            current_user=current_user,
            learning_skill_id=(
                learning_skill_id
            ),
            data=data,
        )
    )


@router.delete(
    "/learning-skills/{learning_skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_learning_skill(
    learning_skill_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    preference_service.delete_learning_skill(
        db=db,
        current_user=current_user,
        learning_skill_id=learning_skill_id,
    )

    return None


# =========================================================
# PERSONALIZATION SETTINGS
# =========================================================

@router.patch(
    "/settings",
    response_model=UserPreferenceResponse,
)
def update_preference_settings(
    data: UserPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    return preference_service.update_settings(
        db=db,
        current_user=current_user,
        data=data,
    )