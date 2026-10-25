"""
app/schemas/user.py

Output schema for "who am I" / user-lookup endpoints. Notice there is no
`hashed_password` field here at all — that's the whole point of keeping
schemas separate from the DB model (see schemas/auth.py for the longer
explanation).
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserOut(BaseModel):
    # ConfigDict(from_attributes=True) lets Pydantic build this schema
    # directly from a SQLAlchemy model instance (reading `.email`,
    # `.role`, etc. as attributes) instead of requiring a dict.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: UserRole
    avatar_url: str | None = None
    is_active: bool
    is_email_verified: bool
    created_at: datetime


class PublicUserOut(BaseModel):
    """Small, non-sensitive profile card for the member directory."""

    id: uuid.UUID
    role: UserRole
    full_name: str
    headline: str | None = None
    avatar_url: str | None = None


class PublicUserProfileOut(BaseModel):
    """Non-sensitive public profile for an authenticated community member."""

    user_id: uuid.UUID
    role: UserRole
    full_name: str
    headline: str | None = None
    avatar_url: str | None = None
    profile: dict[str, Any]
    interests: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    mentor_profile: dict[str, Any] | None = None
    projects: list[dict[str, Any]] = Field(default_factory=list)
