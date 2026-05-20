"""Score business logic: award points and optionally eliminate participants."""

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import RoundStatus
from app.rooms.models import Participant, Room
from app.rounds.models import Round
from app.scores.models import Score
from app.scores.schemas import CreateScoreRequest, ScoreResponse
from app.submissions.models import Submission

logger = logging.getLogger(__name__)


async def submit_score(
    round_id: uuid.UUID,
    body: CreateScoreRequest,
    host_id: uuid.UUID,
    session: AsyncSession,
) -> ScoreResponse:
    """Award points to a participant for a round (host only)."""
    round_ = await session.get(Round, round_id)
    if round_ is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found.")
    if round_.status != RoundStatus.scoring:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scores can only be submitted after the round has ended.",
        )

    room = await session.get(Room, round_.room_id)
    if room is None or room.host_id != host_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can submit scores.")

    # Verify participant belongs to this room
    participant = await session.get(Participant, body.participant_id)
    if participant is None or participant.room_id != room.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Participant not in this room.")

    # Find submission for this participant in this round
    submission = await session.scalar(
        select(Submission).where(
            Submission.round_id == round_id,
            Submission.participant_id == body.participant_id,
        )
    )
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No submission found for this participant in this round.",
        )

    # Prevent duplicate scoring
    existing_score = await session.scalar(
        select(Score).where(
            Score.round_id == round_id,
            Score.participant_id == body.participant_id,
        )
    )
    if existing_score is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This participant has already been scored for this round.",
        )

    score = Score(
        round_id=round_id,
        participant_id=body.participant_id,
        submission_id=submission.id,
        points=body.points,
        is_eliminated=body.is_eliminated,
        scored_by=host_id,
    )
    session.add(score)

    # Apply elimination flag
    if body.is_eliminated:
        participant.is_eliminated = True

    await session.flush()
    logger.info(
        "Score submitted: participant=%s points=%d eliminated=%s",
        body.participant_id,
        body.points,
        body.is_eliminated,
    )
    return ScoreResponse.model_validate(score)


async def get_round_scores(round_id: uuid.UUID, session: AsyncSession) -> list[ScoreResponse]:
    """Return all scores for a given round."""
    result = await session.scalars(select(Score).where(Score.round_id == round_id))
    return [ScoreResponse.model_validate(s) for s in result.all()]
