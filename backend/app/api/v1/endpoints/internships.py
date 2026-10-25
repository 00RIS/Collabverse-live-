import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.internship import (
    ExperienceLevel,
    InternshipStatus,
    InternshipType,
    WorkMode,
)
from app.schemas.internships import (
    InternshipCreate,
    InternshipResponse,
    InternshipUpdate,
)
from app.services.internships import (
    create_internship,
    delete_internship,
    get_internship_by_id,
    list_internships,
    update_internship,
)

router = APIRouter()


@router.post(
    "",
    response_model=InternshipResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_internship_endpoint(
    posted_by: uuid.UUID,
    data: InternshipCreate,
    db: Session = Depends(get_db),
):
    return create_internship(
        db=db,
        posted_by=posted_by,
        data=data,
    )


@router.get(
    "",
    response_model=list[InternshipResponse],
)
def list_internships_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    domain: str | None = None,
    location: str | None = None,
    work_mode: WorkMode | None = None,
    internship_type: InternshipType | None = None,
    experience_level: ExperienceLevel | None = None,
    status_filter: InternshipStatus | None = Query(
        None,
        alias="status",
    ),
    db: Session = Depends(get_db),
):
    return list_internships(
        db=db,
        skip=skip,
        limit=limit,
        domain=domain,
        location=location,
        work_mode=work_mode,
        internship_type=internship_type,
        experience_level=experience_level,
        status=status_filter,
    )


@router.get(
    "/{internship_id}",
    response_model=InternshipResponse,
)
def get_internship_endpoint(
    internship_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    internship = get_internship_by_id(
        db,
        internship_id,
    )

    if not internship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Internship not found",
        )

    return internship


@router.put(
    "/{internship_id}",
    response_model=InternshipResponse,
)
def update_internship_endpoint(
    internship_id: uuid.UUID,
    data: InternshipUpdate,
    db: Session = Depends(get_db),
):
    internship = get_internship_by_id(
        db,
        internship_id,
    )

    if not internship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Internship not found",
        )

    return update_internship(
        db,
        internship,
        data,
    )


@router.delete(
    "/{internship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_internship_endpoint(
    internship_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    internship = get_internship_by_id(
        db,
        internship_id,
    )

    if not internship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Internship not found",
        )

    delete_internship(db, internship)

    return None