"""Abstract base class for AI generation providers."""

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Raised when an AI provider fails to generate a response."""


class AIProvider(ABC):
    """Abstract interface for AI text generation providers."""

    @abstractmethod
    async def generate(self, user_prompt: str, challenge_context: str) -> str:
        """Generate a creative response given a user prompt and challenge context.

        Args:
            user_prompt: The participant's submitted creative prompt.
            challenge_context: The room's challenge description used as system context.

        Returns:
            The generated text output.

        Raises:
            ProviderError: If the generation fails for any reason.
        """
        ...
