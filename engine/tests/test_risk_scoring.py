"""Unit tests for the risk-assessment scoring engine (AUSTRAC Step 2)."""
from types import SimpleNamespace

from routers.risk_assessment import (
    _basel_band,
    _country_rating,
    aggregate_overall,
    review_interval_days,
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


def test_aggregate_overall_kit_rule():
    # AUSTRAC / Law Society combined method: any High -> High; >=2 Mediums -> Medium;
    # a single Medium (or only Lows) -> Low; nothing rated -> unassessed.
    assert aggregate_overall(["low", "medium", "high"]) == "high"
    assert aggregate_overall(["medium", "medium", "low"]) == "medium"
    assert aggregate_overall(["medium", "low", "low"]) == "low"
    assert aggregate_overall(["low", "low"]) == "low"
    assert aggregate_overall(["medium"]) == "low"
    assert aggregate_overall([]) == "unassessed"


def test_review_interval_days_by_rating():
    # High yearly, Medium 2-yearly, Low (and unknown) 3-yearly.
    assert review_interval_days("high") == 365
    assert review_interval_days("medium") == 730
    assert review_interval_days("low") == 1095
    assert review_interval_days("unassessed") == 1095
    assert review_interval_days(None) == 1095


def test_basel_bands():
    # Basel AML Index: <=5.00 = low is the verified AUSTRAC/Basel boundary; the
    # 5.01-6 medium / >6 high split is an Onus banding choice.
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
