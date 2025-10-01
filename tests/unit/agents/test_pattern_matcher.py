"""
Unit tests for PatternMatcher - Agent Auto-Delegation System.

Tests pattern-based agent routing with extension matching, import detection,
keyword frequency analysis, and quality gate patterns.

Coverage target: 95%+
"""

import pytest
from pathlib import Path
import sys

# Add agents module to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / ".claude" / "hooks"))

from devstream.agents.pattern_matcher import PatternMatcher
from devstream.agents.pattern_catalog import PatternMatch, PATTERN_CATALOG


class TestPatternMatcherInit:
    """Test PatternMatcher initialization and setup."""

    def test_initialization_success(self):
        """Test successful PatternMatcher initialization."""
        matcher = PatternMatcher()
        assert matcher._import_patterns is not None
        assert matcher._shebang_patterns is not None
        assert matcher._extension_map is not None
        assert len(matcher._extension_map) > 0

    def test_extension_map_populated(self):
        """Test extension map contains expected mappings."""
        matcher = PatternMatcher()
        assert ".py" in matcher._extension_map
        assert ".ts" in matcher._extension_map
        assert ".rs" in matcher._extension_map
        assert ".go" in matcher._extension_map


class TestExtensionMatching:
    """Test file extension-based pattern matching."""

    @pytest.fixture
    def matcher(self):
        return PatternMatcher()

    def test_python_extension_match(self, matcher):
        """Test Python file extension matching."""
        result = matcher.match_patterns(file_path="test.py")
        assert result is not None
        assert result["agent"] == "@python-specialist"
        assert result["confidence"] == 0.95
        assert result["method"] == "extension"

    def test_typescript_extension_match(self, matcher):
        """Test TypeScript file extension matching."""
        result = matcher.match_patterns(file_path="component.ts")
        assert result is not None
        assert result["agent"] == "@typescript-specialist"
        assert result["confidence"] == 0.95

    def test_rust_extension_match(self, matcher):
        """Test Rust file extension matching."""
        result = matcher.match_patterns(file_path="main.rs")
        assert result is not None
        assert result["agent"] == "@rust-specialist"
        assert result["confidence"] == 0.95

    def test_go_extension_match(self, matcher):
        """Test Go file extension matching."""
        result = matcher.match_patterns(file_path="server.go")
        assert result is not None
        assert result["agent"] == "@go-specialist"
        assert result["confidence"] == 0.95

    def test_unknown_extension_no_match(self, matcher):
        """Test unknown extension returns no match."""
        result = matcher.match_patterns(file_path="file.xyz")
        assert result is None


class TestImportDetection:
    """Test import statement detection."""

    @pytest.fixture
    def matcher(self):
        return PatternMatcher()

    def test_python_fastapi_import(self, matcher):
        """Test FastAPI import detection routes to @python-specialist."""
        content = "from fastapi import FastAPI"
        result = matcher.match_patterns(file_path="api.txt", content=content)
        assert result is not None
        assert result["agent"] == "@python-specialist"
        assert result["confidence"] == 0.90
        assert result["method"] == "import"

    def test_typescript_react_import(self, matcher):
        """Test React import detection routes to @typescript-specialist."""
        content = "import React from 'react'"
        result = matcher.match_patterns(file_path="component.txt", content=content)
        assert result is not None
        assert result["agent"] == "@typescript-specialist"
        assert result["confidence"] == 0.90

    def test_rust_tokio_import(self, matcher):
        """Test Rust Tokio import detection."""
        content = "use tokio::net::TcpListener;"
        result = matcher.match_patterns(file_path="server.txt", content=content)
        assert result is not None
        assert result["agent"] == "@rust-specialist"
        assert result["confidence"] == 0.90

    def test_go_github_import(self, matcher):
        """Test Go GitHub import detection."""
        content = 'import "github.com/gin-gonic/gin"'
        result = matcher.match_patterns(file_path="server.txt", content=content)
        assert result is not None
        assert result["agent"] == "@go-specialist"
        assert result["confidence"] == 0.90

    def test_database_sqlalchemy_import(self, matcher):
        """Test SQLAlchemy import detection."""
        content = "from sqlalchemy import create_engine"
        result = matcher.match_patterns(file_path="db.txt", content=content)
        assert result is not None
        assert result["agent"] == "@database-specialist"
        assert result["confidence"] == 0.90


class TestQualityGatePatterns:
    """Test quality gate pattern matching."""

    @pytest.fixture
    def matcher(self):
        return PatternMatcher()

    def test_git_commit_triggers_review(self, matcher):
        """Test git commit tool triggers @code-reviewer."""
        result = matcher.match_patterns(tool_name="git commit")
        assert result is not None
        assert result["agent"] == "@code-reviewer"
        assert result["confidence"] == 1.0
        assert result["method"] == "mandatory"

    def test_git_tool_triggers_review(self, matcher):
        """Test generic git tool triggers @code-reviewer."""
        result = matcher.match_patterns(tool_name="git")
        assert result is not None
        assert result["agent"] == "@code-reviewer"
        assert result["confidence"] == 1.0

    def test_merge_triggers_review(self, matcher):
        """Test merge tool triggers @code-reviewer."""
        result = matcher.match_patterns(tool_name="merge branch")
        assert result is not None
        assert result["agent"] == "@code-reviewer"
        assert result["confidence"] == 1.0

    def test_quality_gate_priority(self, matcher):
        """Test quality gate has priority over file extension."""
        result = matcher.match_patterns(tool_name="git commit", file_path="api.py")
        assert result["agent"] == "@code-reviewer"
        assert result["confidence"] == 1.0


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def matcher(self):
        return PatternMatcher()

    def test_empty_inputs_returns_none(self, matcher):
        """Test empty inputs return None."""
        result = matcher.match_patterns()
        assert result is None

    def test_none_inputs_returns_none(self, matcher):
        """Test None inputs return None."""
        result = matcher.match_patterns(
            file_path=None, content=None, user_query=None, tool_name=None
        )
        assert result is None

    def test_whitespace_only_content_returns_none(self, matcher):
        """Test whitespace-only content returns None."""
        result = matcher.match_patterns(content="   \n\t  ", user_query="   ")
        assert result is None

    def test_malformed_file_path_no_crash(self, matcher):
        """Test malformed file path does not crash."""
        result = matcher.match_patterns(file_path="////...")
        assert result is None

    def test_case_insensitive_tool_name(self, matcher):
        """Test tool name matching is case-insensitive."""
        result1 = matcher.match_patterns(tool_name="GIT COMMIT")
        result2 = matcher.match_patterns(tool_name="git commit")
        assert result1["agent"] == result2["agent"] == "@code-reviewer"
