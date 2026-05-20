"""Room business logic: creation, join, state snapshot, permission helpers."""

import logging
import random
import string
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import RoomStatus, RoundStatus
from app.rooms.models import Participant, Room
from app.rooms.schemas import (
    CreateRoomRequest,
    ParticipantResponse,
    RoomDetailResponse,
    RoomResponse,
    RoomStateResponse,
)
from app.rounds.models import Round
from app.submissions.models import GenerationJob, Submission

logger = logging.getLogger(__name__)

_JOIN_CODE_LENGTH = 6
_JOIN_CODE_CHARS = string.ascii_uppercase + string.digits


def _generate_room_code() -> str:
    return "".join(random.choices(_JOIN_CODE_CHARS, k=_JOIN_CODE_LENGTH))


async def create_room(
    body: CreateRoomRequest,
    host_id: uuid.UUID,
    session: AsyncSession,
) -> RoomResponse:
    """Create a new room owned by host_id with a unique join code."""
    # Ensure code uniqueness — retry up to 10 times
    for _ in range(10):
        code = _generate_room_code()
        existing = await session.scalar(select(Room).where(Room.code == code))
        if existing is None:
            break
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate unique room code.",
        )

    room = Room(
        code=code,
        title=body.title,
        challenge_prompt=body.challenge_prompt,
        host_id=host_id,
        status=RoomStatus.waiting,
    )
    session.add(room)
    await session.flush()
    logger.info("Room created: %s (code=%s)", room.id, room.code)
    return RoomResponse.model_validate(room)


async def get_room_by_code(code: str, session: AsyncSession) -> RoomDetailResponse:
    """Fetch a room by join code including participants and host name."""
    stmt = (
        select(Room)
        .where(Room.code == code.upper())
        .options(selectinload(Room.participants).selectinload(Participant.user))
        .options(selectinload(Room.host))
    )
    room = await session.scalar(stmt)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")

    participants = [
        ParticipantResponse(
            id=p.id,
            room_id=p.room_id,
            user_id=p.user_id,
            display_name=p.user.display_name,
            joined_at=p.joined_at,
            is_eliminated=p.is_eliminated,
        )
        for p in room.participants
    ]
    return RoomDetailResponse(
        **RoomResponse.model_validate(room).model_dump(),
        participants=participants,
        host_display_name=room.host.display_name,
    )


async def join_room(
    code: str,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> ParticipantResponse:
    """Add a user as a participant to a room identified by code."""
    stmt = (
        select(Room)
        .where(Room.code == code.upper())
        .options(selectinload(Room.host))
    )
    room = await session.scalar(stmt)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")
    if room.status == RoomStatus.completed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is already completed.")
    if room.host_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The host cannot join their own room as a participant.",
        )

    existing = await session.scalar(
        select(Participant).where(
            Participant.room_id == room.id,
            Participant.user_id == user_id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already joined this room.",
        )

    # Mark room active on first join
    if room.status == RoomStatus.waiting:
        room.status = RoomStatus.active

    from app.auth.models import User
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    participant = Participant(room_id=room.id, user_id=user_id)
    session.add(participant)
    await session.flush()
    logger.info("User %s joined room %s", user_id, room.id)

    return ParticipantResponse(
        id=participant.id,
        room_id=participant.room_id,
        user_id=participant.user_id,
        display_name=user.display_name,
        joined_at=participant.joined_at,
        is_eliminated=participant.is_eliminated,
    )


async def get_room_state(room_id: uuid.UUID, session: AsyncSession) -> RoomStateResponse:
    """Build the full room state snapshot used for WS hydration."""
    from app.rounds.schemas import RoundResponse
    from app.submissions.schemas import GenerationJobResponse, SubmissionResponse

    stmt = (
        select(Room)
        .where(Room.id == room_id)
        .options(
            selectinload(Room.participants).selectinload(Participant.user),
            selectinload(Room.rounds),
        )
    )
    room = await session.scalar(stmt)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")

    # Active round
    active_round: Round | None = next(
        (r for r in room.rounds if r.status in (RoundStatus.active, RoundStatus.scoring)),
        None,
    )

    submissions: list[SubmissionResponse] = []
    jobs: list[GenerationJobResponse] = []

    if active_round is not None:
        sub_stmt = (
            select(Submission)
            .where(Submission.round_id == active_round.id)
            .options(selectinload(Submission.generation_job))
        )
        result = await session.scalars(sub_stmt)
        for sub in result.all():
            submissions.append(SubmissionResponse.model_validate(sub))
            if sub.generation_job is not None:
                jobs.append(GenerationJobResponse.model_validate(sub.generation_job))

    participants = [
        ParticipantResponse(
            id=p.id,
            room_id=p.room_id,
            user_id=p.user_id,
            display_name=p.user.display_name,
            joined_at=p.joined_at,
            is_eliminated=p.is_eliminated,
        )
        for p in room.participants
    ]

    return RoomStateResponse(
        room=RoomResponse.model_validate(room),
        participants=participants,
        active_round=RoundResponse.model_validate(active_round) if active_round else None,
        submissions=submissions,
        jobs=jobs,
    )
