"""
Unit tests for AgentRouter - Agent Auto-Delegation System.

Tests task complexity assessment, auto-approval logic, and advisory message generation.

Coverage target: 95%+
Test categories:
- Task complexity assessment (LOW/MEDIUM/HIGH)
- Architectural impact assessment (NONE/LOW/MEDIUM/HIGH)
- Auto-approval logic (>=0.95 confidence + LOW complexity + NONE/LOW impact)
- Recommendation logic (DELEGATE/COORDINATE/ESCALATE)
- Advisory message formatting
- Edge cases and error handling
"""

import pytest
import pytest_asyncio
from pathlib import Path
import sys
from typing import Dict, Any

# Add agents module to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / ".claude" / "hooks"))

from devstream.agents.agent_router import AgentRouter, TaskAssessment
from devstream.agents.pattern_catalog import PatternMatch


class TestAgentRouterInit:
    """Test AgentRouter initialization."""

    def test_initialization_success(self):
        """Test successful AgentRouter initialization."""
        router = AgentRouter()

        # Verify thresholds set correctly
        assert router.AUTO_APPROVE_CONFIDENCE_THRESHOLD == 0.95
        assert router.AUTO_APPROVE_MAX_COMPLEXITY == "LOW"
        assert router.AUTO_APPROVE_MAX_IMPACT == "LOW"

    def test_configurable_thresholds(self):
        """Test that thresholds are configurable."""
        router = AgentRouter()

        # Thresholds should be class-level constants (not hardcoded in logic)
        assert hasattr(router, 'AUTO_APPROVE_CONFIDENCE_THRESHOLD')
        assert hasattr(router, 'AUTO_APPROVE_MAX_COMPLEXITY')
        assert hasattr(router, 'AUTO_APPROVE_MAX_IMPACT')


class TestComplexityAssessment:
    """Test task complexity assessment logic."""

    @pytest.fixture
    def router(self):
        """Provide AgentRouter instance."""
        return AgentRouter()

    def test_low_complexity_single_file(self, router):
        """Test LOW complexity for single file."""
        complexity = router._assess_complexity_signals(
            pattern_match={"agent": "@python-specialist", "confidence": 0.95},
            user_query="fix bug in function",
            file_path="test.py",
            affected_files=["test.py"]
        )

        assert complexity == "LOW"

    def test_medium_complexity_multiple_files(self, router):
        """Test MEDIUM complexity for multiple files (2-5)."""
        complexity = router._assess_complexity_signals(
            pattern_match={"agent": "@python-specialist", "confidence": 0.95},
            user_query="update API endpoints",
            file_path="api.py",
            affected_files=["api.py", "models.py", "schemas.py"]
        )

        assert complexity == "MEDIUM"

    def test_high_complexity_many_files(self, router):
        """Test HIGH complexity for many files (>5)."""
        affected_files = [f"file_{i}.py" for i in range(10)]
        complexity = router._assess_complexity_signals(
            pattern_match={"agent": "@python-specialist", "confidence": 0.95},
            user_query="update all modules",
            file_path="api.py",
            affected_files=affected_files
        )

        assert complexity == "HIGH"

    def test_high_complexity_refactor_keyword(self, router):
        """Test HIGH complexity for refactoring keywords."""
        complexity = router._assess_complexity_signals(
            pattern_match={"agent": "@python-specialist", "confidence": 0.95},
            user_query="refactor entire architecture",
            file_path="api.py",
            affected_files=["api.py"]
        )

        assert complexity == "HIGH"

    def test_high_complexity_migrate_keyword(self, router):
        """Test HIGH complexity for migration keywords."""
        complexity = router._assess_complexity_signals(
            pattern_match={"agent": "@python-specialist", "confidence": 0.95},
            user_query="migrate to new database",
            file_path="api.py",
            affected_files=["api.py"]
        )

        assert complexity == "HIGH"

    def test_medium_complexity_integrate_keyword(self, router):
        """Test MEDIUM complexity for integration keywords."""
        complexity = router._assess_complexity_signals(
            pattern_match={"agent": "@python-specialist", "confidence": 0.95},
            user_query="integrate third-party API",
            file_path="api.py",
            affected_files=["api.py"]
        )

        assert complexity == "MEDIUM"

    def test_low_complexity_default(self, router):
        """Test LOW complexity as default."""
        complexity = router._assess_complexity_signals(
            pattern_match={"agent": "@python-specialist", "confidence": 0.95},
            user_query="add new function",
            file_path="utils.py",
            affected_files=["utils.py"]
        )

        assert complexity == "LOW"


