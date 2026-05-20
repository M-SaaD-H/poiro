"""Rooms router: CRUD room endpoints."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_current_user_id
from app.auth.models import User
from app.database import get_session
from app.rooms.schemas import CreateRoomRequest, ParticipantResponse, RoomDetailResponse, RoomResponse, RoomStateResponse
from app.rooms.service import create_room, get_room_by_code, get_room_state, join_room

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room_endpoint(
    body: CreateRoomRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RoomResponse:
    """Create a new battle room. The authenticated user becomes the host."""
    return await create_room(body, current_user.id, session)


@router.get("/{code}", response_model=RoomDetailResponse)
async def get_room_endpoint(
    code: str,
    session: AsyncSession = Depends(get_session),
    _: uuid.UUID = Depends(get_current_user_id),
) -> RoomDetailResponse:
    """Fetch a room by its 6-character join code."""
    return await get_room_by_code(code, session)


@router.post("/{code}/join", response_model=ParticipantResponse, status_code=status.HTTP_201_CREATED)
async def join_room_endpoint(
    code: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ParticipantResponse:
    """Join a room as a participant using its join code."""
    participant = await join_room(code, current_user.id, session)
    return participant


@router.get("/{room_id}/state", response_model=RoomStateResponse)
async def get_room_state_endpoint(
    room_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: uuid.UUID = Depends(get_current_user_id),
) -> RoomStateResponse:
    """Return the full room state snapshot (room, participants, active round, submissions, jobs)."""
    return await get_room_state(room_id, session)


@router.post("/{room_id}/rounds/start", tags=["rounds"])
async def start_round_endpoint(
    room_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Start a new round in the room (host only)."""
    from app.rounds.service import start_round
    from app.ws.manager import connection_manager

    round_ = await start_round(room_id, current_user.id, session)
    await session.commit()
    await connection_manager.broadcast_to_room(
        str(room_id),
        "round:started",
        {"round_id": str(round_.id), "round_number": round_.round_number},
    )
    return round_.model_dump(mode="json")
