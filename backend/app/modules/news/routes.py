from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

from app.modules.news.schemas import (
    NewsArticleResponse,
    NewsRefreshResponse,
)
from app.modules.news.service import (
    news_service,
)


router = APIRouter(
    prefix="/news",
    tags=["News"],
)


@router.get(
    "/personalized",
    response_model=list[
        NewsArticleResponse
    ],
)
def personalized_news(
    limit: int = Query(
        default=20,
        ge=1,
        le=50,
    ),
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    return news_service.personalized(
        db,
        current_user,
        limit,
    )


@router.post(
    "/refresh",
    response_model=NewsRefreshResponse,
)
def refresh_news(
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    return news_service.refresh(
        db,
        current_user,
    )


@router.get(
    "/categories",
    response_model=list[str],
)
def my_news_categories(
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):
    return (
        news_service
        .get_user_categories(
            db,
            current_user,
        )
    )