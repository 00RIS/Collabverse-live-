import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AssessmentSkillResult,
    AttemptStatus,
    QuestionOption,
)
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentQuestionCreate,
    AssessmentSubmitRequest,
    AssessmentUpdate,
)


def create_assessment(db: Session, data: AssessmentCreate) -> Assessment:
    assessment = Assessment(**data.model_dump())

    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return assessment


def get_assessment_by_id(
    db: Session,
    assessment_id: uuid.UUID,
) -> Assessment | None:
    return db.scalar(
        select(Assessment).where(Assessment.id == assessment_id)
    )


def list_assessments(
    db: Session,
    skip: int = 0,
    limit: int = 20,
) -> list[Assessment]:
    stmt = (
        select(Assessment)
        .where(Assessment.is_active.is_(True))
        .order_by(Assessment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(stmt).unique().all())


def update_assessment(
    db: Session,
    assessment: Assessment,
    data: AssessmentUpdate,
) -> Assessment:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(assessment, field, value)

    db.commit()
    db.refresh(assessment)

    return assessment


def add_question(
    db: Session,
    assessment: Assessment,
    data: AssessmentQuestionCreate,
) -> AssessmentQuestion:
    question = AssessmentQuestion(
        assessment_id=assessment.id,
        skill_id=data.skill_id,
        question_text=data.question_text,
        question_type=data.question_type,
        difficulty=data.difficulty,
        points=data.points,
    )

    db.add(question)
    db.flush()

    for option_data in data.options:
        db.add(
            QuestionOption(
                question_id=question.id,
                option_text=option_data.option_text,
                is_correct=option_data.is_correct,
            )
        )

    db.commit()
    db.refresh(question)

    return question


def start_attempt(
    db: Session,
    student_id: uuid.UUID,
    assessment_id: uuid.UUID,
) -> AssessmentAttempt:
    attempt = AssessmentAttempt(
        student_id=student_id,
        assessment_id=assessment_id,
        status=AttemptStatus.IN_PROGRESS,
        started_at=datetime.now(timezone.utc),
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return attempt


def get_attempt(
    db: Session,
    attempt_id: uuid.UUID,
) -> AssessmentAttempt | None:
    return db.scalar(
        select(AssessmentAttempt).where(
            AssessmentAttempt.id == attempt_id
        )
    )


def submit_attempt(
    db: Session,
    attempt: AssessmentAttempt,
    data: AssessmentSubmitRequest,
) -> AssessmentAttempt:
    attempt.total_score = data.total_score
    attempt.status = AttemptStatus.COMPLETED
    attempt.completed_at = datetime.now(timezone.utc)

    for result in data.skill_results:
        db.add(
            AssessmentSkillResult(
                attempt_id=attempt.id,
                skill_id=result.skill_id,
                score=result.score,
            )
        )

    db.commit()
    db.refresh(attempt)

    return attempt