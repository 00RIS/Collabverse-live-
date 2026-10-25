import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.connection import ConnectionStatus


class ConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requester_id: uuid.UUID
    recipient_id: uuid.UUID
    status: ConnectionStatus
    created_at: datetime
    updated_at: datetime