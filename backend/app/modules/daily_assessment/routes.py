import uuid

from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

from app.modules.daily_assessment.schemas import (
    AnswerCreate,
    AnswerResponse,
    AssessmentResultResponse,
    DailyAssessmentResponse,
    HistoryItemResponse,
    ProgressResponse,
)
from app.modules.daily_assessment.service import (
    daily_assessment_service,
)


router = APIRouter(
    prefix="/daily-assessment",
    tags=["Daily Assessment"],
)


@router.get(
    "/today",
    response_model=DailyAssessmentResponse,
)
def get_today_assessment(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return daily_assessment_service.get_today(
        db,
        current_user,
    )


@router.post(
    "/{attempt_id}/answer",
    response_model=AnswerResponse,
)
def answer_question(
    attempt_id: uuid.UUID,
    payload: AnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return daily_assessment_service.answer(
        db,
        current_user,
        attempt_id,
        payload,
    )


@router.post(
    "/{attempt_id}/submit",
    response_model=AssessmentResultResponse,
)
def submit_assessment(
    attempt_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return daily_assessment_service.submit(
        db,
        current_user,
        attempt_id,
    )


@router.get(
    "/history",
    response_model=list[HistoryItemResponse],
)
def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return daily_assessment_service.history(
        db,
        current_user,
    )


@router.get(
    "/progress",
    response_model=ProgressResponse,
)
def get_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return daily_assessment_service.progress(
        db,
        current_user,
    )