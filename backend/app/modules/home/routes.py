from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
)
from app.models.user import User
from app.modules.home.schemas import HomeResponse
from app.modules.home.service import home_service


router = APIRouter(
    prefix="/home",
    tags=["Home"],
)


@router.get(
    "",
    response_model=HomeResponse,
)
def get_home(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    return home_service.get_home(
        db=db,
        current_user=current_user,
    )