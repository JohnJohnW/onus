"""Onus AI drafting - human-in-the-loop content generation.

These helpers ask the configured AI provider to DRAFT compliance content. The
output is always a draft for a human to review, edit and approve - Onus never
auto-approves a program or auto-lodges a report. Every draft carries a disclaimer.
"""
from __future__ import annotations

import json
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
    "- Prefer specific nouns and verbs over hedging and adverbs.\n"
    "- Structure for fast scanning: use short markdown section headings written as "
    "'## Heading', bullet points starting with '- ', and **bold** for key terms or labels. "
    "Prefer a few labelled bullets over one long paragraph. Do not add a top-level title or a "
    "sign-off. For a flowing narrative (such as a grounds-for-suspicion statement), write prose "
    "instead of bullets."
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


def _fmt_factors(label: str, items: list[tuple[str, str]]) -> str:
    if not items:
        return f"{label}: none recorded."
    joined = "; ".join(f"{name} ({rating})" for name, rating in items)
    return f"{label}: {joined}."


def _sanitize_structure(obj):
    """Recursively ASCII-sanitize every string value in a structured AI result."""
    if isinstance(obj, str):
        return _sanitize(obj)
    if isinstance(obj, list):
        return [_sanitize_structure(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _sanitize_structure(v) for k, v in obj.items()}
    return obj


_REVIEW_ACTION_KEYS = {
    "approve_assessment",
    "rerun_review",
    "draft_summary",
    "update_assessment",
    "review_clients",
    "open_program",
    "none",
}

REVIEW_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "overall_rating": {"type": "string", "enum": ["low", "medium", "high", "unassessed"]},
        "headline": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "severity": {"type": "string", "enum": ["high", "medium", "low", "info"]},
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "action_key": {
                        "type": "string",
                        "enum": [
                            "approve_assessment",
                            "rerun_review",
                            "draft_summary",
                            "update_assessment",
                            "review_clients",
                            "open_program",
                            "none",
                        ],
                    },
                },
                "required": ["severity", "title", "detail", "action_key"],
            },
        },
        "checks": {"type": "array", "items": {"type": "string"}},
        "recommendation": {"type": "string"},
    },
    "required": [
        "overall_rating",
        "headline",
        "findings",
        "checks",
        "recommendation",
    ],
}


async def generate_review(
    *,
    firm_name: Optional[str],
    overall_rating: Optional[str],
    last_approved_on: Optional[str],
    services: list[tuple[str, str]],
    customer_types: list[tuple[str, str]],
    channels: list[tuple[str, str]],
    countries: list[tuple[str, str]],
    pf_rating: Optional[str],
) -> dict:
    """Run a periodic review and return it as structured data (rating, blended findings with
    actions, checks, recommendation) for the app to render as interactive UI."""
    since = (
        f" (last approved {last_approved_on})"
        if last_approved_on
        else " (no prior approval on record)"
    )
    lines = [
        _fmt_factors("Designated services", services),
        _fmt_factors("Customer types", customer_types),
        _fmt_factors("Delivery channels", channels),
        _fmt_factors("Countries", countries),
        f"Proliferation financing: {pf_rating or 'not yet assessed'}.",
    ]
    prompt = (
        f"Run a periodic review of {firm_name or 'the firm'}'s AML/CTF risk assessment as of "
        f"today{since}. Using only the facts below, produce a structured review:\n"
        "- overall_rating: the current overall ML/TF rating.\n"
        "- headline: one sentence on the firm's current position.\n"
        "- findings: the things that matter about the firm's ML/TF risk right now. Each finding "
        "blends the issue and its fix: a severity (high/medium/low/info), a short title, a "
        "one-line detail, and an action_key for the single best next step - chosen ONLY from: "
        "approve_assessment (confirm the assessment as-is), rerun_review, draft_summary (draft the "
        "overall summary), update_assessment (change factors or inputs), review_clients, "
        "open_program; use none if no button fits. Cover the main risk drivers AND the concrete "
        "next steps as findings - do not separate them.\n"
        "- checks: specific things to verify or update since the last approval (have the "
        "designated services, client types, delivery channels, or countries changed?).\n"
        "- recommendation: confirm the assessment as-is, or update specific factors.\n"
        "Do not invent factors beyond those listed. Facts:\n"
        + "\n".join(f"- {line}" for line in lines)
    )
    data = _sanitize_structure(
        await get_ai_provider().complete_structured(prompt=prompt, schema=REVIEW_SCHEMA, system=_SYSTEM)
    )
    # Defensive: only ever surface an allow-listed action key (forced tool use is not strictly
    # schema-validated, so a stray value must not reach the client).
    for finding in data.get("findings") or []:
        if finding.get("action_key") not in _REVIEW_ACTION_KEYS:
            finding["action_key"] = "none"
    return data


