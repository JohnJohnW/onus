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
