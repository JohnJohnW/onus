"""Claude Managed Agents (beta) - cloud Sessions. Anthropic only (no new vendor).

Drives a stateful agent Session in Anthropic's managed cloud sandbox via discrete HTTP
calls (a serverless function cannot hold a long event stream). This is a BETA platform
that CANNOT be exercised from CI, so:
  - it is feature-flagged (MANAGED_AGENTS_ENABLED) and off by default;
  - a deterministic mock path (AI_PROVIDER=mock) lets tests cover the orchestration;
  - the real calls are built to the documented shapes and validated live.

Phase 1 (here): a read-only review session with the firm summary passed INLINE in the
task (no custom tools). Phase 2 adds custom tools so the agent reads firm data and
proposes changes, with tool-confirmation gates. Sessions are deleted after use (they are
not zero-retention); the agent + environment are created per run and torn down too.

Residency note: the cloud sandbox is Anthropic-operated. This is disclosed in-app and is
a deliberate trade-off for the autonomous tier; the rest of Onus stays on the Messages
API + our own engine.
"""
from __future__ import annotations

import json
import os
import uuid

import httpx

_BETA = "managed-agents-2026-04-01"
_BASE = "https://api.anthropic.com/v1"
_TIMEOUT = 60.0

_SYSTEM = (
    "You are Onus's AML/CTF reviewer for a small Australian law firm. Review the risk "
    "assessment you are given and write a short periodic-review note: the current overall "
    "rating and its drivers, what to check since the last approval, and a clear "
    "recommendation. Plain Australian English, no preamble. You never approve - you "
    "prepare for the senior manager. Do not invent facts beyond what you are given."
)


def managed_agents_enabled() -> bool:
    return os.environ.get("MANAGED_AGENTS_ENABLED", "").strip().lower() in ("1", "true", "yes")


def _mock() -> bool:
    return os.environ.get("AI_PROVIDER", "").strip().lower() == "mock"


def _headers() -> dict:
    return {
        "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "anthropic-version": "2023-06-01",
        "anthropic-beta": _BETA,
        "content-type": "application/json",
    }


async def _post(client: httpx.AsyncClient, path: str, body: dict) -> dict:
    r = await client.post(f"{_BASE}{path}", headers=_headers(), json=body)
    r.raise_for_status()
    return r.json()


async def _get(client: httpx.AsyncClient, path: str) -> dict:
    r = await client.get(f"{_BASE}{path}", headers=_headers())
    r.raise_for_status()
    return r.json()


async def start_review_run(*, model: str, task: str) -> dict:
    """Create an agent + cloud environment + session and send the review task. Returns
    {agent_id, environment_id, session_id}. Phase 1: data is inline; no custom tools."""
    if _mock():
        return {"agent_id": "agent_mock", "environment_id": "env_mock", "session_id": "session_mock"}
    suffix = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        agent = await _post(
            client, "/agents", {"name": f"onus-reviewer-{suffix}", "model": model, "system": _SYSTEM}
        )
        env = await _post(
            client,
            "/environments",
            {
                "name": f"onus-env-{suffix}",
                "config": {
                    "type": "cloud",
                    "networking": {
                        "type": "limited",
                        "allow_mcp_servers": False,
                        "allow_package_managers": False,
                    },
                },
            },
        )
        session = await _post(client, "/sessions", {"agent": agent["id"], "environment_id": env["id"]})
        await _post(
            client,
            f"/sessions/{session['id']}/events",
            {"events": [{"type": "user.message", "content": [{"type": "text", "text": task}]}]},
        )
        return {"agent_id": agent["id"], "environment_id": env["id"], "session_id": session["id"]}


def _collect_text(content, out: list) -> None:
    """Pull text out of a content value that may be a string or a list of blocks."""
    if isinstance(content, str):
        out.append(content)
    elif isinstance(content, list):
        for block in content:
            if (
                isinstance(block, dict)
                and block.get("text")
                and block.get("type") not in ("thinking", "tool_use", "tool_result")
            ):
                out.append(str(block["text"]))


def _extract_text(events) -> str:
    """Permissively pull the agent's reply text from a session's event history. The exact
    beta event shape varies, so this skips user/thinking/tool/status events and collects
    text from the rest (top-level content or a nested message). If nothing is found, it
    reports the event types seen so the shape can be pinned down."""
    items = events.get("events", events) if isinstance(events, dict) else events
    if not isinstance(items, list):
        items = []
    texts: list[str] = []
    types_seen: list[str] = []
    for ev in items:
        if not isinstance(ev, dict):
            continue
        etype = str(ev.get("type", ""))
        types_seen.append(etype)
        low = etype.lower()
        if "user" in low or "status" in low:
            continue
        _collect_text(ev.get("content"), texts)
        msg = ev.get("message")
        if isinstance(msg, dict):
            _collect_text(msg.get("content"), texts)
    out = "\n".join(t.strip() for t in texts if t and t.strip()).strip()
    if out:
        return out
    uniq = ", ".join(sorted(set(t for t in types_seen if t))) or "none"
    return f"The review session finished but returned no readable text. (event types seen: {uniq})"


async def poll_review_run(session_id: str) -> dict:
    """Poll a session. Returns {done: bool, note: str|None}. Terminal when the agent's
    turn is idle/ended."""
    if _mock():
        return {
            "done": True,
            "note": "[MOCK AGENT REVIEW] Overall risk reviewed; nothing material has changed "
            "since the last approval. Recommendation: confirm as-is.",
        }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        session = await _get(client, f"/sessions/{session_id}")
        status = (session.get("status") or "").lower()
        if status not in ("idle", "terminated", "completed", "ended"):
            return {"done": False, "note": None}
        events = await _get(client, f"/sessions/{session_id}/events")
        note = _extract_text(events)
        if "no readable text" in note:
            # Temporary: surface the raw beta shapes (truncated) so the parser can be
            # pinned to the real session/events structure, then this block is removed.
            dbg = {
                "status": status,
                "session": json.dumps(session, default=str)[:1100],
                "events": json.dumps(events, default=str)[:1600],
            }
            note = note + "\n\nDEBUG (beta shapes): " + json.dumps(dbg)[:2900]
        return {"done": True, "note": note}


async def cleanup_review_run(*, session_id: str, agent_id: str, environment_id: str) -> None:
    """Best-effort teardown: delete the session (not zero-retention), then the agent and
    environment created for this run."""
    if _mock():
        return
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for path in (
            f"/sessions/{session_id}",
            f"/agents/{agent_id}",
            f"/environments/{environment_id}",
        ):
            try:
                await client.delete(f"{_BASE}{path}", headers=_headers())
            except Exception:
                pass
