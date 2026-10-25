import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services.organization import (
    create_organization,
    delete_organization,
    get_organization_by_id,
    get_organization_by_name,
    list_organizations,
    update_organization,
)

router = APIRouter()


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organization_endpoint(
    data: OrganizationCreate,
    db: Session = Depends(get_db),
):
    existing = get_organization_by_name(db, data.name)

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization with this name already exists",
        )

    return create_organization(db, data)


@router.get(
    "",
    response_model=list[OrganizationResponse],
)
def list_organizations_endpoint(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_organizations(db, skip=skip, limit=limit)


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
)
def get_organization_endpoint(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    organization = get_organization_by_id(db, organization_id)

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return organization


@router.put(
    "/{organization_id}",
    response_model=OrganizationResponse,
)
def update_organization_endpoint(
    organization_id: uuid.UUID,
    data: OrganizationUpdate,
    db: Session = Depends(get_db),
):
    organization = get_organization_by_id(db, organization_id)

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return update_organization(db, organization, data)


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_organization_endpoint(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    organization = get_organization_by_id(db, organization_id)

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    delete_organization(db, organization)

    return None