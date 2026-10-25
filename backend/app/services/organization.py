import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


def create_organization(
    db: Session,
    data: OrganizationCreate,
) -> Organization:
    organization = Organization(
        name=data.name,
        organization_type=data.organization_type,
        industry=data.industry,
        description=data.description,
        website=data.website,
        email_domain=data.email_domain,
        city=data.city,
        state=data.state,
        country=data.country,
    )

    db.add(organization)
    db.commit()
    db.refresh(organization)

    return organization


def get_organization_by_id(
    db: Session,
    organization_id: uuid.UUID,
) -> Organization | None:
    stmt = select(Organization).where(
        Organization.id == organization_id
    )

    return db.scalar(stmt)


def get_organization_by_name(
    db: Session,
    name: str,
) -> Organization | None:
    stmt = select(Organization).where(
        Organization.name == name
    )

    return db.scalar(stmt)


def list_organizations(
    db: Session,
    skip: int = 0,
    limit: int = 20,
) -> list[Organization]:
    stmt = (
        select(Organization)
        .order_by(Organization.name)
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(stmt).all())


def update_organization(
    db: Session,
    organization: Organization,
    data: OrganizationUpdate,
) -> Organization:
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(organization, field, value)

    db.commit()
    db.refresh(organization)

    return organization


def delete_organization(
    db: Session,
    organization: Organization,
) -> None:
    db.delete(organization)
    db.commit()