import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


# =========================================================
# ENUMS
# =========================================================

class ProjectType(str, enum.Enum):
    STUDENT = "student"
    HACKATHON = "hackathon"
    RESEARCH = "research"
    INDUSTRY_LIVE = "industry_live"
    ACADEMIC = "academic"
    STARTUP = "startup"
    INNOVATION_CHALLENGE = "innovation_challenge"
    OPEN_COLLABORATION = "open_collaboration"


class ProjectDifficulty(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectVisibility(str, enum.Enum):
    PUBLIC = "public"
    INSTITUTION_ONLY = "institution_only"
    PRIVATE = "private"


class ProjectMemberRole(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"
    MENTOR = "mentor"
    CONTRIBUTOR = "contributor"


class ProjectApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


# =========================================================
# PROJECT
# =========================================================

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    domain: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    project_type: Mapped[ProjectType] = mapped_column(
        Enum(
            ProjectType,
            name="project_type",
        ),
        nullable=False,
    )

    difficulty: Mapped[ProjectDifficulty] = mapped_column(
        Enum(
            ProjectDifficulty,
            name="project_difficulty",
        ),
        default=ProjectDifficulty.BEGINNER,
        nullable=False,
    )

    status: Mapped[ProjectStatus] = mapped_column(
        Enum(
            ProjectStatus,
            name="project_status",
        ),
        default=ProjectStatus.DRAFT,
        nullable=False,
    )

    visibility: Mapped[ProjectVisibility] = mapped_column(
        Enum(
            ProjectVisibility,
            name="project_visibility",
        ),
        default=ProjectVisibility.PUBLIC,
        nullable=False,
    )

    max_team_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    is_accepting_members: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    skills = relationship(
        "ProjectSkill",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    members = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    applications = relationship(
        "ProjectApplication",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectResource(Base):
    __tablename__ = "project_resources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    added_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# =========================================================
# PROJECT SKILLS
# =========================================================

class ProjectSkill(Base):
    __tablename__ = "project_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "projects.id",
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

    required_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    project = relationship(
        "Project",
        back_populates="skills",
    )


# =========================================================
# PROJECT MEMBERS
# =========================================================

class ProjectMember(Base):
    __tablename__ = "project_members"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_member_user",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
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

    role: Mapped[ProjectMemberRole] = mapped_column(
        Enum(
            ProjectMemberRole,
            name="project_member_role",
        ),
        default=ProjectMemberRole.MEMBER,
        nullable=False,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    project = relationship(
        "Project",
        back_populates="members",
    )

    user = relationship(
        "User",
        foreign_keys=[user_id],
    )


# =========================================================
# PROJECT APPLICATIONS
# =========================================================

class ProjectApplication(Base):
    __tablename__ = "project_applications"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_application_user",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
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

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[ProjectApplicationStatus] = mapped_column(
        Enum(
            ProjectApplicationStatus,
            name="project_application_status",
        ),
        default=ProjectApplicationStatus.PENDING,
        nullable=False,
        index=True,
    )

    applied_at: Mapped[datetime] = mapped_column(
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

    project = relationship(
        "Project",
        back_populates="applications",
    )

    user = relationship(
        "User",
        foreign_keys=[user_id],
    )
