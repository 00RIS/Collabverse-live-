import uuid

from fastapi import HTTPException

from app.models.user import User

from app.modules.posts.models import Post
from app.modules.posts.repositories import PostRepository
from app.modules.posts.schemas import (
    CommentCreate,
    CommentUpdate,
    PostCreate,
    PostDetailResponse,
    PostUpdate,
)

from app.modules.notifications.models import NotificationType
from app.modules.notifications.repositories import (
    NotificationRepository,
)
from app.modules.notifications.service import (
    NotificationService,
)


class PostService:
    def __init__(
        self,
        repository: PostRepository,
    ):
        self.repository = repository

        # Both repositories use the same database session.
        self.notification_service = NotificationService(
            NotificationRepository(
                repository.db
            )
        )

    # ---------------------------------------------------------
    # CREATE POST
    # ---------------------------------------------------------

    def create_post(
        self,
        current_user: User,
        data: PostCreate,
    ):
        return self.repository.create_post(
            author_id=current_user.id,
            content=data.content,
            post_type=data.post_type,
            project_id=data.project_id,
            media=data.media,
        )

    # ---------------------------------------------------------
    # GET POST
    # ---------------------------------------------------------

    def get_post_or_404(
        self,
        post_id: uuid.UUID,
    ) -> Post:

        post = self.repository.get_post(
            post_id
        )

        if post is None:
            raise HTTPException(
                status_code=404,
                detail="Post not found",
            )

        return post

    # ---------------------------------------------------------
    # POST DETAIL
    # ---------------------------------------------------------

    def get_post_detail(
        self,
        post_id: uuid.UUID,
        current_user: User,
    ) -> PostDetailResponse:

        post = self.get_post_or_404(
            post_id
        )

        like_count = (
            self.repository.count_likes(
                post.id
            )
        )

        comment_count = (
            self.repository.count_comments(
                post.id
            )
        )

        liked_by_me = (
            self.repository.get_like(
                post.id,
                current_user.id,
            )
            is not None
        )

        return PostDetailResponse(
            id=post.id,
            author_id=post.author_id,
            post_type=post.post_type,
            content=post.content,
            project_id=post.project_id,
            media=post.media,
            created_at=post.created_at,
            updated_at=post.updated_at,
            like_count=like_count,
            comment_count=comment_count,
            liked_by_me=liked_by_me,
        )

    # ---------------------------------------------------------
    # UPDATE POST
    # ---------------------------------------------------------

    def update_post(
        self,
        post_id: uuid.UUID,
        current_user: User,
        data: PostUpdate,
    ):

        post = self.get_post_or_404(
            post_id
        )

        if post.author_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "You can only edit "
                    "your own posts"
                ),
            )

        return self.repository.update_post(
            post,
            data.content,
        )

    # ---------------------------------------------------------
    # DELETE POST
    # ---------------------------------------------------------

    def delete_post(
        self,
        post_id: uuid.UUID,
        current_user: User,
    ):

        post = self.get_post_or_404(
            post_id
        )

        if post.author_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "You can only delete "
                    "your own posts"
                ),
            )

        self.repository.delete_post(
            post
        )

    # ---------------------------------------------------------
    # LIKE / UNLIKE POST
    # ---------------------------------------------------------

    def toggle_like(
        self,
        post_id: uuid.UUID,
        current_user: User,
    ):

        post = self.get_post_or_404(
            post_id
        )

        existing = (
            self.repository.get_like(
                post.id,
                current_user.id,
            )
        )

        # -----------------------------
        # UNLIKE
        # -----------------------------

        if existing:
            self.repository.remove_like(
                existing
            )

            liked = False

        # -----------------------------
        # LIKE
        # -----------------------------

        else:
            self.repository.add_like(
                post.id,
                current_user.id,
            )

            liked = True

            # Only notify when another user
            # likes the post.
            if post.author_id != current_user.id:

                self.notification_service.create_notification(
                    user_id=post.author_id,
                    actor_id=current_user.id,
                    notification_type=(
                        NotificationType.POST_LIKE
                    ),
                    title="New like",
                    message=(
                        "Someone liked your post."
                    ),
                    entity_type="post",
                    entity_id=post.id,
                )

        return {
            "post_id": post.id,
            "liked": liked,
            "like_count": (
                self.repository.count_likes(
                    post.id
                )
            ),
        }

    # ---------------------------------------------------------
    # CREATE COMMENT
    # ---------------------------------------------------------

    def create_comment(
        self,
        post_id: uuid.UUID,
        current_user: User,
        data: CommentCreate,
    ):

        post = self.get_post_or_404(
            post_id
        )

        comment = (
            self.repository.create_comment(
                post.id,
                current_user.id,
                data.content,
            )
        )

        # Notify the post owner only when
        # another user comments.
        if post.author_id != current_user.id:

            self.notification_service.create_notification(
                user_id=post.author_id,
                actor_id=current_user.id,
                notification_type=(
                    NotificationType.POST_COMMENT
                ),
                title="New comment",
                message=(
                    "Someone commented "
                    "on your post."
                ),
                entity_type="post",
                entity_id=post.id,
            )

        return comment

    # ---------------------------------------------------------
    # UPDATE COMMENT
    # ---------------------------------------------------------

    def update_comment(
        self,
        comment_id: uuid.UUID,
        current_user: User,
        data: CommentUpdate,
    ):

        comment = (
            self.repository.get_comment(
                comment_id
            )
        )

        if comment is None:
            raise HTTPException(
                status_code=404,
                detail="Comment not found",
            )

        if comment.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "You can only edit "
                    "your own comments"
                ),
            )

        return self.repository.update_comment(
            comment,
            data.content,
        )

    # ---------------------------------------------------------
    # DELETE COMMENT
    # ---------------------------------------------------------

    def delete_comment(
        self,
        comment_id: uuid.UUID,
        current_user: User,
    ):

        comment = (
            self.repository.get_comment(
                comment_id
            )
        )

        if comment is None:
            raise HTTPException(
                status_code=404,
                detail="Comment not found",
            )

        if comment.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "You can only delete "
                    "your own comments"
                ),
            )

        self.repository.delete_comment(
            comment
        )
        # =========================================================
    # SOCIAL FEED
    # =========================================================

    def get_feed(
        self,
        current_user: User,
        limit: int = 10,
        offset: int = 0,
    ) -> list[dict]:

        posts = self.repository.get_feed(
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )

        results = []

        for post in posts:

            like_count = (
                self.repository.count_likes(
                    post.id
                )
            )

            comment_count = (
                self.repository.count_comments(
                    post.id
                )
            )

            liked_by_me = (
                self.repository.get_like(
                    post.id,
                    current_user.id,
                )
                is not None
            )

            results.append(
                {
                    "id": str(post.id),
                    "author_id": str(
                        post.author_id
                    ),
                    "post_type": getattr(
                        post.post_type,
                        "value",
                        post.post_type,
                    ),
                    "content": post.content,
                    "project_id": (
                        str(post.project_id)
                        if post.project_id
                        else None
                    ),
                    "created_at": (
                        post.created_at
                    ),
                    "updated_at": (
                        post.updated_at
                    ),
                    "like_count": like_count,
                    "comment_count": (
                        comment_count
                    ),
                    "liked_by_me": (
                        liked_by_me
                    ),
                }
            )

        return results