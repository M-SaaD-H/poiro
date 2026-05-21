"""Rounds router: round lifecycle endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.database import get_session
from app.rounds.schemas import RoundResponse
from app.rounds.service import end_round

router = APIRouter(prefix="/rounds", tags=["rounds"])


@router.post("/{round_id}/end", response_model=RoundResponse)
async def end_round_endpoint(
    round_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RoundResponse:
    """End an active round and transition it to the scoring phase (host only)."""
    from app.ws.manager import connection_manager

    round_ = await end_round(round_id, current_user.id, session)
    # session.commit() owned by get_session
    await connection_manager.broadcast_to_room(
        str(round_.room_id),
        "round:ended",
        {"round_id": str(round_.id)},
    )
    return round_

