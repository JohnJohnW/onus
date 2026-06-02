"""Sanctions name matching: pure, deterministic, recall-favouring.

Given a query name and the active list's entries, this surfaces candidate matches
for a human to adjudicate. It never auto-clears or auto-blocks - it only ranks.
Recall matters more than precision here (a missed sanctioned party is far worse
than a false positive a human dismisses), so the threshold is deliberately loose.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable

DEFAULT_THRESHOLD = 0.5


def normalize_name(value: str | None) -> str:
    """Lowercase, strip diacritics and punctuation, collapse whitespace. So
    'Bjorn Muller', 'Bjoern Mueller' (no) and 'Bjorn  Muller!' normalize alike,
    and accented source names match their unaccented query forms."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = stripped.lower()
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def name_score(query: str, candidate: str) -> float:
    """A 0.0-1.0 similarity. Exact normalized match is 1.0. Otherwise a blend of
    token containment (how much of the query the candidate covers) and Jaccard, so
    a full name that is a subset of a longer listed name (extra middle names) still
    scores high, while unrelated names score near zero."""
    q = normalize_name(query)
    c = normalize_name(candidate)
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    qt = set(q.split())
    ct = set(c.split())
    inter = len(qt & ct)
    if inter == 0:
        return 0.0
    containment = inter / len(qt)
    jaccard = inter / len(qt | ct)
    return round(0.6 * containment + 0.4 * jaccard, 3)


def screen(query: str, entries: Iterable[dict], threshold: float = DEFAULT_THRESHOLD) -> list[dict]:
    """entries: dicts carrying at least 'search_names' (a list of normalized names,
    primary + aliases) plus display fields. Returns the entries scoring at or above
    the threshold, best first, each annotated with 'score' and 'matched_name'."""
    if not normalize_name(query):
        return []
    matches: list[dict] = []
    for entry in entries:
        best, best_name = 0.0, ""
        for candidate in entry.get("search_names") or []:
            current = name_score(query, candidate)
            if current > best:
                best, best_name = current, candidate
        if best >= threshold:
            matches.append({**entry, "score": best, "matched_name": best_name})
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches
