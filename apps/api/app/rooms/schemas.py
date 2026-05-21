"""Pydantic v2 schemas for room and participant request/response payloads."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.enums import RoomStatus


class CreateRoomRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    challenge_prompt: str = Field(min_length=10, max_length=2000)
    max_rounds: int = Field(default=3, ge=1, le=10)


class ParticipantResponse(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    joined_at: datetime
    is_eliminated: bool

    model_config = {"from_attributes": True}


class RoomResponse(BaseModel):
    id: uuid.UUID
    code: str
    title: str
    challenge_prompt: str
    host_id: uuid.UUID
    status: RoomStatus
    max_rounds: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RoomDetailResponse(RoomResponse):
    participants: list[ParticipantResponse] = []
    host_display_name: str


class RoomStateResponse(BaseModel):
    """Full snapshot of a room used for WebSocket hydration and REST polling."""

    room: RoomResponse
    participants: list[ParticipantResponse]
    active_round: "RoundResponse | None" = None  # noqa: F821
    submissions: list["SubmissionResponse"] = []  # noqa: F821
    jobs: list["GenerationJobResponse"] = []  # noqa: F821


# Avoid circular imports — these are resolved at runtime
from app.rounds.schemas import RoundResponse  # noqa: E402
from app.submissions.schemas import GenerationJobResponse, SubmissionResponse  # noqa: E402

RoomStateResponse.model_rebuild()