class TestArchitecturalImpactAssessment:
    """Test architectural impact assessment logic."""

    @pytest.fixture
    def router(self):
        """Provide AgentRouter instance."""
        return AgentRouter()

    def test_high_impact_migration(self, router):
        """Test HIGH impact for database migration."""
        impact = router._assess_architectural_impact(
            user_query="database migration from MySQL to PostgreSQL",
            file_path="migration.py",
            tool_name=None
        )

        assert impact == "HIGH"

    def test_high_impact_breaking_change(self, router):
        """Test HIGH impact for breaking changes."""
        impact = router._assess_architectural_impact(
            user_query="implement breaking change to API",
            file_path="api.py",
            tool_name=None
        )

        assert impact == "HIGH"

    def test_high_impact_new_service(self, router):
        """Test HIGH impact for new service."""
        impact = router._assess_architectural_impact(
            user_query="create new authentication service",
            file_path="auth.py",
            tool_name=None
        )

        assert impact == "HIGH"

    def test_medium_impact_new_api(self, router):
        """Test MEDIUM impact for new API."""
        impact = router._assess_architectural_impact(
            user_query="add new API endpoint",
            file_path="api.py",
            tool_name=None
        )

        assert impact == "MEDIUM"

    def test_medium_impact_integration(self, router):
        """Test MEDIUM impact for third-party integration."""
        impact = router._assess_architectural_impact(
            user_query="integrate Stripe payment gateway",
            file_path="payments.py",
            tool_name=None
        )

        assert impact == "MEDIUM"

    def test_low_impact_fix(self, router):
        """Test LOW impact for bug fix."""
        impact = router._assess_architectural_impact(
            user_query="fix validation bug",
            file_path="validators.py",
            tool_name=None
        )

        assert impact == "LOW"

    def test_low_impact_optimize(self, router):
        """Test LOW impact for optimization."""
        impact = router._assess_architectural_impact(
            user_query="optimize query performance",
            file_path="queries.py",
            tool_name=None
        )

        assert impact == "LOW"

    def test_none_impact_default(self, router):
        """Test NONE impact as default."""
        impact = router._assess_architectural_impact(
            user_query="add logging",
            file_path="logger.py",
            tool_name=None
        )

        assert impact == "NONE"


class TestRecommendationLogic:
    """Test delegation recommendation logic."""

    @pytest.fixture
    def router(self):
        """Provide AgentRouter instance."""
        return AgentRouter()

    def test_delegate_recommendation(self, router):
        """Test DELEGATE recommendation for high confidence + low complexity/impact."""
        recommendation = router._determine_recommendation(
            confidence=0.95,
            complexity="LOW",
            architectural_impact="LOW"
        )

        assert recommendation == "DELEGATE"

    def test_delegate_none_impact(self, router):
        """Test DELEGATE recommendation with NONE impact."""
        recommendation = router._determine_recommendation(
            confidence=0.95,
            complexity="LOW",
            architectural_impact="NONE"
        )

        assert recommendation == "DELEGATE"

    def test_coordinate_medium_complexity(self, router):
        """Test COORDINATE recommendation for medium complexity."""
        recommendation = router._determine_recommendation(
            confidence=0.90,
            complexity="MEDIUM",
            architectural_impact="LOW"
        )

        assert recommendation == "COORDINATE"

    def test_coordinate_medium_impact(self, router):
        """Test COORDINATE recommendation for medium impact."""
        recommendation = router._determine_recommendation(
            confidence=0.90,
            complexity="LOW",
            architectural_impact="MEDIUM"
        )

        assert recommendation == "COORDINATE"

    def test_escalate_high_complexity(self, router):
        """Test ESCALATE recommendation for high complexity."""
        recommendation = router._determine_recommendation(
            confidence=0.95,
            complexity="HIGH",
            architectural_impact="LOW"
        )

        assert recommendation == "ESCALATE"

    def test_escalate_high_impact(self, router):
        """Test ESCALATE recommendation for high impact."""
        recommendation = router._determine_recommendation(
            confidence=0.95,
            complexity="LOW",
            architectural_impact="HIGH"
        )

        assert recommendation == "ESCALATE"

    def test_escalate_low_confidence(self, router):
        """Test ESCALATE recommendation for low confidence (<0.85)."""
        recommendation = router._determine_recommendation(
            confidence=0.80,
            complexity="LOW",
            architectural_impact="LOW"
        )

        assert recommendation == "ESCALATE"

    def test_boundary_confidence_0_85(self, router):
        """Test boundary case: confidence exactly 0.85."""
        recommendation = router._determine_recommendation(
            confidence=0.85,
            complexity="LOW",
            architectural_impact="LOW"
        )

        # 0.85 should COORDINATE (not high enough for DELEGATE)
        assert recommendation == "COORDINATE"


