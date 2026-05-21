"""Redis Pub/Sub backplane for cross-process WebSocket broadcast.

Problem
-------
The ARQ worker runs in a separate OS process. Importing `connection_manager`
there gives a brand-new empty object — all broadcasts to it are silent no-ops.

Solution
--------
The **worker** publishes serialised events to a Redis channel
``ws:room:{room_id}``.  A subscriber coroutine running **inside the API
process** receives those messages and fans them out through the real, live
``connection_manager`` (which holds the actual WebSocket connections).

Usage
-----
API lifespan (main.py):
    task = asyncio.create_task(pubsub_listener(settings.redis_url))
    ...
    task.cancel()

ARQ tasks (jobs/tasks.py) — call the helper with a Redis client:
    async with Redis.from_url(redis_url) as r:
        await publish_room_event(r, room_id_str, "job:running", {"job_id": job_id})
"""

import asyncio
import json
import logging

from redis.asyncio import Redis

from app.ws.manager import connection_manager

logger = logging.getLogger(__name__)

_CHANNEL_PREFIX = "ws:room:"


def _channel(room_id: str) -> str:
    return f"{_CHANNEL_PREFIX}{room_id}"


async def publish_room_event(redis: Redis, room_id: str, event: str, data: dict) -> None:
    """Publish a room WebSocket event to the Redis Pub/Sub channel.

    Called by the ARQ worker (separate process) so it cannot use the
    in-process ``connection_manager`` directly.
    """
    message = json.dumps({"event": event, "data": data})
    await redis.publish(_channel(room_id), message)
    logger.debug("Published %s to channel %s", event, _channel(room_id))


async def pubsub_listener(redis_url: str) -> None:
    """Long-lived coroutine that subscribes to all room channels and fans out
    received events to connected WebSocket clients via ``connection_manager``.

    This runs as a background asyncio.Task inside the API process (started in
    the FastAPI lifespan).  It uses a pattern-subscribe on ``ws:room:*`` so
    there is a single subscriber regardless of how many rooms are active.

    Reconnects automatically if the Redis connection drops.
    """
    backoff = 1.0
    while True:
        try:
            async with Redis.from_url(redis_url, decode_responses=True) as redis:
                async with redis.pubsub() as pubsub:
                    await pubsub.psubscribe(f"{_CHANNEL_PREFIX}*")
                    logger.info("Pub/Sub listener subscribed to %s*", _CHANNEL_PREFIX)
                    backoff = 1.0  # reset on successful connect

                    async for raw in pubsub.listen():
                        if raw["type"] != "pmessage":
                            continue

                        # Extract room_id from channel name "ws:room:<room_id>"
                        channel: str = raw["channel"]
                        room_id = channel.removeprefix(_CHANNEL_PREFIX)

                        try:
                            msg = json.loads(raw["data"])
                            event: str = msg["event"]
                            data: dict = msg["data"]
                        except (json.JSONDecodeError, KeyError) as exc:
                            logger.warning("Malformed Pub/Sub message on %s: %s", channel, exc)
                            continue

                        logger.debug("Pub/Sub → WS: event=%s room=%s", event, room_id)
                        await connection_manager.broadcast_to_room(room_id, event, data)

        except asyncio.CancelledError:
            logger.info("Pub/Sub listener cancelled — shutting down.")
            return
        except Exception as exc:
            logger.error(
                "Pub/Sub listener error (reconnecting in %.0fs): %s", backoff, exc
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)
