from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))

import asyncio
from dataclasses import dataclass

import pytest

from devstream.integrations.codex.dispatcher import CodexIntegrationRuntime
from devstream.integrations.codex.events import CodexEventType, normalize_event
from devstream.integrations.codex.protocol_gateway import ProtocolAssessment


class DummyProtocol:
    async def evaluate_prompt(self, user_input: str) -> ProtocolAssessment:
        return ProtocolAssessment(
            enforce_protocol="implement" in user_input.lower(),
            prompt="prompt" if "implement" in user_input.lower() else None,
            triggers=("sample",),
        )


class DummyContext:
    def __init__(self) -> None:
        self.pre_calls = []
        self.post_calls = []

    async def build_pre_context(self, file_path: str, content: str) -> str:
        self.pre_calls.append((file_path, content))
        return f"context:{file_path}"

    async def capture_post_tool(self, tool_name, tool_input, tool_result):
        self.post_calls.append((tool_name, tool_input, tool_result))
        return "memory-123"


@dataclass
class DummySession:
    started: list
    executed: list
    stopped: list

    async def on_session_start(self, session_id: str, cwd: str) -> None:
        self.started.append((session_id, cwd))

    async def on_tool_execution(self, session_id, tool_name, tool_input, tool_result):
        self.executed.append((session_id, tool_name))

    async def on_session_stop(self, session_id: str):
        self.stopped.append(session_id)
        return "summary"


@pytest.mark.asyncio
async def test_normalize_event_maps_fields():
    raw = {
        "event_type": "session_start",
        "session_id": "abc",
        "cwd": "/tmp",
    }
    event = normalize_event(raw)
    assert event.event_type is CodexEventType.SESSION_START
    assert event.session_id == "abc"
    assert event.cwd == "/tmp"


@pytest.mark.asyncio
async def test_runtime_dispatches_to_adapters():
    protocol = DummyProtocol()
    context = DummyContext()
    session = DummySession([], [], [])

    runtime = CodexIntegrationRuntime(
        protocol_adapter=protocol,
        context_adapter=context,
        session_adapter=session,
    )

    await runtime.handle_event(
        {
            "event_type": "session_start",
            "session_id": "sess-1",
            "cwd": "/repo",
        }
    )

    result_prompt = await runtime.handle_event(
        {
            "event_type": "user_prompt_submit",
            "session_id": "sess-1",
            "user_input": "Implement feature X",
        }
    )

    result_pre = await runtime.handle_event(
        {
            "event_type": "tool_pre_execute",
            "session_id": "sess-1",
            "tool_input": {"file_path": "src/app.py", "content": "print('ok')"},
        }
    )

    result_post = await runtime.handle_event(
        {
            "event_type": "tool_post_execute",
            "session_id": "sess-1",
            "tool_name": "Write",
            "tool_input": {"file_path": "src/app.py", "content": "print('ok')"},
            "tool_result": {"success": True},
        }
    )

    result_stop = await runtime.handle_event(
        {
            "event_type": "session_stop",
            "session_id": "sess-1",
        }
    )

    assert session.started == [("sess-1", "/repo")]
    assert session.executed[-1] == ("sess-1", "Write")
    assert session.stopped == ["sess-1"]
    assert result_prompt["enforce"] is True
    assert result_pre["status"] == "context_ready"
    assert result_post["status"] == "captured"
    assert result_stop["summary"] == "summary"
    assert "tool_post_execute" in runtime.get_payload_samples()
