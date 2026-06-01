"""Deterministic mock provider — for tests and offline development.

Selected with ``AI_PROVIDER=mock``. Makes no network calls and needs no API key,
so engine tests can exercise the AI drafting paths without spending tokens.
"""
from __future__ import annotations

from ai.base import AIProvider


class MockProvider(AIProvider):
    async def complete(self, prompt: str, system: str = None) -> str:
        head = (system or "Onus").strip().splitlines()[0][:60]
        return f"[MOCK DRAFT — {head}]\n\n{prompt.strip()}"

    async def embed(self, text: str) -> list[float]:
        # Tiny deterministic vector; enough for tests, not for real retrieval.
        return [float(len(text) % 7), 1.0, 0.0]
