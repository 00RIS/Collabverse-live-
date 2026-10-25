import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.organization import OrganizationType


class OrganizationCreate(BaseModel):
    name: str
    organization_type: OrganizationType
    industry: str | None = None
    description: str | None = None
    website: str | None = None
    email_domain: str | None = None
    city: str | None = None
    state: str | None = None
    country: str = "India"


class OrganizationUpdate(BaseModel):
    name: str | None = None
    organization_type: OrganizationType | None = None
    industry: str | None = None
    description: str | None = None
    website: str | None = None
    email_domain: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    organization_type: OrganizationType
    industry: str | None
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