@pytest_asyncio.fixture
async def sample_pattern_match() -> PatternMatch:
    """Provide sample pattern match for testing."""
    return PatternMatch(
        agent="@python-specialist",
        confidence=0.95,
        reason="File extension '.py' matched @python-specialist",
        method="extension"
    )


@pytest_asyncio.fixture
async def sample_context() -> Dict[str, Any]:
    """Provide sample context for testing."""
    return {
        "file_path": "api.py",
        "content": "from fastapi import FastAPI",
        "user_query": "fix bug",
        "tool_name": "Edit",
        "affected_files": ["api.py"]
    }


class TestTaskAssessment:
    """Test full task assessment workflow."""

    @pytest.fixture
    def router(self):
        """Provide AgentRouter instance."""
        return AgentRouter()

    @pytest.mark.asyncio
    async def test_assess_low_complexity_task(self, router, sample_pattern_match, sample_context):
        """Test assessment of low complexity task."""
        assessment = await router.assess_task_complexity(
            pattern_match=sample_pattern_match,
            context=sample_context
        )

        assert assessment.complexity == "LOW"
        assert assessment.architectural_impact in ["NONE", "LOW"]
        assert assessment.recommendation in ["DELEGATE", "COORDINATE"]
        assert assessment.suggested_agent == "@python-specialist"
        assert assessment.confidence == 0.95
        assert len(assessment.reason) > 0

    @pytest.mark.asyncio
    async def test_assess_high_complexity_task(self, router, sample_pattern_match):
        """Test assessment of high complexity task."""
        context = {
            "file_path": "api.py",
            "content": "from fastapi import FastAPI",
            "user_query": "refactor entire architecture",
            "tool_name": "Edit",
            "affected_files": ["api.py", "models.py", "schemas.py", "db.py", "utils.py", "config.py"]
        }

        assessment = await router.assess_task_complexity(
            pattern_match=sample_pattern_match,
            context=context
        )

        assert assessment.complexity == "HIGH"
        assert assessment.recommendation == "ESCALATE"

    @pytest.mark.asyncio
    async def test_assess_high_impact_task(self, router, sample_pattern_match):
        """Test assessment of high architectural impact task."""
        context = {
            "file_path": "auth.py",
            "content": "from fastapi import FastAPI",
            "user_query": "implement new authentication system",
            "tool_name": "Edit",
            "affected_files": ["auth.py"]
        }

        assessment = await router.assess_task_complexity(
            pattern_match=sample_pattern_match,
            context=context
        )

        assert assessment.architectural_impact == "HIGH"
        assert assessment.recommendation == "ESCALATE"

    @pytest.mark.asyncio
    async def test_assess_task_invalid_pattern_match(self, router, sample_context):
        """Test that invalid pattern_match raises ValueError."""
        with pytest.raises(ValueError, match="pattern_match cannot be None"):
            await router.assess_task_complexity(
                pattern_match=None,
                context=sample_context
            )

    @pytest.mark.asyncio
    async def test_assess_task_empty_context(self, router, sample_pattern_match):
        """Test assessment with minimal context."""
        context = {}

        assessment = await router.assess_task_complexity(
            pattern_match=sample_pattern_match,
            context=context
        )

        # Should handle gracefully with defaults
        assert assessment.complexity == "LOW"  # Default
        assert assessment.architectural_impact == "NONE"  # Default
        assert assessment.recommendation == "DELEGATE"


