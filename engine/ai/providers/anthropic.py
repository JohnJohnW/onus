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

    async def complete_structured(
        self, *, prompt: str, schema: dict, system: str = None, max_tokens: int = None
    ) -> dict:
        """Force one tool call whose input_schema is the caller's schema, then return the
        validated tool input. Forced tool use is the most broadly compatible way to get
        schema-conformant JSON from the Messages API."""
        tool = {
            "name": "emit",
            "description": "Emit the result as structured data matching the schema.",
            "input_schema": schema,
        }
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "tools": [tool],
            "tool_choice": {"type": "tool", "name": "emit"},
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = [
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ]
        message = await self._client.messages.create(**kwargs)
        for block in message.content:
            if block.type == "tool_use" and block.name == "emit":
                return block.input
        raise RuntimeError("Model did not return structured output.")

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError(
            "Anthropic does not offer a native embeddings API. Use a dedicated "
            "embeddings provider (Anthropic recommends Voyage AI), or set "
            "AI_PROVIDER=openai / azure_openai, whose providers implement embed()."
        )

    _FILES_BETA = "files-api-2025-04-14"

    async def analyze_document(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        instruction: str,
        system: str = None,
    ) -> str:
        """Upload the document to the beta Files API, ask Claude about it, then delete it.
        The file is removed immediately so a client document never lingers in the
        provider's (non zero-retention) file store."""
        import io

        uploaded = await self._client.beta.files.upload(
            file=(filename or "upload", io.BytesIO(file_bytes), content_type or "application/octet-stream"),
            extra_headers={"anthropic-beta": self._FILES_BETA},
        )
        file_id = uploaded.id
        try:
            is_image = (content_type or "").startswith("image/")
            block = {
                "type": "image" if is_image else "document",
                "source": {"type": "file", "file_id": file_id},
            }
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "betas": [self._FILES_BETA],
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": instruction}, block]}
                ],
            }
            if system:
                kwargs["system"] = [
                    {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
                ]
            message = await self._client.beta.messages.create(**kwargs)
            return "".join(b.text for b in message.content if b.type == "text")
        finally:
            try:
                await self._client.beta.files.delete(
                    file_id, extra_headers={"anthropic-beta": self._FILES_BETA}
                )
            except Exception:
                pass  # best-effort cleanup; never block the response on deletion
