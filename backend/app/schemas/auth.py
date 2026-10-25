"""
app/schemas/auth.py

WHAT THIS FILE IS:
Pydantic models describing the *shape* of data going into and out of the
auth endpoints — separate from the SQLAlchemy models in app/models/.

WHY SCHEMAS ARE SEPARATE FROM DATABASE MODELS:
The database model (`User`) has fields like `hashed_password` that must
NEVER be sent back to a client, and doesn't have fields like a plain-text
`password` (which only ever exists for one request, never stored). If we
used the SQLAlchemy model directly as the API's input/output shape, it
would be too easy to accidentally leak a password hash in a response.
Pydantic schemas are the "public contract" of the API: FastAPI uses them
to validate incoming JSON automatically (rejecting bad requests with a
422 error before your code even runs) and to serialize outgoing
responses.
"""

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    full_name: str = Field(min_length=1, max_length=255)
    accepted_terms: bool = False
    website: str = ""

    # Role-specific fields are optional here because a single request
    # body is shared by all four roles. The endpoint logic checks `role`
    # and validates that the fields required for that role are present
    # (e.g. company_name is required when role == RECRUITER).
    institution_name: str | None = None
    company_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
