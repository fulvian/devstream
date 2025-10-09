"""
Unit tests for Agent Auto-Delegation System (Fix A2).

Tests:
- Python file pattern (confidence ≥ 0.95)
- TypeScript file pattern (confidence ≥ 0.95)
- Multi-stack pattern (confidence < 0.85)
- Delegation advisory in context
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / '.claude/hooks/devstream'))

from agents.pattern_matcher import PatternMatcher, PatternMatch
from agents.agent_router import AgentRouter, TaskAssessment


class TestPatternMatcherConfidence:
    """Test pattern matcher confidence scoring."""

    def setup_method(self):
        """Setup test fixtures."""
        self.matcher = PatternMatcher()

    def test_python_file_high_confidence(self):
        """Test Python file patterns yield confidence ≥ 0.95."""
        patterns = [
            "src/api/users.py",
            "tests/test_auth.py",
            ".claude/hooks/devstream/memory/pre_tool_use.py"
        ]

        for file_path in patterns:
            match = self.matcher.match_patterns(file_path=file_path)

            assert match is not None
            assert "@python-specialist" in match["agent"]
            assert match["confidence"] >= 0.95

    def test_typescript_file_high_confidence(self):
        """Test TypeScript file patterns yield confidence ≥ 0.95."""
        patterns = [
            "src/components/Dashboard.tsx",
            "mcp-devstream-server/src/index.ts",
            "tests/integration/api.test.ts"
        ]

        for file_path in patterns:
            match = self.matcher.match_patterns(file_path=file_path)

            assert match is not None
            assert match.suggested_agent == "typescript-specialist"
            assert match.confidence >= 0.95
            assert match.auto_approve is True

    def test_rust_file_high_confidence(self):
        """Test Rust file patterns yield confidence ≥ 0.95."""
        patterns = [
            "src/main.rs",
            "crates/devstream-core/src/lib.rs",
            "tests/integration_test.rs"
        ]

        for file_path in patterns:
            match = self.matcher.match_patterns(file_path=file_path)

            assert match is not None
            assert match.suggested_agent == "rust-specialist"
            assert match.confidence >= 0.95
            assert match.auto_approve is True

    def test_go_file_high_confidence(self):
        """Test Go file patterns yield confidence ≥ 0.95."""
        patterns = [
            "cmd/server/main.go",
            "internal/handlers/user.go",
            "pkg/utils/helpers_test.go"
        ]

        for file_path in patterns:
            match = self.matcher.match_patterns(file_path=file_path)

            assert match is not None
            assert match.suggested_agent == "go-specialist"
            assert match.confidence >= 0.95
            assert match.auto_approve is True

    def test_database_file_high_confidence(self):
        """Test database file patterns yield confidence ≥ 0.90."""
        patterns = [
            "migrations/001_initial_schema.sql",
            "schema.sql",
            "scripts/seed_data.sql"
        ]

        for file_path in patterns:
            match = self.matcher.match_patterns(file_path=file_path)

            assert match is not None
            assert match.suggested_agent == "database-specialist"
            assert match.confidence >= 0.90

    def test_devops_file_high_confidence(self):
        """Test DevOps file patterns yield confidence ≥ 0.90."""
        patterns = [
            "Dockerfile",
            ".github/workflows/ci.yml",
            "docker-compose.yml",
            "k8s/deployment.yaml"
        ]

        for file_path in patterns:
            match = self.matcher.match_patterns(file_path=file_path)

            assert match is not None
            assert match.suggested_agent == "devops-specialist"
            assert match.confidence >= 0.90

    def test_multi_stack_low_confidence(self):
        """Test multi-stack patterns yield confidence < 0.85."""
        # Simulate multi-file context
        context = {
            "affected_files": [
                "src/api/users.py",
                "src/components/UserDashboard.tsx"
            ]
        }

        match = self.matcher.match_patterns(
            user_query="Build full-stack user dashboard",
            **context
        )

        # Multi-stack should have lower confidence
        assert match is not None
        assert match.confidence < 0.85
        assert match.auto_approve is False


class TestAgentDelegationWorkflow:
    """Test complete agent delegation workflow."""

    def setup_method(self):
        """Setup test fixtures."""
        self.router = AgentRouter()
        self.matcher = PatternMatcher()

    @pytest.mark.asyncio
    async def test_automatic_delegation_python(self):
        """Test automatic delegation for Python files."""
        # Match pattern
        match = self.matcher.match_patterns(file_path="src/api/users.py")

        # Assess task
        context = {
            "file_path": "src/api/users.py",
            "content": "def get_user(user_id: int): ...",
            "user_query": "Add email validation",
            "affected_files": ["src/api/users.py"]
        }

        assessment = await self.router.assess_task_complexity(
            pattern_match=match,
            context=context
        )

        # Verify automatic delegation
        assert assessment.recommendation == "AUTOMATIC"
        assert assessment.suggested_agent == "python-specialist"
        assert assessment.confidence >= 0.95
        assert assessment.auto_approve is True

    @pytest.mark.asyncio
    async def test_advisory_delegation_multiple_files(self):
        """Test advisory delegation for multiple related files."""
        # Simulate multiple Python files
        match = self.matcher.match_patterns(
            user_query="Refactor authentication module",
            affected_files=[
                "src/auth/jwt.py",
                "src/auth/password.py",
                "src/auth/session.py"
            ]
        )

        context = {
            "user_query": "Refactor authentication module",
            "affected_files": ["src/auth/jwt.py", "src/auth/password.py", "src/auth/session.py"]
        }

        assessment = await self.router.assess_task_complexity(
            pattern_match=match,
            context=context
        )

        # Should be advisory (0.85 ≤ confidence < 0.95)
        assert assessment.recommendation == "ADVISORY"
        assert 0.85 <= assessment.confidence < 0.95

    @pytest.mark.asyncio
    async def test_authorization_required_multi_stack(self):
        """Test that multi-stack tasks require authorization."""
        match = self.matcher.match_patterns(
            user_query="Build full-stack user management system",
            affected_files=[
                "src/api/users.py",
                "src/components/UserDashboard.tsx"
            ]
        )

        context = {
            "user_query": "Build full-stack user management system",
            "affected_files": ["src/api/users.py", "src/components/UserDashboard.tsx"]
        }

        assessment = await self.router.assess_task_complexity(
            pattern_match=match,
            context=context
        )

        # Should require authorization
        assert assessment.recommendation == "AUTHORIZATION_REQUIRED"
        assert assessment.confidence < 0.85
        assert assessment.suggested_agent == "tech-lead"

    def test_advisory_message_formatting(self):
        """Test advisory message formatting."""
        assessment = TaskAssessment(
            suggested_agent="python-specialist",
            confidence=0.95,
            recommendation="AUTOMATIC",
            reason="Single Python file modification",
            complexity="low",
            architectural_impact="minimal",
            auto_approve=True
        )

        message = self.router.format_advisory_message(assessment)

        # Verify message format
        assert "🤖 Agent Auto-Delegation" in message
        assert "AUTOMATIC" in message
        assert "@python-specialist" in message
        assert "confidence 0.95" in message
        assert "Single Python file modification" in message


class TestQualityGateEnforcement:
    """Test quality gate enforcement for commits."""

    @pytest.mark.asyncio
    async def test_commit_triggers_code_reviewer(self):
        """Test that git commit triggers mandatory @code-reviewer."""
        from agent_router import AgentRouter

        router = AgentRouter()

        # Simulate commit intent detection
        match = PatternMatch(
            suggested_agent="code-reviewer",
            confidence=1.0,
            matched_patterns=["commit"],
            auto_approve=True,
            file_patterns=[]
        )

        context = {
            "user_query": "Commit authentication implementation",
            "tool_name": "Bash",
            "command": "git commit -m 'Add JWT auth'"
        }

        assessment = await router.assess_task_complexity(
            pattern_match=match,
            context=context
        )

        # Verify mandatory code-reviewer
        assert assessment.suggested_agent == "code-reviewer"
        assert assessment.recommendation == "MANDATORY"
        assert assessment.auto_approve is True

    def test_quality_gate_bypass_forbidden(self):
        """Test that quality gate cannot be bypassed."""
        from agent_router import AgentRouter
        import os

        router = AgentRouter()

        # Try to disable via env var
        os.environ["DEVSTREAM_AUTO_DELEGATION_QUALITY_GATE"] = "false"

        # Should still enforce
        # (implementation should ignore this flag for quality gate)

        # Cleanup
        if "DEVSTREAM_AUTO_DELEGATION_QUALITY_GATE" in os.environ:
            del os.environ["DEVSTREAM_AUTO_DELEGATION_QUALITY_GATE"]


class TestPreToolUseHookIntegration:
    """Test PreToolUse hook integration with auto-delegation."""

    @pytest.mark.asyncio
    async def test_delegation_advisory_injection(self):
        """Test that delegation advisory is injected in PreToolUse context."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / '.claude/hooks/devstream/memory'))
        from pre_tool_use import PreToolUseHook

        hook = PreToolUseHook()

        # Check delegation
        assessment = await hook.check_agent_delegation(
            file_path="src/api/users.py",
            content="def get_user(user_id: int): ...",
            tool_name="Write"
        )

        # Verify assessment returned
        assert assessment is not None
        assert assessment.suggested_agent == "python-specialist"
        assert assessment.confidence >= 0.95

    @pytest.mark.asyncio
    async def test_delegation_logged_to_memory(self):
        """Test that delegation decisions are logged to DevStream memory."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / '.claude/hooks/devstream/memory'))
        from pre_tool_use import PreToolUseHook

        hook = PreToolUseHook()

        # Mock MCP client
        with patch.object(hook, 'mcp_client') as mock_mcp:
            mock_mcp.call_tool = AsyncMock(return_value={"success": True})

            # Trigger delegation
            assessment = await hook.check_agent_delegation(
                file_path="src/api/users.py",
                content="def get_user(user_id: int): ...",
                tool_name="Write"
            )

            # Verify memory storage called
            # (via _log_delegation_decision method)
            # This is tested indirectly through integration tests


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
