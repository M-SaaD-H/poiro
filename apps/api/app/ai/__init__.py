"""Factory function for selecting the configured AI provider."""

from app.ai.base import AIProvider
from app.config import get_settings


def get_ai_provider() -> AIProvider:
    """Return the AI provider instance based on the AI_PROVIDER env setting."""
    settings = get_settings()

    if settings.ai_provider == "openai":
        from app.ai.openai_provider import OpenAIProvider
        return OpenAIProvider()

    from app.ai.mock_provider import MockProvider
    return MockProvider()
