import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NewsArticleResponse(BaseModel):
    id: uuid.UUID
    title: str
    summary: str | None
    category: str
    source_name: str | None
    article_url: str
    image_url: str | None = None
    published_at: datetime | None
    relevance_score: float = 0.0

    model_config = ConfigDict(
        from_attributes=True
    )


class NewsRefreshResponse(BaseModel):
    fetched: int
    created: int
    categories: list[str]
