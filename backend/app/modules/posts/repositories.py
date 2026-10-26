import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.posts.models import (
    Post,
    PostComment,
    PostLike,
    PostMedia,
)


class PostRepository:
    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    # =========================================================
    # POSTS
    # =========================================================

    def create_post(
        self,
        author_id: uuid.UUID,
        content,
        post_type,
        project_id=None,
        media=None,
    ) -> Post:

        post = Post(
            author_id=author_id,
            content=content,
            post_type=post_type,
            project_id=project_id,
        )

        self.db.add(post)
        self.db.flush()

        # -----------------------------------------------------
        # MEDIA
        # -----------------------------------------------------

        if media:
            for index, item in enumerate(media):

                media_type = getattr(
                    item,
                    "media_type",
                    None,
                )

                media_url = getattr(
                    item,
                    "media_url",
                    None,
                )

                thumbnail_url = getattr(
                    item,
                    "thumbnail_url",
                    None,
                )

                position = getattr(
                    item,
                    "position",
                    index,
                )

                # Also support dictionary values
                if isinstance(item, dict):
                    media_type = item.get(
                        "media_type"
                    )

                    media_url = item.get(
                        "media_url"
                    )

                    thumbnail_url = item.get(
                        "thumbnail_url"
                    )

                    position = item.get(
                        "position",
                        index,
                    )

                # Pydantic HttpUrl values are URL wrapper objects;
                # SQLAlchemy's string column expects plain strings.
                if media_url is not None:
                    media_url = str(media_url)

                if thumbnail_url is not None:
                    thumbnail_url = str(thumbnail_url)

                post_media = PostMedia(
                    post_id=post.id,
                    media_type=media_type,
                    media_url=media_url,
                    thumbnail_url=thumbnail_url,
                    position=position,
                )

                self.db.add(
                    post_media
                )

        self.db.commit()
        self.db.refresh(post)

        return post

    # ---------------------------------------------------------
    # GET POST
    # ---------------------------------------------------------

    def get_post(
        self,
        post_id: uuid.UUID,
    ) -> Post | None:

        return self.db.get(
            Post,
            post_id,
        )

    # ---------------------------------------------------------
    # UPDATE POST
    # ---------------------------------------------------------

    def update_post(
        self,
        post: Post,
        content,
    ) -> Post:

        post.content = content

        self.db.commit()
        self.db.refresh(post)

        return post

    # ---------------------------------------------------------
    # DELETE POST
    # ---------------------------------------------------------

    def delete_post(
        self,
        post: Post,
    ) -> None:

        self.db.delete(post)
        self.db.commit()

    # =========================================================
    # USER POSTS
    # =========================================================

    def get_user_posts(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Post]:

        query = (
            select(Post)
            .where(
                Post.author_id == user_id
            )
            .order_by(
                Post.created_at.desc()
            )
            .offset(offset)
            .limit(limit)
        )

        return list(
            self.db.scalars(query).all()
        )

    def list_user_posts(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Post]:

        return self.get_user_posts(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    # =========================================================
    # FEED
    # =========================================================

    def get_feed(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Post]:

        # Community posts are visible across the platform, regardless of
        # whether the reader is connected to the author.
        query = (
            select(Post)
            .order_by(
                Post.created_at.desc()
            )
            .offset(offset)
            .limit(limit)
        )

        return list(
            self.db.scalars(query).all()
        )

    def list_feed(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Post]:

        return self.get_feed(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    # =========================================================
    # LIKES
    # =========================================================

    def get_like(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> PostLike | None:

        query = select(
            PostLike
        ).where(
            PostLike.post_id == post_id,
            PostLike.user_id == user_id,
        )

        return self.db.scalar(
            query
        )

    def add_like(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> PostLike:

        like = PostLike(
            post_id=post_id,
            user_id=user_id,
        )

        self.db.add(like)

        self.db.commit()
        self.db.refresh(like)

        return like

    def remove_like(
        self,
        like: PostLike,
    ) -> None:

        self.db.delete(like)
        self.db.commit()

    def count_likes(
        self,
        post_id: uuid.UUID,
    ) -> int:

        query = select(
            func.count(
                PostLike.id
            )
        ).where(
            PostLike.post_id
            == post_id
        )

        result = self.db.scalar(
            query
        )

        return result or 0

    # =========================================================
    # COMMENTS
    # =========================================================

    def create_comment(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
    ) -> PostComment:

        comment = PostComment(
            post_id=post_id,
            user_id=user_id,
            content=content,
        )

        self.db.add(comment)

        self.db.commit()
        self.db.refresh(comment)

        return comment

    def get_comment(
        self,
        comment_id: uuid.UUID,
    ) -> PostComment | None:

        return self.db.get(
            PostComment,
            comment_id,
        )

    def get_comments(
        self,
        post_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PostComment]:

        query = (
            select(PostComment)
            .where(
                PostComment.post_id
                == post_id
            )
            .order_by(
                PostComment.created_at.asc()
            )
            .offset(offset)
            .limit(limit)
        )

        return list(
            self.db.scalars(query).all()
        )

    def list_comments(
        self,
        post_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PostComment]:

        return self.get_comments(
            post_id=post_id,
            limit=limit,
            offset=offset,
        )

    def update_comment(
        self,
        comment: PostComment,
        content: str,
    ) -> PostComment:

        comment.content = content

        self.db.commit()
        self.db.refresh(comment)

        return comment

    def delete_comment(
        self,
        comment: PostComment,
    ) -> None:

        self.db.delete(comment)
        self.db.commit()

    def count_comments(
        self,
        post_id: uuid.UUID,
    ) -> int:

        query = select(
            func.count(
                PostComment.id
            )
        ).where(
            PostComment.post_id
            == post_id
        )

        result = self.db.scalar(
            query
        )

        return result or 0
