"""Unit tests for Managed Agents event-text extraction (shape-tolerant)."""
from ai.managed import _extract_text


def test_extract_text_from_agent_message():
    events = {
        "events": [
            {"type": "user.message", "content": [{"type": "text", "text": "review this"}]},
            {"type": "agent.message", "content": [{"type": "text", "text": "Overall risk is high."}]},
        ]
    }
    # the user message is skipped; the agent reply is returned.
    assert _extract_text(events) == "Overall risk is high."


def test_extract_text_skips_thinking_and_tools():
    events = [
        {"type": "agent.thinking", "content": [{"type": "thinking", "text": "hmm"}]},
        {
            "type": "agent.message",
            "content": [
                {"type": "thinking", "text": "internal"},
                {"type": "text", "text": "The note."},
            ],
        },
    ]
    assert _extract_text(events) == "The note."


def test_extract_text_nested_message_and_string_content():
    events = {"events": [{"type": "message", "message": {"content": "Plain string reply."}}]}
    assert _extract_text(events) == "Plain string reply."


def test_extract_text_real_data_container_shape():
    # The live beta returns events under "data"; the agent reply is an agent.message.
    events = {
        "data": [
            {"type": "session.status_running"},
            {"type": "session.thread_status_running", "agent_name": "onus-reviewer"},
            {"type": "user.message", "content": [{"type": "text", "text": "Review the assessment..."}]},
            {"type": "span.model_request_start"},
            {"type": "agent.thinking"},
            {"type": "agent.message", "content": [{"type": "text", "text": "AML/CTF review note."}]},
        ]
    }
    assert _extract_text(events) == "AML/CTF review note."


def test_extract_text_empty_reports_event_types():
    events = {"events": [{"type": "session.status"}, {"type": "agent.tool_use"}]}
    out = _extract_text(events)
    assert "no readable text" in out
    assert "agent.tool_use" in out
