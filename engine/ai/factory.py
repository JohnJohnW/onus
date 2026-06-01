"""Select and construct the configured :class:`~ai.base.AIProvider`."""
from __future__ import annotations

import os

from ai.base import AIProvider

VALID_PROVIDERS = ("anthropic", "azure_openai", "openai")


def get_ai_provider() -> AIProvider:
    """Return the AI provider configured via the ``AI_PROVIDER`` env var.

    ``AI_PROVIDER`` must be one of ``anthropic``, ``azure_openai`` or ``openai``.
    Provider SDKs are imported lazily, so only the selected provider's
    dependency needs to be installed.

    Raises:
        ValueError: if ``AI_PROVIDER`` is unset or not recognised.
    """
    provider = os.environ.get("AI_PROVIDER")
    if not provider:
        raise ValueError(
            "AI_PROVIDER environment variable is not set. "
            f"Set it to one of: {', '.join(VALID_PROVIDERS)}."
        )

    key = provider.strip().lower()
    if key == "mock":  # deterministic provider for tests / offline dev (not advertised)
        from ai.providers.mock import MockProvider

        return MockProvider()
    if key == "anthropic":
        from ai.providers.anthropic import AnthropicProvider

        return AnthropicProvider()
    if key == "azure_openai":
        from ai.providers.azure_openai import AzureOpenAIProvider

        return AzureOpenAIProvider()
    if key == "openai":
        from ai.providers.openai import OpenAIProvider

        return OpenAIProvider()

    raise ValueError(
        f"Unrecognised AI_PROVIDER '{provider}'. "
        f"Valid values: {', '.join(VALID_PROVIDERS)}."
    )
