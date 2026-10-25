import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.application import ApplicationStatus


class ApplicationCreate(BaseModel):
    internship_id: uuid.UUID
    resume_url: str | None = None
    cover_letter: str | None = None


class ApplicationUpdateStatus(BaseModel):
    status: ApplicationStatus
    note: str | None = None
    recruiter_notes: str | None = None


class ApplicationStatusHistoryResponse(BaseModel):
    id: uuid.UUID
    status: ApplicationStatus
    note: str | None
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    internship_id: uuid.UUID
    status: ApplicationStatus
    match_score: float | None
    resume_url: str | None
    cover_letter: str | None
    recruiter_notes: str | None
    applied_at: datetime
    updated_at: datetime
    status_history: list[ApplicationStatusHistoryResponse] = []

    model_config = ConfigDict(from_attributes=True)