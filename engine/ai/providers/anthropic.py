"""Anthropic (Claude) provider, backed by the async Anthropic SDK."""
from __future__ import annotations

import os

from ai.base import AIProvider

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 4096


class AnthropicProvider(AIProvider):
    """AIProvider backed by the Anthropic Messages API.

    Configuration (environment):
        ANTHROPIC_API_KEY   - required.
        ANTHROPIC_MODEL     - optional, defaults to ``claude-sonnet-4-6``.
        ANTHROPIC_MAX_TOKENS- optional, defaults to ``4096``.
    """

    def __init__(self) -> None:
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:  # pragma: no cover - import guard
            raise ImportError(
                "The 'anthropic' package is required for AnthropicProvider. "
                "Install it with: pip install anthropic"
            ) from exc

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

        self.model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
        self.max_tokens = int(os.environ.get("ANTHROPIC_MAX_TOKENS", DEFAULT_MAX_TOKENS))
        self._client = AsyncAnthropic(api_key=api_key)

    async def complete(self, prompt: str, system: str = None) -> str:
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            # Send the system prompt as a cacheable block. Prompt caching yields
            # large cost/latency savings when the same system prompt recurs; it
            # silently no-ops for prompts below the model's minimum cache size.
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        message = await self._client.messages.create(**kwargs)
        return "".join(block.text for block in message.content if block.type == "text")

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError(
            "Anthropic does not offer a native embeddings API. Use a dedicated "
            "embeddings provider (Anthropic recommends Voyage AI), or set "
            "AI_PROVIDER=openai / azure_openai, whose providers implement embed()."
        )
