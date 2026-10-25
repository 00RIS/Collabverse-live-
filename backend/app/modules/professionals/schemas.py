import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfessionalProfileCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    headline: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=5000)
    designation: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    organization_id: uuid.UUID | None = None
    industry: str | None = Field(default=None, max_length=255)
    years_of_experience: int | None = Field(default=None, ge=0, le=80)
    location: str | None = Field(default=None, max_length=255)
    professional_interests: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    linkedin_url: str | None = Field(default=None, max_length=500)
    portfolio_url: str | None = Field(default=None, max_length=500)
    github_url: str | None = Field(default=None, max_length=500)


class ProfessionalProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    headline: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=5000)
    designation: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    organization_id: uuid.UUID | None = None
    industry: str | None = Field(default=None, max_length=255)
    years_of_experience: int | None = Field(default=None, ge=0, le=80)
    location: str | None = Field(default=None, max_length=255)
    professional_interests: list[str] | None = None
    goals: list[str] | None = None
    linkedin_url: str | None = Field(default=None, max_length=500)
    portfolio_url: str | None = Field(default=None, max_length=500)
    github_url: str | None = Field(default=None, max_length=500)


class ProfessionalProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    headline: str | None
    bio: str | None
    designation: str | None
    company_name: str | None
    organization_id: uuid.UUID | None
    industry: str | None
    years_of_experience: int | None
    location: str | None
    professional_interests: list[str]
    goals: list[str]
    linkedin_url: str | None
    portfolio_url: str | None
    github_url: str | None
    created_at: datetime
    updated_at: datetime