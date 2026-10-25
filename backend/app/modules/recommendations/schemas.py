import uuid
from datetime import datetime

from pydantic import BaseModel


# ============================================================
# COMMON RECOMMENDATION REASON
# ============================================================


class RecommendationReason(BaseModel):
    type: str
    text: str
    points: float


# ============================================================
# PROJECT RECOMMENDATIONS
# ============================================================


class ProjectRecommendationResponse(BaseModel):
    project_id: uuid.UUID
    title: str
    domain: str | None
    score: float
    reasons: list[RecommendationReason]


class RecommendationSummaryResponse(BaseModel):
    total: int
    recommendations: list[
        ProjectRecommendationResponse
    ]


# ============================================================
# HACKATHON RECOMMENDATIONS
# ============================================================


class HackathonRecommendationResponse(BaseModel):
    hackathon_id: uuid.UUID

    title: str
    domain: str | None

    organizer_name: str | None

    mode: str | None
    difficulty: str | None
    location: str | None

    registration_deadline: datetime | None
    start_date: datetime | None
    end_date: datetime | None

    prize_details: str | None
    registration_url: str | None

    source_type: str | None
    source_name: str | None

    score: float

    reasons: list[
        RecommendationReason
    ]


class HackathonRecommendationSummaryResponse(
    BaseModel
):
    total: int

    recommendations: list[
        HackathonRecommendationResponse
    ]