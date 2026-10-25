"""
app/api/v1/api.py

Combines every endpoint router for API version 1 into a single router,
so app/main.py only has to include one thing.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    applications,
    assessments,
    auth,
    careers,
    connections,
    institutions,
    internships,
    organizations,
    projects,
    skills,
    student_skills,
    users,
)


api_router = APIRouter()


# Core auth/user routes
api_router.include_router(auth.router)
api_router.include_router(users.router)


# Skills
api_router.include_router(skills.router)
api_router.include_router(student_skills.router)


# Careers
api_router.include_router(careers.router)


# Connections / Networking
api_router.include_router(connections.router)


# Institutions
api_router.include_router(
    institutions.router,
    prefix="/institutions",
    tags=["institutions"],
)


# Organizations
api_router.include_router(
    organizations.router,
    prefix="/organizations",
    tags=["organizations"],
)


# Assessments
api_router.include_router(
    assessments.router,
    prefix="/assessments",
    tags=["assessments"],
)


# Projects
api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["projects"],
)


# Internships
api_router.include_router(
    internships.router,
    prefix="/internships",
    tags=["internships"],
)


# Applications
api_router.include_router(
    applications.router,
    prefix="/applications",
    tags=["applications"],
)