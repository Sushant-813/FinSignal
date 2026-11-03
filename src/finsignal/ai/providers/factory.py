"""Provider factory initializing configured model providers (Phase 10)."""

from finsignal.ai.providers.base import BaseLLMProvider
from finsignal.ai.providers.mock import MockLLMProvider
from finsignal.core.config import Settings


def get_llm_provider(settings: Settings) -> BaseLLMProvider:
    """Return the configured AI model provider instance.

    Guarantees:
    - Only 'mock' is supported in Phase 10.
    - Unsupported provider configurations fail fast without silent fallbacks.
    """
    if settings.ai_provider == "mock":
        return MockLLMProvider()

    raise ValueError(
        f"Unsupported AI provider '{settings.ai_provider}'. "
        f"Phase 10 strictly supports only the deterministic 'mock' provider."
    )