async def draft_risk_assessment_summary(
    *,
    firm_name: Optional[str],
    overall_rating: Optional[str],
    services: list[tuple[str, str]],
    customer_types: list[tuple[str, str]],
    channels: list[tuple[str, str]],
    countries: list[tuple[str, str]],
    pf_rating: Optional[str],
) -> str:
    """Draft the overall narrative of a firm's AML/CTF risk assessment from its assessed
    factors. A draft for the senior manager to review - Onus never approves the
    assessment."""
    lines = [
        _fmt_factors("Designated services", services),
        _fmt_factors("Customer types", customer_types),
        _fmt_factors("Delivery channels", channels),
        _fmt_factors("Countries", countries),
        f"Proliferation financing: {pf_rating or 'not yet assessed'}.",
    ]
    prompt = (
        "Draft the overall summary of a firm's AML/CTF risk assessment, for the senior "
        "manager to review before approving. "
        f"Firm: {firm_name or 'the firm'}. Overall ML/TF risk rating: "
        f"{overall_rating or 'not yet rated'}. The assessed factors and their inherent "
        "ratings are:\n"
        + "\n".join(f"- {line}" for line in lines)
        + "\n\nExplain in plain English why the overall rating is what it is, which "
        "factors drive it, and what that means in practice for the firm. 4-7 sentences. "
        "Do not invent factors beyond those listed. No heading - just the summary text."
    )
    text = await get_ai_provider().complete(prompt, system=_SYSTEM)
    return _sanitize(text) + DISCLAIMER


async def draft_cdd_plan(
    *,
    client_name: Optional[str],
    client_type: Optional[str],
    level: str,
    edd_reason: Optional[str],
    screening_note: str,
    parties_note: str,
) -> str:
    """Draft a customer due diligence plan for a client, for the firm to follow and
    verify. A draft for human action - Onus never completes or signs off CDD itself."""
    prompt = (
        "Draft a customer due diligence (CDD) plan a small Australian law firm will follow "
        "before acting for this client. "
        f"Client: {client_name or 'the client'} (type: {client_type or 'unspecified'}). "
        f"Required CDD level: {level}"
        + (f" - {edd_reason}" if edd_reason else "")
        + f". {screening_note} {parties_note} "
        "List the identification and verification steps the firm must complete for this "
        "client type and level: who to identify, what evidence to collect, beneficial "
        "ownership and source-of-funds/wealth checks where relevant, and any extra steps "
        "if the level is enhanced. Use a short, practical checklist. Do not invent "
        "obligations beyond standard AML/CTF CDD; the firm must verify identity itself."
    )
    text = await get_ai_provider().complete(prompt, system=_SYSTEM)
    return _sanitize(text) + DISCLAIMER


_ANALYSIS_PURPOSES = {
    "beneficial_owners": (
        "Read this document and extract the beneficial owners: each person's name, their "
        "ownership percentage if stated, and their role (director, shareholder, trustee, etc.). "
        "List them clearly. If beneficial ownership cannot be determined, say so."
    ),
    "identity": (
        "Read this identification document and extract the identity details: full name, date of "
        "birth, document type, document number, and expiry date if present. Flag anything that "
        "looks expired, inconsistent, or unreadable."
    ),
    "summary": (
        "Summarise this document in a few sentences, then flag anything relevant to AML/CTF risk: "
        "source of funds or wealth, unusual ownership structures, high-risk jurisdictions, or PEP "
        "or sanctions indicators. If nothing is notable, say so."
    ),
}


