"""OpenAI-backed AI provider using the official async SDK."""

import logging

from openai import AsyncOpenAI, APIError

from app.ai.base import AIProvider, ProviderError
from app.config import get_settings

logger = logging.getLogger(__name__)

_MAX_TOKENS = 512
_TEMPERATURE = 0.85


class OpenAIProvider(AIProvider):
    """Generates text using OpenAI's gpt-4o-mini model."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    async def generate(self, user_prompt: str, challenge_context: str) -> str:
        """Call the OpenAI chat completions API and return the generated text.

        Args:
            user_prompt: The participant's submitted prompt.
            challenge_context: Used as the system message to provide challenge context.

        Raises:
            ProviderError: Wraps any OpenAI API error.
        """
        system_message = (
            f"You are a creative AI assistant participating in a creative battle challenge.\n\n"
            f"Challenge context: {challenge_context}\n\n"
            "Generate a compelling, creative, and well-crafted response to the user's prompt. "
            "Be original, thoughtful, and showcase genuine creativity."
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=_MAX_TOKENS,
                temperature=_TEMPERATURE,
            )
            content = response.choices[0].message.content
            if content is None:
                raise ProviderError("OpenAI returned an empty response.")
            return content
        except APIError as exc:
            logger.error("OpenAI API error: %s", exc)
            raise ProviderError(f"OpenAI API error: {exc}") from exc
