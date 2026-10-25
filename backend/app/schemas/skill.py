"""
app/schemas/skill.py

Request/response shapes for the Skill Catalog endpoints.
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.skill import SkillCategory


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    category: SkillCategory
    description: str | None = None
    parent_skill_id: uuid.UUID | None = None


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: SkillCategory
    description: str | None
    parent_skill_id: uuid.UUID | None


class SkillRelateRequest(BaseModel):
    related_skill_id: uuid.UUID
