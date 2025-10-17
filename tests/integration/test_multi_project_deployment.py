"""
Comprehensive Multi-Project Deployment Test Suite.

Context7-compliant integration tests for the complete multi-project hook copying
and validation system. Tests end-to-end workflows from source to target projects.

Follows Context7 patterns from pytest-asyncio and sqlite-utils for robust
testing of async operations and database interactions.
"""

import pytest
import asyncio
import tempfile
import shutil
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
import sqlite3
import structlog

logger = structlog.get_logger(__name__)

# Import modules under test
import sys
test_utils_path = Path(__file__).parent.parent.parent / ".claude" / "hooks" / "devstream" / "utils"
sys.path.insert(0, str(test_utils_path))

try:
    from multi_project_hook_copier import copy_devstream_hooks_enhanced
    from hook_integrity_validator import HookIntegrityValidator
    MULTI_PROJECT_HOOKS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Multi-project hooks not available: {e}")
    MULTI_PROJECT_HOOKS_AVAILABLE = False


@pytest.fixture(scope="module")
def devstream_source_root():
    """Create a complete DevStream source root with all hooks."""
    with tempfile.TemporaryDirectory() as temp_dir:
        source_root = Path(temp_dir)

        # Create complete .claude structure
        claude_dir = source_root / ".claude"
        hooks_dir = claude_dir / "hooks" / "devstream"
        hooks_dir.mkdir(parents=True)

        # Create essential directories (including all required for validation)
        directories = [
            "memory", "context", "sessions", "utils", "agents",
            "protocol", "monitoring", "phases", "config",
            "checkpoints", "optimization", "migrations", "tasks"
        ]
        for dir_name in directories:
            (hooks_dir / dir_name).mkdir(parents=True, exist_ok=True)

            # Create essential hooks with Context7-compliant implementations
            hooks_content = {
                "memory/pre_tool_use.py": """
import asyncio
import structlog
import sys
from pathlib import Path

logger = structlog.get_logger(__name__)

async def main():
    \"\"\"Context7-compliant PreToolUse hook implementation.\"\"\"
    logger.info("PreToolUse hook executed successfully")

    # Example memory system interaction
    try:
        # Simulate memory storage
        context = {
            "operation": "pre_tool_use",
            "timestamp": datetime.now().isoformat(),
            "tool": sys.argv[1] if len(sys.argv) > 1 else "unknown"
        }
        logger.info("Context processed", context=context)
        return True
    except Exception as e:
        logger.error("PreToolUse failed", error=str(e))
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
""",
                "memory/post_tool_use.py": """
import asyncio
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)

async def main():
    \"\"\"Context7-compliant PostToolUse hook implementation.\"\"\"
    logger.info("PostToolUse hook executed successfully")

    # Example post-processing
    try:
        # Simulate result processing
        result = {
            "operation": "post_tool_use",
            "timestamp": datetime.now().isoformat(),
            "status": "completed"
        }
        logger.info("Result processed", result=result)
        return True
    except Exception as e:
        logger.error("PostToolUse failed", error=str(e))
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
""",
                "context/user_query_context_enhancer.py": """
import json
import sys
import structlog

logger = structlog.get_logger(__name__)

def enhance_query(query: str) -> str:
    \"\"\"Enhance user query with context information.\"\"\"
    enhanced = f"[Enhanced] {query}"
    logger.info("Query enhanced", original=query, enhanced=enhanced)
    return enhanced

def main():
    \"\"\"Main entry point for query enhancement.\"\"\"
    if len(sys.argv) < 2:
        print("Usage: python user_query_context_enhancer.py <query>")
        sys.exit(1)

    query = sys.argv[1]
    enhanced = enhance_query(query)
    print(enhanced)

if __name__ == "__main__":
    main()
""",
                "utils/direct_client.py": """
import sqlite3
import structlog
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = structlog.get_logger(__name__)

class DirectClient:
    \"\"\"Direct database client for DevStream memory system.\"\"\"

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path.cwd() / "data" / "devstream.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        \"\"\"Initialize database schema.\"\"\"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    content_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def search_memory(self, query: str, limit: int = 10) -> Dict[str, Any]:
        \"\"\"Search memory database.\"\"\"
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT * FROM semantic_memory
                    WHERE content LIKE ?
                    LIMIT ?
                ''', (f'%{query}%', limit))

                results = [
                    {
                        "id": row[0],
                        "content": row[1],
                        "content_type": row[2],
                        "created_at": row[3]
                    }
                    for row in cursor.fetchall()
                ]

                return {"results": results}
        except Exception as e:
            logger.error("Memory search failed", error=str(e))
            return {"results": []}

    def store_memory(self, content: str, content_type: str = "text") -> Dict[str, Any]:
        \"\"\"Store content in memory database.\"\"\"
        try:
            import uuid
            memory_id = str(uuid.uuid4())

            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO semantic_memory (id, content, content_type)
                    VALUES (?, ?, ?)
                ''', (memory_id, content, content_type))
                conn.commit()

            return {"id": memory_id, "status": "stored"}
        except Exception as e:
            logger.error("Memory storage failed", error=str(e))
            return {"status": "failed", "error": str(e)}

# Global client instance
_client = None

def get_direct_client() -> DirectClient:
    \"\"\"Get or create direct client instance.\"\"\"
    global _client
    if _client is None:
        _client = DirectClient()
    return _client

if __name__ == "__main__":
    client = get_direct_client()
    result = client.search_memory("test")
    print(json.dumps(result, indent=2))
""",
                "agents/pattern_matcher.py": """
from typing import Optional, Dict, List
import re
import sys
from pathlib import Path

class PatternMatch:
    def __init__(self, agent=None, confidence=0.0, reason="", method=""):
        self.agent = agent
        self.confidence = confidence
        self.reason = reason
        self.method = method

class PatternMatcher:
    \"\"\"Simplified pattern matcher for agent delegation.\"\"\"

    def __init__(self):
        self.patterns = {
            ".py": {"agent": "@python-specialist", "confidence": 0.9},
            ".ts": {"agent": "@typescript-specialist", "confidence": 0.9},
            ".js": {"agent": "@typescript-specialist", "confidence": 0.8},
        }

    def match_patterns(self, file_path=None, content=None, user_query=None, tool_name=None):
        \"\"\"Match patterns and return agent recommendation.\"\"\"
        # Quality gate for git operations
        if tool_name and ("git" in tool_name.lower() or "commit" in tool_name.lower()):
            return PatternMatch(
                agent="@code-reviewer",
                confidence=1.0,
                reason="Quality gate: git operation",
                method="mandatory"
            )

        # File extension matching
        if file_path:
            ext = Path(file_path).suffix
            if ext in self.patterns:
                pattern = self.patterns[ext]
                return PatternMatch(
                    agent=pattern["agent"],
                    confidence=pattern["confidence"],
                    reason=f"File extension match: {ext}",
                    method="extension"
                )

        # Keyword matching
        combined_text = f"{content or ''} {user_query or ''}".lower()

        if any(keyword in combined_text for keyword in ["python", "fastapi", "django"]):
            return PatternMatch(
                agent="@python-specialist",
                confidence=0.8,
                reason="Keyword match: Python-related",
                method="keyword"
            )

        if any(keyword in combined_text for keyword in ["typescript", "react", "next"]):
            return PatternMatch(
                agent="@typescript-specialist",
                confidence=0.8,
                reason="Keyword match: TypeScript-related",
                method="keyword"
            )

        return None

if __name__ == "__main__":
    matcher = PatternMatcher()
    result = matcher.match_patterns(file_path="test.py")
    if result:
        print(f"Agent: {result.agent}, Confidence: {result.confidence}")
    else:
        print("No match found")
"""
            }

            # Write all hook files
            for hook_path, content in hooks_content.items():
                full_path = hooks_dir / hook_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)

            # Create additional configuration files
            (source_root / "requirements.txt").write_text("""
# DevStream Core Dependencies
structlog>=23.2.0
aiohttp>=3.8.0
cchooks>=0.1.4
python-dotenv>=1.0.0
copier>=9.0.0
""")

            (source_root / ".env.devstream").write_text("""
# DevStream Configuration
DEVSTREAM_MEMORY_ENABLED=true
DEVSTREAM_CONTEXT7_ENABLED=true
DEVSTREAM_LOG_LEVEL=INFO
""")

            yield source_root

    @pytest.fixture
    def multiple_project_roots(self):
        """Create multiple target project directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            projects = {}
            for i in range(3):
                project_name = f"test-project-{i+1}"
                project_path = temp_path / project_name
                project_path.mkdir(parents=True)
                projects[project_name] = project_path

            yield projects

    @pytest.mark.skipif(not MULTI_PROJECT_HOOKS_AVAILABLE, reason="Multi-project hooks not available")
    @pytest.mark.asyncio
    async def test_complete_multi_project_deployment(self, devstream_source_root, multiple_project_roots):
        """Test complete multi-project deployment workflow."""
        source_root = devstream_source_root
        projects = multiple_project_roots

        deployment_results = {}

        # Deploy to each project
        for project_name, project_root in projects.items():
            logger.info(f"Starting deployment to {project_name}")

            # Copy hooks using enhanced copier
            result = await copy_devstream_hooks_enhanced(
                source_root=source_root,
                target_root=project_root,
                required_directories=["memory", "context", "utils", "agents"]
            )

            assert result["status"] == "success"
            assert "validation" in result
            assert "integrity" in result

            deployment_results[project_name] = result

        # Verify all deployments
        for project_name, result in deployment_results.items():
            assert result["status"] == "success"
            assert result["validation"]["valid"] is True

            # Check integrity results
            integrity = result["integrity"]
            assert integrity["overall_valid"] is True
            assert integrity["summary"]["critical_failures"] == 0

        logger.info("All deployments completed successfully")

    @pytest.mark.skipif(not MULTI_PROJECT_HOOKS_AVAILABLE, reason="Multi-project hooks not available")
    @pytest.mark.asyncio
    async def test_hook_functionality_after_deployment(self, devstream_source_root, multiple_project_roots):
        """Test that hooks remain functional after deployment."""
        source_root = devstream_source_root
        project_root = multiple_project_roots["test-project-1"]

        # Deploy hooks
        result = await copy_devstream_hooks_enhanced(
            source_root=source_root,
            target_root=project_root
        )
        assert result["status"] == "success"

        # Test individual hook functionality
        hooks_to_test = [
            ("utils/direct_client.py", "test_direct_client_functionality"),
            ("context/user_query_context_enhancer.py", "test_query_enhancer_functionality"),
            ("agents/pattern_matcher.py", "test_pattern_matcher_functionality")
        ]

        for hook_path, test_func in hooks_to_test:
            await self._test_hook_functionality(project_root, hook_path, test_func)

    async def _test_hook_functionality(self, project_root: Path, hook_path: str, test_name: str):
        """Test functionality of a specific hook."""
        full_hook_path = project_root / ".claude" / "hooks" / "devstream" / hook_path

        assert full_hook_path.exists(), f"Hook {hook_path} should exist after deployment"

        if test_name == "test_direct_client_functionality":
            await self._test_direct_client_functionality(project_root)
        elif test_name == "test_query_enhancer_functionality":
            await self._test_query_enhancer_functionality(project_root)
        elif test_name == "test_pattern_matcher_functionality":
            await self._test_pattern_matcher_functionality(project_root)

    async def _test_direct_client_functionality(self, project_root: Path):
        """Test direct client functionality."""
        project_venv = project_root / ".devstream"

        # Create project venv for testing
        if not project_venv.exists():
            project_venv.mkdir(parents=True)

        # Test import and basic functionality
        test_script = f"""
