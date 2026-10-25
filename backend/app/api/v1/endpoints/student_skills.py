"""
app/api/v1/endpoints/student_skills.py

Lets a logged-in student manage the skills on their own profile.

The route is scoped to "me", so a student can only manage skills attached
to their own StudentProfile.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.skill import Skill
from app.models.student_skill import SkillSource, StudentSkill
from app.models.user import User, UserRole
from app.schemas.student_skill import (
    StudentSkillCreate,
    StudentSkillOut,
    StudentSkillUpdate,
)


router = APIRouter(
    prefix="/students/me/skills",
    tags=["student-skills"],
)


def _get_student_profile_or_404(current_user: User):
    if current_user.student_profile is None:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found",
        )

    return current_user.student_profile


@router.get(
    "",
    response_model=list[StudentSkillOut],
)
def list_my_skills(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
) -> list[StudentSkill]:

    profile = _get_student_profile_or_404(current_user)

    return list(
        db.scalars(
            select(StudentSkill)
            .where(
                StudentSkill.student_profile_id == profile.id
            )
            .order_by(StudentSkill.updated_at.desc())
        )
    )


@router.put(
    "",
    response_model=StudentSkillOut,
)
def add_or_update_my_skill(
    payload: StudentSkillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
) -> StudentSkill:

    profile = _get_student_profile_or_404(current_user)

    skill = db.get(
        Skill,
        payload.skill_id,
    )

    if skill is None:
        raise HTTPException(
            status_code=404,
            detail="Skill not found in catalog",
        )

    existing = db.scalar(
        select(StudentSkill).where(
            StudentSkill.student_profile_id == profile.id,
            StudentSkill.skill_id == payload.skill_id,
        )
    )

    # If skill already exists, update it instead of creating duplicate.
    if existing is not None:
        existing.proficiency_level = payload.proficiency_level

        # Manual edits reset verification.
        existing.source = SkillSource.SELF_DECLARED

        db.commit()
        db.refresh(existing)

        return existing

    student_skill = StudentSkill(
        student_profile_id=profile.id,
        skill_id=payload.skill_id,
        proficiency_level=payload.proficiency_level,
        source=SkillSource.SELF_DECLARED,
    )

    db.add(student_skill)
    db.commit()
    db.refresh(student_skill)

    return student_skill


@router.patch(
    "/{skill_id}",
    response_model=StudentSkillOut,
)
def update_my_skill(
    skill_id: uuid.UUID,
    payload: StudentSkillUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
) -> StudentSkill:

    profile = _get_student_profile_or_404(current_user)

    existing = db.scalar(
        select(StudentSkill).where(
            StudentSkill.student_profile_id == profile.id,
            StudentSkill.skill_id == skill_id,
        )
    )

    if existing is None:
        raise HTTPException(
            status_code=404,
            detail="You have not added this skill",
        )

    existing.proficiency_level = payload.proficiency_level

    # Changing proficiency manually invalidates previous verification.
    existing.source = SkillSource.SELF_DECLARED

    db.commit()
    db.refresh(existing)

    return existing


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_my_skill(
    skill_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
) -> None:

    profile = _get_student_profile_or_404(current_user)

    existing = db.scalar(
        select(StudentSkill).where(
            StudentSkill.student_profile_id == profile.id,
            StudentSkill.skill_id == skill_id,
        )
    )

    if existing is None:
        raise HTTPException(
            status_code=404,
            detail="You have not added this skill",
        )

    db.delete(existing)
    db.commit()