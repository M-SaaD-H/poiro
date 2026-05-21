"""Scores router: submit and retrieve scores for a round."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_current_user_id
from app.auth.models import User
from app.database import get_session
from app.scores.schemas import CreateScoreRequest, ScoreResponse
from app.scores.service import get_round_scores, submit_score

router = APIRouter(tags=["scores"])


@router.post(
    "/rounds/{round_id}/scores",
    response_model=ScoreResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_score_endpoint(
    round_id: uuid.UUID,
    body: CreateScoreRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ScoreResponse:
    """Submit a score for a participant in a round (host only)."""
    from app.ws.manager import connection_manager
    from app.rounds.models import Round

    score = await submit_score(round_id, body, current_user.id, session)
    # session.commit() owned by get_session

    round_ = await session.get(Round, round_id)
    if round_ is not None:
        await connection_manager.broadcast_to_room(
            str(round_.room_id),
            "score:submitted",
            {
                "participant_id": str(score.participant_id),
                "points": score.points,
                "is_eliminated": score.is_eliminated,
            },
        )
    return score


@router.get("/rounds/{round_id}/scores", response_model=list[ScoreResponse])
async def get_scores_endpoint(
    round_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: uuid.UUID = Depends(get_current_user_id),
) -> list[ScoreResponse]:
    """Retrieve all scores for a given round."""
    return await get_round_scores(round_id, session)