class TestAutoApprovalLogic:
    """Test auto-approval decision logic."""

    @pytest.fixture
    def router(self):
        """Provide AgentRouter instance."""
        return AgentRouter()

    def test_auto_approve_success(self, router):
        """Test auto-approval for qualifying task."""
        assessment = TaskAssessment(
            complexity="LOW",
            architectural_impact="NONE",
            recommendation="DELEGATE",
            suggested_agent="@python-specialist",
            confidence=0.95,
            reason="High confidence match"
        )

        assert router.should_auto_approve(assessment) is True

    def test_auto_approve_low_impact(self, router):
        """Test auto-approval with LOW impact."""
        assessment = TaskAssessment(
            complexity="LOW",
            architectural_impact="LOW",
            recommendation="DELEGATE",
            suggested_agent="@python-specialist",
            confidence=0.95,
            reason="High confidence match"
        )

        assert router.should_auto_approve(assessment) is True

    def test_reject_medium_complexity(self, router):
        """Test rejection for medium complexity."""
        assessment = TaskAssessment(
            complexity="MEDIUM",
            architectural_impact="NONE",
            recommendation="COORDINATE",
            suggested_agent="@python-specialist",
            confidence=0.95,
            reason="Medium complexity"
        )

        assert router.should_auto_approve(assessment) is False

    def test_reject_high_complexity(self, router):
        """Test rejection for high complexity."""
        assessment = TaskAssessment(
            complexity="HIGH",
            architectural_impact="NONE",
            recommendation="ESCALATE",
            suggested_agent="@python-specialist",
            confidence=0.95,
            reason="High complexity"
        )

        assert router.should_auto_approve(assessment) is False

    def test_reject_medium_impact(self, router):
        """Test rejection for medium impact."""
        assessment = TaskAssessment(
            complexity="LOW",
            architectural_impact="MEDIUM",
            recommendation="COORDINATE",
            suggested_agent="@python-specialist",
            confidence=0.95,
            reason="Medium impact"
        )

        assert router.should_auto_approve(assessment) is False

    def test_reject_high_impact(self, router):
        """Test rejection for high impact."""
        assessment = TaskAssessment(
            complexity="LOW",
            architectural_impact="HIGH",
            recommendation="ESCALATE",
            suggested_agent="@python-specialist",
            confidence=0.95,
            reason="High impact"
        )

        assert router.should_auto_approve(assessment) is False

    def test_reject_low_confidence(self, router):
        """Test rejection for low confidence (<0.95)."""
        assessment = TaskAssessment(
            complexity="LOW",
            architectural_impact="NONE",
            recommendation="COORDINATE",
            suggested_agent="@python-specialist",
            confidence=0.90,
            reason="Medium confidence"
        )

        assert router.should_auto_approve(assessment) is False

    def test_boundary_confidence_0_95(self, router):
        """Test boundary case: confidence exactly 0.95."""
        assessment = TaskAssessment(
            complexity="LOW",
            architectural_impact="NONE",
            recommendation="DELEGATE",
            suggested_agent="@python-specialist",
            confidence=0.95,
            reason="Exact threshold"
        )

        assert router.should_auto_approve(assessment) is True


class TestAdvisoryMessageFormatting:
    """Test advisory message generation."""

    @pytest.fixture
    def router(self):
        """Provide AgentRouter instance."""
        return AgentRouter()

    def test_format_delegate_message(self, router):
        """Test DELEGATE advisory message formatting."""
        assessment = TaskAssessment(
            complexity="LOW",
            architectural_impact="NONE",
            recommendation="DELEGATE",
            suggested_agent="@python-specialist",
            confidence=0.95,
            reason="High confidence Python file match"
        )

        message = router.format_advisory_message(assessment)

        assert "ADVISORY: DELEGATE with @python-specialist" in message
        assert "Confidence: 0.95" in message
        assert "Complexity: LOW" in message
        assert "Architectural Impact: NONE" in message
        assert "Auto-delegation approved" in message
        assert assessment.reason in message

    def test_format_coordinate_message(self, router):
        """Test COORDINATE advisory message formatting."""
        assessment = TaskAssessment(
            complexity="MEDIUM",
            architectural_impact="LOW",
            recommendation="COORDINATE",
            suggested_agent="@typescript-specialist",
            confidence=0.90,
            reason="Medium complexity TypeScript task"
        )

        message = router.format_advisory_message(assessment)

        assert "ADVISORY: COORDINATE with @typescript-specialist" in message
        assert "Confidence: 0.90" in message
        assert "Complexity: MEDIUM" in message
        assert "Coordination recommended" in message

    def test_format_escalate_message(self, router):
        """Test ESCALATE advisory message formatting."""
        assessment = TaskAssessment(
            complexity="HIGH",
            architectural_impact="HIGH",
            recommendation="ESCALATE",
            suggested_agent="@tech-lead",
            confidence=0.85,
            reason="High complexity architectural change"
        )

        message = router.format_advisory_message(assessment)

        assert "ADVISORY: ESCALATE" in message
        assert "Confidence: 0.85" in message
        assert "Complexity: HIGH" in message
        assert "Architectural Impact: HIGH" in message
        assert "Full @tech-lead analysis required" in message

    def test_message_structure(self, router):
        """Test advisory message has proper structure."""
        assessment = TaskAssessment(
            complexity="LOW",
            architectural_impact="NONE",
            recommendation="DELEGATE",
            suggested_agent="@python-specialist",
            confidence=0.95,
            reason="Test reason"
        )

        message = router.format_advisory_message(assessment)

        # Verify structure
        assert message.startswith("ADVISORY:")
        assert "Metrics:" in message
        assert "Reasoning:" in message
        assert "Action:" in message
        assert "\n" in message  # Multi-line format


