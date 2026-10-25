import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


# =========================================================
# ENUMS
# =========================================================


class InterestCategory(str, enum.Enum):
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    FINANCE = "finance"
    MARKETING = "marketing"
    STARTUPS = "startups"
    ECONOMY = "economy"
    RESEARCH = "research"
    HEALTHCARE = "healthcare"
    DESIGN = "design"
    LAW = "law"
    EDUCATION = "education"
    CYBERSECURITY = "cybersecurity"
    DATA_SCIENCE = "data_science"
    ARTIFICIAL_INTELLIGENCE = "artificial_intelligence"
    ENTREPRENEURSHIP = "entrepreneurship"
    OPERATIONS = "operations"
    GLOBAL_AFFAIRS = "global_affairs"
    OTHER = "other"


class GoalType(str, enum.Enum):
    CAREER = "career"
    LEARNING = "learning"
    PROJECT = "project"
    INTERNSHIP = "internship"
    JOB = "job"
    RESEARCH = "research"
    STARTUP = "startup"
    NETWORKING = "networking"
    PERSONAL = "personal"
    OTHER = "other"


class GoalStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class LearningPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# =========================================================
# USER INTEREST
# =========================================================


class UserInterest(Base):
    __tablename__ = "user_interests"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "name",
            name="uq_user_interest_name",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    category: Mapped[InterestCategory] = mapped_column(
        Enum(
            InterestCategory,
            name="interest_category",
        ),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


# =========================================================
# USER GOAL
# =========================================================


class UserGoal(Base):
    __tablename__ = "user_goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    goal_type: Mapped[GoalType] = mapped_column(
        Enum(
            GoalType,
            name="goal_type",
        ),
        default=GoalType.CAREER,
        nullable=False,
        index=True,
    )

    status: Mapped[GoalStatus] = mapped_column(
        Enum(
            GoalStatus,
            name="goal_status",
        ),
        default=GoalStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    target_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# =========================================================
# SKILL USER WANTS TO LEARN
# =========================================================


class UserLearningSkill(Base):
    __tablename__ = "user_learning_skills"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "skill_id",
            name="uq_user_learning_skill",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "skills.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    target_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    priority: Mapped[LearningPriority] = mapped_column(
        Enum(
            LearningPriority,
            name="learning_priority",
        ),
        default=LearningPriority.MEDIUM,
        nullable=False,
    )

    reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    skill = relationship(
        "Skill",
    )


# =========================================================
# USER PERSONALIZATION SETTINGS
# =========================================================


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        unique=True,
        nullable=False,
        index=True,
    )

    # -----------------------------------------------------
    # PERSONALIZED NEWS
    # -----------------------------------------------------

    personalized_news_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    news_categories: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False,
    )

    # -----------------------------------------------------
    # DAILY ASSESSMENTS
    # -----------------------------------------------------

    daily_assessment_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    daily_assessment_question_count: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
    )

    # -----------------------------------------------------
    # OPPORTUNITY RECOMMENDATIONS
    # -----------------------------------------------------

    project_recommendations_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    internship_recommendations_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    course_recommendations_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    mentor_recommendations_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # -----------------------------------------------------
    # PREFERRED DOMAINS
    # -----------------------------------------------------

    preferred_domains: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=False,
    )

    # -----------------------------------------------------
    # TIMESTAMPS
    # -----------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )