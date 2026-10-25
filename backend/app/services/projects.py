import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.project import (
    Project,
    ProjectApplication,
    ProjectApplicationStatus,
    ProjectMember,
    ProjectMemberRole,
    ProjectSkill,
    ProjectStatus,
)

from app.schemas.projects import (
    ProjectApplicationCreate,
    ProjectCreate,
    ProjectUpdate,
)

from app.modules.notifications.models import NotificationType
from app.modules.notifications.repositories import NotificationRepository
from app.modules.notifications.service import NotificationService


# =========================================================
# NOTIFICATION HELPER
# =========================================================

def get_notification_service(
    db: Session,
) -> NotificationService:
    repository = NotificationRepository(db)

    return NotificationService(
        repository=repository
    )


# =========================================================
# PROJECT HELPERS
# =========================================================

def get_project_by_id(
    db: Session,
    project_id: uuid.UUID,
) -> Project | None:
    return db.scalar(
        select(Project).where(
            Project.id == project_id
        )
    )


def require_project(
    db: Session,
    project_id: uuid.UUID,
) -> Project:
    project = get_project_by_id(
        db,
        project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


def require_owner(
    project: Project,
    user_id: uuid.UUID,
) -> None:
    if project.creator_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can perform this action",
        )


# =========================================================
# CREATE PROJECT
# =========================================================

def create_project(
    db: Session,
    creator_id: uuid.UUID,
    data: ProjectCreate,
) -> Project:
    if (
        data.start_date is not None
        and data.end_date is not None
        and data.end_date < data.start_date
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date cannot be before start_date",
        )

    project = Project(
        creator_id=creator_id,
        title=data.title,
        description=data.description,
        domain=data.domain,
        project_type=data.project_type,
        difficulty=data.difficulty,

        # If project is accepting members, open it automatically.
        status=(
            ProjectStatus.OPEN
            if data.is_accepting_members
            else ProjectStatus.DRAFT
        ),

        visibility=data.visibility,
        max_team_size=data.max_team_size,
        is_accepting_members=data.is_accepting_members,
        start_date=data.start_date,
        end_date=data.end_date,
    )

    db.add(project)
    db.flush()

    # Creator automatically becomes project OWNER.
    owner = ProjectMember(
        project_id=project.id,
        user_id=creator_id,
        role=ProjectMemberRole.OWNER,
    )

    db.add(owner)

    # Add project skill requirements.
    for skill_data in data.skills:
        project_skill = ProjectSkill(
            project_id=project.id,
            skill_id=skill_data.skill_id,
            required_level=skill_data.required_level,
            priority=skill_data.priority,
        )

        db.add(project_skill)

    db.commit()
    db.refresh(project)

    return project


# =========================================================
# LIST PROJECTS
# =========================================================

