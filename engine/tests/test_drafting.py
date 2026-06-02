"""Guard tests for AI-draft sanitisation: drafts must come back as plain ASCII
with no em/en dashes, smart quotes, ellipsis characters, bullets or emojis."""
from ai.drafting import _sanitize


def test_em_and_en_dashes_become_spaced_hyphen():
    assert _sanitize("layered" + chr(0x2014) + "then moved") == "layered - then moved"
    assert _sanitize("2020" + chr(0x2013) + "2021") == "2020 - 2021"


def test_smart_quotes_and_ellipsis_normalised():
    s = chr(0x201C) + "it is fine" + chr(0x201D) + chr(0x2026)
    assert _sanitize(s) == '"it is fine"...'


def test_emoji_stripped():
    assert _sanitize("flag " + chr(0x1F6A9) + " raised") == "flag raised"


def test_ascii_double_dash_collapsed():
    assert _sanitize("shell--companies") == "shell - companies"


def test_accented_letters_preserved():
    # Real names with diacritics must survive (data integrity in a lodged report).
    name = chr(0x42) + chr(0x6A) + chr(0xF6) + "rn M" + chr(0xFC) + "ller"
    assert _sanitize(name) == name


def test_plain_ascii_unchanged():
    s = "Funds moved to a high-risk jurisdiction (s32). No reasonable explanation."
    assert _sanitize(s) == s


def test_output_is_pure_ascii():
    dirty = "a" + chr(0x2014) + "b " + chr(0x1F600) + " " + chr(0x2019) + "c" + chr(0x2026)
    assert all(ord(c) < 0x80 for c in _sanitize(dirty))
