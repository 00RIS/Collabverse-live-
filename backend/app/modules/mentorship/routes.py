import uuid

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.mentorship.repositories import MentorRepository
from app.modules.mentorship.schemas import (
    MentorCapacityResponse,
    MentorDiscoveryResponse,
    MentorProfileCreate,
    MentorProfileResponse,
    MentorProfileUpdate,
    MentorshipAcceptRequest,
    MentorshipCancelRequest,
    MentorshipCompleteRequest,
    MentorshipListResponse,
    MentorshipRejectRequest,
    MentorshipRequestCreate,
    MentorshipResponse,
    MyMenteeResponse,
    MyMentorResponse,
)
from app.modules.mentorship.service import MentorService


# ============================================================
# ROUTER
# ============================================================


router = APIRouter(
    prefix="/mentorship/mentors",
    tags=["mentorship"],
)


# ============================================================
# SERVICE DEPENDENCY
# ============================================================


def get_service(
    db: Session,
) -> MentorService:
    return MentorService(
        MentorRepository(db)
    )


# ============================================================
# CREATE MENTOR PROFILE
# ============================================================


@router.post(
    "",
    response_model=MentorProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_mentor_profile(
    payload: MentorProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_service(
        db
    ).create_profile(
        current_user=current_user,
        payload=payload,
    )


# ============================================================
# GET MY MENTOR PROFILE
# ============================================================


@router.get(
    "/me",
    response_model=MentorProfileResponse,
)
def get_my_mentor_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_service(
        db
    ).get_my_profile(
        current_user=current_user,
    )


# ============================================================
# UPDATE MY MENTOR PROFILE
# ============================================================


@router.patch(
    "/me",
    response_model=MentorProfileResponse,
)
def update_my_mentor_profile(
    payload: MentorProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_service(
        db
    ).update_profile(
        current_user=current_user,
        payload=payload,
    )


# ============================================================
# DISCOVER / BROWSE MENTORS
# ============================================================


@router.get(
    "/discover",
    response_model=list[MentorDiscoveryResponse],
)
def discover_mentors(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    accepting_only: bool = Query(
        default=True,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Browse mentor profiles.

    By default only mentors currently accepting
    mentees are returned.
    """

    return get_service(
        db
    ).list_mentors(
        current_user=current_user,
        limit=limit,
        offset=offset,
        accepting_only=accepting_only,
    )


# ============================================================
# CREATE MENTORSHIP REQUEST
# ============================================================


@router.post(
    "/requests",
    response_model=MentorshipResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_mentorship_request(
    payload: MentorshipRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a mentorship request to a mentor.
    """

    return get_service(
        db
    ).create_mentorship_request(
        current_user=current_user,
        payload=payload,
    )


# ============================================================
# SENT MENTORSHIP REQUESTS
# ============================================================


@router.get(
    "/requests/sent",
    response_model=MentorshipListResponse,
)
def get_sent_mentorship_requests(
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Requests sent by the currently authenticated user.
    """

    return get_service(
        db
    ).get_sent_requests(
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


# ============================================================
# RECEIVED MENTORSHIP REQUESTS
# ============================================================


@router.get(
    "/requests/received",
    response_model=MentorshipListResponse,
)
def get_received_mentorship_requests(
    pending_only: bool = Query(
        default=False,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Requests received by the current mentor.

    Set pending_only=true to show only requests
    that still require a decision.
    """

    return get_service(
        db
    ).get_received_requests(
        current_user=current_user,
        limit=limit,
        offset=offset,
        pending_only=pending_only,
    )


# ============================================================
# MY ACTIVE MENTORS
# ============================================================


@router.get(
    "/my-mentors",
    response_model=list[MyMentorResponse],
)
def get_my_active_mentors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Active mentors for the currently authenticated user.
    """

    return get_service(
        db
    ).get_my_mentors(
        current_user=current_user,
    )


# ============================================================
# MY ACTIVE MENTEES
# ============================================================


@router.get(
    "/my-mentees",
    response_model=list[MyMenteeResponse],
)
def get_my_active_mentees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Active mentees for the current mentor.
    """

    return get_service(
        db
    ).get_my_mentees(
        current_user=current_user,
    )


# ============================================================
# MENTORSHIP HISTORY
# ============================================================


@router.get(
    "/history",
    response_model=list[MentorshipResponse],
)
def get_mentorship_history(
    limit: int = Query(
        default=100,
        ge=1,
        le=200,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Complete mentorship history for the current user.

    Includes relationships where the current user
    participated as either mentor or mentee.
    """

    return get_service(
        db
    ).get_history(
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


# ============================================================
# GET ONE MENTORSHIP
# ============================================================


@router.get(
    "/requests/{mentorship_id}",
    response_model=MentorshipResponse,
)
def get_mentorship(
    mentorship_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get one mentorship.

    Only the mentor or mentee involved in the
    relationship can access it.
    """

    return get_service(
        db
    ).get_mentorship(
        mentorship_id=mentorship_id,
        current_user=current_user,
    )


# ============================================================
# ACCEPT MENTORSHIP REQUEST
# ============================================================


@router.post(
    "/requests/{mentorship_id}/accept",
    response_model=MentorshipResponse,
)
def accept_mentorship_request(
    mentorship_id: uuid.UUID,
    payload: MentorshipAcceptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accept a pending mentorship request.

    Only the mentor who received the request
    can perform this action.
    """

    return get_service(
        db
    ).accept_request(
        mentorship_id=mentorship_id,
        current_user=current_user,
        payload=payload,
    )


# ============================================================
# REJECT MENTORSHIP REQUEST
# ============================================================


@router.post(
    "/requests/{mentorship_id}/reject",
    response_model=MentorshipResponse,
)
def reject_mentorship_request(
    mentorship_id: uuid.UUID,
    payload: MentorshipRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reject a pending mentorship request.

    Only the requested mentor can reject it.
    """

    return get_service(
        db
    ).reject_request(
        mentorship_id=mentorship_id,
        current_user=current_user,
        payload=payload,
    )


# ============================================================
# CANCEL MENTORSHIP
# ============================================================


@router.post(
    "/requests/{mentorship_id}/cancel",
    response_model=MentorshipResponse,
)
def cancel_mentorship(
    mentorship_id: uuid.UUID,
    payload: MentorshipCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a pending request or an active mentorship.

    Only one of the mentorship participants can
    perform this action.
    """

    return get_service(
        db
    ).cancel_mentorship(
        mentorship_id=mentorship_id,
        current_user=current_user,
        payload=payload,
    )


# ============================================================
# COMPLETE MENTORSHIP
# ============================================================


@router.post(
    "/requests/{mentorship_id}/complete",
    response_model=MentorshipResponse,
)
def complete_mentorship(
    mentorship_id: uuid.UUID,
    payload: MentorshipCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark an active mentorship as completed.

    Either participant can complete the mentorship.
    """

    return get_service(
        db
    ).complete_mentorship(
        mentorship_id=mentorship_id,
        current_user=current_user,
        payload=payload,
    )


# ============================================================
# MENTOR CAPACITY
# ============================================================


@router.get(
    "/{mentor_id}/capacity",
    response_model=MentorCapacityResponse,
)
def get_mentor_capacity(
    mentor_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get mentor capacity information.

    Useful for showing availability on the frontend.
    """

    return get_service(
        db
    ).get_mentor_capacity(
        mentor_profile_id=mentor_id,
    )


# ============================================================
# GET PUBLIC MENTOR PROFILE
#
# IMPORTANT:
# Keep this dynamic route LAST.
# ============================================================


@router.get(
    "/{mentor_id}",
    response_model=MentorProfileResponse,
)
def get_mentor_profile(
    mentor_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_service(
        db
    ).get_public_profile(
        mentor_id=mentor_id,
    )