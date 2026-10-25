import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.student_skill import ProficiencyLevel, SkillSource
from app.schemas.skill import SkillOut


class StudentSkillCreate(BaseModel):
    skill_id: uuid.UUID
    proficiency_level: ProficiencyLevel


class StudentSkillUpdate(BaseModel):
    proficiency_level: ProficiencyLevel


class StudentSkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill: SkillOut
    proficiency_level: ProficiencyLevel
    source: SkillSource
    updated_at: datetime