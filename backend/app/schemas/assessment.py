import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.assessment import (
    AssessmentType,
    AttemptStatus,
    DifficultyLevel,
    QuestionType,
)


class QuestionOptionCreate(BaseModel):
    option_text: str
    is_correct: bool = False


class QuestionOptionResponse(BaseModel):
    id: uuid.UUID
    option_text: str
    is_correct: bool

    model_config = ConfigDict(from_attributes=True)


class AssessmentQuestionCreate(BaseModel):
    skill_id: uuid.UUID | None = None
    question_text: str
    question_type: QuestionType
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    points: int = 1
    options: list[QuestionOptionCreate] = []


class AssessmentQuestionResponse(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    skill_id: uuid.UUID | None
    question_text: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    points: int
    options: list[QuestionOptionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class AssessmentCreate(BaseModel):
    title: str
    description: str | None = None
    assessment_type: AssessmentType
    career_id: uuid.UUID | None = None
    duration_minutes: int | None = None
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM


class AssessmentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assessment_type: AssessmentType | None = None
    career_id: uuid.UUID | None = None
    duration_minutes: int | None = None
    difficulty: DifficultyLevel | None = None
    is_active: bool | None = None


class AssessmentResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    assessment_type: AssessmentType
    career_id: uuid.UUID | None
    duration_minutes: int | None
    difficulty: DifficultyLevel
    is_active: bool
    created_at: datetime
    updated_at: datetime
    questions: list[AssessmentQuestionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class AssessmentAttemptResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    assessment_id: uuid.UUID
    status: AttemptStatus
    total_score: float | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssessmentSkillResultCreate(BaseModel):
    skill_id: uuid.UUID
    score: float


class AssessmentSubmitRequest(BaseModel):
    total_score: float
    skill_results: list[AssessmentSkillResultCreate]


class AssessmentSkillResultResponse(BaseModel):
    id: uuid.UUID
    skill_id: uuid.UUID
    score: float

    model_config = ConfigDict(from_attributes=True)