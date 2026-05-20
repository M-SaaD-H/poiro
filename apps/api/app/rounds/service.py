"""Round business logic: start and end rounds."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import RoomStatus, RoundStatus
from app.rooms.models import Room
from app.rounds.models import Round
from app.rounds.schemas import RoundResponse

logger = logging.getLogger(__name__)


async def start_round(
    room_id: uuid.UUID,
    host_id: uuid.UUID,
    session: AsyncSession,
) -> RoundResponse:
    """Start a new round in the given room (host only)."""
    room = await session.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")
    if room.host_id != host_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can start a round.")
    if room.status != RoomStatus.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room must be active before starting a round.",
        )

    # Ensure no currently active round
    active_count = await session.scalar(
        select(func.count(Round.id)).where(
            Round.room_id == room_id,
            Round.status.in_([RoundStatus.active, RoundStatus.scoring]),
        )
    )
    if active_count and active_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A round is already active.",
        )

    # Determine next round number
    max_round_number = await session.scalar(
        select(func.max(Round.round_number)).where(Round.room_id == room_id)
    )
    next_round_number = (max_round_number or 0) + 1

    new_round = Round(
        room_id=room_id,
        round_number=next_round_number,
        status=RoundStatus.active,
        started_at=datetime.now(timezone.utc),
    )
    session.add(new_round)
    await session.flush()
    logger.info("Round %d started in room %s", next_round_number, room_id)
    return RoundResponse.model_validate(new_round)


async def end_round(
    round_id: uuid.UUID,
    host_id: uuid.UUID,
    session: AsyncSession,
) -> RoundResponse:
    """End an active round and transition it to scoring (host only)."""
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found.")

    room = await session.get(Room, round_.room_id)
    if room is None or room.host_id != host_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can end a round.")
    if round_.status != RoundStatus.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only an active round can be ended.",
        )

    round_.status = RoundStatus.scoring
    round_.ended_at = datetime.now(timezone.utc)
    await session.flush()
    logger.info("Round %s ended", round_id)
    return RoundResponse.model_validate(round_)