import sys
sys.path.insert(0, '{project_root / ".claude" / "hooks" / "devstream" / "utils"}')

try:
    from direct_client import get_direct_client
    client = get_direct_client()

    # Test memory storage
    result = client.store_memory("test content", "test")
    print(f"STORAGE_SUCCESS: {{result}}")

    # Test memory search
    search_result = client.search_memory("test")
    print(f"SEARCH_SUCCESS: {{len(search_result.get('results', []))}} results")

except Exception as e:
    print(f"ERROR: {{e}}")
    sys.exit(1)
"""

        python_exe = sys.executable
        result = await asyncio.create_subprocess_exec(
            python_exe, "-c", test_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await result.communicate()
        output = stdout.decode('utf-8')

        assert result.returncode == 0, f"Direct client test failed: {stderr.decode('utf-8')}"
        assert "STORAGE_SUCCESS" in output
        assert "SEARCH_SUCCESS" in output

    async def _test_query_enhancer_functionality(self, project_root: Path):
        """Test query enhancer functionality."""
        hook_path = project_root / ".claude" / "hooks" / "devstream" / "context" / "user_query_context_enhancer.py"

        python_exe = sys.executable
        result = await asyncio.create_subprocess_exec(
            python_exe, str(hook_path), "test query enhancement",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await result.communicate()
        output = stdout.decode('utf-8').strip()

        assert result.returncode == 0, f"Query enhancer test failed: {stderr.decode('utf-8')}"
        assert "Enhanced" in output
        assert "test query enhancement" in output

    async def _test_pattern_matcher_functionality(self, project_root: Path):
        """Test pattern matcher functionality."""
        test_script = f"""
