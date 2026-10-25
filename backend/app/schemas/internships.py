import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.internship import (
    ExperienceLevel,
    InternshipStatus,
    InternshipType,
    WorkMode,
)


class InternshipSkillCreate(BaseModel):
    skill_id: uuid.UUID
    required_score: int | None = None
    importance_weight: float = 1.0
    mandatory: bool = False


class InternshipSkillResponse(BaseModel):
    id: uuid.UUID
    skill_id: uuid.UUID
    required_score: int | None
    importance_weight: float
    mandatory: bool

    model_config = ConfigDict(from_attributes=True)


class InternshipCreate(BaseModel):
    organization_id: uuid.UUID
    title: str
    description: str
    domain: str | None = None
    location: str | None = None
    work_mode: WorkMode
    internship_type: InternshipType
    experience_level: ExperienceLevel = ExperienceLevel.BEGINNER
    is_paid: bool = False
    stipend: float | None = None
    duration_weeks: int | None = None
    openings: int = 1
    deadline: datetime | None = None
    skills: list[InternshipSkillCreate] = []


class InternshipUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    domain: str | None = None
    location: str | None = None
    work_mode: WorkMode | None = None
    internship_type: InternshipType | None = None
    experience_level: ExperienceLevel | None = None
    is_paid: bool | None = None
    stipend: float | None = None
    duration_weeks: int | None = None
    openings: int | None = None
    deadline: datetime | None = None
    status: InternshipStatus | None = None


class InternshipResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    posted_by: uuid.UUID
    title: str
    description: str
    domain: str | None
    location: str | None
    work_mode: WorkMode
    internship_type: InternshipType
    experience_level: ExperienceLevel
    is_paid: bool
    stipend: float | None
    duration_weeks: int | None
    openings: int
    deadline: datetime | None
    status: InternshipStatus
    created_at: datetime
    updated_at: datetime
    skills: list[InternshipSkillResponse] = []

    model_config = ConfigDict(from_attributes=True)