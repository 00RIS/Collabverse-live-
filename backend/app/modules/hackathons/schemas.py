import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    model_validator,
)

from app.modules.hackathons.models import (
    HackathonDifficulty,
    HackathonMode,
    HackathonParticipantStatus,
    HackathonSourceType,
    HackathonStatus,
)


# =========================================================
# HACKATHON SKILLS
# =========================================================


class HackathonSkillCreate(BaseModel):
    skill_id: uuid.UUID

    required_level: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    priority: int = Field(
        default=1,
        ge=1,
        le=5,
    )

    mandatory: bool = False


class HackathonSkillResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: uuid.UUID
    skill_id: uuid.UUID

    required_level: int | None = None
    priority: int
    mandatory: bool


# =========================================================
# HACKATHON CREATE
# =========================================================


class HackathonCreate(BaseModel):
    title: str = Field(
        min_length=3,
        max_length=255,
    )

    description: str = Field(
        min_length=10,
    )

    domain: str | None = Field(
        default=None,
        max_length=255,
    )

    organizer_name: str | None = Field(
        default=None,
        max_length=255,
    )

    mode: HackathonMode = (
        HackathonMode.ONLINE
    )

    difficulty: HackathonDifficulty = (
        HackathonDifficulty.OPEN
    )

    status: HackathonStatus = (
        HackathonStatus.DRAFT
    )

    location: str | None = Field(
        default=None,
        max_length=255,
    )

    min_team_size: int = Field(
        default=1,
        ge=1,
        le=100,
    )

    max_team_size: int = Field(
        default=4,
        ge=1,
        le=100,
    )

    registration_deadline: (
        datetime | None
    ) = None

    start_date: datetime | None = None

    end_date: datetime | None = None

    prize_details: str | None = None

    registration_url: HttpUrl | None = None

    banner_url: HttpUrl | None = None

    is_featured: bool = False

    skills: list[
        HackathonSkillCreate
    ] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_hackathon(
        self,
    ):
        if (
            self.min_team_size
            > self.max_team_size
        ):
            raise ValueError(
                "min_team_size cannot be "
                "greater than max_team_size"
            )

        if (
            self.start_date
            and self.end_date
            and self.start_date
            > self.end_date
        ):
            raise ValueError(
                "start_date cannot be "
                "after end_date"
            )

        if (
            self.registration_deadline
            and self.start_date
            and self.registration_deadline
            > self.start_date
        ):
            raise ValueError(
                "registration_deadline "
                "cannot be after start_date"
            )

        return self


# =========================================================
# HACKATHON UPDATE
# =========================================================


class HackathonUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=3,
        max_length=255,
    )

    description: str | None = Field(
        default=None,
        min_length=10,
    )

    domain: str | None = Field(
        default=None,
        max_length=255,
    )

    organizer_name: str | None = Field(
        default=None,
        max_length=255,
    )

    mode: HackathonMode | None = None

    difficulty: (
        HackathonDifficulty | None
    ) = None

    status: HackathonStatus | None = None

    location: str | None = Field(
        default=None,
        max_length=255,
    )

    min_team_size: int | None = Field(
        default=None,
        ge=1,
        le=100,
    )

    max_team_size: int | None = Field(
        default=None,
        ge=1,
        le=100,
    )

    registration_deadline: (
        datetime | None
    ) = None

    start_date: datetime | None = None

    end_date: datetime | None = None

    prize_details: str | None = None

    registration_url: HttpUrl | None = None

    banner_url: HttpUrl | None = None

    is_featured: bool | None = None

    is_active: bool | None = None


# =========================================================
# EXTERNAL HACKATHON IMPORT
# =========================================================


class ExternalHackathonCreate(
    HackathonCreate
):
    source_name: str = Field(
        min_length=1,
        max_length=255,
    )

    source_url: HttpUrl

    external_id: str | None = Field(
        default=None,
        max_length=255,
    )

    # Imported hackathons are external.
    source_type: HackathonSourceType = (
        HackathonSourceType.EXTERNAL
    )


# =========================================================
# HACKATHON RESPONSE
# =========================================================


class HackathonResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: uuid.UUID

    title: str
    description: str

    domain: str | None = None

    organizer_name: str | None = None

    created_by: uuid.UUID | None = None

    source_type: HackathonSourceType

    source_name: str | None = None

    source_url: str | None = None

    external_id: str | None = None

    last_synced_at: datetime | None = None

    mode: HackathonMode

    difficulty: HackathonDifficulty

    status: HackathonStatus

    location: str | None = None

    min_team_size: int

    max_team_size: int

    registration_deadline: (
        datetime | None
    ) = None

    start_date: datetime | None = None

    end_date: datetime | None = None

    prize_details: str | None = None

    registration_url: str | None = None

    banner_url: str | None = None

    is_verified: bool
    is_featured: bool
    is_active: bool

    created_at: datetime
    updated_at: datetime

    skills: list[
        HackathonSkillResponse
    ] = Field(
        default_factory=list
    )


# =========================================================
# HACKATHON LIST RESPONSE
# =========================================================


class HackathonListResponse(BaseModel):
    total: int

    hackathons: list[
        HackathonResponse
    ] = Field(
        default_factory=list
    )


# =========================================================
# PARTICIPANT
# =========================================================


class HackathonParticipantCreate(
    BaseModel
):
    team_name: str | None = Field(
        default=None,
        max_length=255,
    )


class HackathonParticipantResponse(
    BaseModel
):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: uuid.UUID

    hackathon_id: uuid.UUID

    user_id: uuid.UUID

    team_name: str | None = None

    status: HackathonParticipantStatus

    registered_at: datetime


# =========================================================
# HACKATHON RECOMMENDATION
# =========================================================


class HackathonRecommendationReason(
    BaseModel
):
    type: str
    text: str
    points: float


class HackathonRecommendation(
    BaseModel
):
    hackathon_id: uuid.UUID

    title: str

    domain: str | None = None

    organizer_name: str | None = None

    mode: HackathonMode

    difficulty: HackathonDifficulty

    location: str | None = None

    registration_deadline: (
        datetime | None
    ) = None

    start_date: datetime | None = None

    prize_details: str | None = None

    registration_url: str | None = None

    source_name: str | None = None

    score: float = Field(
        ge=0,
        le=100,
    )

    reasons: list[
        HackathonRecommendationReason
    ] = Field(
        default_factory=list
    )


class HackathonRecommendationResponse(
    BaseModel
):
    total: int

    recommendations: list[
        HackathonRecommendation
    ] = Field(
        default_factory=list
    )