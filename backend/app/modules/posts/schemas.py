import uuid
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    model_validator,
)

from app.modules.posts.models import (
    MediaType,
    PostType,
)


class PostMediaCreate(BaseModel):
    media_type: MediaType

    media_url: HttpUrl

    thumbnail_url: HttpUrl | None = None

    position: int = Field(
        default=0,
        ge=0,
        le=20,
    )


class PostMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    post_id: uuid.UUID

    media_type: MediaType

    media_url: str
    thumbnail_url: str | None

    position: int
    created_at: datetime


class PostCreate(BaseModel):
    content: str | None = Field(
        default=None,
        max_length=5000,
    )

    post_type: PostType = PostType.TEXT

    project_id: uuid.UUID | None = None

    media: list[PostMediaCreate] = Field(
        default_factory=list,
        max_length=10,
    )

    @model_validator(mode="after")
    def validate_post(self):

        has_content = bool(
            self.content and self.content.strip()
        )

        has_media = len(self.media) > 0

        if self.post_type == PostType.TEXT:
            if not has_content:
                raise ValueError(
                    "Text posts require content"
                )

            if has_media:
                raise ValueError(
                    "Use post_type='media' when attaching images or videos"
                )

            if self.project_id is not None:
                raise ValueError(
                    "Text posts cannot contain project_id"
                )

        elif self.post_type == PostType.MEDIA:
            if not has_media:
                raise ValueError(
                    "Media posts require at least one image or video"
                )

            if self.project_id is not None:
                raise ValueError(
                    "Media posts cannot contain project_id"
                )

        elif self.post_type == PostType.PROJECT:
            if self.project_id is None:
                raise ValueError(
                    "Project posts require project_id"
                )

        return self


class PostUpdate(BaseModel):
    content: str | None = Field(
        default=None,
        max_length=5000,
    )


class CommentCreate(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=2000,
    )


class CommentUpdate(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=2000,
    )


class PostCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    post_id: uuid.UUID
    user_id: uuid.UUID

    content: str

    created_at: datetime
    updated_at: datetime


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author_id: uuid.UUID

    post_type: PostType

    content: str | None

    project_id: uuid.UUID | None

    media: list[PostMediaResponse] = []

    created_at: datetime
    updated_at: datetime


class PostDetailResponse(PostResponse):
    like_count: int = 0
    comment_count: int = 0
    liked_by_me: bool = False


class LikeResponse(BaseModel):
    post_id: uuid.UUID
    liked: bool
    like_count: int


class SavedPostState(BaseModel):
    post_id: uuid.UUID
    saved: bool


class PostReportCreate(BaseModel):
    reason: Literal[
        "spam",
        "harassment",
        "hate",
        "false_information",
        "inappropriate",
        "other",
    ]
    details: str | None = Field(default=None, max_length=1000)


class PostReportResponse(BaseModel):
    id: uuid.UUID
    post_id: uuid.UUID
    submitted: bool = True
