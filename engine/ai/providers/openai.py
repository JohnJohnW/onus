"""OpenAI provider, backed by the async OpenAI SDK."""
from __future__ import annotations

import os

from ai.base import AIProvider

DEFAULT_MODEL = "gpt-4o"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class OpenAIProvider(AIProvider):
    """AIProvider backed by the OpenAI Chat Completions and Embeddings APIs.

    Configuration (environment):
        OPENAI_API_KEY         - required.
        OPENAI_MODEL           - optional, defaults to ``gpt-4o``.
        OPENAI_EMBEDDING_MODEL - optional, defaults to ``text-embedding-3-small``.

    Requires the ``openai`` package (``pip install openai``).
    """

    def __init__(self) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for OpenAIProvider. "
                "Install it with: pip install openai"
            ) from exc

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")

        self.model = os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL
        self.embedding_model = (
            os.environ.get("OPENAI_EMBEDDING_MODEL") or DEFAULT_EMBEDDING_MODEL
        )
        self._client = AsyncOpenAI(api_key=api_key)

    async def complete(self, prompt: str, system: str = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = await self._client.chat.completions.create(
            model=self.model, messages=messages
        )
        return resp.choices[0].message.content or ""

    async def embed(self, text: str) -> list[float]:
        resp = await self._client.embeddings.create(
            model=self.embedding_model, input=text
        )
        return resp.data[0].embedding
