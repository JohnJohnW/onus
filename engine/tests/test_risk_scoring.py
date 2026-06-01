"""Unit tests for the risk-assessment scoring engine (AUSTRAC Step 2)."""
from types import SimpleNamespace

from routers.risk_assessment import (
    _basel_band,
    _country_rating,
    _matrix_rating,
)


def _country(**kw):
    base = dict(
        country="Test",
        basel_score=None,
        fatf_listed=False,
        sanctions_listed=False,
        prescribed_foreign_country=False,
        tax_haven=False,
        terrorism_support=False,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_inherent_matrix_step2_p28():
    # The 3x3 matrix exactly as published (Step 2 p.28).
    assert _matrix_rating("very_likely", "low") == "medium"
    assert _matrix_rating("very_likely", "medium") == "high"
    assert _matrix_rating("very_likely", "high") == "high"
    assert _matrix_rating("likely", "low") == "low"
    assert _matrix_rating("likely", "medium") == "medium"
    assert _matrix_rating("likely", "high") == "high"
    assert _matrix_rating("not_likely", "low") == "low"
    assert _matrix_rating("not_likely", "medium") == "low"
    assert _matrix_rating("not_likely", "high") == "medium"


def test_matrix_unknown_inputs_return_none():
    assert _matrix_rating(None, None) is None
    assert _matrix_rating("sometimes", "low") is None


def test_basel_bands():
    # low 0-5, medium 5.01-6, high 6.01-10 (Step 2 p.20).
    assert _basel_band(None) is None
    assert _basel_band(0) == "low"
    assert _basel_band(4.04) == "low"
    assert _basel_band(5) == "low"
    assert _basel_band(5.01) == "medium"
    assert _basel_band(6) == "medium"
    assert _basel_band(6.01) == "high"
    assert _basel_band(9.5) == "high"


def test_country_override_forces_high():
    # Any AUSTRAC high-risk trigger forces High regardless of Basel band.
    assert _country_rating(_country(basel_score=4.0, fatf_listed=True)) == "high"
    assert _country_rating(_country(basel_score=2.0, sanctions_listed=True)) == "high"
    assert _country_rating(_country(prescribed_foreign_country=True)) == "high"
    assert _country_rating(_country(tax_haven=True)) == "high"
    assert _country_rating(_country(terrorism_support=True)) == "high"


def test_country_rating_falls_back_to_basel_band():
    assert _country_rating(_country(basel_score=4.04)) == "low"
    assert _country_rating(_country(basel_score=5.75)) == "medium"
    # No score, no override -> default low.
    assert _country_rating(_country()) == "low"
