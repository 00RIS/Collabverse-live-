from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# =========================================================
# STUDENT
# =========================================================

class StudentProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    institution_name: str | None = Field(default=None, max_length=255)
    course: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    graduation_year: int | None = None
    bio: str | None = None
    career_goal: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)


class StudentProfileResponse(BaseModel):
    id: UUID
    user_id: UUID

    full_name: str
    institution_name: str | None
    course: str | None
    department: str | None
    graduation_year: int | None
    bio: str | None
    career_goal: str | None
    location: str | None

    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


# =========================================================
# RECRUITER
# =========================================================

class RecruiterProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    designation: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=255)
    company_website: str | None = Field(default=None, max_length=255)


class RecruiterProfileResponse(BaseModel):
    id: UUID
    user_id: UUID

    full_name: str
    company_name: str
    designation: str | None
    industry: str | None
    company_website: str | None

    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


# =========================================================
# ACADEMICIAN
# =========================================================

class AcademicianProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    institution_name: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    designation: str | None = Field(default=None, max_length=255)
    research_interests: str | None = None


class AcademicianProfileResponse(BaseModel):
    id: UUID
    user_id: UUID

    full_name: str
    institution_name: str | None
    department: str | None
    designation: str | None
    research_interests: str | None

    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


# =========================================================
# PROFESSIONAL
# =========================================================

class ProfessionalProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    headline: str | None = Field(default=None, max_length=255)
    bio: str | None = None
    designation: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)
    organization_id: UUID | None = None
    industry: str | None = Field(default=None, max_length=255)
    years_of_experience: int | None = Field(default=None, ge=0, le=80)
    location: str | None = Field(default=None, max_length=255)
    professional_interests: list[str] | None = None
    goals: list[str] | None = None
    linkedin_url: str | None = Field(default=None, max_length=500)
    portfolio_url: str | None = Field(default=None, max_length=500)
    github_url: str | None = Field(default=None, max_length=500)


class ProfessionalProfileResponse(BaseModel):
    id: UUID
    user_id: UUID

    full_name: str
    headline: str | None
    bio: str | None
    designation: str | None
    company_name: str | None
    organization_id: UUID | None
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

    model_config = {
        "from_attributes": True
    }


# =========================================================
# INSTITUTION ADMIN
# =========================================================

class InstitutionProfileUpdate(BaseModel):
    institution_name: str | None = Field(default=None, max_length=255)
    admin_name: str | None = Field(default=None, max_length=255)
    accreditation: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    established_date: date | None = None


class InstitutionProfileResponse(BaseModel):
    id: UUID
    user_id: UUID

    institution_name: str
    admin_name: str
    accreditation: str | None
    website: str | None
    established_date: date | None

    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


# =========================================================
# COMMON PROFILE WRAPPER
# =========================================================

class MyProfileResponse(BaseModel):
    user_id: UUID
    email: str
    role: str
    profile: dict[str, Any]