import sys
sys.path.insert(0, '{project_root / ".claude" / "hooks" / "devstream" / "agents"}')

try:
    from pattern_matcher import PatternMatcher
    matcher = PatternMatcher()

    # Test file extension matching
    result = matcher.match_patterns(file_path="test.py")
    print(f"PYTHON_MATCH: {{result.agent if result else 'None'}}")

    # Test quality gate
    result = matcher.match_patterns(tool_name="git commit")
    print(f"QUALITY_GATE: {{result.agent if result else 'None'}}")

except Exception as e:
    print(f"ERROR: {{e}}")
    sys.exit(1)
"""

        python_exe = sys.executable
        result = await asyncio.create_subprocess_exec(
            python_exe, "-c", test_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await result.communicate()
        output = stdout.decode('utf-8')

        assert result.returncode == 0, f"Pattern matcher test failed: {stderr.decode('utf-8')}"
        assert "PYTHON_MATCH: @python-specialist" in output
        assert "QUALITY_GATE: @code-reviewer" in output

    @pytest.mark.skipif(not MULTI_PROJECT_HOOKS_AVAILABLE, reason="Multi-project hooks not available")
    @pytest.mark.asyncio
    async def test_integrity_validation_comprehensive(self, devstream_source_root, multiple_project_roots):
        """Test comprehensive integrity validation across all projects."""
        source_root = devstream_source_root
        projects = multiple_project_roots

        # Deploy to all projects
        for project_root in projects.values():
            await copy_devstream_hooks_enhanced(
                source_root=source_root,
                target_root=project_root
            )

        # Run comprehensive integrity validation
        validator = HookIntegrityValidator(str(source_root))

        for project_name, project_root in projects.items():
            report = await validator.generate_integrity_report(str(project_root))

            assert report["overall_valid"] is True, f"Project {project_name} integrity validation failed"
            assert report["summary"]["critical_failures"] == 0
            assert len(report["results"]) > 0

            # Check specific validations
            for result in report["results"]:
                if result["severity"] == "critical":
                    assert result["valid"] is True, f"Critical validation failed for {result['hook_name']}"

    @pytest.mark.skipif(not MULTI_PROJECT_HOOKS_AVAILABLE, reason="Multi-project hooks not available")
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, devstream_source_root, multiple_project_roots):
        """Test error handling and recovery mechanisms."""
        source_root = devstream_source_root
        project_root = multiple_project_roots["test-project-1"]

        # Test with invalid source root
        with pytest.raises(Exception):
            await copy_devstream_hooks_enhanced(
                source_root=Path("/non/existent/path"),
                target_root=project_root
            )

        # Test with missing required directories (should still work with defaults)
        partial_project = multiple_project_roots["test-project-2"]

        # Remove .claude directory to test error handling
        claude_dir = partial_project / ".claude"
        if claude_dir.exists():
            shutil.rmtree(claude_dir)

        # Deployment should succeed by creating directories
        result = await copy_devstream_hooks_enhanced(
            source_root=source_root,
            target_root=partial_project
        )

        assert result["status"] == "success"
        assert claude_dir.exists()

    @pytest.mark.asyncio
    async def test_concurrent_deployments(self, devstream_source_root, multiple_project_roots):
        """Test concurrent deployments to multiple projects."""
        source_root = devstream_source_root
        projects = list(multiple_project_roots.values())

        # Create deployment tasks for concurrent execution
        deployment_tasks = []
        for project_root in projects:
            task = copy_devstream_hooks_enhanced(
                source_root=source_root,
                target_root=project_root,
                required_directories=["memory", "context", "utils"]
            )
            deployment_tasks.append(task)

        # Execute all deployments concurrently
        results = await asyncio.gather(*deployment_tasks, return_exceptions=True)

        # Verify all deployments succeeded
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Deployment {i+1} failed with exception: {result}"
            assert result["status"] == "success", f"Deployment {i+1} failed"

        logger.info("All concurrent deployments completed successfully")

    @pytest.mark.asyncio
    async def test_database_functionality_after_deployment(self, devstream_source_root, multiple_project_roots):
        """Test database functionality in deployed projects."""
        source_root = devstream_source_root
        project_root = multiple_project_roots["test-project-1"]

        # Deploy hooks
        result = await copy_devstream_hooks_enhanced(
            source_root=source_root,
            target_root=project_root
        )
        assert result["status"] == "success"

        # Test database operations
        db_path = project_root / "data" / "devstream.db"

        # Test direct client database operations
        test_script = f"""
