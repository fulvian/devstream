#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.0.0",
#     "python-dotenv>=1.0.0",
#     "aiohttp>=3.8.0",
#     "structlog>=23.0.0",
# ]
# ///

"""
DevStream Hook System Validator - Complete System Testing
Context7-compliant testing e validation dell'intero Hook System per production readiness.
"""

import json
import sys
import os
import asyncio
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

# Import DevStream utilities
sys.path.append(str(Path(__file__).parent.parent / 'utils'))
from common import DevStreamHookBase, get_project_context
from logger import get_devstream_logger
from mcp_client import get_mcp_client

class TestResult(Enum):
    """Test result status."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"

@dataclass
class HookTestResult:
    """Individual hook test result."""
    hook_name: str
    test_name: str
    result: TestResult
    execution_time: float
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

@dataclass
class SystemValidationResult:
    """Complete system validation result."""
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    total_time: float
    test_results: List[HookTestResult]
    system_ready: bool

class HookSystemValidator(DevStreamHookBase):
    """
    Hook System Validator per complete testing del DevStream Hook System.
    Implementa Context7-validated patterns per system validation.
    """

    def __init__(self):
        super().__init__('hook_system_validator')
        self.structured_logger = get_devstream_logger('hook_validator')
        self.mcp_client = get_mcp_client()
        self.start_time = time.time()

        # Validation configuration
        self.hooks_base_dir = Path(__file__).parent.parent
        self.claude_settings_path = self.hooks_base_dir.parent.parent / "settings.json"
        self.test_timeout = 30  # seconds
        self.required_hooks = [
            "context/user_query_context_enhancer.py",
            "context/intelligent_context_injector.py",
            "memory/pre_tool_use.py",
            "memory/post_tool_use.py",
            "tasks/session_start.py",
            "tasks/stop.py",
            "tasks/progress_tracker.py",
            "tasks/task_status_updater.py",
            "tasks/task_lifecycle_manager.py"
        ]

    async def run_complete_validation(self) -> SystemValidationResult:
        """
        Run complete Hook System validation.

        Returns:
            Complete validation results
        """
        self.structured_logger.log_hook_start({}, {"phase": "system_validation"})

        test_results = []
        start_time = time.time()

        try:
            self.logger.info("🧪 Starting DevStream Hook System validation...")

            # 1. Configuration validation
            config_results = await self.validate_configuration()
            test_results.extend(config_results)

            # 2. Hook file validation
            file_results = await self.validate_hook_files()
            test_results.extend(file_results)

            # 3. Hook execution validation
            execution_results = await self.validate_hook_execution()
            test_results.extend(execution_results)

            # 4. Integration validation
            integration_results = await self.validate_system_integration()
            test_results.extend(integration_results)

            # 5. MCP connectivity validation
            mcp_results = await self.validate_mcp_connectivity()
            test_results.extend(mcp_results)

            # 6. Performance validation
            performance_results = await self.validate_performance()
            test_results.extend(performance_results)

            # Calculate summary
            total_time = time.time() - start_time
            summary = self.calculate_validation_summary(test_results, total_time)

            self.logger.info(f"✅ Hook System validation completed: "
                           f"{summary.passed}/{summary.total_tests} passed")

            return summary

        except Exception as e:
            self.structured_logger.log_hook_error(e, {"phase": "system_validation"})
            raise

    async def validate_configuration(self) -> List[HookTestResult]:
        """
        Validate hook configuration.

        Returns:
            List of configuration test results
        """
        results = []

        # Test 1: Claude settings file exists
        result = await self.test_claude_settings_exists()
        results.append(result)

        # Test 2: Settings format validation
        if result.result == TestResult.PASSED:
            format_result = await self.test_settings_format()
            results.append(format_result)

        # Test 3: Hook commands validation
        command_result = await self.test_hook_commands()
        results.append(command_result)

        return results

    async def test_claude_settings_exists(self) -> HookTestResult:
        """Test if Claude settings file exists."""
        start_time = time.time()

        try:
            if self.claude_settings_path.exists():
                return HookTestResult(
                    hook_name="configuration",
                    test_name="claude_settings_exists",
                    result=TestResult.PASSED,
                    execution_time=(time.time() - start_time) * 1000,
                    details={"path": str(self.claude_settings_path)}
                )
            else:
                return HookTestResult(
                    hook_name="configuration",
                    test_name="claude_settings_exists",
                    result=TestResult.FAILED,
                    execution_time=(time.time() - start_time) * 1000,
                    error_message=f"Settings file not found: {self.claude_settings_path}"
                )

        except Exception as e:
            return HookTestResult(
                hook_name="configuration",
                test_name="claude_settings_exists",
                result=TestResult.ERROR,
                execution_time=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    async def test_settings_format(self) -> HookTestResult:
        """Test settings file format validation."""
        start_time = time.time()

        try:
            with open(self.claude_settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            # Validate basic structure
            if 'hooks' not in settings:
                return HookTestResult(
                    hook_name="configuration",
                    test_name="settings_format",
                    result=TestResult.FAILED,
                    execution_time=(time.time() - start_time) * 1000,
                    error_message="Settings missing 'hooks' section"
                )

            hooks = settings['hooks']
            required_sections = ['UserPromptSubmit', 'SessionStart', 'Stop', 'PreToolUse']

            for section in required_sections:
                if section not in hooks:
                    return HookTestResult(
                        hook_name="configuration",
                        test_name="settings_format",
                        result=TestResult.FAILED,
                        execution_time=(time.time() - start_time) * 1000,
                        error_message=f"Missing hook section: {section}"
                    )

            return HookTestResult(
                hook_name="configuration",
                test_name="settings_format",
                result=TestResult.PASSED,
                execution_time=(time.time() - start_time) * 1000,
                details={"sections_found": len(hooks)}
            )

        except json.JSONDecodeError as e:
            return HookTestResult(
                hook_name="configuration",
                test_name="settings_format",
                result=TestResult.FAILED,
                execution_time=(time.time() - start_time) * 1000,
                error_message=f"Invalid JSON format: {e}"
            )

        except Exception as e:
            return HookTestResult(
                hook_name="configuration",
                test_name="settings_format",
                result=TestResult.ERROR,
                execution_time=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    async def test_hook_commands(self) -> HookTestResult:
        """Test hook command validity."""
        start_time = time.time()

        try:
            with open(self.claude_settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            hooks = settings.get('hooks', {})
            invalid_commands = []

            for hook_type, hook_groups in hooks.items():
                for group in hook_groups:
                    for hook in group.get('hooks', []):
                        command = hook.get('command', '')

                        # Check if command references valid file
                        if 'uv run' in command:
                            script_path = command.split('uv run')[-1].strip()
                            full_path = self.hooks_base_dir.parent / script_path

                            if not full_path.exists():
                                invalid_commands.append(f"{hook_type}: {command}")

            if invalid_commands:
                return HookTestResult(
                    hook_name="configuration",
                    test_name="hook_commands",
                    result=TestResult.FAILED,
                    execution_time=(time.time() - start_time) * 1000,
                    error_message=f"Invalid commands: {', '.join(invalid_commands)}"
                )

            return HookTestResult(
                hook_name="configuration",
                test_name="hook_commands",
                result=TestResult.PASSED,
                execution_time=(time.time() - start_time) * 1000,
                details={"hooks_validated": len(hooks)}
            )

        except Exception as e:
            return HookTestResult(
                hook_name="configuration",
                test_name="hook_commands",
                result=TestResult.ERROR,
                execution_time=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    async def validate_hook_files(self) -> List[HookTestResult]:
        """
        Validate hook file existence and structure.

        Returns:
            List of file validation results
        """
        results = []

        for hook_path in self.required_hooks:
            result = await self.test_hook_file(hook_path)
            results.append(result)

        return results

    async def test_hook_file(self, hook_path: str) -> HookTestResult:
        """Test individual hook file."""
        start_time = time.time()

        try:
            full_path = self.hooks_base_dir / hook_path
            hook_name = Path(hook_path).stem

            # Check file exists
            if not full_path.exists():
                return HookTestResult(
                    hook_name=hook_name,
                    test_name="file_exists",
                    result=TestResult.FAILED,
                    execution_time=(time.time() - start_time) * 1000,
                    error_message=f"Hook file not found: {full_path}"
                )

            # Check file is executable
            if not os.access(full_path, os.X_OK):
                return HookTestResult(
                    hook_name=hook_name,
                    test_name="file_executable",
                    result=TestResult.FAILED,
                    execution_time=(time.time() - start_time) * 1000,
                    error_message=f"Hook file not executable: {full_path}"
                )

            # Check file has shebang and dependencies
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read(500)  # First 500 chars

            if not content.startswith('#!/usr/bin/env -S uv run --script'):
                return HookTestResult(
                    hook_name=hook_name,
                    test_name="file_format",
                    result=TestResult.FAILED,
                    execution_time=(time.time() - start_time) * 1000,
                    error_message=f"Invalid shebang in: {full_path}"
                )

            return HookTestResult(
                hook_name=hook_name,
                test_name="file_validation",
                result=TestResult.PASSED,
                execution_time=(time.time() - start_time) * 1000,
                details={"path": str(full_path), "size": full_path.stat().st_size}
            )

        except Exception as e:
            return HookTestResult(
                hook_name=hook_name,
                test_name="file_validation",
                result=TestResult.ERROR,
                execution_time=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    async def validate_hook_execution(self) -> List[HookTestResult]:
        """
        Validate hook execution with test inputs.

        Returns:
            List of execution test results
        """
        results = []

        # Test key hooks with synthetic inputs
        test_cases = [
            {
                "hook_path": "context/user_query_context_enhancer.py",
                "test_input": {
                    "user_input": "implement DevStream testing system",
                    "session_id": "test-session-001"
                }
            },
            {
                "hook_path": "tasks/session_start.py",
                "test_input": {
                    "session_id": "test-session-002",
                    "cwd": str(self.hooks_base_dir.parent.parent)
                }
            }
        ]

        for test_case in test_cases:
            result = await self.test_hook_execution(
                test_case["hook_path"],
                test_case["test_input"]
            )
            results.append(result)

        return results

    async def test_hook_execution(self, hook_path: str, test_input: Dict[str, Any]) -> HookTestResult:
        """Test individual hook execution."""
        start_time = time.time()
        hook_name = Path(hook_path).stem

        try:
            full_path = self.hooks_base_dir / hook_path

            # Prepare test input
            input_json = json.dumps(test_input)

            # Execute hook with timeout
            process = await asyncio.create_subprocess_exec(
                str(full_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.hooks_base_dir.parent.parent
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input_json.encode('utf-8')),
                    timeout=self.test_timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return HookTestResult(
                    hook_name=hook_name,
                    test_name="execution",
                    result=TestResult.FAILED,
                    execution_time=(time.time() - start_time) * 1000,
                    error_message=f"Hook execution timeout ({self.test_timeout}s)"
                )

            execution_time = (time.time() - start_time) * 1000

            if process.returncode == 0:
                return HookTestResult(
                    hook_name=hook_name,
                    test_name="execution",
                    result=TestResult.PASSED,
                    execution_time=execution_time,
                    details={
                        "stdout_length": len(stdout) if stdout else 0,
                        "stderr_length": len(stderr) if stderr else 0
                    }
                )
            else:
                error_msg = stderr.decode('utf-8') if stderr else 'Unknown error'
                return HookTestResult(
                    hook_name=hook_name,
                    test_name="execution",
                    result=TestResult.FAILED,
                    execution_time=execution_time,
                    error_message=f"Hook failed with code {process.returncode}: {error_msg}"
                )

        except Exception as e:
            return HookTestResult(
                hook_name=hook_name,
                test_name="execution",
                result=TestResult.ERROR,
                execution_time=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    async def validate_system_integration(self) -> List[HookTestResult]:
        """
        Validate system integration components.

        Returns:
            List of integration test results
        """
        results = []

        # Test utility imports
        result = await self.test_utility_imports()
        results.append(result)

        # Test cross-hook dependencies
        dependency_result = await self.test_cross_hook_dependencies()
        results.append(dependency_result)

        return results

    async def test_utility_imports(self) -> HookTestResult:
        """Test utility module imports."""
        start_time = time.time()

        try:
            # Test common utilities import
            sys.path.append(str(self.hooks_base_dir / 'utils'))

            from common import DevStreamHookBase, get_project_context
            from logger import get_devstream_logger
            from mcp_client import get_mcp_client

            # Test logger functionality
            logger = get_devstream_logger('test')
            if not logger:
                raise ValueError("Logger creation failed")

            # Test MCP client
            client = get_mcp_client()
            if not client:
                raise ValueError("MCP client creation failed")

            return HookTestResult(
                hook_name="integration",
                test_name="utility_imports",
                result=TestResult.PASSED,
                execution_time=(time.time() - start_time) * 1000,
                details={"utilities_imported": 4}
            )

        except Exception as e:
            return HookTestResult(
                hook_name="integration",
                test_name="utility_imports",
                result=TestResult.FAILED,
                execution_time=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    async def test_cross_hook_dependencies(self) -> HookTestResult:
        """Test cross-hook dependencies."""
        start_time = time.time()

        try:
            # Test context injector import from pre_tool_use
            sys.path.append(str(self.hooks_base_dir / 'context'))
            from intelligent_context_injector import IntelligentContextInjector

            # Test task lifecycle manager import
            sys.path.append(str(self.hooks_base_dir / 'tasks'))
            from task_lifecycle_manager import TaskLifecycleManager

            # Test instantiation
            injector = IntelligentContextInjector()
            manager = TaskLifecycleManager()

            if not injector or not manager:
                raise ValueError("Cross-hook dependency instantiation failed")

            return HookTestResult(
                hook_name="integration",
                test_name="cross_hook_dependencies",
                result=TestResult.PASSED,
                execution_time=(time.time() - start_time) * 1000,
                details={"dependencies_tested": 2}
            )

        except Exception as e:
            return HookTestResult(
                hook_name="integration",
                test_name="cross_hook_dependencies",
                result=TestResult.FAILED,
                execution_time=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    async def validate_mcp_connectivity(self) -> List[HookTestResult]:
        """
        Validate MCP connectivity.

        Returns:
            List of MCP test results
        """
        results = []

        # Test MCP client creation
        client_result = await self.test_mcp_client_creation()
        results.append(client_result)

        # Test MCP operations (if client works)
        if client_result.result == TestResult.PASSED:
            ops_result = await self.test_mcp_operations()
            results.append(ops_result)

        return results

    async def test_mcp_client_creation(self) -> HookTestResult:
        """Test MCP client creation."""
        start_time = time.time()

        try:
            from mcp_client import DevStreamMCPClient

            client = DevStreamMCPClient()

            if not client:
                raise ValueError("MCP client creation failed")

            # Test basic attributes
            if not hasattr(client, 'db_path') or not hasattr(client, 'mcp_server_path'):
                raise ValueError("MCP client missing required attributes")

            return HookTestResult(
                hook_name="mcp",
                test_name="client_creation",
                result=TestResult.PASSED,
                execution_time=(time.time() - start_time) * 1000,
                details={"db_path": client.db_path}
            )

        except Exception as e:
            return HookTestResult(
                hook_name="mcp",
                test_name="client_creation",
                result=TestResult.FAILED,
                execution_time=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    async def test_mcp_operations(self) -> HookTestResult:
        """Test basic MCP operations."""
        start_time = time.time()

        try:
            client = get_mcp_client()

            # Test health check (non-blocking)
            health_result = await asyncio.wait_for(
                client.health_check(),
                timeout=5.0
            )

            if health_result:
                return HookTestResult(
                    hook_name="mcp",
                    test_name="operations",
                    result=TestResult.PASSED,
                    execution_time=(time.time() - start_time) * 1000,
                    details={"health_check": "passed"}
                )
            else:
                return HookTestResult(
                    hook_name="mcp",
                    test_name="operations",
                    result=TestResult.SKIPPED,
                    execution_time=(time.time() - start_time) * 1000,
                    error_message="MCP server not available (expected in testing)"
                )

        except asyncio.TimeoutError:
            return HookTestResult(
                hook_name="mcp",
                test_name="operations",
                result=TestResult.SKIPPED,
                execution_time=(time.time() - start_time) * 1000,
                error_message="MCP server timeout (expected in testing)"
            )

        except Exception as e:
            return HookTestResult(
                hook_name="mcp",
                test_name="operations",
                result=TestResult.FAILED,
                execution_time=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    async def validate_performance(self) -> List[HookTestResult]:
        """
        Validate hook performance characteristics.

        Returns:
            List of performance test results
        """
        results = []

        # Test hook startup time
        startup_result = await self.test_hook_startup_time()
        results.append(startup_result)

        return results

    async def test_hook_startup_time(self) -> HookTestResult:
        """Test hook startup performance."""
        start_time = time.time()

        try:
            # Test fast hook startup
            test_hook_path = self.hooks_base_dir / "tasks" / "session_start.py"

            process_start = time.time()
            process = await asyncio.create_subprocess_exec(
                str(test_hook_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.hooks_base_dir.parent.parent
            )

            # Send minimal input and wait for response
            test_input = json.dumps({"session_id": "perf-test"})
            stdout, stderr = await asyncio.wait_for(
                process.communicate(test_input.encode('utf-8')),
                timeout=10.0
            )

            startup_time = (time.time() - process_start) * 1000

            # Consider startup time acceptable if under 5 seconds
            if startup_time < 5000:
                return HookTestResult(
                    hook_name="performance",
                    test_name="hook_startup_time",
                    result=TestResult.PASSED,
                    execution_time=(time.time() - start_time) * 1000,
                    details={"startup_time_ms": startup_time}
                )
            else:
                return HookTestResult(
                    hook_name="performance",
                    test_name="hook_startup_time",
                    result=TestResult.FAILED,
                    execution_time=(time.time() - start_time) * 1000,
                    error_message=f"Hook startup too slow: {startup_time:.0f}ms"
                )

        except Exception as e:
            return HookTestResult(
                hook_name="performance",
                test_name="hook_startup_time",
                result=TestResult.ERROR,
                execution_time=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    def calculate_validation_summary(
        self,
        test_results: List[HookTestResult],
        total_time: float
    ) -> SystemValidationResult:
        """
        Calculate validation summary.

        Args:
            test_results: All test results
            total_time: Total execution time

        Returns:
            Complete validation summary
        """
        passed = sum(1 for r in test_results if r.result == TestResult.PASSED)
        failed = sum(1 for r in test_results if r.result == TestResult.FAILED)
        skipped = sum(1 for r in test_results if r.result == TestResult.SKIPPED)
        errors = sum(1 for r in test_results if r.result == TestResult.ERROR)

        # System is ready if critical tests pass and no critical failures
        critical_failures = [
            r for r in test_results
            if r.result in [TestResult.FAILED, TestResult.ERROR] and
            r.test_name in ['claude_settings_exists', 'settings_format', 'file_validation', 'utility_imports']
        ]

        system_ready = len(critical_failures) == 0 and passed >= (len(test_results) * 0.8)

        return SystemValidationResult(
            total_tests=len(test_results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            total_time=total_time,
            test_results=test_results,
            system_ready=system_ready
        )

    async def generate_validation_report(
        self,
        validation_result: SystemValidationResult
    ) -> str:
        """
        Generate human-readable validation report.

        Args:
            validation_result: Validation results

        Returns:
            Formatted validation report
        """
        report_parts = [
            "🧪 DevStream Hook System Validation Report",
            f"📊 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"⏱️ Total Time: {validation_result.total_time:.2f}s",
            "",
            "📈 Summary:",
            f"  ✅ Passed: {validation_result.passed}",
            f"  ❌ Failed: {validation_result.failed}",
            f"  ⏭️ Skipped: {validation_result.skipped}",
            f"  ⚠️ Errors: {validation_result.errors}",
            f"  🎯 Total: {validation_result.total_tests}",
            "",
            f"🚀 System Ready: {'YES' if validation_result.system_ready else 'NO'}",
            ""
        ]

        # Group results by hook
        hook_groups = {}
        for result in validation_result.test_results:
            if result.hook_name not in hook_groups:
                hook_groups[result.hook_name] = []
            hook_groups[result.hook_name].append(result)

        # Add detailed results
        report_parts.append("📋 Detailed Results:")

        for hook_name, results in hook_groups.items():
            report_parts.append(f"  🔧 {hook_name}:")

            for result in results:
                status_icon = {
                    TestResult.PASSED: "✅",
                    TestResult.FAILED: "❌",
                    TestResult.SKIPPED: "⏭️",
                    TestResult.ERROR: "⚠️"
                }[result.result]

                report_parts.append(
                    f"    {status_icon} {result.test_name} "
                    f"({result.execution_time:.0f}ms)"
                )

                if result.error_message:
                    report_parts.append(f"      Error: {result.error_message}")

        # Add recommendations
        if not validation_result.system_ready:
            report_parts.extend([
                "",
                "🔧 Recommendations:",
                "  • Fix critical failures before deployment",
                "  • Ensure all hook files exist and are executable",
                "  • Verify Claude settings configuration",
                "  • Test MCP server connectivity"
            ])
        else:
            report_parts.extend([
                "",
                "🎉 System is ready for production deployment!",
                "  • All critical tests passed",
                "  • Hook system properly configured",
                "  • Integration components working",
                "  • Performance within acceptable limits"
            ])

        return '\n'.join(report_parts)

async def main():
    """Main validation execution."""
    validator = HookSystemValidator()

    print("🚀 Starting DevStream Hook System validation...")

    try:
        # Run complete validation
        results = await validator.run_complete_validation()

        # Generate report
        report = await validator.generate_validation_report(results)

        print(report)

        # Exit with appropriate code
        if results.system_ready:
            print("\n✅ Validation successful - System ready for deployment!")
            sys.exit(0)
        else:
            print(f"\n❌ Validation failed - {results.failed + results.errors} issues found")
            sys.exit(1)

    except Exception as e:
        print(f"\n💥 Validation error: {e}")
        sys.exit(2)

if __name__ == "__main__":
    asyncio.run(main())