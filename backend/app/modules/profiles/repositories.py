from uuid import UUID

from sqlalchemy.orm import Session

from app.models.profile import (
    StudentProfile,
    RecruiterProfile,
    AcademicianProfile,
    InstitutionProfile,
)
from app.modules.professionals.models import ProfessionalProfile


class ProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    # =====================================================
    # GET PROFILE
    # =====================================================

    def get_student_profile(
        self,
        user_id: UUID,
    ) -> StudentProfile | None:
        return (
            self.db.query(StudentProfile)
            .filter(StudentProfile.user_id == user_id)
            .first()
        )

    def get_recruiter_profile(
        self,
        user_id: UUID,
    ) -> RecruiterProfile | None:
        return (
            self.db.query(RecruiterProfile)
            .filter(RecruiterProfile.user_id == user_id)
            .first()
        )

    def get_academician_profile(
        self,
        user_id: UUID,
    ) -> AcademicianProfile | None:
        return (
            self.db.query(AcademicianProfile)
            .filter(AcademicianProfile.user_id == user_id)
            .first()
        )

    def get_professional_profile(
        self,
        user_id: UUID,
    ) -> ProfessionalProfile | None:
        return (
            self.db.query(ProfessionalProfile)
            .filter(ProfessionalProfile.user_id == user_id)
            .first()
        )

    def get_institution_profile(
        self,
        user_id: UUID,
    ) -> InstitutionProfile | None:
        return (
            self.db.query(InstitutionProfile)
            .filter(InstitutionProfile.user_id == user_id)
            .first()
        )

    # =====================================================
    # UPDATE PROFILE
    # =====================================================

    def update_profile(
        self,
        profile,
        update_data: dict,
    ):
        for field, value in update_data.items():
            setattr(profile, field, value)

        self.db.commit()
        self.db.refresh(profile)

        return profile