"""Guard tests for the AML/CTF program policy catalogue."""
from routers.program import POLICY_CATALOGUE


def test_catalogue_keys_unique():
    keys = [e["area_key"] for e in POLICY_CATALOGUE]
    assert len(keys) == len(set(keys)), "area_key values must be unique"


def test_catalogue_entries_well_formed():
    assert len(POLICY_CATALOGUE) >= 14
    for e in POLICY_CATALOGUE:
        assert e["area_key"] and e["title"]
        assert e["obligation_key"], f"{e['area_key']} missing obligation_key"
        assert e["act_reference"], f"{e['area_key']} missing act_reference"


def test_core_obligations_present():
    keys = {e["area_key"] for e in POLICY_CATALOGUE}
    for required in ("cdd", "smr", "sanctions", "record_keeping", "independent_evaluation"):
        assert required in keys
