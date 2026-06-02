"""Tests for the sanctions matcher and the list parser. These cover the
safety-critical core (name matching favours recall) and the header-tolerant,
group-by-reference parsing - no DB or network required."""
from sanctions.ingest import content_hash, parse_csv, rows_to_entries
from sanctions.matching import DEFAULT_THRESHOLD, name_score, normalize_name, screen


# --- normalize_name ---

def test_normalize_strips_case_punctuation_and_diacritics():
    assert normalize_name("  Bjorn  Muller!! ") == "bjorn muller"
    # accented source name normalizes to its unaccented query form
    assert normalize_name(chr(0x42) + "j" + chr(0xF6) + "rn M" + chr(0xFC) + "ller") == "bjorn muller"


def test_normalize_empty():
    assert normalize_name(None) == ""
    assert normalize_name("") == ""


# --- name_score ---

def test_exact_match_scores_one():
    assert name_score("John Smith", "john smith") == 1.0


def test_full_name_subset_of_longer_listed_name_scores_high():
    # query is a subset of a longer listed name (extra middle name) -> should surface
    assert name_score("John Smith", "John Andrew Smith") >= DEFAULT_THRESHOLD


def test_unrelated_names_score_low():
    assert name_score("John Smith", "Maria Garcia") < DEFAULT_THRESHOLD


def test_empty_query_scores_zero():
    assert name_score("", "John Smith") == 0.0


# --- screen ---

ENTRIES = [
    {"reference": "1", "entity_type": "individual", "primary_name": "Ali Hassan",
     "search_names": ["ali hassan", "ali h hassan"], "aliases": ["Ali H Hassan"]},
    {"reference": "2", "entity_type": "entity", "primary_name": "Acme Trading Co",
     "search_names": ["acme trading co"], "aliases": []},
    {"reference": "3", "entity_type": "individual", "primary_name": "Maria Garcia",
     "search_names": ["maria garcia"], "aliases": []},
]


def test_screen_surfaces_exact_and_alias_matches():
    out = screen("Ali Hassan", ENTRIES)
    assert out and out[0]["reference"] == "1"
    assert out[0]["score"] == 1.0
    assert out[0]["matched_name"]


def test_screen_orders_by_score_desc():
    out = screen("Ali Hassan", ENTRIES)
    scores = [m["score"] for m in out]
    assert scores == sorted(scores, reverse=True)


def test_screen_excludes_unrelated():
    out = screen("Zxqv Nobody", ENTRIES)
    assert out == []


def test_screen_empty_query_returns_nothing():
    assert screen("   ", ENTRIES) == []


# --- parser (header-tolerant, group-by-reference) ---

CSV_SAMPLE = (
    "Reference,Name of Individual or Entity,Type,Date of Birth,Citizenship\n"
    "1001,John Andrew Smith,Individual,1970-01-01,Australia\n"
    "1001,Johnny Smith,Individual,,\n"  # alias row, same reference
    "1002,Acme Trading Co,Entity,,\n"
)


def test_parser_groups_aliases_by_reference():
    entries = rows_to_entries(parse_csv(CSV_SAMPLE))
    assert len(entries) == 2  # two references -> two entries
    smith = next(e for e in entries if e["reference"] == "1001")
    assert smith["primary_name"] == "John Andrew Smith"
    assert "Johnny Smith" in smith["aliases"]
    # both names are searchable (normalized)
    assert "john andrew smith" in smith["search_names"]
    assert "johnny smith" in smith["search_names"]
    assert smith["entity_type"] == "individual"
    assert smith["dob"] == "1970-01-01"


def test_parser_screening_finds_alias():
    entries = rows_to_entries(parse_csv(CSV_SAMPLE))
    # searching the alias should surface the entry
    out = screen("Johnny Smith", entries)
    assert out and out[0]["reference"] == "1001"


def test_content_hash_is_stable_and_order_independent_on_content():
    a = rows_to_entries(parse_csv(CSV_SAMPLE))
    b = rows_to_entries(parse_csv(CSV_SAMPLE))
    assert content_hash(a) == content_hash(b)
