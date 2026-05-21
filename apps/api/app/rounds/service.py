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

    # Auto-complete any round currently in scoring phase so the host can
    # start the next round directly from the ScoringPanel.
    scoring_round = await session.scalar(
        select(Round).where(
            Round.room_id == room_id,
            Round.status == RoundStatus.scoring,
        )
    )
    if scoring_round is not None:
        scoring_round.status = RoundStatus.completed
        await session.flush()

    # Ensure no currently active round
    active_count = await session.scalar(
        select(func.count(Round.id)).where(
            Round.room_id == room_id,
            Round.status == RoundStatus.active,
        )
    )
    if active_count and active_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A round is already active.",
        )

    # Enforce max_rounds cap — count all rounds (including just-completed one)
    total_count = await session.scalar(
        select(func.count(Round.id)).where(Round.room_id == room_id)
    )
    if total_count is not None and total_count >= room.max_rounds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"All {room.max_rounds} rounds have already been played.",
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


async def auto_end_round_if_all_submitted(
    round_id: uuid.UUID,
    session: AsyncSession,
) -> RoundResponse | None:
    """Auto-transition a round to scoring when every non-eliminated participant
    has submitted.

    Returns the updated RoundResponse if the round was ended, or None if there
    are still outstanding submissions. Safe to call multiple times — a no-op if
    the round is already in scoring/completed status.

    This is an *internal* helper — it skips the host auth check because it is
    triggered by a participant action (submitting), not a host action.
    """
    from app.rooms.models import Participant
    from app.submissions.models import Submission
    from sqlalchemy import func

    round_ = await session.get(Round, round_id)
    if round_ is None or round_.status != RoundStatus.active:
        return None

    # Count non-eliminated participants in the room
    eligible_count = await session.scalar(
        select(func.count(Participant.id)).where(
            Participant.room_id == round_.room_id,
            Participant.is_eliminated.is_(False),
        )
    )

    # Count submissions for this round
    submitted_count = await session.scalar(
        select(func.count(Submission.id)).where(
            Submission.round_id == round_id,
        )
    )

    if eligible_count is None or submitted_count is None:
        return None

    if submitted_count < eligible_count:
        # Still waiting for more submissions
        logger.debug(
            "Round %s: %d/%d submitted — not auto-ending yet",
            round_id, submitted_count, eligible_count,
        )
        return None

    # All in — transition to scoring
    round_.status = RoundStatus.scoring
    round_.ended_at = datetime.now(timezone.utc)
    await session.flush()
    logger.info(
        "Round %s auto-ended: all %d participant(s) submitted",
        round_id, submitted_count,
    )
    return RoundResponse.model_validate(round_)



async def complete_room(
    room_id: uuid.UUID,
    host_id: uuid.UUID,
    session: AsyncSession,
) -> None:
    """Mark a room as completed (host only). Called after the final round is scored."""
    room = await session.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")
    if room.host_id != host_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can complete the room.")
    if room.status == RoomStatus.completed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is already completed.")
    room.status = RoomStatus.completed
    await session.flush()
    logger.info("Room %s marked as completed", room_id)
