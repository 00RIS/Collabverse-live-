from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.modules.news.provider import (
    news_provider,
)
from app.modules.news.repositories import (
    NewsRepository,
)


DEFAULT_CATEGORIES = [
    "technology",
    "business",
    "artificial_intelligence",
    "startups",
    "economy",
]


class NewsService:
    def _repo(
        self,
        db: Session,
    ) -> NewsRepository:

        return NewsRepository(db)

    def get_user_categories(
        self,
        db: Session,
        current_user: User,
    ) -> list[str]:

        repo = self._repo(db)

        categories = []

        preferences = repo.get_preferences(
            current_user.id
        )

        if preferences:
            preferred = getattr(
                preferences,
                "news_categories",
                None,
            )

            if preferred:
                categories.extend(
                    preferred
                )

        interests = repo.get_interests(
            current_user.id
        )

        for interest in interests:

            category = getattr(
                interest,
                "category",
                None,
            )

            if category is None:
                continue

            value = getattr(
                category,
                "value",
                category,
            )

            value = str(value)

            if value not in categories:
                categories.append(
                    value
                )

        if not categories:
            categories = (
                DEFAULT_CATEGORIES.copy()
            )

        # Avoid fetching too many feeds.
        return categories[:5]

    def refresh(
        self,
        db: Session,
        current_user: User,
    ) -> dict:

        repo = self._repo(db)

        categories = (
            self.get_user_categories(
                db,
                current_user,
            )
        )

        all_articles = []

        successful_categories = []

        for category in categories:

            try:
                articles = (
                    news_provider
                    .fetch_category(
                        category,
                        limit=10,
                    )
                )

            except RuntimeError:
                # One failed category should not
                # destroy the whole feed.
                continue

            all_articles.extend(
                articles
            )

            successful_categories.append(
                category
            )

        if not successful_categories:
            raise HTTPException(
                status_code=503,
                detail=(
                    "News provider is temporarily "
                    "unavailable."
                ),
            )

        created = repo.save_articles(
            all_articles
        )

        return {
            "fetched": len(
                all_articles
            ),
            "created": created,
            "categories": (
                successful_categories
            ),
        }

    def personalized(
        self,
        db: Session,
        current_user: User,
        limit: int = 20,
    ) -> list[dict]:

        repo = self._repo(db)

        categories = (
            self.get_user_categories(
                db,
                current_user,
            )
        )

        articles = repo.list_recent(
            categories=categories,
            limit=100,
        )

        if not articles:
            self.refresh(
                db,
                current_user,
            )

            articles = repo.list_recent(
                categories=categories,
                limit=100,
            )

        now = datetime.now(
            timezone.utc
        )

        ranked = []

        for article in articles:

            score = 0.0

            if (
                article.category
                in categories
            ):
                category_position = (
                    categories.index(
                        article.category
                    )
                )

                score += max(
                    1.0,
                    5.0 - category_position,
                )

            if article.published_at:

                published_at = (
                    article.published_at
                )

                if (
                    published_at.tzinfo
                    is None
                ):
                    published_at = (
                        published_at.replace(
                            tzinfo=timezone.utc
                        )
                    )

                age_hours = (
                    now - published_at
                ).total_seconds() / 3600

                if age_hours <= 24:
                    score += 4

                elif age_hours <= 72:
                    score += 2

                elif age_hours <= 168:
                    score += 1

            ranked.append(
                {
                    "article": article,
                    "score": round(
                        score,
                        2,
                    ),
                }
            )

        ranked.sort(
            key=lambda item: (
                item["score"],
                item["article"]
                .published_at
                or datetime.min.replace(
                    tzinfo=timezone.utc
                ),
            ),
            reverse=True,
        )

        results = []

        for item in ranked[:limit]:

            article = item[
                "article"
            ]

            results.append(
                {
                    "id": article.id,
                    "title": article.title,
                    "summary": article.summary,
                    "category": (
                        article.category
                    ),
                    "source_name": (
                        article.source_name
                    ),
                    "article_url": (
                        article.article_url
                    ),
                    "published_at": (
                        article.published_at
                    ),
                    "relevance_score": (
                        item["score"]
                    ),
                }
            )

        return results


news_service = NewsService()