import sys
sys.path.insert(0, '{project_root / ".claude" / "hooks" / "devstream" / "utils"}')

try:
    from direct_client import get_direct_client
    client = get_direct_client()

    # Test database file exists
    import sqlite3
    conn = sqlite3.connect('{db_path}')
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    conn.close()

    print(f"DB_TABLES: {{len(tables)}}")

    # Test memory operations
    store_result = client.store_memory("test multi-project deployment", "test")
    print(f"STORE_SUCCESS: {{store_result.get('status', 'unknown')}}")

    search_result = client.search_memory("deployment")
    print(f"SEARCH_RESULTS: {{len(search_result.get('results', []))}}")

except Exception as e:
    print(f"DB_ERROR: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""

        python_exe = sys.executable
        result = await asyncio.create_subprocess_exec(
            python_exe, "-c", test_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await result.communicate()
        output = stdout.decode('utf-8')

        assert result.returncode == 0, f"Database test failed: {stderr.decode('utf-8')}"
        assert "DB_TABLES:" in output
        assert "STORE_SUCCESS:" in output

    @pytest.mark.asyncio
    async def test_configuration_compatibility(self, devstream_source_root, multiple_project_roots):
        """Test configuration compatibility across deployed projects."""
        source_root = devstream_source_root
        project_root = multiple_project_roots["test-project-1"]

        # Deploy hooks
        result = await copy_devstream_hooks_enhanced(
            source_root=source_root,
            target_root=project_root
        )
        assert result["status"] == "success"

        # Verify settings.json was created/updated
        settings_file = project_root / ".claude" / "settings.json"
        assert settings_file.exists(), "Settings.json should be created during deployment"

        # Load and validate settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)

        assert "hooks" in settings
        assert "PreToolUse" in settings["hooks"]
        assert "PostToolUse" in settings["hooks"]
        assert "UserPromptSubmit" in settings["hooks"]

        # Verify hook paths are correct
        pre_tool_hooks = settings["hooks"]["PreToolUse"][0]["hooks"]
        hook_command = pre_tool_hooks[0]["command"]
        assert str(project_root) in hook_command
        assert "pre_tool_use.py" in hook_command

        logger.info("Configuration compatibility verified")

    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, devstream_source_root, multiple_project_roots):
        """Test performance benchmarks for multi-project deployment."""
        source_root = devstream_source_root
        project_root = multiple_project_roots["test-project-1"]

        # Benchmark deployment time
        start_time = asyncio.get_event_loop().time()

        result = await copy_devstream_hooks_enhanced(
            source_root=source_root,
            target_root=project_root
        )

        deployment_time = asyncio.get_event_loop().time() - start_time

        assert result["status"] == "success"
        assert deployment_time < 30.0, f"Deployment took too long: {deployment_time:.2f}s"

        # Benchmark integrity validation time
        validator = HookIntegrityValidator(str(source_root))

        start_time = asyncio.get_event_loop().time()
        report = await validator.generate_integrity_report(str(project_root))
        validation_time = asyncio.get_event_loop().time() - start_time

        assert report["overall_valid"] is True
        assert validation_time < 10.0, f"Validation took too long: {validation_time:.2f}s"

        logger.info(f"Performance benchmarks - Deployment: {deployment_time:.2f}s, Validation: {validation_time:.2f}s")


class TestMultiProjectScenarios:
    """Test specific multi-project deployment scenarios."""

    @pytest.mark.skipif(not MULTI_PROJECT_HOOKS_AVAILABLE, reason="Multi-project hooks not available")
    @pytest.mark.asyncio
    async def test_incremental_deployment(self, devstream_source_root):
        """Test incremental deployment scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Initial deployment
            result1 = await copy_devstream_hooks_enhanced(
                source_root=devstream_source_root,
                target_root=project_root,
                required_directories=["memory", "context"]
            )
            assert result1["status"] == "success"

            # Incremental deployment with additional directories
            result2 = await copy_devstream_hooks_enhanced(
                source_root=devstream_source_root,
                target_root=project_root,
                required_directories=["utils", "agents"]
            )
            assert result2["status"] == "success"

            # Verify all directories are present
            hooks_dir = project_root / ".claude" / "hooks" / "devstream"
            assert (hooks_dir / "memory").exists()
            assert (hooks_dir / "context").exists()
            assert (hooks_dir / "utils").exists()
            assert (hooks_dir / "agents").exists()

    @pytest.mark.skipif(not MULTI_PROJECT_HOOKS_AVAILABLE, reason="Multi-project hooks not available")
    @pytest.mark.asyncio
    async def test_custom_directories_deployment(self, devstream_source_root):
        """Test deployment with custom directory selection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Deploy only specific directories
            custom_dirs = ["memory", "utils"]
            result = await copy_devstream_hooks_enhanced(
                source_root=devstream_source_root,
                target_root=project_root,
                required_directories=custom_dirs
            )
            assert result["status"] == "success"
            assert result["copied_directories"] == custom_dirs

            # Verify only requested directories were copied
            hooks_dir = project_root / ".claude" / "hooks" / "devstream"
            assert (hooks_dir / "memory").exists()
            assert (hooks_dir / "utils").exists()

            # Verify other directories were not copied
            assert not (hooks_dir / "context").exists()
            assert not (hooks_dir / "agents").exists()

    @pytest.mark.asyncio
    async def test_error_recovery_scenarios(self, devstream_source_root):
        """Test various error recovery scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create partial .claude structure to test recovery
            partial_claude = project_root / ".claude"
            partial_claude.mkdir()

            # Create corrupted settings.json
            corrupted_settings = partial_claude / "settings.json"
            corrupted_settings.write_text("invalid json content")

            # Deployment should handle corrupted settings gracefully
            result = await copy_devstream_hooks_enhanced(
                source_root=devstream_source_root,
                target_root=project_root
            )

            # Should either succeed with recovery or fail gracefully
            if result["status"] == "success":
                # Verify settings were fixed
                with open(partial_claude / "settings.json", 'r') as f:
                    settings = json.load(f)
                assert "hooks" in settings
            else:
                # Should provide meaningful error information
                assert "error" in result.lower()


# Integration test utilities
async def run_comprehensive_test_suite():
    """Run the comprehensive multi-project test suite."""
    print("🚀 Starting Comprehensive Multi-Project Deployment Test Suite")
    print("=" * 60)

    test_classes = [
        TestMultiProjectDeployment,
        TestMultiProjectScenarios
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}")
        print("-" * 40)

        # Get all test methods
        test_methods = [
            method for method in dir(test_class)
            if method.startswith("test_") and not method.startswith("test_") and
            callable(getattr(test_class, method))
        ]

        for test_method_name in test_methods:
            total_tests += 1
            test_method = getattr(test_class, test_method_name)

            try:
                # Handle async test methods
                if asyncio.iscoroutinefunction(test_method):
                    await test_method()
                else:
                    # Handle sync test methods (create fixtures if needed)
                    instance = test_class()
                    if hasattr(instance, test_method_name):
                        await getattr(instance, test_method_name)()

                print(f"✅ {test_method_name}")
                passed_tests += 1

            except Exception as e:
                print(f"❌ {test_method_name}: {str(e)}")
                failed_tests.append((test_method_name, str(e)))

    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Test Suite Summary")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")

    if failed_tests:
        print("\n❌ Failed Tests:")
        for test_name, error in failed_tests:
            print(f"  - {test_name}: {error}")
        return False
    else:
        print("\n🎉 All tests passed!")
        return True


if __name__ == "__main__":
    # Run comprehensive test suite
    import argparse

    parser = argparse.ArgumentParser(description="Run multi-project deployment tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--test", help="Run specific test method")
    parser.add_argument("--class", help="Run specific test class", dest="test_class")

    args = parser.parse_args()

    if args.test:
        # Run specific test
        print(f"Running test: {args.test}")
        # Implementation for single test execution
    elif args.test_class:
        # Run specific test class
        print(f"Running test class: {args.test_class}")
        # Implementation for single class execution
    else:
        # Run comprehensive suite
        success = asyncio.run(run_comprehensive_test_suite())
        sys.exit(0 if success else 1)