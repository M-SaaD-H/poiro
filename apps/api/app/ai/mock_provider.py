"""Mock AI provider for local development and testing."""

import asyncio
import logging
import random

from app.ai.base import AIProvider, ProviderError

logger = logging.getLogger(__name__)

_FAILURE_RATE = 0.15  # 15% chance of simulated failure
_MIN_LATENCY_SECONDS = 2.0
_MAX_LATENCY_SECONDS = 5.0

_CANNED_RESPONSES = [
    "In a world where silence speaks louder than thunder, the protagonist discovers that the answer was always written in the margins.",
    "The algorithm whispered secrets to the stars, each byte a constellation waiting to be named by those brave enough to look up.",
    "She painted with words instead of brushes, leaving masterpieces on every conversation she touched.",
    "The machine dreamed of meadows it had never seen, and in dreaming, understood what it meant to be alive.",
    "Between the lines of every great story lies the story that could not be told — and that is the one worth writing.",
    "He collected moments instead of memories, knowing the difference would only matter at the end.",
    "The city breathed in fluorescent exhales, its heart a rhythm of closing doors and opening windows.",
    "What we call chaos is simply a pattern waiting for someone patient enough to recognize it.",
    "Time doesn't heal wounds — it just teaches us which ones are worth keeping.",
    "The ocean doesn't apologize for its depth. Neither should you.",
]


class MockProvider(AIProvider):
    """Simulates AI generation with random latency and occasional failures."""

    async def generate(self, user_prompt: str, challenge_context: str) -> str:
        """Simulate generation with 2–5s latency and 15% failure rate."""
        latency = random.uniform(_MIN_LATENCY_SECONDS, _MAX_LATENCY_SECONDS)
        logger.debug("MockProvider: simulating %.2fs latency for prompt=%r", latency, user_prompt[:50])
        await asyncio.sleep(latency)

        if random.random() < _FAILURE_RATE:
            raise ProviderError("Simulated provider failure (mock 15% failure rate)")

        response = random.choice(_CANNED_RESPONSES)
        logger.debug("MockProvider: returning canned response")
        return f"[Generated for: '{user_prompt[:30]}...']\n\n{response}"