class TestReasonBuilding:
    """Test assessment reason building."""

    @pytest.fixture
    def router(self):
        """Provide AgentRouter instance."""
        return AgentRouter()

    def test_reason_includes_all_components(self, router):
        """Test reason includes pattern match, complexity, and impact."""
        pattern_match = PatternMatch(
            agent="@python-specialist",
            confidence=0.95,
            reason="Extension match",
            method="extension"
        )

        reason = router._build_assessment_reason(
            pattern_match=pattern_match,
            complexity="LOW",
            architectural_impact="NONE",
            recommendation="DELEGATE"
        )

        assert "Extension match" in reason
        assert "LOW" in reason
        assert "NONE" in reason
        assert "single-file, well-defined scope" in reason
        assert "no architectural impact" in reason
        assert "Auto-delegation criteria met" in reason

    def test_reason_coordinate_context(self, router):
        """Test reason includes coordination context."""
        pattern_match = PatternMatch(
            agent="@typescript-specialist",
            confidence=0.90,
            reason="Import match",
            method="import"
        )

        reason = router._build_assessment_reason(
            pattern_match=pattern_match,
            complexity="MEDIUM",
            architectural_impact="LOW",
            recommendation="COORDINATE"
        )

        assert "MEDIUM" in reason
        assert "multi-file or moderate scope" in reason
        assert "Coordination recommended" in reason

    def test_reason_escalate_context(self, router):
        """Test reason includes escalation context."""
        pattern_match = PatternMatch(
            agent="@tech-lead",
            confidence=0.80,
            reason="Low confidence",
            method="keyword"
        )

        reason = router._build_assessment_reason(
            pattern_match=pattern_match,
            complexity="HIGH",
            architectural_impact="HIGH",
            recommendation="ESCALATE"
        )

        assert "HIGH" in reason
        assert "complex refactoring or broad scope" in reason
        assert "core architecture modifications" in reason
        assert "Full analysis required" in reason


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def router(self):
        """Provide AgentRouter instance."""
        return AgentRouter()

    @pytest.mark.asyncio
    async def test_missing_optional_fields(self, router):
        """Test assessment with missing optional context fields."""
        pattern_match = PatternMatch(
            agent="@python-specialist",
            confidence=0.95,
            reason="Test",
            method="extension"
        )

        context = {
            "file_path": None,
            "user_query": "",
            "affected_files": []
        }

        assessment = await router.assess_task_complexity(
            pattern_match=pattern_match,
            context=context
        )

        # Should handle gracefully
        assert assessment.complexity == "LOW"
        assert assessment.architectural_impact == "NONE"

    @pytest.mark.asyncio
    async def test_extreme_confidence_values(self, router):
        """Test assessment with extreme confidence values."""
        pattern_match = PatternMatch(
            agent="@python-specialist",
            confidence=1.0,  # Maximum confidence
            reason="Quality gate",
            method="mandatory"
        )

        context = {"file_path": "test.py"}

        assessment = await router.assess_task_complexity(
            pattern_match=pattern_match,
            context=context
        )

        assert assessment.confidence == 1.0
        assert router.should_auto_approve(assessment) is True

    def test_case_insensitive_keyword_matching(self, router):
        """Test keyword matching is case-insensitive."""
        impact1 = router._assess_architectural_impact(
            user_query="MIGRATION DATABASE",
            file_path="migrate.py",
            tool_name=None
        )

        impact2 = router._assess_architectural_impact(
            user_query="migration database",
            file_path="migrate.py",
            tool_name=None
        )

        assert impact1 == impact2 == "HIGH"
