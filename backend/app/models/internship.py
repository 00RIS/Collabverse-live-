import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class WorkMode(str, enum.Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class InternshipType(str, enum.Enum):
    SUMMER = "summer"
    WINTER = "winter"
    PART_TIME = "part_time"
    FULL_TIME = "full_time"
    RESEARCH = "research"
    APPRENTICESHIP = "apprenticeship"
    OTHER = "other"


class ExperienceLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class InternshipStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    FILLED = "filled"
    CANCELLED = "cancelled"


class Internship(Base):
    __tablename__ = "internships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    posted_by: Mapped[uuid.UUID] = mapped_column(
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

    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    work_mode: Mapped[WorkMode] = mapped_column(
        Enum(WorkMode, name="work_mode"),
        nullable=False,
    )

    internship_type: Mapped[InternshipType] = mapped_column(
        Enum(InternshipType, name="internship_type"),
        nullable=False,
    )

    experience_level: Mapped[ExperienceLevel] = mapped_column(
        Enum(ExperienceLevel, name="internship_experience_level"),
        default=ExperienceLevel.BEGINNER,
        nullable=False,
    )

    is_paid: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    stipend: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    duration_weeks: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    openings: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[InternshipStatus] = mapped_column(
        Enum(InternshipStatus, name="internship_status"),
        default=InternshipStatus.DRAFT,
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

    skills = relationship(
        "InternshipSkill",
        back_populates="internship",
        cascade="all, delete-orphan",
    )


class InternshipSkill(Base):
    __tablename__ = "internship_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    internship_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("internships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    required_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    importance_weight: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )

    mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    internship = relationship(
        "Internship",
        back_populates="skills",
    )