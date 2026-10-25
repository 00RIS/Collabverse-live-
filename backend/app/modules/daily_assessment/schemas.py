import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class OptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    option_text: str


class QuestionResponse(BaseModel):
    id: uuid.UUID
    skill_id: uuid.UUID | None
    skill_name: str | None = None
    question_text: str
    difficulty: str
    points: int
    options: list[OptionResponse]


class DailyAssessmentResponse(BaseModel):
    id: uuid.UUID
    attempt_id: uuid.UUID
    assessment_date: date
    question_count: int
    completed: bool
    answered_count: int
    questions: list[QuestionResponse]


class AnswerCreate(BaseModel):
    question_id: uuid.UUID
    selected_option_id: uuid.UUID


class AnswerResponse(BaseModel):
    question_id: uuid.UUID
    answered: bool


class SkillResultResponse(BaseModel):
    skill_id: uuid.UUID
    skill_name: str | None = None
    correct: int
    total: int
    score: float


class AssessmentResultResponse(BaseModel):
    attempt_id: uuid.UUID
    score: float
    correct_answers: int
    total_questions: int
    completed_at: datetime
    skill_results: list[SkillResultResponse]


class HistoryItemResponse(BaseModel):
    daily_assessment_id: uuid.UUID
    attempt_id: uuid.UUID
    assessment_date: date
    completed: bool
    score: float | None
    question_count: int


class ProgressResponse(BaseModel):
    total_completed: int
    average_score: float
    latest_score: float | None
    best_score: float | None