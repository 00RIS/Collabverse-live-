import logging
import uuid
from pathlib import Path
from tempfile import SpooledTemporaryFile

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.uploads import save_upload
from app.db.session import get_db
from app.models.user import User
from app.modules.posts.repositories import PostRepository
from app.modules.posts.models import PostReport, SavedPost
from app.modules.posts.schemas import (
    CommentCreate,
    CommentUpdate,
    LikeResponse,
    PostCommentResponse,
    PostCreate,
    PostDetailResponse,
    PostResponse,
    PostReportCreate,
    PostReportResponse,
    SavedPostState,
    PostUpdate,
)
from app.modules.posts.service import PostService


router = APIRouter(
    prefix="/posts",
    tags=["posts"],
)
logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024
ALLOWED_MEDIA = {
    ".jpg": ("image/jpeg", "image"),
    ".jpeg": ("image/jpeg", "image"),
    ".png": ("image/png", "image"),
    ".webp": ("image/webp", "image"),
    ".mp4": ("video/mp4", "video"),
    ".webm": ("video/webm", "video"),
}


def get_post_service(
    db: Session = Depends(get_db),
) -> PostService:
    return PostService(PostRepository(db))


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(
    data: PostCreate,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    return service.create_post(current_user, data)


@router.post(
    "/media/upload",
    status_code=status.HTTP_201_CREATED,
)
def upload_post_media(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Store a supported image or video for a new community post."""
    suffix = Path(file.filename or "").suffix.lower()
    media_config = ALLOWED_MEDIA.get(suffix)
    if media_config is None or file.content_type != media_config[0]:
        raise HTTPException(
            status_code=415,
            detail="Upload a JPG, PNG, WebP, MP4, or WebM file.",
        )

    media_type = media_config[1]
    size_limit = MAX_IMAGE_BYTES if media_type == "image" else MAX_VIDEO_BYTES
    stored_name = f"{current_user.id}-{uuid.uuid4().hex}{suffix}"
    total = 0
    first_chunk = True

    try:
        with SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b") as output:
            while chunk := file.file.read(1024 * 1024):
                if first_chunk:
                    first_chunk = False
                    valid_signature = (
                        (suffix in {".jpg", ".jpeg"} and chunk.startswith(b"\xff\xd8\xff"))
                        or (suffix == ".png" and chunk.startswith(b"\x89PNG\r\n\x1a\n"))
                        or (suffix == ".webp" and chunk.startswith(b"RIFF") and chunk[8:12] == b"WEBP")
                        or (suffix == ".mp4" and len(chunk) >= 12 and chunk[4:8] == b"ftyp")
                        or (suffix == ".webm" and chunk.startswith(b"\x1a\x45\xdf\xa3"))
                    )
                    if not valid_signature:
                        raise HTTPException(status_code=415, detail="The file contents do not match the selected media type.")
                total += len(chunk)
                if total > size_limit:
                    raise HTTPException(
                        status_code=413,
                        detail=("Images must be 10 MB or smaller." if media_type == "image" else "Videos must be 100 MB or smaller."),
                    )
                output.write(chunk)
            if total == 0:
                raise HTTPException(status_code=400, detail="The selected file is empty.")
            hosted_url = save_upload(output, f"posts/{stored_name}", media_config[0])
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Post media storage failed for user %s", current_user.id)
        raise HTTPException(status_code=503, detail="Could not store the upload. Check the configured upload storage and try again.") from exc
    finally:
        file.file.close()

    media_url = hosted_url or f"{str(request.base_url).rstrip('/')}/uploads/posts/{stored_name}"
    return {"media_url": media_url, "media_type": media_type}


@router.get(
    "/feed",
    response_model=list[PostResponse],
)
def get_feed(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = PostRepository(db)

    return repository.get_feed(
        current_user.id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/users/{user_id}",
    response_model=list[PostResponse],
)
def get_user_posts(
    user_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = PostRepository(db)

    return repository.get_user_posts(
        user_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/saved/ids",
    response_model=list[uuid.UUID],
)
def get_saved_post_ids(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list(db.scalars(
        select(SavedPost.post_id)
        .where(SavedPost.user_id == current_user.id)
    ).all())


@router.get(
    "/saved",
    response_model=list[PostDetailResponse],
)
def get_saved_posts(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    saved = db.scalars(
        select(SavedPost)
        .where(SavedPost.user_id == current_user.id)
        .order_by(SavedPost.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [service.get_post_detail(item.post_id, current_user) for item in saved]


@router.put(
    "/{post_id}/save",
    response_model=SavedPostState,
)
def save_post(
    post_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    post = service.get_post_or_404(post_id)
    saved = db.scalar(
        select(SavedPost).where(
            SavedPost.post_id == post.id,
            SavedPost.user_id == current_user.id,
        )
    )
    if saved is None:
        db.add(SavedPost(post_id=post.id, user_id=current_user.id))
        db.commit()
    return SavedPostState(post_id=post.id, saved=True)


@router.delete(
    "/{post_id}/save",
    response_model=SavedPostState,
)
def unsave_post(
    post_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    post = service.get_post_or_404(post_id)
    saved = db.scalar(
        select(SavedPost).where(
            SavedPost.post_id == post.id,
            SavedPost.user_id == current_user.id,
        )
    )
    if saved is not None:
        db.delete(saved)
        db.commit()
    return SavedPostState(post_id=post.id, saved=False)


@router.post(
    "/{post_id}/report",
    response_model=PostReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def report_post(
    post_id: uuid.UUID,
    payload: PostReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    post = service.get_post_or_404(post_id)
    if post.author_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot report your own post.")
    existing = db.scalar(
        select(PostReport).where(
            PostReport.post_id == post.id,
            PostReport.reporter_id == current_user.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="You have already reported this post.")
    report = PostReport(
        post_id=post.id,
        reporter_id=current_user.id,
        reason=payload.reason,
        details=payload.details.strip() if payload.details else None,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return PostReportResponse(id=report.id, post_id=report.post_id)


@router.get(
    "/{post_id}",
    response_model=PostDetailResponse,
)
def get_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    return service.get_post_detail(
        post_id,
        current_user,
    )


@router.patch(
    "/{post_id}",
    response_model=PostResponse,
)
def update_post(
    post_id: uuid.UUID,
    data: PostUpdate,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    return service.update_post(
        post_id,
        current_user,
        data,
    )


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_post(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    service.delete_post(
        post_id,
        current_user,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


@router.post(
    "/{post_id}/like",
    response_model=LikeResponse,
)
def toggle_like(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    return service.toggle_like(
        post_id,
        current_user,
    )


@router.post(
    "/{post_id}/comments",
    response_model=PostCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    post_id: uuid.UUID,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    return service.create_comment(
        post_id,
        current_user,
        data,
    )


@router.get(
    "/{post_id}/comments",
    response_model=list[PostCommentResponse],
)
def get_comments(
    post_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PostService = Depends(get_post_service),
):
    service.get_post_or_404(post_id)

    repository = PostRepository(db)

    return repository.get_comments(post_id)


@router.patch(
    "/comments/{comment_id}",
    response_model=PostCommentResponse,
)
def update_comment(
    comment_id: uuid.UUID,
    data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    return service.update_comment(
        comment_id,
        current_user,
        data,
    )


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_comment(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
):
    service.delete_comment(
        comment_id,
        current_user,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )
