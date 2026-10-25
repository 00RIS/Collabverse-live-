"""
app/models/skill.py

WHAT THIS FILE IS:
The centralized **Skill Catalog** (spec Section 3). A `Skill` is a
controlled, reusable entity — "Python", "SQL", "Public Speaking" — that
every other part of the platform points to by foreign key, instead of
each feature inventing its own free-text skill strings.

WHY THIS MATTERS (uncontrolled strings vs a catalog):
If a student's profile just stored `skills = "python, ml, react"` as
text, and a career role stored `required_skills = "Python, Machine
Learning"`, the system could never reliably match them — "python" vs
"Python" vs "ML" vs "Machine Learning" are different strings to a
database even though they mean the same thing to a person. By making
`Skill` its own table with a stable ID, every feature that needs
"skills" (student profiles, career requirements, project requirements,
assessments, collaborator matching) points at the SAME row, so matching
is a simple, reliable ID comparison rather than fuzzy string guessing.

TWO KINDS OF SKILL-TO-SKILL RELATIONSHIPS:

1. PARENT / SUB-SKILL — a hierarchy (one-to-many, self-referential).
   Example: "Machine Learning" (parent) -> "Supervised Learning",
   "Deep Learning" (children). Modeled with `parent_skill_id`, a foreign
   key from `skills` back to `skills` itself. Each skill has AT MOST one
   parent, but a parent can have MANY children — that's what makes it
   one-to-many even though both sides are the same table.

2. RELATED SKILLS — a symmetric, non-hierarchical association
   (many-to-many, self-referential). Example: "React" and "Vue" are
   related but neither is a sub-skill of the other. A many-to-many
   relationship needs its own association table (`skill_relations`)
   with two foreign keys, both pointing at `skills.id`.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class SkillCategory(str, enum.Enum):
    TECHNICAL = "technical"
    BUSINESS = "business"
    ANALYTICAL = "analytical"
    COMMUNICATION = "communication"
    LEADERSHIP = "leadership"
    DESIGN = "design"
    DOMAIN_KNOWLEDGE = "domain_knowledge"
    SOFT_SKILLS = "soft_skills"


# --- Association table for the many-to-many "related skills" relation ---
#
# WHY A PLAIN Table() INSTEAD OF A MODEL CLASS:
# This table has no data of its own beyond the two foreign keys — no
# extra columns like "how related" or "when added". When an association
# table is JUST a link with no extra attributes, SQLAlchemy lets us
# declare it as a bare Table instead of a full model class, and it
# handles insert/delete automatically through the `relationship(...,
# secondary=...)` on Skill below. (Contrast this with StudentSkill in
# student_skill.py, which DOES need extra columns like
# proficiency_level — that one has to be a full model class instead.)
skill_relations = Table(
    "skill_relations",
    Base.metadata,
    Column("skill_id", UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "related_skill_id",
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    UniqueConstraint("skill_id", "related_skill_id", name="uq_skill_relation_pair"),
)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    category: Mapped[SkillCategory] = mapped_column(Enum(SkillCategory, name="skill_category"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Self-referential one-to-many: nullable because a top-level skill
    # (e.g. "Machine Learning") has no parent.
    parent_skill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # remote_side tells SQLAlchemy which side of the self-join is the
    # "one" (the parent) — required for any self-referential
    # relationship, or it can't tell parent from child.
    parent: Mapped["Skill | None"] = relationship(
        "Skill", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["Skill"]] = relationship("Skill", back_populates="parent")

    # Many-to-many "related skills". primaryjoin/secondaryjoin are
    # spelled out because both foreign keys in skill_relations point at
    # the same table (skills), so SQLAlchemy can't infer direction on
    # its own the way it can for a normal two-table many-to-many.
    related_skills: Mapped[list["Skill"]] = relationship(
        "Skill",
        secondary=skill_relations,
        primaryjoin=id == skill_relations.c.skill_id,
        secondaryjoin=id == skill_relations.c.related_skill_id,
    )
