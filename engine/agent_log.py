"""Record what Onus does (or flags for a human) as AgentTask rows. These populate
the dashboard "Onus activity" feed - the visible trace of the AI GRC officer at work.

The caller owns the transaction; this only adds the row to the session."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from models import AgentTask


def record_agent_task(
    db: Session,
    firm_id,
    *,
    task_type: str,
    summary: str,
    human_action_required: bool = False,
    human_action_type: Optional[str] = None,
    input_state: Optional[dict] = None,
    output_state: Optional[dict] = None,
    status: str = "done",
) -> AgentTask:
    out = dict(output_state or {})
    out["summary"] = summary
    task = AgentTask(
        firm_id=firm_id,
        agent_type="onus",
        task_type=task_type,
        status=status,
        input_state=input_state,
        output_state=out,
        human_action_required=human_action_required,
        human_action_type=human_action_type,
    )
    db.add(task)
    return task
