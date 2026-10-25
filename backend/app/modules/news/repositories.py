import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.news.models import (
    NewsArticle,
)
from app.modules.preferences.models import (
    UserInterest,
    UserPreference,
)


class NewsRepository:
    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def get_preferences(
        self,
        user_id: uuid.UUID,
    ) -> UserPreference | None:

        return self.db.scalar(
            select(UserPreference).where(
                UserPreference.user_id
                == user_id
            )
        )

    def get_interests(
        self,
        user_id: uuid.UUID,
    ) -> list[UserInterest]:

        return list(
            self.db.scalars(
                select(UserInterest).where(
                    UserInterest.user_id
                    == user_id
                )
            ).all()
        )

    def get_by_url(
        self,
        article_url: str,
    ) -> NewsArticle | None:

        return self.db.scalar(
            select(NewsArticle).where(
                NewsArticle.article_url
                == article_url
            )
        )

    def save_articles(
        self,
        articles: list[dict],
    ) -> int:

        created = 0

        for article_data in articles:

            existing = self.get_by_url(
                article_data[
                    "article_url"
                ]
            )

            if existing:
                if not existing.image_url and article_data.get("image_url"):
                    existing.image_url = article_data["image_url"]
                if existing.summary and "<" in existing.summary and article_data.get("summary"):
                    existing.summary = article_data["summary"]
                continue

            article = NewsArticle(
                **article_data
            )

            self.db.add(article)
            created += 1

        self.db.commit()

        return created

    def list_recent(
        self,
        categories: list[str] | None = None,
        limit: int = 50,
    ) -> list[NewsArticle]:

        query = select(
            NewsArticle
        )

        if categories:
            query = query.where(
                NewsArticle.category.in_(
                    categories
                )
            )

        query = (
            query
            .order_by(
                NewsArticle
                .published_at
                .desc()
            )
            .limit(limit)
        )

        return list(
            self.db.scalars(
                query
            ).all()
        )
