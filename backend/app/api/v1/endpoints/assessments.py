import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.assessment import (
    AssessmentAttemptResponse,
    AssessmentCreate,
    AssessmentQuestionCreate,
    AssessmentQuestionResponse,
    AssessmentResponse,
    AssessmentSubmitRequest,
    AssessmentUpdate,
)
from app.services.assessment import (
    add_question,
    create_assessment,
    get_assessment_by_id,
    get_attempt,
    list_assessments,
    start_attempt,
    submit_attempt,
    update_assessment,
)

router = APIRouter()


@router.post(
    "",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assessment_endpoint(
    data: AssessmentCreate,
    db: Session = Depends(get_db),
):
    return create_assessment(db, data)


@router.get(
    "",
    response_model=list[AssessmentResponse],
)
def list_assessments_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_assessments(db, skip, limit)


@router.get(
    "/{assessment_id}",
    response_model=AssessmentResponse,
)
def get_assessment_endpoint(
    assessment_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    assessment = get_assessment_by_id(db, assessment_id)

    if not assessment:
        raise HTTPException(
            status_code=404,
            detail="Assessment not found",
        )

    return assessment


@router.put(
    "/{assessment_id}",
    response_model=AssessmentResponse,
)
def update_assessment_endpoint(
    assessment_id: uuid.UUID,
    data: AssessmentUpdate,
    db: Session = Depends(get_db),
):
    assessment = get_assessment_by_id(db, assessment_id)

    if not assessment:
        raise HTTPException(
            status_code=404,
            detail="Assessment not found",
        )

    return update_assessment(db, assessment, data)


@router.post(
    "/{assessment_id}/questions",
    response_model=AssessmentQuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_question_endpoint(
    assessment_id: uuid.UUID,
    data: AssessmentQuestionCreate,
    db: Session = Depends(get_db),
):
    assessment = get_assessment_by_id(db, assessment_id)

    if not assessment:
        raise HTTPException(
            status_code=404,
            detail="Assessment not found",
        )

    return add_question(db, assessment, data)


@router.post(
    "/{assessment_id}/attempts",
    response_model=AssessmentAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_attempt_endpoint(
    assessment_id: uuid.UUID,
    student_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    assessment = get_assessment_by_id(db, assessment_id)

    if not assessment:
        raise HTTPException(
            status_code=404,
            detail="Assessment not found",
        )

    return start_attempt(db, student_id, assessment_id)


@router.post(
    "/attempts/{attempt_id}/submit",
    response_model=AssessmentAttemptResponse,
)
def submit_attempt_endpoint(
    attempt_id: uuid.UUID,
    data: AssessmentSubmitRequest,
    db: Session = Depends(get_db),
):
    attempt = get_attempt(db, attempt_id)

    if not attempt:
        raise HTTPException(
            status_code=404,
            detail="Assessment attempt not found",
        )

    if attempt.status == "completed":
        raise HTTPException(
            status_code=409,
            detail="Assessment attempt already completed",
        )

    return submit_attempt(db, attempt, data)