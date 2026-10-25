from fastapi import HTTPException

from app.models.user import User, UserRole
from app.modules.professionals.repositories import ProfessionalRepository
from app.modules.professionals.schemas import (
    ProfessionalProfileCreate,
    ProfessionalProfileUpdate,
)


class ProfessionalService:
    def __init__(self, repository: ProfessionalRepository):
        self.repository = repository

    def _check_role(self, current_user: User) -> None:
        if current_user.role != UserRole.PROFESSIONAL:
            raise HTTPException(
                status_code=403,
                detail="Only professional users can use professional profiles",
            )

    def create_profile(
        self,
        current_user: User,
        payload: ProfessionalProfileCreate,
    ):
        self._check_role(current_user)

        existing = self.repository.get_by_user_id(current_user.id)

        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="Professional profile already exists",
            )

        if payload.organization_id is not None:
            organization = self.repository.get_organization(
                payload.organization_id
            )

            if organization is None:
                raise HTTPException(
                    status_code=404,
                    detail="Organization not found",
                )

        return self.repository.create(
            user_id=current_user.id,
            **payload.model_dump(),
        )

    def get_my_profile(self, current_user: User):
        self._check_role(current_user)

        profile = self.repository.get_by_user_id(current_user.id)

        if profile is None:
            raise HTTPException(
                status_code=404,
                detail="Professional profile not found",
            )

        return profile

    def get_public_profile(self, profile_id):
        profile = self.repository.get_by_id(profile_id)

        if profile is None:
            raise HTTPException(
                status_code=404,
                detail="Professional profile not found",
            )

        return profile

    def update_profile(
        self,
        current_user: User,
        payload: ProfessionalProfileUpdate,
    ):
        profile = self.get_my_profile(current_user)

        update_data = payload.model_dump(exclude_unset=True)

        if "organization_id" in update_data:
            organization_id = update_data["organization_id"]

            if organization_id is not None:
                organization = self.repository.get_organization(
                    organization_id
                )

                if organization is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Organization not found",
                    )

        return self.repository.update(
            profile,
            update_data,
        )