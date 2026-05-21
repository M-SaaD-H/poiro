"""Rooms router: CRUD room endpoints."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_current_user_id
from app.auth.models import User
from app.database import get_session
from app.rooms.schemas import CreateRoomRequest, ParticipantResponse, RoomDetailResponse, RoomResponse, RoomStateResponse
from app.rooms.service import create_room, get_room_by_code, get_room_state, join_room, leave_room
from app.rounds.service import complete_room as complete_room_service
from app.ws.manager import connection_manager

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
    # session.commit() is owned by get_session — no explicit commit needed here.

    # Broadcast real-time participant:joined event to all connected clients.
    # Include room_status so the host's store can transition waiting→active
    # without needing a page refresh.
    from app.rooms.models import Room
    room = await session.get(Room, participant.room_id)
    room_status = room.status.value if room else None

    await connection_manager.broadcast_to_room(
        str(participant.room_id),
        "participant:joined",
        {**participant.model_dump(mode="json"), "room_status": room_status},
    )

    return participant


@router.delete("/{room_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_room_endpoint(
    room_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Remove the current user from a room and notify all clients."""
    participant_id = await leave_room(room_id, current_user.id, session)
    # session.commit() owned by get_session
    await connection_manager.broadcast_to_room(
        str(room_id),
        "participant:left",
        {"participant_id": str(participant_id)},
    )


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

    round_ = await start_round(room_id, current_user.id, session)
    # session.commit() owned by get_session
    await connection_manager.broadcast_to_room(
        str(room_id),
        "round:started",
        {"round_id": str(round_.id), "round_number": round_.round_number},
    )
    return round_.model_dump(mode="json")


@router.post("/{room_id}/complete", status_code=status.HTTP_204_NO_CONTENT, tags=["rooms"])
async def complete_room_endpoint(
    room_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Mark a room as completed and broadcast to all clients (host only)."""
    await complete_room_service(room_id, current_user.id, session)
    # session.commit() owned by get_session
    await connection_manager.broadcast_to_room(
        str(room_id),
        "room:completed",
        {"room_id": str(room_id)},
    )


@router.get("/{room_id}/leaderboard", tags=["rooms"])
async def get_leaderboard_endpoint(
    room_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: uuid.UUID = Depends(get_current_user_id),
) -> list[dict]:
    """Return aggregated scores per participant across all rounds in a room."""
    from app.scores.service import get_room_leaderboard
    return await get_room_leaderboard(room_id, session)
