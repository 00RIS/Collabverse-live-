import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.internship import Internship, InternshipSkill
from app.schemas.internships import InternshipCreate, InternshipUpdate


def create_internship(
    db: Session,
    posted_by: uuid.UUID,
    data: InternshipCreate,
) -> Internship:
    internship = Internship(
        organization_id=data.organization_id,
        posted_by=posted_by,
        title=data.title,
        description=data.description,
        domain=data.domain,
        location=data.location,
        work_mode=data.work_mode,
        internship_type=data.internship_type,
        experience_level=data.experience_level,
        is_paid=data.is_paid,
        stipend=data.stipend,
        duration_weeks=data.duration_weeks,
        openings=data.openings,
        deadline=data.deadline,
    )

    db.add(internship)
    db.flush()

    for skill_data in data.skills:
        db.add(
            InternshipSkill(
                internship_id=internship.id,
                skill_id=skill_data.skill_id,
                required_score=skill_data.required_score,
                importance_weight=skill_data.importance_weight,
                mandatory=skill_data.mandatory,
            )
        )

    db.commit()
    db.refresh(internship)

    return internship


def get_internship_by_id(
    db: Session,
    internship_id: uuid.UUID,
) -> Internship | None:
    return db.scalar(
        select(Internship).where(Internship.id == internship_id)
    )


def list_internships(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    domain: str | None = None,
    location: str | None = None,
    work_mode=None,
    internship_type=None,
    experience_level=None,
    status=None,
) -> list[Internship]:
    stmt = select(Internship)

    if domain:
        stmt = stmt.where(Internship.domain.ilike(f"%{domain}%"))

    if location:
        stmt = stmt.where(Internship.location.ilike(f"%{location}%"))

    if work_mode:
        stmt = stmt.where(Internship.work_mode == work_mode)

    if internship_type:
        stmt = stmt.where(
            Internship.internship_type == internship_type
        )

    if experience_level:
        stmt = stmt.where(
            Internship.experience_level == experience_level
        )

    if status:
        stmt = stmt.where(Internship.status == status)

    stmt = (
        stmt.order_by(Internship.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(stmt).unique().all())


def update_internship(
    db: Session,
    internship: Internship,
    data: InternshipUpdate,
) -> Internship:
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(internship, field, value)

    db.commit()
    db.refresh(internship)

    return internship


def delete_internship(
    db: Session,
    internship: Internship,
) -> None:
    db.delete(internship)
    db.commit()