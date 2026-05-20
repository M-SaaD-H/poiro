"""Pydantic v2 schemas for round request/response payloads."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.enums import RoundStatus


class RoundResponse(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    round_number: int
    status: RoundStatus
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
