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
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func

from app.db.base import Base


# =========================================================
# ENUMS
# =========================================================


class HackathonMode(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    HYBRID = "hybrid"


class HackathonDifficulty(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    OPEN = "open"


class HackathonStatus(str, enum.Enum):
    DRAFT = "draft"
    REGISTRATION_OPEN = "registration_open"
    REGISTRATION_CLOSED = "registration_closed"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class HackathonSourceType(str, enum.Enum):
    COLLABVERSE = "collabverse"
    EXTERNAL = "external"


class HackathonParticipantStatus(
    str,
    enum.Enum,
):
    REGISTERED = "registered"
    WITHDRAWN = "withdrawn"
    COMPLETED = "completed"


# =========================================================
# HACKATHON
# =========================================================


class Hackathon(Base):
    __tablename__ = "hackathons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # =====================================================
    # BASIC INFORMATION
    # =====================================================

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

    organizer_name: Mapped[
        str | None
    ] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # User who created/imported the hackathon.
    # External hackathons do not necessarily
    # have a CollabVerse organizer account.
    created_by: Mapped[
        uuid.UUID | None
    ] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # =====================================================
    # SOURCE / AGGREGATOR INFORMATION
    # =====================================================

    source_type: Mapped[
        HackathonSourceType
    ] = mapped_column(
        Enum(
            HackathonSourceType,
            name="hackathon_source_type",
        ),
        default=(
            HackathonSourceType.COLLABVERSE
        ),
        nullable=False,
        index=True,
    )

    # Example:
    # "Devpost"
    # "Devfolio"
    # "Unstop"
    # "University Website"
    # "CollabVerse"
    source_name: Mapped[
        str | None
    ] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Original page from which the event
    # was discovered.
    source_url: Mapped[
        str | None
    ] = mapped_column(
        String(1000),
        nullable=True,
    )

    # ID used by the external source.
    # Helps us update instead of duplicating.
    external_id: Mapped[
        str | None
    ] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # When we last refreshed information
    # from the external source.
    last_synced_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # =====================================================
    # EVENT INFORMATION
    # =====================================================

    mode: Mapped[
        HackathonMode
    ] = mapped_column(
        Enum(
            HackathonMode,
            name="hackathon_mode",
        ),
        default=HackathonMode.ONLINE,
        nullable=False,
        index=True,
    )

    difficulty: Mapped[
        HackathonDifficulty
    ] = mapped_column(
        Enum(
            HackathonDifficulty,
            name="hackathon_difficulty",
        ),
        default=HackathonDifficulty.OPEN,
        nullable=False,
        index=True,
    )

    status: Mapped[
        HackathonStatus
    ] = mapped_column(
        Enum(
            HackathonStatus,
            name="hackathon_status",
        ),
        default=HackathonStatus.DRAFT,
        nullable=False,
        index=True,
    )

    location: Mapped[
        str | None
    ] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    min_team_size: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    max_team_size: Mapped[int] = mapped_column(
        Integer,
        default=4,
        nullable=False,
    )

    registration_deadline: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    start_date: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    end_date: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    prize_details: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    registration_url: Mapped[
        str | None
    ] = mapped_column(
        String(1000),
        nullable=True,
    )

    banner_url: Mapped[
        str | None
    ] = mapped_column(
        String(1000),
        nullable=True,
    )

    # =====================================================
    # TRUST / MODERATION
    # =====================================================

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    skills = relationship(
        "HackathonSkill",
        back_populates="hackathon",
        cascade="all, delete-orphan",
    )

    participants = relationship(
        "HackathonParticipant",
        back_populates="hackathon",
        cascade="all, delete-orphan",
    )

    creator = relationship(
        "User",
        foreign_keys=[created_by],
    )


# =========================================================
# HACKATHON SKILLS
# =========================================================


class HackathonSkill(Base):
    __tablename__ = "hackathon_skills"

    __table_args__ = (
        UniqueConstraint(
            "hackathon_id",
            "skill_id",
            name="uq_hackathon_skill",
        ),
    )

    id: Mapped[
        uuid.UUID
    ] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    hackathon_id: Mapped[
        uuid.UUID
    ] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "hackathons.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    skill_id: Mapped[
        uuid.UUID
    ] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "skills.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    required_level: Mapped[
        int | None
    ] = mapped_column(
        Integer,
        nullable=True,
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    hackathon = relationship(
        "Hackathon",
        back_populates="skills",
    )

    skill = relationship(
        "Skill",
        foreign_keys=[skill_id],
    )


# =========================================================
# HACKATHON PARTICIPANTS
# =========================================================


class HackathonParticipant(Base):
    __tablename__ = "hackathon_participants"

    __table_args__ = (
        UniqueConstraint(
            "hackathon_id",
            "user_id",
            name="uq_hackathon_participant_user",
        ),
    )

    id: Mapped[
        uuid.UUID
    ] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    hackathon_id: Mapped[
        uuid.UUID
    ] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "hackathons.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user_id: Mapped[
        uuid.UUID
    ] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    team_name: Mapped[
        str | None
    ] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[
        HackathonParticipantStatus
    ] = mapped_column(
        Enum(
            HackathonParticipantStatus,
            name=(
                "hackathon_participant_status"
            ),
        ),
        default=(
            HackathonParticipantStatus
            .REGISTERED
        ),
        nullable=False,
        index=True,
    )

    registered_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    hackathon = relationship(
        "Hackathon",
        back_populates="participants",
    )

    user = relationship(
        "User",
        foreign_keys=[user_id],
    )