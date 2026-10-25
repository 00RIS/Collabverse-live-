"""
app/api/v1/endpoints/careers.py

WHAT THIS FILE IS:
CareerRole CRUD, adding skill requirements to a career, and the
Career Readiness endpoint — the API surface for spec Section 5.

HOW THE READINESS ENDPOINT WORKS:
This endpoint is deliberately a THIN wrapper: it does exactly two things
—fetch data from Postgres, then hand it to the pure `calculate_readiness`
function in app/services/readiness.py — and returns whatever comes back.
No scoring logic lives here. That separation is what makes the scoring
logic unit-testable without a database (see the long comment in
services/readiness.py).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.career import CareerRole, CareerSkillRequirement
from app.models.skill import Skill
from app.models.student_skill import StudentSkill
from app.models.user import User, UserRole
from app.schemas.career import (
    CareerRoleCreate,
    CareerRoleOut,
    CareerSkillRequirementCreate,
    CareerSkillRequirementOut,
    ReadinessResponse,
    SkillGap,
)
from app.services.readiness import RequirementInput, calculate_readiness

router = APIRouter(prefix="/careers", tags=["careers"])


@router.get("", response_model=list[CareerRoleOut])
def list_careers(db: Session = Depends(get_db)) -> list[CareerRole]:
    return list(db.scalars(select(CareerRole).order_by(CareerRole.title)))


@router.post("", response_model=CareerRoleOut, status_code=status.HTTP_201_CREATED)
def create_career(
    payload: CareerRoleCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.ACADEMICIAN, UserRole.INSTITUTION_ADMIN)),
) -> CareerRole:
    existing = db.scalar(select(CareerRole).where(CareerRole.title == payload.title))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Career role already exists")

    career = CareerRole(title=payload.title, description=payload.description)
    db.add(career)
    db.commit()
    db.refresh(career)
    return career


@router.post(
    "/{career_id}/requirements",
    response_model=CareerSkillRequirementOut,
    status_code=status.HTTP_201_CREATED,
)
def add_skill_requirement(
    career_id: uuid.UUID,
    payload: CareerSkillRequirementCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.ACADEMICIAN, UserRole.INSTITUTION_ADMIN)),
) -> CareerSkillRequirement:
    career = db.get(CareerRole, career_id)
    if career is None:
        raise HTTPException(status_code=404, detail="Career role not found")

    skill = db.get(Skill, payload.skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found in catalog")

    if not (1 <= payload.required_proficiency <= 4):
        raise HTTPException(status_code=400, detail="required_proficiency must be between 1 and 4")

    existing = db.scalar(
        select(CareerSkillRequirement).where(
            CareerSkillRequirement.career_role_id == career_id,
            CareerSkillRequirement.skill_id == payload.skill_id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This skill is already a requirement for this career"
        )

    requirement = CareerSkillRequirement(
        career_role_id=career_id,
        skill_id=payload.skill_id,
        required_proficiency=payload.required_proficiency,
        importance_weight=payload.importance_weight,
    )
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


@router.get("/{career_id}/readiness", response_model=ReadinessResponse)
def get_my_readiness(
    career_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
) -> ReadinessResponse:
    career = db.get(CareerRole, career_id)
    if career is None:
        raise HTTPException(status_code=404, detail="Career role not found")

    if current_user.student_profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found")
    profile_id = current_user.student_profile.id

    # --- Step 1: fetch requirements for this career, with skill names ---
    requirement_rows = list(
        db.scalars(
            select(CareerSkillRequirement).where(CareerSkillRequirement.career_role_id == career_id)
        )
    )
    requirement_inputs = [
        RequirementInput(
            skill_id=str(r.skill_id),
            skill_name=r.skill.name,
            required_proficiency=r.required_proficiency,
            importance_weight=r.importance_weight,
        )
        for r in requirement_rows
    ]

    # --- Step 2: fetch this student's proficiencies as a plain dict ---
    student_skill_rows = list(
        db.scalars(select(StudentSkill).where(StudentSkill.student_profile_id == profile_id))
    )
    proficiencies = {str(s.skill_id): int(s.proficiency_level) for s in student_skill_rows}

    # --- Step 3: hand off to the pure, testable scoring function ---
    result = calculate_readiness(requirement_inputs, proficiencies)

    # --- Step 4: map the plain-dataclass result onto the API schema ---
    skill_by_id = {str(r.skill_id): r.skill for r in requirement_rows}

    def to_gap_schema(g) -> SkillGap:
        return SkillGap(
            skill=skill_by_id[g.skill_id],
            required_proficiency=g.required_proficiency,
            student_proficiency=g.student_proficiency,
            importance_weight=g.importance_weight,
            status=g.status,
        )

    return ReadinessResponse(
        career_role_id=career.id,
        career_title=career.title,
        readiness_score=result.readiness_score,
        strong=[to_gap_schema(g) for g in result.strong],
        partial=[to_gap_schema(g) for g in result.partial],
        missing=[to_gap_schema(g) for g in result.missing],
        priority_gaps=[to_gap_schema(g) for g in result.priority_gaps],
        recommended_actions=result.recommended_actions,
    )
