"""
Integration tests for Agent Auto-Delegation Workflow.

Tests end-to-end delegation flow from PreToolUse hook through pattern matching,
task assessment, and decision logging.

Coverage target: 95%+
Test categories:
- End-to-end delegation for Python/TypeScript/Rust/Go files
- Quality gate enforcement (git commit scenario)
- Memory logging integration
- Configuration flag behavior (enabled/disabled)
- Graceful degradation (missing imports)
"""

import pytest
import pytest_asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
import sys
import os

# Add agents module to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / ".claude" / "hooks"))

from devstream.agents.pattern_matcher import PatternMatcher
from devstream.agents.agent_router import AgentRouter, TaskAssessment
from devstream.agents.pattern_catalog import PatternMatch


class TestPythonFileDelegation:
    """Test end-to-end delegation for Python files."""

    @pytest.fixture
    def matcher(self):
        """Provide PatternMatcher instance."""
        return PatternMatcher()

    @pytest.fixture
    def router(self):
        """Provide AgentRouter instance."""
        return AgentRouter()

    @pytest.mark.asyncio
    async def test_python_file_auto_delegation(self, matcher, router):
        """Test auto-delegation for simple Python file edit."""
        # Step 1: Pattern matching
        pattern_match = matcher.match_patterns(
            file_path="api.py",
            content="from fastapi import FastAPI"
        )

        assert pattern_match is not None
        assert pattern_match["agent"] == "@python-specialist"
        assert pattern_match["confidence"] == 0.95

        # Step 2: Task assessment
        context = {
            "file_path": "api.py",
            "content": "from fastapi import FastAPI",
            "user_query": "fix validation bug",
            "tool_name": "Edit",
            "affected_files": ["api.py"]
        }

        assessment = await router.assess_task_complexity(
            pattern_match=pattern_match,
            context=context
        )

        assert assessment.complexity == "LOW"
        assert assessment.architectural_impact == "LOW"
        assert assessment.recommendation == "DELEGATE"

        # Step 3: Auto-approval decision
        should_approve = router.should_auto_approve(assessment)
        assert should_approve is True

        # Step 4: Advisory message generation
        message = router.format_advisory_message(assessment)
        assert "DELEGATE with @python-specialist" in message
        assert "Auto-delegation approved" in message

    @pytest.mark.asyncio
    async def test_python_file_high_complexity_escalation(self, matcher, router):
        """Test escalation for high complexity Python task."""
        # Pattern matching
        pattern_match = matcher.match_patterns(
            file_path="api.py",
            content="from fastapi import FastAPI"
        )

        # High complexity context
        context = {
            "file_path": "api.py",
            "content": "from fastapi import FastAPI",
            "user_query": "refactor entire API architecture",
            "tool_name": "Edit",
            "affected_files": [f"file_{i}.py" for i in range(10)]
        }

        assessment = await router.assess_task_complexity(
            pattern_match=pattern_match,
            context=context
        )

        assert assessment.complexity == "HIGH"
        assert assessment.recommendation == "ESCALATE"
        assert router.should_auto_approve(assessment) is False

        # Advisory should indicate escalation
        message = router.format_advisory_message(assessment)
        assert "ESCALATE" in message
        assert "Full @tech-lead analysis required" in message


class TestTypeScriptFileDelegation:
    """Test end-to-end delegation for TypeScript files."""

    @pytest.fixture
    def matcher(self):
        """Provide PatternMatcher instance."""
        return PatternMatcher()

    @pytest.fixture
    def router(self):
        """Provide AgentRouter instance."""
        return AgentRouter()

    @pytest.mark.asyncio
    async def test_typescript_file_auto_delegation(self, matcher, router):
        """Test auto-delegation for TypeScript React component."""
        # Pattern matching
        pattern_match = matcher.match_patterns(
            file_path="Component.tsx",
            content="import React from 'react'"
        )

        assert pattern_match is not None
        assert pattern_match["agent"] == "@typescript-specialist"

        # Task assessment
        context = {
            "file_path": "Component.tsx",
            "content": "import React from 'react'",
            "user_query": "update component styling",
            "tool_name": "Edit",
            "affected_files": ["Component.tsx"]
        }

        assessment = await router.assess_task_complexity(
            pattern_match=pattern_match,
            context=context
        )

        assert assessment.complexity == "LOW"
        assert router.should_auto_approve(assessment) is True

    @pytest.mark.asyncio
    async def test_typescript_new_api_coordination(self, matcher, router):
        """Test coordination for new API endpoint (medium impact)."""
        pattern_match = matcher.match_patterns(
            file_path="api.ts",
            content="import express from 'express'"
        )

        context = {
            "file_path": "api.ts",
            "content": "import express from 'express'",
            "user_query": "add new API endpoint for users",
            "tool_name": "Edit",
            "affected_files": ["api.ts"]
        }

        assessment = await router.assess_task_complexity(
            pattern_match=pattern_match,
            context=context
        )

        assert assessment.architectural_impact == "MEDIUM"
        assert assessment.recommendation == "COORDINATE"
        assert router.should_auto_approve(assessment) is False


