import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.professionals.repositories import ProfessionalRepository
from app.modules.professionals.schemas import (
    ProfessionalProfileCreate,
    ProfessionalProfileResponse,
    ProfessionalProfileUpdate,
)
from app.modules.professionals.service import ProfessionalService


router = APIRouter(
    prefix="/professionals",
    tags=["professionals"],
)


def get_service(db: Session) -> ProfessionalService:
    return ProfessionalService(
        ProfessionalRepository(db)
    )


@router.post(
    "",
    response_model=ProfessionalProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_professional_profile(
    payload: ProfessionalProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_service(db).create_profile(
        current_user,
        payload,
    )


@router.get(
    "/me",
    response_model=ProfessionalProfileResponse,
)
def get_my_professional_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_service(db).get_my_profile(
        current_user
    )


@router.patch(
    "/me",
    response_model=ProfessionalProfileResponse,
)
def update_my_professional_profile(
    payload: ProfessionalProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_service(db).update_profile(
        current_user,
        payload,
    )


@router.get(
    "/{profile_id}",
    response_model=ProfessionalProfileResponse,
)
def get_professional_profile(
    profile_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_service(db).get_public_profile(
        profile_id
    )