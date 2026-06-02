"""AI matter classification: given a plain-English matter description, suggest the
designated service (AML/CTF Act s6 Tables 5-6), the customer, and the CDD tier, as a
draft for the solicitor to confirm. The hardest thing for a newly-regulated small firm
is knowing WHEN it is even captured; this turns that into a one-click suggestion.

Parsing is separated from the model call so it is testable and fails safely: if the
model does not return clean JSON, we surface no suggestion rather than guess."""
from __future__ import annotations

import json
from typing import List, Tuple

from ai.drafting import _sanitize
from ai.factory import get_ai_provider

_VALID_TIERS = {"simplified", "standard", "enhanced"}

_SYSTEM = (
    "You are Onus, an AML/CTF compliance assistant for small Australian law firms. "
    "Classify a described legal matter against the designated services in section 6 of the "
    "Anti-Money Laundering and Counter-Terrorism Financing Act 2006 (Tables 5 and 6). Decide "
    "whether providing this is a designated service, which one, who the customer is, and the "
    "customer-due-diligence tier. Respond with a SINGLE JSON object and nothing else, with keys: "
    "service_key (one of the provided keys, or null if none applies), is_designated_service "
    "(true or false), customer (short string or null), cdd_tier (one of simplified, standard, "
    "enhanced, or null), rationale (one or two plain sentences). Use only the provided service "
    "keys. If you are unsure or it is not a designated service, set service_key to null and say why."
)


def _service_menu(services: List[Tuple[str, str, str]]) -> str:
    return "\n".join(f"- {key}: {label} (customer: {customer})" for key, label, customer in services)


def parse_classification(text: str, valid_keys: set) -> dict:
    """Extract the JSON object the model returns and normalise it. Always returns a
    dict with the same keys; service_key is only kept if it is a known key."""
    result = {
        "service_key": None,
        "is_designated_service": None,
        "customer": None,
        "cdd_tier": None,
        "rationale": "",
        "parsed": False,
    }
    if not text:
        return result
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
        except Exception:
            data = None
        if isinstance(data, dict):
            key = data.get("service_key")
            result["service_key"] = key if key in valid_keys else None
            ids = data.get("is_designated_service")
            if isinstance(ids, bool):
                result["is_designated_service"] = ids
            else:
                result["is_designated_service"] = result["service_key"] is not None
            customer = data.get("customer")
            result["customer"] = _sanitize(str(customer)) if customer else None
            tier = data.get("cdd_tier")
            tier = tier.lower() if isinstance(tier, str) else None
            result["cdd_tier"] = tier if tier in _VALID_TIERS else None
            rationale = data.get("rationale")
            result["rationale"] = _sanitize(str(rationale)) if rationale else ""
            result["parsed"] = True
            return result
    # Could not parse JSON: surface the raw text as the rationale, suggest nothing.
    result["rationale"] = _sanitize(text)[:500]
    return result


async def classify_matter(*, description: str, services: List[Tuple[str, str, str]]) -> dict:
    prompt = (
        "Designated service options (key: description):\n"
        f"{_service_menu(services)}\n\n"
        f"Matter description: {description}\n\n"
        "Return the JSON object now."
    )
    text = await get_ai_provider().complete(prompt, system=_SYSTEM)
    valid_keys = {key for key, _, _ in services}
    return parse_classification(text, valid_keys)