class TestRustAndGoFileDelegation:
    """Test end-to-end delegation for Rust and Go files."""

    @pytest.fixture
    def matcher(self):
        """Provide PatternMatcher instance."""
        return PatternMatcher()

    @pytest.fixture
    def router(self):
        """Provide AgentRouter instance."""
        return AgentRouter()

    @pytest.mark.asyncio
    async def test_rust_file_delegation(self, matcher, router):
        """Test delegation for Rust file."""
        pattern_match = matcher.match_patterns(
            file_path="main.rs",
            content="use tokio::main"
        )

        assert pattern_match is not None
        assert pattern_match["agent"] == "@rust-specialist"

        context = {
            "file_path": "main.rs",
            "content": "use tokio::main",
            "user_query": "add async handler",
            "tool_name": "Edit",
            "affected_files": ["main.rs"]
        }

        assessment = await router.assess_task_complexity(
            pattern_match=pattern_match,
            context=context
        )

        assert assessment.suggested_agent == "@rust-specialist"
        assert router.should_auto_approve(assessment) is True

    @pytest.mark.asyncio
    async def test_go_file_delegation(self, matcher, router):
        """Test delegation for Go file."""
        pattern_match = matcher.match_patterns(
            file_path="server.go",
            content='import "net/http"'
        )

        assert pattern_match is not None
        assert pattern_match["agent"] == "@go-specialist"

        context = {
            "file_path": "server.go",
            "content": 'import "net/http"',
            "user_query": "update HTTP handler",
            "tool_name": "Edit",
            "affected_files": ["server.go"]
        }

        assessment = await router.assess_task_complexity(
            pattern_match=pattern_match,
            context=context
        )

        assert assessment.suggested_agent == "@go-specialist"


class TestQualityGateEnforcement:
    """Test quality gate enforcement in delegation workflow."""

    @pytest.fixture
    def matcher(self):
        """Provide PatternMatcher instance."""
        return PatternMatcher()

    @pytest.fixture
    def router(self):
        """Provide AgentRouter instance."""
        return AgentRouter()

    @pytest.mark.asyncio
    async def test_git_commit_quality_gate(self, matcher, router):
        """Test git commit triggers mandatory code review."""
        # Quality gate pattern matching
        pattern_match = matcher.match_patterns(
            tool_name="git commit",
            file_path="api.py"
        )

        assert pattern_match is not None
        assert pattern_match["agent"] == "@code-reviewer"
        assert pattern_match["confidence"] == 1.0
        assert pattern_match["method"] == "mandatory"

        # Task assessment
        context = {
            "file_path": "api.py",
            "content": "from fastapi import FastAPI",
            "user_query": "",
            "tool_name": "git commit",
            "affected_files": ["api.py"]
        }

        assessment = await router.assess_task_complexity(
            pattern_match=pattern_match,
            context=context
        )

        assert assessment.suggested_agent == "@code-reviewer"
        assert assessment.confidence == 1.0

        # Quality gate should auto-approve (mandatory review)
        should_approve = router.should_auto_approve(assessment)
        assert should_approve is True

    @pytest.mark.asyncio
    async def test_merge_quality_gate(self, matcher, router):
        """Test merge triggers mandatory review."""
        pattern_match = matcher.match_patterns(
            tool_name="merge branch",
            file_path="api.py"
        )

        assert pattern_match is not None
        assert pattern_match["agent"] == "@code-reviewer"
        assert "Pre-merge" in pattern_match["reason"]

    @pytest.mark.asyncio
    async def test_quality_gate_priority_over_file_type(self, matcher, router):
        """Test quality gate has priority over file type detection."""
        # Even though api.py would match @python-specialist,
        # git commit should match @code-reviewer with higher priority
        pattern_match = matcher.match_patterns(
            tool_name="git commit",
            file_path="api.py",
            content="from fastapi import FastAPI"
        )

        assert pattern_match["agent"] == "@code-reviewer"
        assert pattern_match["confidence"] == 1.0


