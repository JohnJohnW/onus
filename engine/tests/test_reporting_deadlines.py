"""Unit tests for the reporting deadline engine (AUSTRAC Act Pt 3)."""
from datetime import datetime, timezone

from routers.reports import _add_business_days, _compute_due


def test_add_business_days_lands_on_weekdays():
    start = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    for n in range(1, 12):
        assert _add_business_days(start, n).weekday() < 5
    # From a weekday, 5 business days = +7 calendar days (skips one weekend).
    if start.weekday() < 5:
        assert (_add_business_days(start, 5).date() - start.date()).days == 7


def test_smr_deadlines():
    t = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
    due, basis = _compute_due("smr", tf=True, lpp=False, trigger=t, period_end=None)
    assert basis == "smr_tf_24h" and (due - t).total_seconds() == 24 * 3600
    assert _compute_due("smr", tf=False, lpp=True, trigger=t, period_end=None)[1] == "smr_lpp_5bd"
    assert _compute_due("smr", tf=False, lpp=False, trigger=t, period_end=None)[1] == "smr_3bd"


def test_ttr_ifti_annual_deadlines():
    t = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
    assert _compute_due("ttr", tf=False, lpp=False, trigger=t, period_end=None)[1] == "ttr_10bd"
    assert _compute_due("ifti", tf=False, lpp=False, trigger=t, period_end=None)[1] == "ifti_10bd"
    due, basis = _compute_due("annual_compliance", tf=False, lpp=False, trigger=t, period_end="2027-06-30")
    assert basis == "annual_3mo"
    assert due.year == 2027 and due.month == 9 and due.day == 30
