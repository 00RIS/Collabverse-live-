import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.modules.professionals.models import ProfessionalProfile


class ProfessionalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(
        self,
        user_id: uuid.UUID,
    ) -> ProfessionalProfile | None:
        return self.db.scalar(
            select(ProfessionalProfile).where(
                ProfessionalProfile.user_id == user_id
            )
        )

    def get_by_id(
        self,
        profile_id: uuid.UUID,
    ) -> ProfessionalProfile | None:
        return self.db.get(ProfessionalProfile, profile_id)

    def get_organization(
        self,
        organization_id: uuid.UUID,
    ) -> Organization | None:
        return self.db.get(Organization, organization_id)

    def create(
        self,
        user_id: uuid.UUID,
        **data,
    ) -> ProfessionalProfile:
        profile = ProfessionalProfile(
            user_id=user_id,
            **data,
        )

        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)

        return profile

    def update(
        self,
        profile: ProfessionalProfile,
        data: dict,
    ) -> ProfessionalProfile:
        for field, value in data.items():
            setattr(profile, field, value)

        self.db.commit()
        self.db.refresh(profile)

        return profile