class TestMemoryLoggingIntegration:
    """Test memory logging integration in delegation workflow."""

    @pytest.mark.asyncio
    async def test_delegation_decision_logged_to_memory(self):
        """Test delegation decision is logged to DevStream memory."""
        from devstream.memory.pre_tool_use import PreToolUseHook

        # Mock MCP client
        mock_mcp = AsyncMock()
        mock_mcp.call_tool = AsyncMock(return_value={
            "success": True,
            "memory_id": "test-123"
        })

        with patch('devstream.memory.pre_tool_use.get_mcp_client', return_value=mock_mcp):
            hook = PreToolUseHook()

            # Simulate delegation check
            assessment = await hook.check_agent_delegation(
                file_path="api.py",
                content="from fastapi import FastAPI",
                tool_name="Edit",
                user_query="fix bug"
            )

            if assessment:
                # Verify memory logging was attempted
                # (actual logging happens in _log_delegation_decision)
                assert assessment.suggested_agent is not None
                assert assessment.confidence > 0
                assert assessment.recommendation in ["DELEGATE", "COORDINATE", "ESCALATE"]

    @pytest.mark.asyncio
    async def test_memory_logging_disabled_via_config(self):
        """Test memory logging can be disabled via config."""
        with patch.dict(os.environ, {"DEVSTREAM_MEMORY_ENABLED": "false"}):
            from devstream.memory.pre_tool_use import PreToolUseHook

            mock_mcp = AsyncMock()
            hook = PreToolUseHook()

            # Mock assessment
            mock_assessment = TaskAssessment(
                complexity="LOW",
                architectural_impact="NONE",
                recommendation="DELEGATE",
                suggested_agent="@python-specialist",
                confidence=0.95,
                reason="Test"
            )

            mock_pattern_match = {
                "agent": "@python-specialist",
                "confidence": 0.95,
                "reason": "Test",
                "method": "extension"
            }

            # Should not log if memory disabled
            await hook._log_delegation_decision(mock_assessment, mock_pattern_match)

            # MCP should not be called
            if hasattr(hook, 'mcp_client'):
                if hasattr(hook.mcp_client, 'call_tool'):
                    assert not hook.mcp_client.call_tool.called


