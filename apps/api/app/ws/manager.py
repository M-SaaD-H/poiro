"""WebSocket connection manager: room-keyed registry for broadcasting events."""

import json
import logging
from collections import defaultdict

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by room_id.

    Connections are keyed by room_id string for efficient room-scoped broadcasts.
    """

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, room_id: str, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection for a room."""
        await websocket.accept()
        self._connections[room_id].append(websocket)
        logger.info("WS connected: room=%s total=%d", room_id, len(self._connections[room_id]))

    def disconnect(self, room_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket from the room registry."""
        connections = self._connections.get(room_id, [])
        if websocket in connections:
            connections.remove(websocket)
        logger.info("WS disconnected: room=%s remaining=%d", room_id, len(connections))

    async def broadcast_to_room(self, room_id: str, event: str, data: dict) -> None:
        """Send a JSON event to all connected clients in a room.

        Silently removes any dead connections encountered during broadcast.
        """
        message = json.dumps({"event": event, "data": data})
        connections = self._connections.get(room_id, [])
        dead: list[WebSocket] = []

        for websocket in list(connections):
            if websocket.client_state == WebSocketState.DISCONNECTED:
                dead.append(websocket)
                continue
            try:
                await websocket.send_text(message)
            except Exception as exc:
                logger.warning("Failed to send to WS in room %s: %s", room_id, exc)
                dead.append(websocket)

        for websocket in dead:
            self.disconnect(room_id, websocket)


# Module-level singleton shared across the application
connection_manager = ConnectionManager()
