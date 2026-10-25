
"""
app/models/user.py

The central User model for CollabVerse.

Supports:
- Email/password authentication
- OAuth-only accounts (Google and Microsoft)
- External account linking
- Role-based user profiles
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class UserRole(str, enum.Enum):
    STUDENT = "student"
    RECRUITER = "recruiter"
    ACADEMICIAN = "academician"
    PROFESSIONAL = "professional"
    INSTITUTION_ADMIN = "institution_admin"


class User(Base):
    __tablename__ = "users"

    # ---------------------------------------------------------
    # PRIMARY KEY
    # ---------------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------------
    # AUTHENTICATION
    # ---------------------------------------------------------

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Nullable for OAuth-only accounts.
    # Email/password accounts continue storing a secure hash.
    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # ---------------------------------------------------------
    # USER ROLE
    # ---------------------------------------------------------

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # ---------------------------------------------------------
    # ACCOUNT STATUS
    # ---------------------------------------------------------

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    terms_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    terms_version: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    # ---------------------------------------------------------
    # TIMESTAMPS
    # ---------------------------------------------------------

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

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ---------------------------------------------------------
    # ROLE-SPECIFIC PROFILES
    # ---------------------------------------------------------

    student_profile = relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    recruiter_profile = relationship(
        "RecruiterProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    academician_profile = relationship(
        "AcademicianProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    institution_profile = relationship(
        "InstitutionProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # ---------------------------------------------------------
    # OAUTH ACCOUNTS
    # ---------------------------------------------------------

    oauth_accounts = relationship(
        "OAuthAccount",
        back_populates="user",
        cascade="all, delete-orphan",
    )
