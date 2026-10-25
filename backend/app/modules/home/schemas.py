from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class HomeUser(BaseModel):
    id: str
    name: str
    role: str
    profile_image: Optional[str] = None


class HomeDailyAssessment(BaseModel):
    available: bool
    generated: bool
    completed: bool
    question_count: int
    answered_count: int
    attempt_id: Optional[str] = None
    score: Optional[float] = None


class HomeResponse(BaseModel):
    user: HomeUser

    daily_assessment: HomeDailyAssessment

    recommendations: List[Dict[str, Any]] = []

    feed: List[Dict[str, Any]] = []

    news: List[Dict[str, Any]] = []

    notifications: List[Dict[str, Any]] = []