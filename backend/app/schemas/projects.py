import uuid
from datetime import datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

from app.models.project import (
    ProjectApplicationStatus,
    ProjectDifficulty,
    ProjectMemberRole,
    ProjectStatus,
    ProjectType,
    ProjectVisibility,
)


# =========================================================
# PROJECT SKILLS
# =========================================================

class ProjectSkillCreate(BaseModel):
    skill_id: uuid.UUID
    required_level: int | None = None
    priority: int = 1


class ProjectSkillResponse(BaseModel):
    id: uuid.UUID
    skill_id: uuid.UUID
    required_level: int | None
    priority: int

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# PROJECT CREATE
# =========================================================

class ProjectCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str = Field(
        min_length=1,
    )

    domain: str | None = Field(
        default=None,
        max_length=255,
    )

    project_type: ProjectType

    difficulty: ProjectDifficulty = (
        ProjectDifficulty.BEGINNER
    )

    visibility: ProjectVisibility = (
        ProjectVisibility.PUBLIC
    )

    max_team_size: int | None = Field(
        default=None,
        ge=1,
        le=100,
    )

    is_accepting_members: bool = True

    start_date: datetime | None = None
    end_date: datetime | None = None

    skills: list[ProjectSkillCreate] = Field(
        default_factory=list
    )


# =========================================================
# PROJECT UPDATE
# =========================================================

class ProjectUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = Field(
        default=None,
        min_length=1,
    )

    domain: str | None = Field(
        default=None,
        max_length=255,
    )

    project_type: ProjectType | None = None

    difficulty: ProjectDifficulty | None = None

    status: ProjectStatus | None = None

    visibility: ProjectVisibility | None = None

    max_team_size: int | None = Field(
        default=None,
        ge=1,
        le=100,
    )

    is_accepting_members: bool | None = None

    start_date: datetime | None = None
    end_date: datetime | None = None


# =========================================================
# PROJECT RESPONSE
# =========================================================

class ProjectResponse(BaseModel):
    id: uuid.UUID
    creator_id: uuid.UUID

    title: str
    description: str

    domain: str | None

    project_type: ProjectType
    difficulty: ProjectDifficulty
    status: ProjectStatus
    visibility: ProjectVisibility

    max_team_size: int | None
    is_accepting_members: bool

    start_date: datetime | None
    end_date: datetime | None

    created_at: datetime
    updated_at: datetime

    skills: list[ProjectSkillResponse] = Field(
        default_factory=list
    )

    model_config = ConfigDict(
        from_attributes=True
    )


class ProjectResourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    resource_type: Literal["repository", "document", "media", "link"] = "link"
    url: AnyHttpUrl
    description: str | None = Field(default=None, max_length=2000)


class ProjectResourceResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    added_by: uuid.UUID
    title: str
    resource_type: str
    url: str
    description: str | None
    file_name: str | None
    content_type: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class ProjectChatMessageResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    created_at: datetime


class ProjectMeetingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    starts_at: datetime
    ends_at: datetime
    meeting_url: AnyHttpUrl | None = None

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("Meeting end time must be after its start time.")
        return self


class ProjectMeetingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    meeting_url: AnyHttpUrl | None = None
    status: Literal["scheduled", "cancelled"] | None = None


class ProjectMeetingResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by: uuid.UUID
    title: str
    description: str | None
    starts_at: datetime
    ends_at: datetime
    meeting_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# PROJECT APPLICATIONS
# =========================================================

class ProjectApplicationCreate(BaseModel):
    message: str | None = Field(
        default=None,
        max_length=2000,
    )


class ProjectApplicationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID

    message: str | None

    status: ProjectApplicationStatus

    applied_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# PROJECT MEMBERS
# =========================================================

class ProjectMemberResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID

    role: ProjectMemberRole
    joined_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
