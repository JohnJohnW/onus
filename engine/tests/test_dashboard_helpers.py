from datetime import datetime, timedelta, timezone

from routers.dashboard import _days_remaining, _estimate_label


def test_estimate_label():
    assert _estimate_label(None) is None
    assert _estimate_label(0) is None
    assert _estimate_label(15) == "About 15 minutes"
    assert _estimate_label(60) == "About 1 hour"
    assert _estimate_label(120) == "About 2 hours"


def test_days_remaining():
    now = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
    assert _days_remaining(None, now) is None
    assert _days_remaining(now + timedelta(days=5), now) == 5
    assert _days_remaining(now - timedelta(days=2), now) == -2
