"""
app/api/v1/endpoints/users.py

The "who am I" endpoint. This is intentionally the first *protected*
endpoint we build — it exists mainly to prove the whole auth chain works
end to end: client sends a bearer token -> get_current_user validates it
-> the matching User row comes back.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import UserRole
from app.models.user import User
from app.models.project import Project, ProjectVisibility
from app.models.project import ProjectMember
from app.modules.profiles.repositories import ProfileRepository
from app.modules.profiles.schemas import (
    AcademicianProfileResponse,
    InstitutionProfileResponse,
    ProfessionalProfileResponse,
    RecruiterProfileResponse,
    StudentProfileResponse,
)
from app.modules.preferences.repositories import PreferenceRepository
from app.modules.mentorship.repositories import MentorRepository
from app.modules.mentorship.schemas import MentorProfileResponse
from app.schemas.user import PublicUserOut, PublicUserProfileOut, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/directory", response_model=list[PublicUserOut])
def list_directory(
    limit: int = Query(default=40, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List minimal public profile cards; never exposes emails or account data."""
    users = db.scalars(
        select(User)
        .where(User.is_active.is_(True), User.id != current_user.id)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    profiles = ProfileRepository(db)
    results = []

    for user in users:
        role = user.role
        if role == UserRole.STUDENT:
            profile = profiles.get_student_profile(user.id)
            name = getattr(profile, "full_name", None)
            headline = " · ".join(filter(None, [getattr(profile, "course", None), getattr(profile, "institution_name", None)])) if profile else None
        elif role == UserRole.RECRUITER:
            profile = profiles.get_recruiter_profile(user.id)
            name = getattr(profile, "full_name", None)
            headline = " · ".join(filter(None, [getattr(profile, "designation", None), getattr(profile, "company_name", None)])) if profile else None
        elif role == UserRole.ACADEMICIAN:
            profile = profiles.get_academician_profile(user.id)
            name = getattr(profile, "full_name", None)
            headline = " · ".join(filter(None, [getattr(profile, "designation", None), getattr(profile, "institution_name", None)])) if profile else None
        elif role == UserRole.PROFESSIONAL:
            profile = profiles.get_professional_profile(user.id)
            name = getattr(profile, "full_name", None)
            headline = getattr(profile, "headline", None) or getattr(profile, "company_name", None) if profile else None
        else:
            profile = profiles.get_institution_profile(user.id)
            name = getattr(profile, "admin_name", None)
            headline = getattr(profile, "institution_name", None) if profile else None

        if name:
            results.append({"id": user.id, "role": role, "full_name": name, "headline": headline, "avatar_url": user.avatar_url})

    return results


@router.get("/{user_id}/profile", response_model=PublicUserProfileOut)
def read_public_profile(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return profile details that are safe to show to other signed-in members."""
    target = db.get(User, user_id)
    if target is None or not target.is_active:
        raise HTTPException(status_code=404, detail="Member not found")

    profiles = ProfileRepository(db)
    profile_schema_by_role = {
        UserRole.STUDENT: (profiles.get_student_profile, StudentProfileResponse),
        UserRole.RECRUITER: (profiles.get_recruiter_profile, RecruiterProfileResponse),
        UserRole.ACADEMICIAN: (profiles.get_academician_profile, AcademicianProfileResponse),
        UserRole.PROFESSIONAL: (profiles.get_professional_profile, ProfessionalProfileResponse),
        UserRole.INSTITUTION_ADMIN: (profiles.get_institution_profile, InstitutionProfileResponse),
    }
    getter, response_schema = profile_schema_by_role[target.role]
    profile_model = getter(target.id)
    if profile_model is None:
        raise HTTPException(status_code=404, detail="Member profile not found")

    profile_data = response_schema.model_validate(profile_model).model_dump(
        mode="json",
        exclude={"id", "user_id", "created_at", "updated_at"},
    )
    full_name = (
        profile_data.get("full_name")
        or profile_data.get("admin_name")
        or profile_data.get("institution_name")
        or "CollabVerse member"
    )
    headline = (
        profile_data.get("headline")
        or " · ".join(filter(None, [
            profile_data.get("designation"),
            profile_data.get("company_name") or profile_data.get("institution_name"),
        ]))
        or " · ".join(filter(None, [
            profile_data.get("course"), profile_data.get("institution_name"),
        ]))
        or profile_data.get("industry")
    )

    interests = [
        item.name
        for item in PreferenceRepository(db).list_interests(target.id)
    ]
    goals = [item.title for item in PreferenceRepository(db).list_goals(target.id)]

    mentor_model = MentorRepository(db).get_by_user_id(target.id)
    mentor_profile = None
    if mentor_model is not None:
        mentor_profile = MentorProfileResponse.model_validate(mentor_model).model_dump(
            mode="json",
            exclude={"id", "user_id", "organization_id", "institution_id", "linkedin_url", "portfolio_url", "created_at", "updated_at", "skills"},
        )

    project_rows = db.scalars(
        select(Project)
        .where(
            Project.visibility == ProjectVisibility.PUBLIC,
            or_(
                Project.creator_id == target.id,
                Project.id.in_(
                    select(ProjectMember.project_id).where(
                        ProjectMember.user_id == target.id
                    )
                ),
            ),
        )
        .order_by(Project.updated_at.desc())
        .limit(6)
    ).all()
    public_projects = [
        {
            "id": str(project.id),
            "title": project.title,
            "description": project.description,
            "domain": project.domain,
            "project_type": project.project_type.value,
            "status": project.status.value,
            "role": "owner" if project.creator_id == target.id else "member",
            "updated_at": project.updated_at.isoformat(),
        }
        for project in project_rows
    ]

    return PublicUserProfileOut(
        user_id=target.id,
        role=target.role,
        full_name=full_name,
        headline=headline,
        avatar_url=target.avatar_url,
        profile=profile_data,
        interests=interests,
        goals=goals,
        mentor_profile=mentor_profile,
        projects=public_projects,
    )
