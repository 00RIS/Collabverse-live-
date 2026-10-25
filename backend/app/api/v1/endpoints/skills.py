"""
app/api/v1/endpoints/skills.py

WHAT THIS FILE IS:
The Skill Catalog's own CRUD endpoints, separate from any one student's
skills (that's endpoints/student_skills.py). Anyone logged in can browse
the catalog (GET) — you need it to search for skills to add to your
profile or a project. Only academicians and institution admins can add
new skills to the shared catalog (POST), since a catalog only stays
useful if it's curated rather than let anyone create a duplicate
"Python" and a "python" side by side.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.skill import Skill
from app.models.user import User, UserRole
from app.schemas.skill import SkillCreate, SkillOut, SkillRelateRequest

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillOut])
def list_skills(
    search: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[Skill]:
    """
    Search/browse the catalog. `search` does a simple case-insensitive
    substring match on the skill name — good enough for an autocomplete
    box; a full-text or fuzzy search can replace this later without
    changing the response shape.
    """
    query = select(Skill)
    if search:
        query = query.where(Skill.name.ilike(f"%{search}%"))
    if category:
        query = query.where(Skill.category == category)
    return list(db.scalars(query.order_by(Skill.name)))


@router.post("", response_model=SkillOut, status_code=status.HTTP_201_CREATED)
def create_skill(
    payload: SkillCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.ACADEMICIAN, UserRole.INSTITUTION_ADMIN)),
) -> Skill:
    existing = db.scalar(select(Skill).where(Skill.name == payload.name))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Skill already exists")

    if payload.parent_skill_id is not None:
        parent = db.get(Skill, payload.parent_skill_id)
        if parent is None:
            raise HTTPException(status_code=400, detail="parent_skill_id does not exist")

    skill = Skill(
        name=payload.name,
        category=payload.category,
        description=payload.description,
        parent_skill_id=payload.parent_skill_id,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.post("/{skill_id}/related", status_code=status.HTTP_204_NO_CONTENT)
def add_related_skill(
    skill_id: uuid.UUID,
    payload: SkillRelateRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.ACADEMICIAN, UserRole.INSTITUTION_ADMIN)),
) -> None:
    """
    Link two skills as "related" (symmetric — e.g. React <-> Vue). We add
    the link in both directions so a lookup from either skill finds the
    other, since the relationship has no inherent direction.
    """
    skill = db.get(Skill, skill_id)
    related = db.get(Skill, payload.related_skill_id)
    if skill is None or related is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    if related not in skill.related_skills:
        skill.related_skills.append(related)
    if skill not in related.related_skills:
        related.related_skills.append(skill)

    db.commit()
