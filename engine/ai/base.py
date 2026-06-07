"""Abstract interface every AI provider implements."""
from __future__ import annotations

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Provider-agnostic interface for AI completions and embeddings.

    Concrete providers live in ``ai.providers`` and are selected at runtime by
    :func:`ai.factory.get_ai_provider`. Engine code should depend on this
    interface, never on a specific provider.
    """

    @abstractmethod
    async def complete(self, prompt: str, system: str = None) -> str:
        """Return a text completion for ``prompt``, optionally guided by ``system``."""
        raise NotImplementedError

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Return an embedding vector for ``text``."""
        raise NotImplementedError

    async def analyze_document(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        instruction: str,
        system: str = None,
    ) -> str:
        """Analyze an uploaded document (PDF / image / text) and return Claude's text
        answer. Optional capability - providers that cannot read documents leave this
        unimplemented."""
        raise NotImplementedError("This provider does not support document analysis.")

    async def complete_structured(
        self,
        *,
        prompt: str,
        schema: dict,
        system: str = None,
        max_tokens: int = None,
    ) -> dict:
        """Return a JSON object conforming to ``schema`` (a JSON Schema dict). Lets the app
        render AI output as structured, interactive UI instead of free text. Optional
        capability - providers that cannot do this leave it unimplemented."""
        raise NotImplementedError("This provider does not support structured output.")
