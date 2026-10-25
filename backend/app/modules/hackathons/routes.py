import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User

from app.modules.hackathons.collectors.unstop import unstop_collector

from app.modules.hackathons.schemas import (
    ExternalHackathonCreate,
    HackathonCreate,
    HackathonListResponse,
    HackathonParticipantCreate,
    HackathonParticipantResponse,
    HackathonResponse,
    HackathonUpdate,
)

from app.modules.hackathons.service import hackathon_service


router = APIRouter(
    prefix="/hackathons",
    tags=["Hackathons"],
)


# =========================================================
# LIST HACKATHONS
# =========================================================

@router.get(
    "",
    response_model=HackathonListResponse,
)
def list_hackathons(
    db: Session = Depends(get_db),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
):
    """
    Return hackathons stored inside CollabVerse.
    """

    return hackathon_service.list_hackathons(
        db=db,
        limit=limit,
        offset=offset,
    )


# =========================================================
# SEARCH HACKATHONS
# =========================================================

@router.get(
    "/search",
    response_model=HackathonListResponse,
)
def search_hackathons(
    q: str = Query(
        ...,
        min_length=1,
        max_length=200,
    ),
    db: Session = Depends(get_db),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
):
    """
    Search hackathons by title, description,
    domain or organizer.
    """

    return hackathon_service.search_hackathons(
        db=db,
        query=q,
        limit=limit,
        offset=offset,
    )


# =========================================================
# SYNC REAL UNSTOP HACKATHONS
# =========================================================

@router.post("/sync/unstop")
def sync_unstop_hackathons(
    max_pages: int | None = Query(
        default=None,
        ge=1,
        le=50,
    ),
    per_page: int = Query(
        default=18,
        ge=1,
        le=50,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Synchronize open Unstop hackathons
    with the CollabVerse database.

    max_pages:
        empty = all available pages
        1 = first page
        2 = first two pages
        etc.
    """

    return hackathon_service.sync_unstop_hackathons(
        db=db,
        max_pages=max_pages,
        per_page=per_page,
    )
    """
    Fetch real open hackathons from Unstop
    and sync them into CollabVerse.

    Existing hackathons are updated using
    source_name + external_id / source_url
    instead of creating duplicates.

    NOTE:
    This endpoint currently requires an authenticated
    user. Later we can restrict this to admins/system
    jobs only.
    """

    try:
        external_hackathons = (
            unstop_collector.fetch_hackathons(
                page=page,
                per_page=per_page,
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Failed to fetch hackathons "
                f"from Unstop: {exc}"
            ),
        )

    created_count = 0
    updated_count = 0
    failed_count = 0

    errors: list[dict] = []

    for hackathon_data in external_hackathons:
        try:
            _, created = (
                hackathon_service.upsert_external_hackathon(
                    db=db,
                    data=hackathon_data,
                )
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        except Exception as exc:
            failed_count += 1

            errors.append(
                {
                    "external_id": (
                        hackathon_data.external_id
                    ),
                    "title": hackathon_data.title,
                    "error": str(exc),
                }
            )

    return {
        "source": "Unstop",
        "page": page,
        "per_page": per_page,
        "fetched": len(external_hackathons),
        "created": created_count,
        "updated": updated_count,
        "failed": failed_count,
        "errors": errors,
    }


# =========================================================
# CREATE COLLABVERSE HACKATHON
# =========================================================

@router.post(
    "",
    response_model=HackathonResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_hackathon(
    data: HackathonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a hackathon directly on CollabVerse.
    """

    return hackathon_service.create_hackathon(
        db=db,
        current_user=current_user,
        data=data,
    )


# =========================================================
# MANUAL EXTERNAL HACKATHON IMPORT
# =========================================================

@router.post(
    "/external/import",
)
def import_external_hackathon(
    data: ExternalHackathonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Temporary development endpoint for manually
    importing an external hackathon.

    Later this should be admin/system-only.
    """

    hackathon, created = (
        hackathon_service.upsert_external_hackathon(
            db=db,
            data=data,
        )
    )

    return {
        "created": created,
        "hackathon": HackathonResponse.model_validate(
            hackathon
        ),
    }


# =========================================================
# GET ONE HACKATHON
#
# IMPORTANT:
# Keep dynamic /{hackathon_id} routes AFTER:
#
# /search
# /sync/unstop
# /external/import
#
# =========================================================

@router.get(
    "/{hackathon_id}",
    response_model=HackathonResponse,
)
def get_hackathon(
    hackathon_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Return one hackathon by ID.
    """

    return hackathon_service.get_hackathon(
        db=db,
        hackathon_id=hackathon_id,
    )


# =========================================================
# UPDATE HACKATHON
# =========================================================

@router.patch(
    "/{hackathon_id}",
    response_model=HackathonResponse,
)
def update_hackathon(
    hackathon_id: uuid.UUID,
    data: HackathonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a CollabVerse-created hackathon.
    """

    return hackathon_service.update_hackathon(
        db=db,
        hackathon_id=hackathon_id,
        current_user=current_user,
        data=data,
    )


# =========================================================
# DEACTIVATE HACKATHON
# =========================================================

@router.delete(
    "/{hackathon_id}",
)
def deactivate_hackathon(
    hackathon_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft-delete/deactivate a hackathon.
    """

    hackathon_service.deactivate_hackathon(
        db=db,
        hackathon_id=hackathon_id,
        current_user=current_user,
    )

    return {
        "message": "Hackathon deactivated successfully."
    }


# =========================================================
# REGISTER FOR COLLABVERSE HACKATHON
# =========================================================

@router.post(
    "/{hackathon_id}/register",
    response_model=HackathonParticipantResponse,
)
def register_for_hackathon(
    hackathon_id: uuid.UUID,
    data: HackathonParticipantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register for a CollabVerse-hosted hackathon.

    External hackathons should redirect users to
    their external registration URL.
    """

    return hackathon_service.register_participant(
        db=db,
        hackathon_id=hackathon_id,
        current_user=current_user,
        data=data,
    )


# =========================================================
# WITHDRAW FROM HACKATHON
# =========================================================

@router.post(
    "/{hackathon_id}/withdraw",
    response_model=HackathonParticipantResponse,
)
def withdraw_from_hackathon(
    hackathon_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Withdraw the current user from a
    CollabVerse-hosted hackathon.
    """

    return hackathon_service.withdraw_participant(
        db=db,
        hackathon_id=hackathon_id,
        current_user=current_user,
    )