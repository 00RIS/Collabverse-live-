from fastapi import (
    APIRouter,
    Depends,
    Query,
)

from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
)

from app.db.session import (
    get_db,
)

from app.models.user import User

from app.modules.recommendations.schemas import (
    HackathonRecommendationSummaryResponse,
    RecommendationSummaryResponse,
)

from app.modules.recommendations.service import (
    recommendation_service,
)


router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"],
)


# ============================================================
# PROJECT RECOMMENDATIONS
# ============================================================


@router.get(
    "/projects",
    response_model=RecommendationSummaryResponse,
)
def recommended_projects(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
    ),
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):

    return (
        recommendation_service
        .recommend_projects(
            db=db,
            current_user=current_user,
            limit=limit,
        )
    )


# ============================================================
# INTERNSHIP RECOMMENDATIONS
# ============================================================


@router.get(
    "/internships",
)
def recommended_internships(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
    ),
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):

    result = (
        recommendation_service
        .recommend_internships(
            db=db,
            current_user=current_user,
            limit=limit,
        )
    )

    for item in result.get(
        "recommendations",
        [],
    ):

        internship_id = item.get(
            "internship_id"
        )

        if internship_id is not None:

            item["internship_id"] = str(
                internship_id
            )

    return result


# ============================================================
# HACKATHON RECOMMENDATIONS
# ============================================================


@router.get(
    "/hackathons",
    response_model=(
        HackathonRecommendationSummaryResponse
    ),
)
def recommended_hackathons(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
    ),
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):

    return (
        recommendation_service
        .recommend_hackathons(
            db=db,
            current_user=current_user,
            limit=limit,
        )
    )


# ============================================================
# COMBINED RECOMMENDATIONS
# ============================================================


@router.get(
    "",
)
def recommended_opportunities(
    project_limit: int = Query(
        default=5,
        ge=1,
        le=20,
    ),
    internship_limit: int = Query(
        default=5,
        ge=1,
        le=20,
    ),
    hackathon_limit: int = Query(
        default=5,
        ge=1,
        le=20,
    ),
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        get_current_user
    ),
):

    # --------------------------------------------------------
    # PROJECTS
    # --------------------------------------------------------

    project_result = (
        recommendation_service
        .recommend_projects(
            db=db,
            current_user=current_user,
            limit=project_limit,
        )
    )

    projects = project_result.get(
        "recommendations",
        [],
    )

    for item in projects:

        project_id = item.get(
            "project_id"
        )

        if project_id is not None:

            item["project_id"] = str(
                project_id
            )

    # --------------------------------------------------------
    # INTERNSHIPS
    # --------------------------------------------------------

    internship_result = (
        recommendation_service
        .recommend_internships(
            db=db,
            current_user=current_user,
            limit=internship_limit,
        )
    )

    internships = internship_result.get(
        "recommendations",
        [],
    )

    for item in internships:

        internship_id = item.get(
            "internship_id"
        )

        if internship_id is not None:

            item["internship_id"] = str(
                internship_id
            )

    # --------------------------------------------------------
    # HACKATHONS
    # --------------------------------------------------------

    hackathon_result = (
        recommendation_service
        .recommend_hackathons(
            db=db,
            current_user=current_user,
            limit=hackathon_limit,
        )
    )

    hackathons = hackathon_result.get(
        "recommendations",
        [],
    )

    for item in hackathons:

        hackathon_id = item.get(
            "hackathon_id"
        )

        if hackathon_id is not None:

            item["hackathon_id"] = str(
                hackathon_id
            )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "projects": {
            "total": len(projects),
            "recommendations": projects,
        },

        "internships": {
            "total": len(internships),
            "recommendations": internships,
        },

        "hackathons": {
            "total": len(hackathons),
            "recommendations": hackathons,
        },
    }