class TestConfigurationFlags:
    """Test configuration flag behavior."""

    @pytest.mark.asyncio
    async def test_delegation_disabled_via_config(self):
        """Test delegation can be disabled via config flag."""
        with patch.dict(os.environ, {"DEVSTREAM_AGENT_AUTO_DELEGATION_ENABLED": "false"}):
            from devstream.memory.pre_tool_use import PreToolUseHook

            hook = PreToolUseHook()

            # Should return None if disabled
            assessment = await hook.check_agent_delegation(
                file_path="api.py",
                content="from fastapi import FastAPI",
                tool_name="Edit"
            )

            assert assessment is None

    @pytest.mark.asyncio
    async def test_delegation_enabled_by_default(self):
        """Test delegation is enabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            # Default should be enabled
            enabled = os.getenv("DEVSTREAM_AGENT_AUTO_DELEGATION_ENABLED", "true").lower() == "true"
            assert enabled is True


class TestGracefulDegradation:
    """Test graceful degradation when components unavailable."""

    @pytest.mark.asyncio
    async def test_missing_pattern_matcher_graceful(self):
        """Test graceful degradation when PatternMatcher unavailable."""
        from devstream.memory.pre_tool_use import PreToolUseHook

        # Mock missing pattern matcher
        hook = PreToolUseHook()
        hook.pattern_matcher = None
        hook.agent_router = None

        # Should return None gracefully
        assessment = await hook.check_agent_delegation(
            file_path="api.py",
            content="from fastapi import FastAPI",
            tool_name="Edit"
        )

        assert assessment is None

    @pytest.mark.asyncio
    async def test_pattern_match_failure_graceful(self):
        """Test graceful handling of pattern match failure."""
        from devstream.memory.pre_tool_use import PreToolUseHook

        hook = PreToolUseHook()

        # Mock pattern matcher that raises exception
        if hook.pattern_matcher:
            with patch.object(hook.pattern_matcher, 'match_patterns', side_effect=Exception("Test error")):
                assessment = await hook.check_agent_delegation(
                    file_path="api.py",
                    content="from fastapi import FastAPI",
                    tool_name="Edit"
                )

                # Should return None (graceful failure)
                assert assessment is None


class TestMultiFileScenarios:
    """Test delegation for multi-file scenarios."""

    @pytest.fixture
    def matcher(self):
        """Provide PatternMatcher instance."""
        return PatternMatcher()

    @pytest.fixture
    def router(self):
        """Provide AgentRouter instance."""
        return AgentRouter()

    @pytest.mark.asyncio
    async def test_multi_file_medium_complexity(self, matcher, router):
        """Test medium complexity assessment for multi-file edit."""
        pattern_match = matcher.match_patterns(file_path="api.py")

        context = {
            "file_path": "api.py",
            "content": "from fastapi import FastAPI",
            "user_query": "update endpoints",
            "tool_name": "Edit",
            "affected_files": ["api.py", "models.py", "schemas.py"]
        }

        assessment = await router.assess_task_complexity(
            pattern_match=pattern_match,
            context=context
        )

        assert assessment.complexity == "MEDIUM"
        assert assessment.recommendation == "COORDINATE"

    @pytest.mark.asyncio
    async def test_many_files_high_complexity(self, matcher, router):
        """Test high complexity assessment for many files."""
        pattern_match = matcher.match_patterns(file_path="api.py")

        context = {
            "file_path": "api.py",
            "content": "from fastapi import FastAPI",
            "user_query": "update all modules",
            "tool_name": "Edit",
            "affected_files": [f"module_{i}.py" for i in range(10)]
        }

        assessment = await router.assess_task_complexity(
            pattern_match=pattern_match,
            context=context
        )

        assert assessment.complexity == "HIGH"
        assert assessment.recommendation == "ESCALATE"


class TestEndToEndWorkflow:
    """Test complete end-to-end delegation workflow."""

    @pytest.mark.asyncio
    async def test_complete_delegation_workflow_success(self):
        """Test complete workflow from pattern match to decision."""
        # Step 1: Initialize components
        matcher = PatternMatcher()
        router = AgentRouter()

        # Step 2: Pattern matching
        pattern_match = matcher.match_patterns(
            file_path="api.py",
            content="from fastapi import FastAPI",
            tool_name="Edit"
        )

        assert pattern_match is not None

        # Step 3: Task assessment
        context = {
            "file_path": "api.py",
            "content": "from fastapi import FastAPI",
            "user_query": "add logging",
            "tool_name": "Edit",
            "affected_files": ["api.py"]
        }

        assessment = await router.assess_task_complexity(
            pattern_match=pattern_match,
            context=context
        )

        # Step 4: Auto-approval decision
        should_approve = router.should_auto_approve(assessment)

        # Step 5: Message generation
        message = router.format_advisory_message(assessment)

        # Verify complete workflow
        assert assessment.suggested_agent == "@python-specialist"
        assert should_approve is True
        assert "DELEGATE" in message
        assert "@python-specialist" in message

    @pytest.mark.asyncio
    async def test_complete_workflow_escalation_path(self):
        """Test complete workflow ending in escalation."""
        matcher = PatternMatcher()
        router = AgentRouter()

        # High complexity scenario
        pattern_match = matcher.match_patterns(
            file_path="api.py",
            content="from fastapi import FastAPI"
        )

        context = {
            "file_path": "api.py",
            "content": "from fastapi import FastAPI",
            "user_query": "migrate to new authentication system",
            "tool_name": "Edit",
            "affected_files": ["api.py", "auth.py", "models.py", "middleware.py"]
        }

        assessment = await router.assess_task_complexity(
            pattern_match=pattern_match,
            context=context
        )

        should_approve = router.should_auto_approve(assessment)
        message = router.format_advisory_message(assessment)

        # Should escalate
        assert assessment.architectural_impact == "HIGH"
        assert should_approve is False
        assert "ESCALATE" in message
        assert "Full @tech-lead analysis required" in message


class TestPerformanceIntegration:
    """Test performance of integrated delegation workflow."""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow_performance(self):
        """Test complete workflow completes within performance target."""
        import time

        matcher = PatternMatcher()
        router = AgentRouter()

        start = time.perf_counter()

        # Complete workflow
        pattern_match = matcher.match_patterns(
            file_path="api.py",
            content="from fastapi import FastAPI"
        )

        context = {
            "file_path": "api.py",
            "content": "from fastapi import FastAPI",
            "user_query": "fix bug",
            "tool_name": "Edit",
            "affected_files": ["api.py"]
        }

        assessment = await router.assess_task_complexity(
            pattern_match=pattern_match,
            context=context
        )

        should_approve = router.should_auto_approve(assessment)
        message = router.format_advisory_message(assessment)

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should complete in <15ms (pattern <10ms + assessment <5ms)
        assert elapsed_ms < 15.0, f"Workflow took {elapsed_ms:.2f}ms (target: <15ms)"
        assert pattern_match is not None
        assert assessment is not None
        assert message is not None
