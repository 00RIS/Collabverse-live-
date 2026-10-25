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
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


# ============================================================
# ENUMS
# ============================================================


class MentoringMode(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    HYBRID = "hybrid"


class MentorshipStatus(str, enum.Enum):
    """
    Lifecycle of a mentorship relationship.

    PENDING:
        Student has requested mentorship and is waiting
        for the mentor to respond.

    ACCEPTED:
        Mentor accepted the request and the mentorship
        is currently active.

    REJECTED:
        Mentor rejected the request.

    CANCELLED:
        Request/mentorship was cancelled by one of
        the participants.

    COMPLETED:
        Mentorship finished successfully.
    """

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


# ============================================================
# MENTOR PROFILE
# ============================================================


class MentorProfile(Base):
    __tablename__ = "mentor_profiles"

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

    headline: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    designation: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    years_of_experience: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "institutions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    mentor_domains: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        nullable=False,
        default=list,
    )

    mentoring_topics: Mapped[list[str]] = mapped_column(
        ARRAY(String(150)),
        nullable=False,
        default=list,
    )

    mentoring_mode: Mapped[MentoringMode] = mapped_column(
        Enum(
            MentoringMode,
            name="mentoring_mode",
        ),
        default=MentoringMode.ONLINE,
        nullable=False,
    )

    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    linkedin_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    portfolio_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_accepting_mentees: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    max_mentees: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
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

    # --------------------------------------------------------
    # RELATIONSHIPS
    # --------------------------------------------------------

    user = relationship(
        "User",
        foreign_keys=[user_id],
    )

    organization = relationship(
        "Organization",
        foreign_keys=[organization_id],
    )

    institution = relationship(
        "Institution",
        foreign_keys=[institution_id],
    )

    skills = relationship(
        "MentorSkill",
        back_populates="mentor_profile",
        cascade="all, delete-orphan",
    )

    mentorships = relationship(
        "Mentorship",
        back_populates="mentor_profile",
        cascade="all, delete-orphan",
        foreign_keys="Mentorship.mentor_profile_id",
    )


# ============================================================
# MENTOR SKILLS
# ============================================================


class MentorSkill(Base):
    __tablename__ = "mentor_skills"

    __table_args__ = (
        UniqueConstraint(
            "mentor_profile_id",
            "skill_id",
            name="uq_mentor_skill",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    mentor_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "mentor_profiles.id",
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

    mentor_profile = relationship(
        "MentorProfile",
        back_populates="skills",
    )

    skill = relationship(
        "Skill",
        foreign_keys=[skill_id],
    )


# ============================================================
# MENTORSHIP
# ============================================================


class Mentorship(Base):
    """
    Represents the relationship between a mentor and mentee.

    The same model represents both:
        1. The initial mentorship request.
        2. The active mentorship after acceptance.
        3. The final history after completion/cancellation.
    """

    __tablename__ = "mentorships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # --------------------------------------------------------
    # PARTICIPANTS
    # --------------------------------------------------------

    mentor_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "mentor_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    mentee_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # --------------------------------------------------------
    # REQUEST INFORMATION
    # --------------------------------------------------------

    request_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    goals: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    status: Mapped[MentorshipStatus] = mapped_column(
        Enum(
            MentorshipStatus,
            name="mentorship_status",
        ),
        default=MentorshipStatus.PENDING,
        nullable=False,
        index=True,
    )

    # --------------------------------------------------------
    # RESPONSE / COMPLETION NOTES
    # --------------------------------------------------------

    response_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    completion_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    cancellation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------------

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
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

    # --------------------------------------------------------
    # RELATIONSHIPS
    # --------------------------------------------------------

    mentor_profile = relationship(
        "MentorProfile",
        back_populates="mentorships",
        foreign_keys=[mentor_profile_id],
    )

    mentee = relationship(
        "User",
        foreign_keys=[mentee_user_id],
    )