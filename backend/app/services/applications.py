import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import (
    Application,
    ApplicationStatus,
    ApplicationStatusHistory,
)
from app.schemas.applications import (
    ApplicationCreate,
    ApplicationUpdateStatus,
)


def create_application(
    db: Session,
    student_id: uuid.UUID,
    data: ApplicationCreate,
) -> Application:
    existing = db.scalar(
        select(Application).where(
            Application.student_id == student_id,
            Application.internship_id == data.internship_id,
        )
    )

    if existing:
        return existing

    application = Application(
        student_id=student_id,
        internship_id=data.internship_id,
        resume_url=data.resume_url,
        cover_letter=data.cover_letter,
        status=ApplicationStatus.APPLIED,
    )

    db.add(application)
    db.flush()

    history = ApplicationStatusHistory(
        application_id=application.id,
        status=ApplicationStatus.APPLIED,
        note="Application submitted",
    )

    db.add(history)

    db.commit()
    db.refresh(application)

    return application


def get_application_by_id(
    db: Session,
    application_id: uuid.UUID,
) -> Application | None:
    return db.scalar(
        select(Application).where(
            Application.id == application_id
        )
    )


def list_student_applications(
    db: Session,
    student_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
) -> list[Application]:
    stmt = (
        select(Application)
        .where(Application.student_id == student_id)
        .order_by(Application.applied_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(stmt).unique().all())


def list_internship_applications(
    db: Session,
    internship_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
) -> list[Application]:
    stmt = (
        select(Application)
        .where(Application.internship_id == internship_id)
        .order_by(Application.applied_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(stmt).unique().all())


def update_application_status(
    db: Session,
    application: Application,
    data: ApplicationUpdateStatus,
) -> Application:
    application.status = data.status

    if data.recruiter_notes is not None:
        application.recruiter_notes = data.recruiter_notes

    history = ApplicationStatusHistory(
        application_id=application.id,
        status=data.status,
        note=data.note,
    )

    db.add(history)

    db.commit()
    db.refresh(application)

    return application


def withdraw_application(
    db: Session,
    application: Application,
) -> Application:
    application.status = ApplicationStatus.WITHDRAWN

    history = ApplicationStatusHistory(
        application_id=application.id,
        status=ApplicationStatus.WITHDRAWN,
        note="Application withdrawn by student",
    )

    db.add(history)

    db.commit()
    db.refresh(application)

    return application