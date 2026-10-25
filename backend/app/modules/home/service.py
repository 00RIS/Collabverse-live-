from sqlalchemy.orm import Session

from app.models.user import User

from app.modules.daily_assessment.service import (
    daily_assessment_service,
)
from app.modules.recommendations.service import (
    recommendation_service,
)
from app.modules.news.service import (
    news_service,
)
from app.modules.notifications.repositories import (
    NotificationRepository,
)
from app.modules.notifications.service import (
    NotificationService,
)
from app.modules.posts.repositories import (
    PostRepository,
)
from app.modules.posts.service import (
    PostService,
)


class HomeService:

    # =========================================================
    # USER
    # =========================================================

    def _get_user_data(
        self,
        current_user: User,
    ) -> dict:

        name = (
            getattr(
                current_user,
                "full_name",
                None,
            )
            or getattr(
                current_user,
                "name",
                None,
            )
            or getattr(
                current_user,
                "username",
                None,
            )
            or getattr(
                current_user,
                "email",
                None,
            )
            or "User"
        )

        role = getattr(
            current_user,
            "role",
            "student",
        )

        role = getattr(
            role,
            "value",
            role,
        )

        profile_image = (
            getattr(
                current_user,
                "profile_image",
                None,
            )
            or getattr(
                current_user,
                "profile_image_url",
                None,
            )
        )

        return {
            "id": str(current_user.id),
            "name": str(name),
            "role": str(role),
            "profile_image": profile_image,
        }

    # =========================================================
    # HOME
    # =========================================================

    def get_home(
        self,
        db: Session,
        current_user: User,
    ) -> dict:

        # -----------------------------------------------------
        # USER
        # -----------------------------------------------------

        user_data = self._get_user_data(
            current_user
        )

        # -----------------------------------------------------
        # DAILY ASSESSMENT
        # -----------------------------------------------------

        daily_assessment = (
            daily_assessment_service
            .get_today_status(
                db=db,
                current_user=current_user,
            )
        )

        if (
            daily_assessment.get(
                "attempt_id"
            )
            is not None
        ):
            daily_assessment[
                "attempt_id"
            ] = str(
                daily_assessment[
                    "attempt_id"
                ]
            )

        # -----------------------------------------------------
        # RECOMMENDATIONS
        # -----------------------------------------------------

        recommendation_result = (
            recommendation_service
            .recommend_projects(
                db=db,
                current_user=current_user,
                limit=5,
            )
        )

        recommendations = (
            recommendation_result.get(
                "recommendations",
                [],
            )
        )

        for recommendation in recommendations:

            project_id = (
                recommendation.get(
                    "project_id"
                )
            )

            if project_id is not None:
                recommendation[
                    "project_id"
                ] = str(
                    project_id
                )

        # -----------------------------------------------------
        # SOCIAL FEED
        # -----------------------------------------------------

        post_service = PostService(
            PostRepository(db)
        )

        feed = post_service.get_feed(
            current_user=current_user,
            limit=10,
            offset=0,
        )

        # -----------------------------------------------------
        # NEWS
        # -----------------------------------------------------

        news = news_service.personalized(
            db=db,
            current_user=current_user,
            limit=5,
        )

        for article in news:

            article_id = article.get(
                "id"
            )

            if article_id is not None:
                article["id"] = str(
                    article_id
                )

        # -----------------------------------------------------
        # NOTIFICATIONS
        # -----------------------------------------------------

        notification_service = (
            NotificationService(
                NotificationRepository(
                    db
                )
            )
        )

        notification_result = (
            notification_service
            .get_notifications(
                current_user=current_user,
                limit=5,
                offset=0,
                unread_only=False,
            )
        )

        notifications = []

        for notification in (
            notification_result.notifications
        ):
            notifications.append(
                notification.model_dump(
                    mode="json"
                )
            )

        # -----------------------------------------------------
        # FINAL HOME RESPONSE
        # -----------------------------------------------------

        return {
            "user": user_data,
            "daily_assessment": (
                daily_assessment
            ),
            "recommendations": (
                recommendations
            ),
            "feed": feed,
            "news": news,
            "notifications": (
                notifications
            ),
        }


home_service = HomeService()