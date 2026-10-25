import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.institution import Institution
from app.schemas.institution import InstitutionCreate, InstitutionUpdate


def create_institution(
    db: Session,
    data: InstitutionCreate,
) -> Institution:

    institution = Institution(
        name=data.name,
        institution_type=data.institution_type,
        description=data.description,
        website=data.website,
        email_domain=data.email_domain,
        city=data.city,
        state=data.state,
        country=data.country,
    )

    db.add(institution)
    db.commit()
    db.refresh(institution)

    return institution


def get_institution_by_id(
    db: Session,
    institution_id: uuid.UUID,
) -> Institution | None:

    stmt = select(Institution).where(
        Institution.id == institution_id
    )

    return db.scalar(stmt)


def get_institution_by_name(
    db: Session,
    name: str,
) -> Institution | None:

    stmt = select(Institution).where(
        Institution.name == name
    )

    return db.scalar(stmt)


def list_institutions(
    db: Session,
    skip: int = 0,
    limit: int = 20,
) -> list[Institution]:

    stmt = (
        select(Institution)
        .order_by(Institution.name)
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(stmt).all())


def update_institution(
    db: Session,
    institution: Institution,
    data: InstitutionUpdate,
) -> Institution:

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(institution, field, value)

    db.commit()
    db.refresh(institution)

    return institution


def delete_institution(
    db: Session,
    institution: Institution,
) -> None:

    db.delete(institution)
    db.commit()