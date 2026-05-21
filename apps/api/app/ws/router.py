"""WebSocket router: authenticated real-time connection endpoint."""

import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import verify_supabase_token
from app.database import AsyncSessionLocal
from app.rooms.service import get_room_state
from app.ws.manager import connection_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

_CLOSE_CODE_POLICY_VIOLATION = 1008
_CLOSE_CODE_INTERNAL_ERROR = 1011


@router.websocket("/ws/rooms/{room_id}")
async def websocket_room(
    room_id: uuid.UUID,
    websocket: WebSocket,
    token: str = "",
) -> None:
    """WebSocket endpoint for real-time room events.

    Authentication: pass JWT as query param ?token=<jwt>

    On connect:
        1. Validate JWT — close with 1008 if invalid.
        2. Register connection in ConnectionManager.
        3. Send full room state snapshot as 'room:state' event.

    On disconnect: deregister connection.
    """
    # 1. Authenticate
    if not token:
        await websocket.close(code=_CLOSE_CODE_POLICY_VIOLATION, reason="Missing authentication token.")
        return

    try:
        _user_id = await verify_supabase_token(token)
    except (JWTError, ValueError) as exc:
        logger.warning("WS auth failed for room %s: %s", room_id, exc)
        await websocket.close(code=_CLOSE_CODE_POLICY_VIOLATION, reason="Invalid authentication token.")
        return

    room_id_str = str(room_id)

    # 2. Connect
    await connection_manager.connect(room_id_str, websocket)

    # 3. Send initial room state snapshot
    try:
        async with AsyncSessionLocal() as session:
            try:
                snapshot = await get_room_state(room_id, session)
                await websocket.send_json(
                    {"event": "room:state", "data": snapshot.model_dump(mode="json")}
                )
            except Exception as exc:
                logger.error("Failed to send room state for room %s: %s", room_id, exc)
                await websocket.send_json(
                    {"event": "error", "data": {"message": "Failed to load room state."}}
                )

        # Keep connection alive — just receive (clients send via REST, not WS)
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        logger.debug("WS disconnected normally: room=%s", room_id)
    except Exception as exc:
        logger.exception("Unexpected WS error for room %s: %s", room_id, exc)
    finally:
        connection_manager.disconnect(room_id_str, websocket)