def list_projects(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    domain: str | None = None,
    project_type=None,
    difficulty=None,
    status=None,
) -> list[Project]:
    stmt = select(Project)

    if domain:
        stmt = stmt.where(
            Project.domain.ilike(
                f"%{domain}%"
            )
        )

    if project_type:
        stmt = stmt.where(
            Project.project_type == project_type
        )

    if difficulty:
        stmt = stmt.where(
            Project.difficulty == difficulty
        )

    if status:
        stmt = stmt.where(
            Project.status == status
        )

    stmt = (
        stmt
        .order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(
        db.scalars(stmt).unique().all()
    )


# =========================================================
# UPDATE PROJECT
# =========================================================

def update_project(
    db: Session,
    project: Project,
    data: ProjectUpdate,
) -> Project:
    update_data = data.model_dump(
        exclude_unset=True
    )

    new_start = update_data.get(
        "start_date",
        project.start_date,
    )

    new_end = update_data.get(
        "end_date",
        project.end_date,
    )

    if (
        new_start is not None
        and new_end is not None
        and new_end < new_start
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date cannot be before start_date",
        )

    for field, value in update_data.items():
        setattr(
            project,
            field,
            value,
        )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


# =========================================================
# DELETE PROJECT
# =========================================================

def delete_project(
    db: Session,
    project: Project,
) -> None:
    db.delete(project)
    db.commit()


# =========================================================
# APPLY TO PROJECT
# =========================================================

def apply_to_project(
    db: Session,
    project: Project,
    user_id: uuid.UUID,
    data: ProjectApplicationCreate,
) -> ProjectApplication:

    if project.creator_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot apply to your own project",
        )

    if not project.is_accepting_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This project is not accepting members",
        )

    if project.status != ProjectStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Applications are only allowed for open projects",
        )

    existing_member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user_id,
        )
    )

    if existing_member is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already a member of this project",
        )

    existing_application = db.scalar(
        select(ProjectApplication).where(
            ProjectApplication.project_id == project.id,
            ProjectApplication.user_id == user_id,
        )
    )

    # Re-apply after rejection or withdrawal.
    if existing_application is not None:
        if existing_application.status in {
            ProjectApplicationStatus.PENDING,
            ProjectApplicationStatus.ACCEPTED,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already applied to this project",
            )

        existing_application.status = (
            ProjectApplicationStatus.PENDING
        )

        existing_application.message = data.message

        db.commit()
        db.refresh(existing_application)

        notification_service = get_notification_service(db)

        notification_service.create_notification(
            user_id=project.creator_id,
            actor_id=user_id,
            notification_type=NotificationType.PROJECT_UPDATE,
            title="New project application",
            message=f"A user applied to join {project.title}.",
            entity_type="project_application",
            entity_id=existing_application.id,
        )

        return existing_application

    application = ProjectApplication(
        project_id=project.id,
        user_id=user_id,
        message=data.message,
        status=ProjectApplicationStatus.PENDING,
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    notification_service = get_notification_service(db)

    notification_service.create_notification(
        user_id=project.creator_id,
        actor_id=user_id,
        notification_type=NotificationType.PROJECT_UPDATE,
        title="New project application",
        message=f"A user applied to join {project.title}.",
        entity_type="project_application",
        entity_id=application.id,
    )

    return application


# =========================================================
# APPLICATION LIST
# =========================================================

def list_project_applications(
    db: Session,
    project_id: uuid.UUID,
) -> list[ProjectApplication]:

    stmt = (
        select(ProjectApplication)
        .where(
            ProjectApplication.project_id
            == project_id
        )
        .order_by(
            ProjectApplication.applied_at.desc()
        )
    )

    return list(
        db.scalars(stmt).all()
    )


def get_application(
    db: Session,
    project_id: uuid.UUID,
    application_id: uuid.UUID,
) -> ProjectApplication:

    application = db.scalar(
        select(ProjectApplication).where(
            ProjectApplication.id == application_id,
            ProjectApplication.project_id == project_id,
        )
    )

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project application not found",
        )

    return application


# =========================================================
# ACCEPT APPLICATION
# =========================================================

def accept_application(
    db: Session,
    project: Project,
    application: ProjectApplication,
) -> ProjectApplication:

    if application.status != ProjectApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending applications can be accepted",
        )

    if project.max_team_size is not None:
        member_count = db.scalar(
            select(
                func.count(ProjectMember.id)
            ).where(
                ProjectMember.project_id == project.id
            )
        )

        if member_count >= project.max_team_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project team is already full",
            )

    existing_member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == application.user_id,
        )
    )

    if existing_member is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Applicant is already a project member",
        )

    member = ProjectMember(
        project_id=project.id,
        user_id=application.user_id,
        role=ProjectMemberRole.MEMBER,
    )

    db.add(member)

    application.status = (
        ProjectApplicationStatus.ACCEPTED
    )

    db.commit()
    db.refresh(application)

    notification_service = get_notification_service(db)

    notification_service.create_notification(
        user_id=application.user_id,
        actor_id=project.creator_id,
        notification_type=NotificationType.APPLICATION_UPDATE,
        title="Project application accepted",
        message=f"Your application to join {project.title} was accepted.",
        entity_type="project",
        entity_id=project.id,
    )

    return application


# =========================================================
# REJECT APPLICATION
# =========================================================

def reject_application(
    db: Session,
    project: Project,
    application: ProjectApplication,
) -> ProjectApplication:

    if application.status != ProjectApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending applications can be rejected",
        )

    application.status = (
        ProjectApplicationStatus.REJECTED
    )

    db.commit()
    db.refresh(application)

    notification_service = get_notification_service(db)

    notification_service.create_notification(
        user_id=application.user_id,
        actor_id=project.creator_id,
        notification_type=NotificationType.APPLICATION_UPDATE,
        title="Project application update",
        message=f"Your application to join {project.title} was not accepted.",
        entity_type="project",
        entity_id=project.id,
    )

    return application


