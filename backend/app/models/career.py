"""
app/models/career.py

WHAT THIS FILE IS:
`CareerRole` (e.g. "Data Analyst", "ML Engineer") and
`CareerSkillRequirement`, the association object that says "this career
needs this skill, at this proficiency, with this importance".

WHY CareerSkillRequirement NEEDS TO BE ITS OWN TABLE (not a plain
many-to-many): same reasoning as StudentSkill. "Required proficiency"
and "importance weight" are properties of the *pairing* (this career
needs this skill at level 3), not of the career or the skill alone. A
bare link table can't hold that data — an association object can.

`importance_weight` is a float (we use 0.0–1.0, or any positive number —
only relative size matters since the readiness formula normalizes by the
total weight) representing how much this particular skill matters to
this particular career, e.g. SQL might be weight 1.0 for a Data Analyst
role but weight 0.3 for a Software Developer role.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class CareerRole(Base):
    __tablename__ = "career_roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # One-to-many: one CareerRole has many skill requirements.
    skill_requirements = relationship(
        "CareerSkillRequirement", back_populates="career_role", cascade="all, delete-orphan"
    )


class CareerSkillRequirement(Base):
    __tablename__ = "career_skill_requirements"
    __table_args__ = (UniqueConstraint("career_role_id", "skill_id", name="uq_career_skill"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    career_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("career_roles.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )

    # 1-4, matching ProficiencyLevel's integer scale (see student_skill.py)
    required_proficiency: Mapped[int] = mapped_column(Integer, nullable=False)
    importance_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    career_role = relationship("CareerRole", back_populates="skill_requirements")
    skill = relationship("Skill")
