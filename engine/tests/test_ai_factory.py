import pytest

from ai.base import AIProvider
from ai.factory import get_ai_provider


def test_unset_provider_raises(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    with pytest.raises(ValueError):
        get_ai_provider()


def test_unrecognised_provider_raises(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    with pytest.raises(ValueError):
        get_ai_provider()


def test_anthropic_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-dummy")
    provider = get_ai_provider()
    assert isinstance(provider, AIProvider)
    assert type(provider).__name__ == "AnthropicProvider"
