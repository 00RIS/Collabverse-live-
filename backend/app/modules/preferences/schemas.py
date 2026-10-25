import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.preferences.models import (
    GoalStatus,
    GoalType,
    InterestCategory,
    LearningPriority,
)


# =========================================================
# INTEREST SCHEMAS
# =========================================================


class UserInterestCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=150,
    )

    category: InterestCategory


class UserInterestResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    category: InterestCategory
    created_at: datetime


# =========================================================
# GOAL SCHEMAS
# =========================================================


class UserGoalCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    goal_type: GoalType = GoalType.CAREER

    target_date: date | None = None

    priority: int = Field(
        default=1,
        ge=1,
        le=5,
    )


class UserGoalUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    goal_type: GoalType | None = None

    status: GoalStatus | None = None

    target_date: date | None = None

    priority: int | None = Field(
        default=None,
        ge=1,
        le=5,
    )


class UserGoalResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    goal_type: GoalType
    status: GoalStatus
    target_date: date | None
    priority: int
    created_at: datetime
    updated_at: datetime


# =========================================================
# SKILLS TO LEARN SCHEMAS
# =========================================================


class UserLearningSkillCreate(BaseModel):
    skill_id: uuid.UUID

    target_level: int | None = Field(
        default=None,
        ge=1,
        le=4,
    )

    priority: LearningPriority = (
        LearningPriority.MEDIUM
    )

    reason: str | None = Field(
        default=None,
        max_length=500,
    )


class UserLearningSkillUpdate(BaseModel):
    target_level: int | None = Field(
        default=None,
        ge=1,
        le=4,
    )

    priority: LearningPriority | None = None

    reason: str | None = Field(
        default=None,
        max_length=500,
    )


class SkillSummary(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    name: str


class UserLearningSkillResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    user_id: uuid.UUID
    skill_id: uuid.UUID
    target_level: int | None
    priority: LearningPriority
    reason: str | None
    created_at: datetime
    updated_at: datetime

    skill: SkillSummary


# =========================================================
# PERSONALIZATION SETTINGS
# =========================================================


class UserPreferenceUpdate(BaseModel):
    personalized_news_enabled: bool | None = None

    news_categories: list[str] | None = None

    daily_assessment_enabled: bool | None = None

    daily_assessment_question_count: int | None = (
        Field(
            default=None,
            ge=1,
            le=20,
        )
    )

    project_recommendations_enabled: bool | None = None

    internship_recommendations_enabled: bool | None = None

    course_recommendations_enabled: bool | None = None

    mentor_recommendations_enabled: bool | None = None

    preferred_domains: list[str] | None = None


class UserPreferenceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    user_id: uuid.UUID

    personalized_news_enabled: bool
    news_categories: list[str]

    daily_assessment_enabled: bool
    daily_assessment_question_count: int

    project_recommendations_enabled: bool
    internship_recommendations_enabled: bool
    course_recommendations_enabled: bool
    mentor_recommendations_enabled: bool

    preferred_domains: list[str]

    created_at: datetime
    updated_at: datetime


# =========================================================
# COMPLETE PREFERENCE PROFILE
# =========================================================


class MyPreferencesResponse(BaseModel):
    interests: list[UserInterestResponse]

    goals: list[UserGoalResponse]

    skills_to_learn: list[
        UserLearningSkillResponse
    ]

    settings: UserPreferenceResponse