from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))

import asyncio
import pytest

from devstream.integrations.codex.context_pipeline import ContextPipelineAdapter


class StubPre:
    async def assemble_context(self, file_path: str, content: str) -> str:
        return f"ctx:{file_path}"


class StubPost:
    def __init__(self) -> None:
        self.stored = []
        self.audit = []

    def extract_topics(self, content, file_path):
        return ["topic"]

    def extract_entities(self, content):
        return ["entity"]

    def classify_content_type(self, tool_name, tool_result, content):
        return "code"

    async def store_in_memory(self, **kwargs):
        self.stored.append(kwargs)
        return "mem-id"

    async def update_session_tracking(self, tool_name, tool_input):
        pass

    async def trigger_checkpoint_for_critical_tool(self, tool_name):
        pass

    def should_capture_bash_output(self, tool_input, tool_result):
        return True

    def should_capture_read_content(self, file_path):
        return True

    def log_capture_audit(self, **kwargs):
        self.audit.append(kwargs)


@pytest.mark.asyncio
async def test_capture_post_tool_routes_write(monkeypatch):
    adapter = ContextPipelineAdapter.__new__(ContextPipelineAdapter)
    adapter.settings = type("S", (), {"protocol_timeout_seconds": 5.0})()
    adapter.logger = type("L", (), {"warning": lambda *a, **k: None, "error": lambda *a, **k: None})()
    adapter._pre_hook = StubPre()
    stub_post = StubPost()
    adapter._post_hook = stub_post

    memory_id = await adapter.capture_post_tool(
        "Write",
        {"file_path": "src/app.py", "content": "print('x')"},
        {"success": True},
    )

    assert memory_id == "mem-id"
    assert stub_post.stored[0]["file_path"] == "src/app.py"


@pytest.mark.asyncio
async def test_capture_post_tool_routes_bash():
    adapter = ContextPipelineAdapter.__new__(ContextPipelineAdapter)
    adapter.settings = type("S", (), {"protocol_timeout_seconds": 5.0})()
    adapter.logger = type("L", (), {"warning": lambda *a, **k: None, "error": lambda *a, **k: None})()
    adapter._pre_hook = StubPre()
    stub_post = StubPost()
    adapter._post_hook = stub_post

    memory_id = await adapter.capture_post_tool(
        "Bash",
        {"command": "pytest"},
        {"output": "ok", "success": True},
    )

    assert memory_id == "mem-id"
    assert stub_post.stored[0]["operation"] == "Bash"
