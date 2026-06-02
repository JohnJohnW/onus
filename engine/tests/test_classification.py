"""Tests for AI matter classification parsing. The model call is exercised end-to-end
(with the mock provider) in test_integration; here we pin the pure parser, which must
fail safe: only keep a known service key, never crash on garbage, sanitise rationale."""
from ai.classification import parse_classification

VALID = {"T5_1", "T6_1", "T6_3"}


def test_parses_clean_json():
    txt = (
        '{"service_key":"T6_1","is_designated_service":true,'
        '"customer":"the person","cdd_tier":"standard",'
        '"rationale":"Assisting a real estate transaction."}'
    )
    r = parse_classification(txt, VALID)
    assert r["service_key"] == "T6_1"
    assert r["is_designated_service"] is True
    assert r["customer"] == "the person"
    assert r["cdd_tier"] == "standard"
    assert r["parsed"] is True


def test_unknown_service_key_is_dropped():
    r = parse_classification('{"service_key":"ZZ_9","is_designated_service":true}', VALID)
    assert r["service_key"] is None


def test_json_embedded_in_prose_is_extracted():
    r = parse_classification('Sure: {"service_key":"T5_1","cdd_tier":"enhanced"} hope this helps', VALID)
    assert r["service_key"] == "T5_1"
    assert r["cdd_tier"] == "enhanced"


def test_invalid_tier_is_nulled():
    r = parse_classification('{"service_key":"T6_1","cdd_tier":"ultra"}', VALID)
    assert r["service_key"] == "T6_1"
    assert r["cdd_tier"] is None


def test_non_json_falls_back_safely():
    r = parse_classification("[MOCK DRAFT - this is not json]", VALID)
    assert r["parsed"] is False
    assert r["service_key"] is None
    assert r["rationale"]  # surfaced as rationale rather than crashing


def test_empty_input():
    r = parse_classification("", VALID)
    assert r["service_key"] is None
    assert r["parsed"] is False


def test_rationale_is_sanitised():
    txt = '{"service_key":"T6_1","rationale":"layered' + chr(0x2014) + 'then moved"}'
    r = parse_classification(txt, VALID)
    assert chr(0x2014) not in r["rationale"]
    assert " - " in r["rationale"]
