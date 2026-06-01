"""Unit tests for the CDD-tier decision engine (Act ss28/31/32)."""
from routers.clients import _resolve_risk, compute_cdd_level


def test_simplified_for_low_risk():
    assert compute_cdd_level(risk_rating="low", foreign_pep=False) == ("simplified", None)


def test_standard_for_medium_risk():
    assert compute_cdd_level(risk_rating="medium", foreign_pep=False) == ("standard", None)


def test_enhanced_for_high_risk():
    level, reason = compute_cdd_level(risk_rating="high", foreign_pep=False)
    assert level == "enhanced"
    assert reason and "s32(a)" in reason


def test_foreign_pep_forces_enhanced_even_when_low():
    level, reason = compute_cdd_level(risk_rating="low", foreign_pep=True)
    assert level == "enhanced"
    assert reason and "Foreign PEP" in reason


def test_resolve_risk():
    assert _resolve_risk(None, True, "foreign") == "high"
    assert _resolve_risk("low", True, "foreign") == "high"  # foreign PEP overrides provided
    assert _resolve_risk("low", False, None) == "low"
    assert _resolve_risk(None, False, None) == "medium"
    assert _resolve_risk(None, True, "domestic") == "medium"  # domestic PEP not auto-high
