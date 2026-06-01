"""Guard tests for the suspicious-activity indicator catalogue (Risk insights section 4)."""
from routers.alerts import INDICATOR_CATALOGUE, _IND


def test_indicator_keys_unique():
    keys = [k for _g, _gl, k, _l in INDICATOR_CATALOGUE]
    assert len(keys) == len(set(keys))


def test_entries_well_formed():
    assert len(INDICATOR_CATALOGUE) >= 12
    for group, group_label, key, label in INDICATOR_CATALOGUE:
        assert group and group_label and key and label
        assert _IND[key] == (group, group_label, label)


def test_core_indicators_present():
    keys = {k for _g, _gl, k, _l in INDICATOR_CATALOGUE}
    for required in ("trust_account_layering", "structuring", "unexplained_wealth", "high_risk_jurisdiction"):
        assert required in keys