async def analyze_uploaded_document(
    *, file_bytes: bytes, filename: str, content_type: str, purpose: str
) -> str:
    """Have Onus read an uploaded document and return an extraction/summary for review."""
    instruction = _ANALYSIS_PURPOSES.get(purpose, _ANALYSIS_PURPOSES["summary"])
    instruction += (
        " Extract only what the document actually contains; do not invent details. This is a "
        "draft to help the firm, not a verified determination."
    )
    text = await get_ai_provider().analyze_document(
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
        instruction=instruction,
        system=_SYSTEM,
    )
    return _sanitize(text) + DISCLAIMER


_OWNERS_INSTRUCTION = (
    "Read this document and identify the beneficial owners (the individuals who own or "
    "control the entity). Return ONLY a JSON array, no prose, where each element is "
    '{"name": string, "ownership_pct": number or null, "role": string or null}. '
    "If you cannot determine any, return []."
)


def _parse_owners(text: str) -> list[dict]:
    """Best-effort parse of a JSON array of owners from the model's reply (tolerates
    markdown fences and surrounding prose)."""
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        data = json.loads(text[start : end + 1])
    except Exception:
        return []
    owners = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("name"):
                pct = item.get("ownership_pct")
                # bool is a subclass of int - exclude it so a JSON `true` is not read as 1.0.
                numeric_pct = isinstance(pct, (int, float)) and not isinstance(pct, bool)
                owners.append(
                    {
                        "name": str(item["name"])[:200],
                        "ownership_pct": float(pct) if numeric_pct else None,
                        "role": (str(item["role"])[:100] if item.get("role") else None),
                    }
                )
    return owners[:20]


async def extract_beneficial_owners(
    *, file_bytes: bytes, filename: str, content_type: str
) -> tuple[list[dict], str]:
    """Extract beneficial owners as structured data plus a readable summary for review."""
    raw = await get_ai_provider().analyze_document(
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
        instruction=_OWNERS_INSTRUCTION,
        system=_SYSTEM,
    )
    owners = _parse_owners(raw)
    if owners:
        lines = []
        for o in owners:
            pct = f"{o['ownership_pct']:g}%" if o.get("ownership_pct") is not None else "ownership not stated"
            role = o.get("role") or "role not stated"
            lines.append(f"- {o['name']} ({pct}, {role})")
        text = "Onus identified these beneficial owners:\n" + "\n".join(lines)
    else:
        text = "Onus could not identify beneficial owners in this document. Review it manually."
    return owners, _sanitize(text) + DISCLAIMER


def _brief_block(label: str, items: list[str]) -> str:
    body = "\n".join(f"- {i}" for i in items) if items else "- (none)"
    return f"{label}:\n{body}"


# draft_compliance_brief removed: the live brief flow is generate_brief (structured output).


_BRIEF_ACTION_KEYS = {
    "open_risk_profile",
    "review_clients",
    "open_program",
    "open_reporting",
    "open_documents",
    "none",
}

BRIEF_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "headline": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "severity": {"type": "string", "enum": ["high", "medium", "low", "info"]},
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "action_key": {
                        "type": "string",
                        "enum": [
                            "open_risk_profile",
                            "review_clients",
                            "open_program",
                            "open_reporting",
                            "open_documents",
                            "none",
                        ],
                    },
                },
                "required": ["severity", "title", "detail", "action_key"],
            },
        },
    },
    "required": ["headline", "items"],
}


