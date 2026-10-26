import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from tempfile import SpooledTemporaryFile

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    Request,
    status,
    UploadFile,
    HTTPException,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.uploads import save_upload
from app.db.session import get_db
from app.models.project import Project, ProjectMeeting, ProjectMember, ProjectResource
from app.models.project import (
    ProjectDifficulty,
    ProjectStatus,
    ProjectType,
)
from app.models.user import User
from app.modules.messaging.models import (
    Conversation,
    ConversationParticipant,
    ConversationType,
    Message,
)
from app.schemas.projects import (
    ProjectApplicationCreate,
    ProjectApplicationResponse,
    ProjectCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectResourceCreate,
    ProjectResourceResponse,
    ProjectChatMessageCreate,
    ProjectChatMessageResponse,
    ProjectMeetingCreate,
    ProjectMeetingResponse,
    ProjectMeetingUpdate,
    ProjectUpdate,
)
from app.services.projects import (
    accept_application,
    apply_to_project,
    create_project,
    delete_project,
    get_application,
    leave_project,
    list_created_projects,
    list_joined_projects,
    list_project_applications,
    list_project_members,
    list_projects,
    reject_application,
    remove_project_member,
    require_owner,
    require_project,
    update_project,
    withdraw_application,
)


router = APIRouter()
logger = logging.getLogger(__name__)

PROJECT_UPLOADS = {
    ".jpg": ("image/jpeg", "media"),
    ".jpeg": ("image/jpeg", "media"),
    ".png": ("image/png", "media"),
    ".webp": ("image/webp", "media"),
    ".mp4": ("video/mp4", "media"),
    ".webm": ("video/webm", "media"),
    ".pdf": ("application/pdf", "document"),
}


def require_workspace_member(project: Project, user: User, db: Session) -> None:
    if project.creator_id == user.id:
        return
    member_id = db.scalar(
        select(ProjectMember.id).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user.id,
        )
    )
    if member_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Join this project to access its shared workspace.",
        )


def get_project_chat_conversation(project: Project, db: Session) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.project_id == project.id,
            Conversation.conversation_type == ConversationType.PROJECT,
        )
    )
    if conversation is None:
        conversation = Conversation(
            conversation_type=ConversationType.PROJECT,
            title=project.title,
            project_id=project.id,
            created_by=project.creator_id,
        )
        db.add(conversation)
        db.flush()

    active_member_ids = set(
        db.scalars(
            select(ProjectMember.user_id).where(ProjectMember.project_id == project.id)
        ).all()
    )
    participants = list(
        db.scalars(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id == conversation.id
            )
        ).all()
    )
    participant_ids = {participant.user_id for participant in participants}
    for user_id in active_member_ids - participant_ids:
        db.add(ConversationParticipant(conversation_id=conversation.id, user_id=user_id))
    for participant in participants:
        if participant.user_id not in active_member_ids:
            db.delete(participant)
    db.flush()
    return conversation


# =========================================================
# CREATE PROJECT
# =========================================================