# =========================================================
# WITHDRAW APPLICATION
# =========================================================

def withdraw_application(
    db: Session,
    application: ProjectApplication,
    user_id: uuid.UUID,
) -> ProjectApplication:

    if application.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only withdraw your own application",
        )

    if application.status != ProjectApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending applications can be withdrawn",
        )

    application.status = (
        ProjectApplicationStatus.WITHDRAWN
    )

    db.commit()
    db.refresh(application)

    return application


# =========================================================
# MEMBERS
# =========================================================

def list_project_members(
    db: Session,
    project_id: uuid.UUID,
) -> list[ProjectMember]:

    stmt = (
        select(ProjectMember)
        .where(
            ProjectMember.project_id
            == project_id
        )
        .order_by(
            ProjectMember.joined_at.asc()
        )
    )

    return list(
        db.scalars(stmt).all()
    )


# =========================================================
# REMOVE MEMBER
# =========================================================

def remove_project_member(
    db: Session,
    project: Project,
    member_user_id: uuid.UUID,
    owner_user_id: uuid.UUID,
) -> None:

    require_owner(
        project,
        owner_user_id,
    )

    if member_user_id == project.creator_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project owner cannot be removed",
        )

    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == member_user_id,
        )
    )

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project member not found",
        )

    # If the member originally joined through an accepted application,
    # change the application so they can apply again later.
    application = db.scalar(
        select(ProjectApplication).where(
            ProjectApplication.project_id == project.id,
            ProjectApplication.user_id == member_user_id,
        )
    )

    if (
        application is not None
        and application.status
        == ProjectApplicationStatus.ACCEPTED
    ):
        application.status = (
            ProjectApplicationStatus.REJECTED
        )

    db.delete(member)
    db.commit()

    notification_service = get_notification_service(db)

    notification_service.create_notification(
        user_id=member_user_id,
        actor_id=owner_user_id,
        notification_type=NotificationType.PROJECT_UPDATE,
        title="Removed from project",
        message=f"You were removed from {project.title}.",
        entity_type="project",
        entity_id=project.id,
    )


# =========================================================
# LEAVE PROJECT
# =========================================================

def leave_project(
    db: Session,
    project: Project,
    user_id: uuid.UUID,
) -> None:

    if project.creator_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project owner cannot leave the project",
        )

    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == user_id,
        )
    )

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of this project",
        )

    # Change accepted application to withdrawn so the user
    # can apply again later if they want.
    application = db.scalar(
        select(ProjectApplication).where(
            ProjectApplication.project_id == project.id,
            ProjectApplication.user_id == user_id,
        )
    )

    if (
        application is not None
        and application.status
        == ProjectApplicationStatus.ACCEPTED
    ):
        application.status = (
            ProjectApplicationStatus.WITHDRAWN
        )

    db.delete(member)
    db.commit()

    notification_service = get_notification_service(db)

    notification_service.create_notification(
        user_id=project.creator_id,
        actor_id=user_id,
        notification_type=NotificationType.PROJECT_UPDATE,
        title="Project member left",
        message=f"A member left {project.title}.",
        entity_type="project",
        entity_id=project.id,
    )


# =========================================================
# MY CREATED PROJECTS
# =========================================================

def list_created_projects(
    db: Session,
    user_id: uuid.UUID,
) -> list[Project]:

    stmt = (
        select(Project)
        .where(
            Project.creator_id == user_id
        )
        .order_by(
            Project.created_at.desc()
        )
    )

    return list(
        db.scalars(stmt).unique().all()
    )


# =========================================================
# MY JOINED PROJECTS
# =========================================================

def list_joined_projects(
    db: Session,
    user_id: uuid.UUID,
) -> list[Project]:

    stmt = (
        select(Project)
        .join(
            ProjectMember,
            ProjectMember.project_id == Project.id,
        )
        .where(
            ProjectMember.user_id == user_id,
            ProjectMember.role != ProjectMemberRole.OWNER,
        )
        .order_by(
            Project.created_at.desc()
        )
    )

    return list(
        db.scalars(stmt).unique().all()
    )