async def generate_brief(
    *, firm_name: Optional[str], did: list[str], needs: list[str], deadlines: list[str]
) -> dict:
    """Structured compliance brief: a headline plus prioritised, actionable items."""
    prompt = (
        f"You are briefing the principal of {firm_name or 'the firm'} on AML/CTF compliance. "
        "Using only the facts below, produce a one-sentence headline on where things stand and a "
        "short, prioritised list of items. For each item set: severity (high if it needs action "
        "now, medium for an upcoming deadline, low or info for things already handled), a short "
        "title, a one-line detail, and an action_key for where to deal with it (open_risk_profile, "
        "review_clients, open_program, open_reporting, open_documents, or none). Focus the items "
        "on what needs attention and what is coming up. Do not invent anything; if nothing needs "
        "attention, say so in the headline and keep the item list short or reassuring.\n\n"
        + _brief_block("What Onus did recently", did)
        + "\n\n"
        + _brief_block("Needs your attention", needs)
        + "\n\n"
        + _brief_block("Upcoming deadlines", deadlines)
    )
    data = _sanitize_structure(
        await get_ai_provider().complete_structured(prompt=prompt, schema=BRIEF_SCHEMA, system=_SYSTEM)
    )
    for item in data.get("items") or []:
        if item.get("action_key") not in _BRIEF_ACTION_KEYS:
            item["action_key"] = "none"
    return data


_IDENTITY_INSTRUCTION = (
    "Read this identification document and extract the identity details. Return ONLY a JSON "
    "object, no prose, with keys: full_name (string or null), date_of_birth (string or null), "
    "document_type (string or null), document_number (string or null), expiry (string or null), "
    "notes (string - flag anything expired, inconsistent, or unreadable). If you cannot read it, "
    "set the fields to null and explain in notes."
)


def _parse_identity(text: str):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    def field(key: str):
        value = data.get(key)
        return str(value)[:200] if value not in (None, "") else None

    return {
        "full_name": field("full_name"),
        "date_of_birth": field("date_of_birth"),
        "document_type": field("document_type"),
        "document_number": field("document_number"),
        "expiry": field("expiry"),
        "notes": field("notes"),
    }


async def extract_identity(*, file_bytes: bytes, filename: str, content_type: str):
    """Extract identity details from an ID document as structured data plus a readable
    summary for review. Returns (identity_dict_or_None, summary_text)."""
    raw = await get_ai_provider().analyze_document(
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
        instruction=_IDENTITY_INSTRUCTION,
        system=_SYSTEM,
    )
    ident = _parse_identity(raw)
    if ident and not any(ident.values()):
        ident = None  # all fields null - treat as nothing extracted
    if ident:
        labels = [
            ("Name", ident.get("full_name")),
            ("Date of birth", ident.get("date_of_birth")),
            ("Document", ident.get("document_type")),
            ("Number", ident.get("document_number")),
            ("Expiry", ident.get("expiry")),
        ]
        lines = [f"- {label}: {value}" for label, value in labels if value]
        text = "Onus read this identification:\n" + "\n".join(lines)
        if ident.get("notes"):
            text += f"\n- Notes: {ident['notes']}"
    else:
        text = "Onus could not extract identity details from this document. Review it manually."
    return ident, _sanitize(text) + DISCLAIMER


# draft_review_note removed: the live review flow is generate_review (structured output).


_SOF_INSTRUCTION = (
    "Read this document and write a concise source-of-funds / source-of-wealth statement for "
    "the client file: where the funds or wealth come from, based only on this document. 1 to 3 "
    "sentences, factual. If the document does not establish a source of funds, say so plainly."
)


async def extract_source_of_funds(
    *, file_bytes: bytes, filename: str, content_type: str
) -> tuple[str, str]:
    """Extract a concise source-of-funds statement to save on the client file, plus the same
    text with the disclaimer for display. Returns (statement, display_text)."""
    raw = await get_ai_provider().analyze_document(
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
        instruction=_SOF_INSTRUCTION,
        system=_SYSTEM,
    )
    statement = _sanitize(raw).strip()
    return statement, statement + DISCLAIMER
