import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.mentorship.models import (
    MentoringMode,
    MentorshipStatus,
)


# ============================================================
# MENTOR PROFILE SCHEMAS
# ============================================================


class MentorProfileCreate(BaseModel):
    headline: str | None = Field(
        default=None,
        max_length=255,
    )

    bio: str | None = Field(
        default=None,
        max_length=5000,
    )

    designation: str | None = Field(
        default=None,
        max_length=255,
    )

    years_of_experience: int | None = Field(
        default=None,
        ge=0,
        le=80,
    )

    organization_id: uuid.UUID | None = None
    institution_id: uuid.UUID | None = None

    mentor_domains: list[str] = Field(
        default_factory=list,
    )

    mentoring_topics: list[str] = Field(
        default_factory=list,
    )

    mentoring_mode: MentoringMode = MentoringMode.ONLINE

    location: str | None = Field(
        default=None,
        max_length=255,
    )

    linkedin_url: str | None = Field(
        default=None,
        max_length=500,
    )

    portfolio_url: str | None = Field(
        default=None,
        max_length=500,
    )

    is_accepting_mentees: bool = True

    max_mentees: int | None = Field(
        default=None,
        ge=1,
        le=100,
    )

    skill_ids: list[uuid.UUID] = Field(
        default_factory=list,
    )


class MentorProfileUpdate(BaseModel):
    headline: str | None = Field(
        default=None,
        max_length=255,
    )

    bio: str | None = Field(
        default=None,
        max_length=5000,
    )

    designation: str | None = Field(
        default=None,
        max_length=255,
    )

    years_of_experience: int | None = Field(
        default=None,
        ge=0,
        le=80,
    )

    organization_id: uuid.UUID | None = None
    institution_id: uuid.UUID | None = None

    mentor_domains: list[str] | None = None
    mentoring_topics: list[str] | None = None

    mentoring_mode: MentoringMode | None = None

    location: str | None = Field(
        default=None,
        max_length=255,
    )

    linkedin_url: str | None = Field(
        default=None,
        max_length=500,
    )

    portfolio_url: str | None = Field(
        default=None,
        max_length=500,
    )

    is_accepting_mentees: bool | None = None

    max_mentees: int | None = Field(
        default=None,
        ge=1,
        le=100,
    )

    skill_ids: list[uuid.UUID] | None = None


# ============================================================
# MENTOR SKILL RESPONSE
# ============================================================


class MentorSkillResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    skill_id: uuid.UUID


# ============================================================
# MENTOR PROFILE RESPONSE
# ============================================================


class MentorProfileResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    user_id: uuid.UUID

    headline: str | None
    bio: str | None

    designation: str | None
    years_of_experience: int | None

    organization_id: uuid.UUID | None
    institution_id: uuid.UUID | None

    mentor_domains: list[str]
    mentoring_topics: list[str]

    mentoring_mode: MentoringMode

    location: str | None

    linkedin_url: str | None
    portfolio_url: str | None

    is_accepting_mentees: bool
    max_mentees: int | None

    is_verified: bool

    skills: list[MentorSkillResponse]

    created_at: datetime
    updated_at: datetime


# ============================================================
# MENTOR DISCOVERY RESPONSE
# ============================================================


class MentorDiscoveryResponse(BaseModel):
    """
    Lightweight mentor information used when displaying
    mentor discovery/search results.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    user_id: uuid.UUID

    headline: str | None
    bio: str | None

    designation: str | None
    years_of_experience: int | None

    mentor_domains: list[str]
    mentoring_topics: list[str]

    mentoring_mode: MentoringMode

    location: str | None

    is_accepting_mentees: bool
    max_mentees: int | None

    is_verified: bool

    skills: list[MentorSkillResponse]

    created_at: datetime


# ============================================================
# CREATE MENTORSHIP REQUEST
# ============================================================


class MentorshipRequestCreate(BaseModel):
    """
    Payload sent by a student/user when requesting mentorship.
    """

    mentor_profile_id: uuid.UUID

    request_message: str | None = Field(
        default=None,
        max_length=3000,
    )

    goals: str | None = Field(
        default=None,
        max_length=5000,
    )


# ============================================================
# MENTOR RESPONSE
# ============================================================


class MentorshipAcceptRequest(BaseModel):
    """
    Optional response message when accepting a mentorship.
    """

    response_message: str | None = Field(
        default=None,
        max_length=3000,
    )


class MentorshipRejectRequest(BaseModel):
    """
    Optional explanation when rejecting a mentorship request.
    """

    response_message: str | None = Field(
        default=None,
        max_length=3000,
    )


# ============================================================
# MENTORSHIP CANCELLATION
# ============================================================


class MentorshipCancelRequest(BaseModel):
    cancellation_reason: str | None = Field(
        default=None,
        max_length=3000,
    )


# ============================================================
# MENTORSHIP COMPLETION
# ============================================================


class MentorshipCompleteRequest(BaseModel):
    completion_note: str | None = Field(
        default=None,
        max_length=5000,
    )


# ============================================================
# MENTORSHIP RESPONSE
# ============================================================


class MentorshipResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID

    mentor_profile_id: uuid.UUID
    mentee_user_id: uuid.UUID

    request_message: str | None
    goals: str | None

    status: MentorshipStatus

    response_message: str | None
    completion_note: str | None
    cancellation_reason: str | None

    requested_at: datetime

    responded_at: datetime | None
    started_at: datetime | None

    completed_at: datetime | None
    cancelled_at: datetime | None

    created_at: datetime
    updated_at: datetime


# ============================================================
# MENTORSHIP DETAIL RESPONSE
# ============================================================


class MentorshipDetailResponse(MentorshipResponse):
    """
    Detailed mentorship response.

    Includes mentor profile information so the frontend
    does not need to make another request just to display
    basic mentor information.
    """

    mentor_profile: MentorProfileResponse


# ============================================================
# MENTORSHIP LIST RESPONSE
# ============================================================


class MentorshipListResponse(BaseModel):
    mentorships: list[MentorshipResponse]

    total: int


# ============================================================
# MY MENTORS RESPONSE
# ============================================================


class MyMentorResponse(BaseModel):
    """
    Returned to a mentee for active mentorships.
    """

    mentorship_id: uuid.UUID

    mentor: MentorProfileResponse

    status: MentorshipStatus

    goals: str | None

    started_at: datetime | None

    created_at: datetime


# ============================================================
# MY MENTEES RESPONSE
# ============================================================


class MyMenteeResponse(BaseModel):
    """
    Returned to mentors for their active mentees.

    We intentionally expose the mentee user ID here.
    Rich student-profile information can later be added
    through the profile/portfolio system.
    """

    mentorship_id: uuid.UUID

    mentee_user_id: uuid.UUID

    status: MentorshipStatus

    request_message: str | None
    goals: str | None

    started_at: datetime | None

    created_at: datetime


# ============================================================
# MENTOR CAPACITY RESPONSE
# ============================================================


class MentorCapacityResponse(BaseModel):
    mentor_profile_id: uuid.UUID

    is_accepting_mentees: bool

    max_mentees: int | None

    active_mentees: int

    available_slots: int | None

    is_full: bool