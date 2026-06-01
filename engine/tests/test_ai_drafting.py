"""Unit tests for Onus AI drafting (using the deterministic mock provider)."""
import asyncio

from ai.drafting import DISCLAIMER, draft_policy, draft_smr_narrative
from ai.factory import get_ai_provider


def test_mock_provider_selected(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    assert type(get_ai_provider()).__name__ == "MockProvider"


def test_draft_policy_includes_context_and_disclaimer(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    out = asyncio.run(
        draft_policy(
            title="Customer due diligence",
            act_reference="Act s26F",
            firm_name="Acme Legal",
            risk_rating="high",
        )
    )
    # The mock echoes the prompt, so the context must be present...
    assert "Customer due diligence" in out
    assert "Acme Legal" in out
    # ...and every draft carries the disclaimer.
    assert "Drafted by Onus" in out
    assert "not legal advice" in out
    assert out.endswith(DISCLAIMER)


def test_draft_smr_narrative_includes_indicator_and_disclaimer(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    out = asyncio.run(
        draft_smr_narrative(
            indicator="trust account layering",
            client_name="Watch Trust",
            matter="conveyancing settlement",
        )
    )
    assert "trust account layering" in out
    assert "not legal advice" in out
