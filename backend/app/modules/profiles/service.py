from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import UserRole

from .repositories import ProfileRepository


class ProfileService:
    def get_profile(
        self,
        db: Session,
        user,
    ):
        repository = ProfileRepository(db)

        if user.role == UserRole.STUDENT:
            profile = repository.get_student_profile(
                user.id
            )

        elif user.role == UserRole.RECRUITER:
            profile = repository.get_recruiter_profile(
                user.id
            )

        elif user.role == UserRole.ACADEMICIAN:
            profile = repository.get_academician_profile(
                user.id
            )

        elif user.role == UserRole.PROFESSIONAL:
            profile = repository.get_professional_profile(
                user.id
            )

        elif user.role == UserRole.INSTITUTION_ADMIN:
            profile = repository.get_institution_profile(
                user.id
            )

        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported user role",
            )

        if profile is None:
            raise HTTPException(
                status_code=404,
                detail="Profile not found",
            )

        return profile

    def update_profile(
        self,
        db: Session,
        user,
        update_data: dict,
    ):
        repository = ProfileRepository(db)

        profile = self.get_profile(
            db=db,
            user=user,
        )

        allowed_fields = self._get_allowed_fields(
            user.role
        )

        safe_data = {
            key: value
            for key, value in update_data.items()
            if key in allowed_fields
        }

        if not safe_data:
            return profile

        return repository.update_profile(
            profile=profile,
            update_data=safe_data,
        )

    def _get_allowed_fields(
        self,
        role: UserRole,
    ) -> set[str]:
        if role == UserRole.STUDENT:
            return {
                "full_name",
                "institution_name",
                "course",
                "department",
                "graduation_year",
                "bio",
                "career_goal",
                "location",
            }

        if role == UserRole.RECRUITER:
            return {
                "full_name",
                "company_name",
                "designation",
                "industry",
                "company_website",
            }

        if role == UserRole.ACADEMICIAN:
            return {
                "full_name",
                "institution_name",
                "department",
                "designation",
                "research_interests",
            }

        if role == UserRole.PROFESSIONAL:
            return {
                "full_name",
                "headline",
                "bio",
                "designation",
                "company_name",
                "organization_id",
                "industry",
                "years_of_experience",
                "location",
                "professional_interests",
                "goals",
                "linkedin_url",
                "portfolio_url",
                "github_url",
            }

        if role == UserRole.INSTITUTION_ADMIN:
            return {
                "institution_name",
                "admin_name",
                "accreditation",
                "website",
                "established_date",
            }

        return set()


profile_service = ProfileService()