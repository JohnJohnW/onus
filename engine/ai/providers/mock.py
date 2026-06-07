"""Deterministic mock provider - for tests and offline development.

Selected with ``AI_PROVIDER=mock``. Makes no network calls and needs no API key,
so engine tests can exercise the AI drafting paths without spending tokens.
"""
from __future__ import annotations

from ai.base import AIProvider


class MockProvider(AIProvider):
    async def complete(self, prompt: str, system: str = None) -> str:
        head = (system or "Onus").strip().splitlines()[0][:60]
        return f"[MOCK DRAFT - {head}]\n\n{prompt.strip()}"

    async def complete_structured(self, *, prompt, schema, system=None, max_tokens=None) -> dict:
        return _fake_from_schema(schema)

    async def embed(self, text: str) -> list[float]:
        # Tiny deterministic vector; enough for tests, not for real retrieval.
        return [float(len(text) % 7), 1.0, 0.0]

    async def analyze_document(
        self, *, file_bytes, filename, content_type, instruction, system=None
    ) -> str:
        if "JSON array" in instruction:  # structured extraction (e.g. beneficial owners)
            return '[{"name": "Jane Doe", "ownership_pct": 60, "role": "director"}]'
        if "JSON object" in instruction:  # structured extraction (e.g. identity)
            return (
                '{"full_name": "Jane Doe", "date_of_birth": "1980-01-01", '
                '"document_type": "passport", "document_number": "P1234567", '
                '"expiry": "2030-01-01", "notes": "Appears valid."}'
            )
        return (
            f"[MOCK ANALYSIS - {instruction[:60]}] file={filename} type={content_type} "
            f"bytes={len(file_bytes)}"
        )


def _fake_from_schema(schema: dict):
    """Build a deterministic, schema-valid object so structured-output paths work offline."""
    t = schema.get("type")
    if t == "object":
        props = schema.get("properties", {})
        required = schema.get("required") or list(props.keys())
        return {k: _fake_from_schema(props[k]) for k in required if k in props}
    if t == "array":
        return [_fake_from_schema(schema.get("items") or {"type": "string"})]
    if t == "string":
        enum = schema.get("enum")
        return enum[0] if enum else "Sample text from Onus (mock)."
    if t in ("number", "integer"):
        return 0
    if t == "boolean":
        return False
    return None
