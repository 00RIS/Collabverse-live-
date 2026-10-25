import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionResponse,
    InstitutionUpdate,
)
from app.services.institution import (
    create_institution,
    delete_institution,
    get_institution_by_id,
    get_institution_by_name,
    list_institutions,
    update_institution,
)

router = APIRouter()


@router.post(
    "",
    response_model=InstitutionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_institution_endpoint(
    data: InstitutionCreate,
    db: Session = Depends(get_db),
):
    existing = get_institution_by_name(db, data.name)

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Institution with this name already exists",
        )

    return create_institution(db, data)


@router.get(
    "",
    response_model=list[InstitutionResponse],
)
def list_institutions_endpoint(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_institutions(db, skip=skip, limit=limit)


@router.get(
    "/{institution_id}",
    response_model=InstitutionResponse,
)
def get_institution_endpoint(
    institution_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    institution = get_institution_by_id(db, institution_id)

    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found",
        )

    return institution


@router.put(
    "/{institution_id}",
    response_model=InstitutionResponse,
)
def update_institution_endpoint(
    institution_id: uuid.UUID,
    data: InstitutionUpdate,
    db: Session = Depends(get_db),
):
    institution = get_institution_by_id(db, institution_id)

    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found",
        )

    return update_institution(db, institution, data)


@router.delete(
    "/{institution_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_institution_endpoint(
    institution_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    institution = get_institution_by_id(db, institution_id)

    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found",
        )

    delete_institution(db, institution)

    return None