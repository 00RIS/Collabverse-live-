"""
app/models/student_skill.py

WHAT THIS FILE IS:
The link between a StudentProfile and a Skill — but unlike
`skill_relations` in skill.py, this link needs to carry its OWN data
(what proficiency level, how it was verified, when it was added). That
extra data is exactly why this is a full model class (the "association
object" pattern) rather than a bare `Table()`.

RELATIONSHIP TYPE — MANY-TO-MANY (via association object):
One student can have many skills; one skill (e.g. "Python") is held by
many students. Normally SQLAlchemy can express many-to-many as two
foreign keys in a link table with no model of its own — but the moment
you need to attach data to the *relationship itself* (proficiency level
is a property of "this student's Python skill", not of the student or
the skill alone), that link needs a primary key and columns, i.e. its
own table with a model class.

`UniqueConstraint(student_profile_id, skill_id)` guarantees a student
can't have two rows for the same skill — updating proficiency means
updating the existing row, not inserting a second one.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ProficiencyLevel(int, enum.Enum):
    """
    An integer-backed enum: BEGINNER stores as 1, EXPERT as 4. Storing
    it as an ordered integer (rather than just a string enum) is what
    lets the readiness-scoring algorithm later compare "required
    proficiency 3" against "student has 2" with ordinary math, while the
    API still shows/accepts readable names.
    """
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4


class SkillSource(str, enum.Enum):
    """
    Where a student's claimed proficiency came from. This matters for
    trust: a self-declared skill and one confirmed by a passed
    assessment should not be treated as equally reliable evidence
    everywhere the platform uses skill data (matching, readiness,
    portfolio verification).
    """
    SELF_DECLARED = "self_declared"
    ASSESSMENT_VERIFIED = "assessment_verified"
    PROJECT_VERIFIED = "project_verified"


class StudentSkill(Base):
    __tablename__ = "student_skills"
    __table_args__ = (UniqueConstraint("student_profile_id", "skill_id", name="uq_student_skill"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    student_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )

    proficiency_level: Mapped[ProficiencyLevel] = mapped_column(
        Enum(ProficiencyLevel, name="proficiency_level"), nullable=False
    )
    source: Mapped[SkillSource] = mapped_column(
        Enum(SkillSource, name="skill_source"), nullable=False, default=SkillSource.SELF_DECLARED
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    student_profile = relationship("StudentProfile", back_populates="student_skills")
    skill = relationship("Skill")
