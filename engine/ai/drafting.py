"""Onus AI drafting - human-in-the-loop content generation.

These helpers ask the configured AI provider to DRAFT compliance content. The
output is always a draft for a human to review, edit and approve - Onus never
auto-approves a program or auto-lodges a report. Every draft carries a disclaimer.
"""
from __future__ import annotations

import re
from typing import Optional

from ai.factory import get_ai_provider

DISCLAIMER = (
    "\n\n- Drafted by Onus to save you time. This is not legal advice; review and "
    "edit it before you rely on it."
)

_SYSTEM = (
    "You are Onus, an AML/CTF compliance assistant for small Australian law firms newly "
    "regulated under the Anti-Money Laundering and Counter-Terrorism Financing Act 2006 and "
    "the AML/CTF Rules 2025 (Tranche 2, in force from 1 July 2026). Write in plain, practical "
    "Australian English for a busy solicitor: concise and specific. Do not invent legal "
    "obligations; where the detail depends on the firm, say what they must decide. Never claim "
    "to be a lawyer or to give legal advice.\n\n"
    "Style rules, follow exactly:\n"
    "- Use only plain ASCII punctuation. Never use em dashes or en dashes. To separate or join "
    "clauses use a comma, a full stop, parentheses or a colon, never a dash.\n"
    "- No emojis, no curly or smart quotes, no special symbols.\n"
    "- Write direct, declarative sentences. No preamble, no filler, no marketing language and "
    "no cliches. Avoid words like robust, comprehensive, seamless, leverage, navigate, delve, "
    "landscape, realm, and openers like 'in today's' or 'it is important to note'.\n"
    "- Do not pad with rhetorical contrast such as 'not just X, but Y'. Make the point once.\n"
    "- Prefer specific nouns and verbs over hedging and adverbs."
)

# Non-ASCII codepoints to rewrite, expressed as integers so this source stays pure
# ASCII. Dash-like codepoints become a single spaced hyphen.
_SLOP_CHARS = {
    0x2010: "-",     # hyphen
    0x2011: "-",     # non-breaking hyphen
    0x2012: "-",     # figure dash
    0x2013: " - ",   # en dash
    0x2014: " - ",   # em dash
    0x2015: " - ",   # horizontal bar
    0x2212: "-",     # minus sign
    0x2018: "'",     # left single quote
    0x2019: "'",     # right single quote / apostrophe
    0x201C: '"',     # left double quote
    0x201D: '"',     # right double quote
    0x2026: "...",   # horizontal ellipsis
    0x00A0: " ",     # non-breaking space
    0x00B7: "-",     # middot
    0x2022: "-",     # bullet
}
# Codepoint ranges deleted entirely: emoji, dingbats, arrows, variation selectors
# and misc technical symbols.
_DROP_RANGES = (
    (0x1F000, 0x1FAFF),
    (0x2300, 0x23FF),
    (0x2190, 0x21FF),
    (0x2600, 0x27BF),
    (0x2B00, 0x2BFF),
    (0xFE00, 0xFE0F),
)


def _sanitize(text: str) -> str:
    """Force drafts to plain ASCII for the things the model tends to overuse: em or
    en dashes, smart quotes, ellipsis, bullets and emojis. Other letters (for example
    accented characters in a name) are preserved. The model is instructed to avoid
    these too, but this guarantees it."""
    out = []
    for ch in text:
        cp = ord(ch)
        if cp < 0x80:
            if cp < 0x20 and ch not in "\n\r\t":
                continue  # drop stray ASCII control chars the model occasionally emits
            out.append(ch)
        elif cp in _SLOP_CHARS:
            out.append(_SLOP_CHARS[cp])
        elif any(lo <= cp <= hi for lo, hi in _DROP_RANGES):
            continue  # drop emoji / pictographs
        else:
            out.append(ch)  # keep other characters (e.g. accented names)
    text = "".join(out)
    text = re.sub(r"-{2,}", " - ", text)    # collapse ASCII double dashes too
    text = re.sub(r"[ \t]{2,}", " ", text)  # collapse doubled spaces
    text = re.sub(r" +- +", " - ", text)    # tidy the spaced hyphen
    return text.strip()


async def draft_policy(
    *,
    title: str,
    act_reference: Optional[str],
    firm_name: Optional[str],
    risk_rating: Optional[str],
) -> str:
    ref = f" (authority: {act_reference})" if act_reference else ""
    prompt = (
        f'Draft a short AML/CTF policy section titled "{title}"{ref} for '
        f"{firm_name or 'the firm'} (overall ML/TF risk: {risk_rating or 'not yet rated'}). "
        "Cover what the policy requires, who is responsible, and the practical steps staff "
        "follow. 4-8 sentences. No preamble or heading - just the policy text."
    )
    text = await get_ai_provider().complete(prompt, system=_SYSTEM)
    return _sanitize(text) + DISCLAIMER


async def draft_smr_narrative(
    *,
    indicator: str,
    client_name: Optional[str],
    matter: Optional[str],
) -> str:
    prompt = (
        "Draft the 'grounds for suspicion' narrative for an AUSTRAC suspicious matter report. "
        f"Indicator observed: {indicator}. Client: {client_name or 'the client'}. "
        f"Matter: {matter or 'not specified'}. Explain, factually and objectively, why there "
        "are reasonable grounds to suspect, referring to the observed behaviour and why it is "
        "unusual. 3-6 sentences. State only facts and the reasoning - do not add advice."
    )
    text = await get_ai_provider().complete(prompt, system=_SYSTEM)
    return _sanitize(text) + DISCLAIMER
