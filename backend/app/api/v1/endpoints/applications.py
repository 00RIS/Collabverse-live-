import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.applications import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationUpdateStatus,
)
from app.services.applications import (
    create_application,
    get_application_by_id,
    list_internship_applications,
    list_student_applications,
    update_application_status,
    withdraw_application,
)

router = APIRouter()


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_application_endpoint(
    student_id: uuid.UUID,
    data: ApplicationCreate,
    db: Session = Depends(get_db),
):
    return create_application(
        db=db,
        student_id=student_id,
        data=data,
    )


@router.get(
    "/student/{student_id}",
    response_model=list[ApplicationResponse],
)
def list_student_applications_endpoint(
    student_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_student_applications(
        db=db,
        student_id=student_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/internship/{internship_id}",
    response_model=list[ApplicationResponse],
)
def list_internship_applications_endpoint(
    internship_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_internship_applications(
        db=db,
        internship_id=internship_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
)
def get_application_endpoint(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    application = get_application_by_id(
        db,
        application_id,
    )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    return application


@router.put(
    "/{application_id}/status",
    response_model=ApplicationResponse,
)
def update_application_status_endpoint(
    application_id: uuid.UUID,
    data: ApplicationUpdateStatus,
    db: Session = Depends(get_db),
):
    application = get_application_by_id(
        db,
        application_id,
    )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    return update_application_status(
        db,
        application,
        data,
    )


@router.put(
    "/{application_id}/withdraw",
    response_model=ApplicationResponse,
)
def withdraw_application_endpoint(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    application = get_application_by_id(
        db,
        application_id,
    )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    return withdraw_application(
        db,
        application,
    )