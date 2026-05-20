"""Pydantic v2 schemas for scoring request/response payloads."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateScoreRequest(BaseModel):
    participant_id: uuid.UUID
    points: int = Field(ge=0, le=100)
    is_eliminated: bool = False


class ScoreResponse(BaseModel):
    id: uuid.UUID
    round_id: uuid.UUID
    participant_id: uuid.UUID
    submission_id: uuid.UUID
    points: int
    is_eliminated: bool
    scored_by: uuid.UUID
    scored_at: datetime

    model_config = {"from_attributes": True}
