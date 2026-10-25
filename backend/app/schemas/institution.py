import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.institution import InstitutionType


class InstitutionCreate(BaseModel):
    name: str
    institution_type: InstitutionType
    description: str | None = None
    website: str | None = None
    email_domain: str | None = None
    city: str | None = None
    state: str | None = None
    country: str = "India"


class InstitutionUpdate(BaseModel):
    name: str | None = None
    institution_type: InstitutionType | None = None
    description: str | None = None
    website: str | None = None
    email_domain: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None


class InstitutionResponse(BaseModel):
    id: uuid.UUID
    name: str
    institution_type: InstitutionType
    description: str | None
    website: str | None
    email_domain: str | None
    city: str | None
    state: str | None
    country: str
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)