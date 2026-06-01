"""Unit tests for the first-independent-evaluation deadline (Transitional Rules s17)."""
from datetime import date

from routers.evaluations import _first_eval_deadline


def test_staggered_deadline_by_aan_parity():
    assert _first_eval_deadline("AAN0013") == (date(2029, 6, 30), True)  # both odd
    assert _first_eval_deadline("AAN0034") == (date(2029, 12, 31), True)  # odd, even
    assert _first_eval_deadline("AAN0046") == (date(2030, 6, 30), True)  # both even
    assert _first_eval_deadline("AAN0047") == (date(2030, 12, 31), True)  # even, odd


def test_default_until_enrolment_known():
    assert _first_eval_deadline(None) == (date(2029, 6, 30), False)
    assert _first_eval_deadline("no-digits") == (date(2029, 6, 30), False)
    assert _first_eval_deadline("7") == (date(2029, 6, 30), False)  # only one digit
