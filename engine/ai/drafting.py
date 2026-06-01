"""Onus AI drafting — human-in-the-loop content generation.

These helpers ask the configured AI provider to DRAFT compliance content. The
output is always a draft for a human to review, edit and approve — Onus never
auto-approves a program or auto-lodges a report. Every draft carries a disclaimer.
"""
from __future__ import annotations

from typing import Optional

from ai.factory import get_ai_provider

DISCLAIMER = (
    "\n\n— Drafted by Onus to save you time. This is not legal advice; review and "
    "edit it before you rely on it."
)

_SYSTEM = (
    "You are Onus, an AML/CTF compliance assistant for small Australian law firms newly "
    "regulated under the Anti-Money Laundering and Counter-Terrorism Financing Act 2006 and "
    "the AML/CTF Rules 2025 (Tranche 2, in force from 1 July 2026). Write in plain, practical "
    "Australian English for a busy solicitor — concise and specific. Do not invent legal "
    "obligations; where the detail depends on the firm, say what they must decide. Never claim "
    "to be a lawyer or to give legal advice."
)


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
        "follow. 4–8 sentences. No preamble or heading — just the policy text."
    )
    text = await get_ai_provider().complete(prompt, system=_SYSTEM)
    return text.strip() + DISCLAIMER


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
        "unusual. 3–6 sentences. State only facts and the reasoning — do not add advice."
    )
    text = await get_ai_provider().complete(prompt, system=_SYSTEM)
    return text.strip() + DISCLAIMER