@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_endpoint(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_project(
        db=db,
        creator_id=current_user.id,
        data=data,
    )


# =========================================================
# MY PROJECTS
# =========================================================

@router.get(
    "/me/created",
    response_model=list[ProjectResponse],
)
def get_my_created_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_created_projects(
        db=db,
        user_id=current_user.id,
    )


@router.get(
    "/me/joined",
    response_model=list[ProjectResponse],
)
def get_my_joined_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_joined_projects(
        db=db,
        user_id=current_user.id,
    )


# =========================================================
# LIST PROJECTS
# =========================================================

@router.get(
    "",
    response_model=list[ProjectResponse],
)
def list_projects_endpoint(
    skip: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    domain: str | None = None,
    project_type: ProjectType | None = None,
    difficulty: ProjectDifficulty | None = None,
    status_filter: ProjectStatus | None = Query(
        default=None,
        alias="status",
    ),
    db: Session = Depends(get_db),
):
    return list_projects(
        db=db,
        skip=skip,
        limit=limit,
        domain=domain,
        project_type=project_type,
        difficulty=difficulty,
        status=status_filter,
    )


# =========================================================
# GET PROJECT
# =========================================================

@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
)
def get_project_endpoint(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    return require_project(
        db=db,
        project_id=project_id,
    )


# =========================================================
# UPDATE PROJECT
# =========================================================

@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
)
def update_project_endpoint(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(
        db=db,
        project_id=project_id,
    )

    require_owner(
        project,
        current_user.id,
    )

    return update_project(
        db=db,
        project=project,
        data=data,
    )


# =========================================================
# DELETE PROJECT
# =========================================================

@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_project_endpoint(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(
        db=db,
        project_id=project_id,
    )

    require_owner(
        project,
        current_user.id,
    )

    delete_project(
        db=db,
        project=project,
    )

    return None


# =========================================================
# APPLY TO PROJECT
# =========================================================

@router.post(
    "/{project_id}/apply",
    response_model=ProjectApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_to_project_endpoint(
    project_id: uuid.UUID,
    data: ProjectApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(
        db=db,
        project_id=project_id,
    )

    return apply_to_project(
        db=db,
        project=project,
        user_id=current_user.id,
        data=data,
    )


# =========================================================
# APPLICATIONS
# =========================================================

@router.get(
    "/{project_id}/applications",
    response_model=list[ProjectApplicationResponse],
)
def get_project_applications_endpoint(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(
        db=db,
        project_id=project_id,
    )

    require_owner(
        project,
        current_user.id,
    )

    return list_project_applications(
        db=db,
        project_id=project.id,
    )


@router.post(
    "/{project_id}/applications/{application_id}/accept",
    response_model=ProjectApplicationResponse,
)
def accept_project_application_endpoint(
    project_id: uuid.UUID,
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(
        db=db,
        project_id=project_id,
    )

    require_owner(
        project,
        current_user.id,
    )

    application = get_application(
        db=db,
        project_id=project.id,
        application_id=application_id,
    )

    return accept_application(
        db=db,
        project=project,
        application=application,
    )


@router.post(
    "/{project_id}/applications/{application_id}/reject",
    response_model=ProjectApplicationResponse,
)
def reject_project_application_endpoint(
    project_id: uuid.UUID,
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(
        db=db,
        project_id=project_id,
    )

    require_owner(
        project,
        current_user.id,
    )

    application = get_application(
        db=db,
        project_id=project.id,
        application_id=application_id,
    )

    return reject_application(
        db=db,
        project=project,
        application=application,
    )


@router.post(
    "/{project_id}/applications/{application_id}/withdraw",
    response_model=ProjectApplicationResponse,
)
def withdraw_project_application_endpoint(
    project_id: uuid.UUID,
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project(
        db=db,
        project_id=project_id,
    )

    application = get_application(
        db=db,
        project_id=project_id,
        application_id=application_id,
    )

    return withdraw_application(
        db=db,
        application=application,
        user_id=current_user.id,
    )


# =========================================================
# MEMBERS
# =========================================================

@router.get(
    "/{project_id}/members",
    response_model=list[ProjectMemberResponse],
)
def get_project_members_endpoint(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    project = require_project(
        db=db,
        project_id=project_id,
    )

    return list_project_members(
        db=db,
        project_id=project.id,
    )


@router.delete(
    "/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_project_member_endpoint(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(
        db=db,
        project_id=project_id,
    )

    remove_project_member(
        db=db,
        project=project,
        member_user_id=user_id,
        owner_user_id=current_user.id,
    )

    return None


@router.delete(
    "/{project_id}/leave",
    status_code=status.HTTP_204_NO_CONTENT,
)
def leave_project_endpoint(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(
        db=db,
        project_id=project_id,
    )

    leave_project(
        db=db,
        project=project,
        user_id=current_user.id,
    )

    return None


@router.get(
    "/{project_id}/resources",
    response_model=list[ProjectResourceResponse],
)
def list_project_resources_endpoint(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db=db, project_id=project_id)
    require_workspace_member(project, current_user, db)
    return list(
        db.scalars(
            select(ProjectResource)
            .where(ProjectResource.project_id == project.id)
            .order_by(ProjectResource.created_at.desc())
        )
    )


@router.post(
    "/{project_id}/resources",
    response_model=ProjectResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_project_resource_endpoint(
    project_id: uuid.UUID,
    data: ProjectResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db=db, project_id=project_id)
    require_workspace_member(project, current_user, db)
    resource = ProjectResource(
        project_id=project.id,
        added_by=current_user.id,
        title=data.title.strip(),
        resource_type=data.resource_type,
        url=str(data.url),
        description=data.description.strip() if data.description else None,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.post(
    "/{project_id}/resources/upload",
    response_model=ProjectResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_project_resource_endpoint(
    project_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(default=""),
    description: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db=db, project_id=project_id)
    require_workspace_member(project, current_user, db)

    suffix = Path(file.filename or "").suffix.lower()
    upload_config = PROJECT_UPLOADS.get(suffix)
    if upload_config is None or file.content_type != upload_config[0]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPG, PNG, WebP, MP4, WebM, or PDF file.",
        )

    max_bytes = 100 * 1024 * 1024 if suffix in {".mp4", ".webm"} else 20 * 1024 * 1024
    stored_name = f"{current_user.id}-{uuid.uuid4().hex}{suffix}"
    total = 0
    first_chunk = True
    try:
        with SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b") as output:
            while chunk := file.file.read(1024 * 1024):
                if first_chunk:
                    valid = (
                        (suffix in {".jpg", ".jpeg"} and chunk.startswith(b"\xff\xd8\xff"))
                        or (suffix == ".png" and chunk.startswith(b"\x89PNG\r\n\x1a\n"))
                        or (suffix == ".webp" and chunk.startswith(b"RIFF") and chunk[8:12] == b"WEBP")
                        or (suffix == ".mp4" and len(chunk) >= 12 and chunk[4:8] == b"ftyp")
                        or (suffix == ".webm" and chunk.startswith(b"\x1a\x45\xdf\xa3"))
                        or (suffix == ".pdf" and chunk.startswith(b"%PDF-"))
                    )
                    if not valid:
                        raise HTTPException(
                            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail="The file contents do not match the selected file type.",
                        )
                    first_chunk = False
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Videos must be 100 MB or smaller; other files must be 20 MB or smaller.",
                    )
                output.write(chunk)
            if total == 0:
                raise HTTPException(status_code=400, detail="The selected file is empty.")
            media_type = upload_config[0]
            hosted_url = save_upload(
                output,
                f"projects/{project.id}/{stored_name}",
                media_type,
            )

        resource = ProjectResource(
            project_id=project.id,
            added_by=current_user.id,
            title=(title.strip()[:255] or Path(file.filename or "Shared file").name),
            resource_type=upload_config[1],
            url=hosted_url or f"{str(request.base_url).rstrip('/')}/uploads/projects/{project.id}/{stored_name}",
            description=description.strip() or None,
            file_name=Path(file.filename or stored_name).name[:255],
            content_type=media_type,
        )
        db.add(resource)
        db.commit()
        db.refresh(resource)
        return resource
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Project resource upload failed for project %s", project.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not store this project resource. Check the configured upload storage and try again.",
        ) from exc
    finally:
        file.file.close()


@router.delete(
    "/{project_id}/resources/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_project_resource_endpoint(
    project_id: uuid.UUID,
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db=db, project_id=project_id)
    require_workspace_member(project, current_user, db)
    resource = db.scalar(
        select(ProjectResource).where(
            ProjectResource.id == resource_id,
            ProjectResource.project_id == project.id,
        )
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="Project resource not found.")
    if resource.added_by != current_user.id and project.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can remove only resources you added.")
    db.delete(resource)
    db.commit()
    return None


@router.get(
    "/{project_id}/chat",
    response_model=list[ProjectChatMessageResponse],
)
def get_project_chat_endpoint(
    project_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db=db, project_id=project_id)
    require_workspace_member(project, current_user, db)
    conversation = get_project_chat_conversation(project, db)
    db.commit()
    messages = list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        ).all()
    )
    messages.reverse()
    return [
        {
            "id": message.id,
            "project_id": project.id,
            "sender_id": message.sender_id,
            "content": message.content,
            "created_at": message.created_at,
        }
        for message in messages
    ]


@router.post(
    "/{project_id}/chat",
    response_model=ProjectChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_project_chat_message_endpoint(
    project_id: uuid.UUID,
    data: ProjectChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db=db, project_id=project_id)
    require_workspace_member(project, current_user, db)
    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message cannot be empty.")
    conversation = get_project_chat_conversation(project, db)
    message = Message(
        conversation_id=conversation.id,
        sender_id=current_user.id,
        content=content,
    )
    conversation.updated_at = datetime.now(timezone.utc)
    db.add(message)
    db.commit()
    db.refresh(message)
    return {
        "id": message.id,
        "project_id": project.id,
        "sender_id": message.sender_id,
        "content": message.content,
        "created_at": message.created_at,
    }


@router.get(
    "/{project_id}/meetings",
    response_model=list[ProjectMeetingResponse],
)
def list_project_meetings_endpoint(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db=db, project_id=project_id)
    require_workspace_member(project, current_user, db)
    return list(
        db.scalars(
            select(ProjectMeeting)
            .where(ProjectMeeting.project_id == project.id)
            .order_by(ProjectMeeting.starts_at.asc())
        ).all()
    )


@router.post(
    "/{project_id}/meetings",
    response_model=ProjectMeetingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_meeting_endpoint(
    project_id: uuid.UUID,
    data: ProjectMeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db=db, project_id=project_id)
    require_owner(project, current_user.id)
    meeting = ProjectMeeting(
        project_id=project.id,
        created_by=current_user.id,
        title=data.title.strip(),
        description=data.description.strip() if data.description else None,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        meeting_url=str(data.meeting_url) if data.meeting_url else None,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


@router.patch(
    "/{project_id}/meetings/{meeting_id}",
    response_model=ProjectMeetingResponse,
)
def update_project_meeting_endpoint(
    project_id: uuid.UUID,
    meeting_id: uuid.UUID,
    data: ProjectMeetingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db=db, project_id=project_id)
    require_owner(project, current_user.id)
    meeting = db.scalar(
        select(ProjectMeeting).where(
            ProjectMeeting.id == meeting_id,
            ProjectMeeting.project_id == project.id,
        )
    )
    if meeting is None:
        raise HTTPException(status_code=404, detail="Project meeting not found.")
    changes = data.model_dump(exclude_unset=True)
    if "starts_at" in changes and changes["starts_at"] is None:
        raise HTTPException(status_code=422, detail="Meeting start time is required.")
    if "ends_at" in changes and changes["ends_at"] is None:
        raise HTTPException(status_code=422, detail="Meeting end time is required.")
    starts_at = changes.get("starts_at", meeting.starts_at)
    ends_at = changes.get("ends_at", meeting.ends_at)
    if ends_at <= starts_at:
        raise HTTPException(status_code=422, detail="Meeting end time must be after its start time.")
    for key, value in changes.items():
        setattr(meeting, key, str(value) if key == "meeting_url" and value else value)
    db.commit()
    db.refresh(meeting)
    return meeting


@router.delete(
    "/{project_id}/meetings/{meeting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cancel_project_meeting_endpoint(
    project_id: uuid.UUID,
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db=db, project_id=project_id)
    require_owner(project, current_user.id)
    meeting = db.scalar(
        select(ProjectMeeting).where(
            ProjectMeeting.id == meeting_id,
            ProjectMeeting.project_id == project.id,
        )
    )
    if meeting is None:
        raise HTTPException(status_code=404, detail="Project meeting not found.")
    meeting.status = "cancelled"
    db.commit()
    return None
