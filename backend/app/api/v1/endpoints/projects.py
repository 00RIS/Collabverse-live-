import uuid

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.project import (
    ProjectDifficulty,
    ProjectStatus,
    ProjectType,
)
from app.models.user import User
from app.schemas.projects import (
    ProjectApplicationCreate,
    ProjectApplicationResponse,
    ProjectCreate,
    ProjectMemberResponse,
    ProjectResponse,
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