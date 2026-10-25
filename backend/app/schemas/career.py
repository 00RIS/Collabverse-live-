"""
app/schemas/career.py

Request/response shapes for CareerRole, CareerSkillRequirement, and the
Career Readiness Score response. The readiness schema deliberately
mirrors the example format from the project spec:

    Data Analyst Internship
    Match: 82%
    Strong: Python, SQL, Excel
    Partial: Statistics
    Missing: Power BI

so the frontend can render "why" a score is what it is, not just the
number.
"""

import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.skill import SkillOut


class CareerRoleCreate(BaseModel):
    title: str
    description: str | None = None


class CareerRoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None


class CareerSkillRequirementCreate(BaseModel):
    skill_id: uuid.UUID
    required_proficiency: int  # 1-4, matches ProficiencyLevel's scale
    importance_weight: float = 1.0


class CareerSkillRequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill: SkillOut
    required_proficiency: int
    importance_weight: float


class SkillGap(BaseModel):
    """One line of the readiness breakdown: how a student compares to a
    single required skill."""

    skill: SkillOut
    required_proficiency: int
    student_proficiency: int  # 0 if the student doesn't have the skill at all
    importance_weight: float
    status: str  # "strong" | "partial" | "missing"


class ReadinessResponse(BaseModel):
    career_role_id: uuid.UUID
    career_title: str
    readiness_score: float  # 0-100
    strong: list[SkillGap]
    partial: list[SkillGap]
    missing: list[SkillGap]
    priority_gaps: list[SkillGap]  # partial + missing, sorted by importance
    recommended_actions: list[str]
