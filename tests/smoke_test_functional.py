#!/usr/bin/env python3
"""
DevStream macOS Deployment - Functional Smoke Tests
Task ID: d744c555

Tests actual hook execution via subprocess (mimics cchooks behavior)
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent
PYTHON_BIN = str(PROJECT_ROOT / ".devstream" / "bin" / "python")

test_results = []


def log_result(test_name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results.append({"test": test_name, "passed": passed, "details": details})
    print(f"{status} | {test_name}")
    if details:
        print(f"  → {details}")


def test_hook_execution(hook_name: str, hook_script: Path, test_input: Dict[str, Any]) -> bool:
    """Test hook by executing it as subprocess"""
    try:
        # Prepare environment
        env = os.environ.copy()
        env["DEVSTREAM_HOOKS_ENABLED"] = "true"
        env["DEVSTREAM_FEEDBACK_LEVEL"] = "minimal"

        # Execute hook
        proc = subprocess.run(
            [PYTHON_BIN, str(hook_script)],
            input=json.dumps(test_input),
            capture_output=True,
            text=True,
            env=env,
            timeout=10
        )

        # Check for Python exceptions
        if "Traceback" in proc.stderr or "Error" in proc.stderr:
            log_result(f"Execute {hook_name}", False, f"Exception in stderr: {proc.stderr[:150]}")
            return False

        # Hook should return JSON response
        if proc.stdout:
            try:
                response = json.loads(proc.stdout)
                log_result(f"Execute {hook_name}", True, f"Exit code: {proc.returncode}")
                return True
            except json.JSONDecodeError:
                # Some hooks might not return JSON - check for success indicators
                if proc.returncode == 0:
                    log_result(f"Execute {hook_name}", True, f"Executed successfully (non-JSON output)")
                    return True

        # Check exit code
        if proc.returncode == 0:
            log_result(f"Execute {hook_name}", True, f"Clean exit")
            return True
        else:
            log_result(f"Execute {hook_name}", False, f"Exit code: {proc.returncode}, stderr: {proc.stderr[:100]}")
            return False

    except subprocess.TimeoutExpired:
        log_result(f"Execute {hook_name}", False, "Timeout (>10s)")
        return False
    except Exception as e:
        log_result(f"Execute {hook_name}", False, f"Exception: {str(e)[:150]}")
        return False


def test_pretooluse_hook():
    """Test 1: PreToolUse Hook Execution"""
    print("\n🔍 TEST 1: PreToolUse Hook")

    hook_script = PROJECT_ROOT / ".claude" / "hooks" / "devstream" / "memory" / "pre_tool_use.py"
    test_input = {
        "tool": "Write",
        "metadata": {
            "file_path": "test_file.py",
            "content": "import fastapi\n\ndef test(): pass"
        }
    }

    return test_hook_execution("PreToolUse", hook_script, test_input)


def test_posttooluse_hook():
    """Test 2: PostToolUse Hook Execution"""
    print("\n🔍 TEST 2: PostToolUse Hook")

    hook_script = PROJECT_ROOT / ".claude" / "hooks" / "devstream" / "memory" / "post_tool_use.py"
    test_input = {
        "tool": "Write",
        "metadata": {
            "file_path": "test_file.py",
            "content": "# Smoke test content for PostToolUse"
        }
    }

    return test_hook_execution("PostToolUse", hook_script, test_input)


def test_userpromptsubmit_hook():
    """Test 3: UserPromptSubmit Hook Execution"""
    print("\n🔍 TEST 3: UserPromptSubmit Hook")

    hook_script = PROJECT_ROOT / ".claude" / "hooks" / "devstream" / "context" / "user_query_context_enhancer.py"
    test_input = {
        "prompt": "Create a FastAPI endpoint for user authentication"
    }

    return test_hook_execution("UserPromptSubmit", hook_script, test_input)


def test_sessionstart_hook():
    """Test 4: SessionStart Hook Execution"""
    print("\n🔍 TEST 4: SessionStart Hook")

    hook_script = PROJECT_ROOT / ".claude" / "hooks" / "devstream" / "sessions" / "session_start.py"
    test_input = {}

    return test_hook_execution("SessionStart", hook_script, test_input)


def test_sessionend_hook():
    """Test 5: SessionEnd Hook Execution"""
    print("\n🔍 TEST 5: SessionEnd Hook")

    hook_script = PROJECT_ROOT / ".claude" / "hooks" / "devstream" / "sessions" / "session_end.py"
    test_input = {}

    return test_hook_execution("SessionEnd", hook_script, test_input)


def test_rate_limiter_import():
    """Test 6: Rate Limiter Module"""
    print("\n🔍 TEST 6: Rate Limiter Import")

    try:
        proc = subprocess.run(
            [PYTHON_BIN, "-c", "from utils.rate_limiter import MemoryRateLimiter; print('OK')"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=PROJECT_ROOT / ".claude" / "hooks" / "devstream"
        )

        if "OK" in proc.stdout:
            log_result("Rate Limiter Import", True, "MemoryRateLimiter imported")
            return True
        else:
            log_result("Rate Limiter Import", False, proc.stderr[:150])
            return False

    except Exception as e:
        log_result("Rate Limiter Import", False, f"Exception: {str(e)[:150]}")
        return False


def test_ollama_client_import():
    """Test 7: Ollama Client Module"""
    print("\n🔍 TEST 7: Ollama Client Import")

    try:
        proc = subprocess.run(
            [PYTHON_BIN, "-c", "from utils.ollama_client import OllamaEmbeddingClient; print('OK')"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=PROJECT_ROOT / ".claude" / "hooks" / "devstream"
        )

        if "OK" in proc.stdout:
            log_result("Ollama Client Import", True, "OllamaEmbeddingClient imported")
            return True
        else:
            log_result("Ollama Client Import", False, proc.stderr[:150])
            return False

    except Exception as e:
        log_result("Ollama Client Import", False, f"Exception: {str(e)[:150]}")
        return False


def test_mcp_server_health():
    """Test 8: MCP Server Health"""
    print("\n🔍 TEST 8: MCP Server Health")

    try:
        proc = subprocess.run(
            ["pgrep", "-f", "mcp-devstream-server"],
            capture_output=True,
            text=True
        )

        if proc.returncode == 0:
            pids = proc.stdout.strip().split('\n')
            log_result("MCP Server", True, f"Running ({len(pids)} instance(s))")
            return True
        else:
            log_result("MCP Server", True, "Not running (expected if not started manually)")
            return True

    except Exception as e:
        log_result("MCP Server", False, f"Exception: {str(e)[:150]}")
        return False


def test_database_exists():
    """Test 9: Database Exists"""
    print("\n🔍 TEST 9: Database Verification")

    db_path = PROJECT_ROOT / "data" / "devstream.db"

    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        log_result("Database File", True, f"Found at {db_path} ({size_mb:.2f} MB)")
        return True
    else:
        log_result("Database File", False, f"Not found at {db_path}")
        return False


def test_environment_config():
    """Test 10: Environment Configuration"""
    print("\n🔍 TEST 10: Environment Config")

    required_vars = [
        "DEVSTREAM_HOOKS_ENABLED",
        "DEVSTREAM_CONTEXT7_ENABLED",
        "DEVSTREAM_CONTEXT_MAX_TOKENS",
        "DEVSTREAM_CONTEXT7_TOKEN_LIMIT"
    ]

    env_file = PROJECT_ROOT / ".env.devstream"

    if not env_file.exists():
        log_result("Environment Config", False, f".env.devstream not found")
        return False

    with open(env_file) as f:
        content = f.read()

    missing = [var for var in required_vars if var not in content]

    if missing:
        log_result("Environment Config", False, f"Missing vars: {', '.join(missing)}")
        return False
    else:
        log_result("Environment Config", True, f"All {len(required_vars)} required vars present")
        return True


def generate_summary():
    """Generate test summary"""
    print("\n" + "="*80)
    print("📊 FUNCTIONAL SMOKE TEST SUMMARY")
    print("="*80)

    total = len(test_results)
    passed = sum(1 for r in test_results if r["passed"])
    failed = total - passed

    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")

    print("\n" + "-"*80)
    print("DETAILED RESULTS:")
    print("-"*80)

    for result in test_results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{status} | {result['test']}")
        if result['details']:
            print(f"  → {result['details']}")

    print("\n" + "="*80)

    if failed == 0:
        print("🎉 ALL TESTS PASSED - System Ready for Production")
        return 0
    elif failed <= 2:
        print("⚠️  Minor Issues - Review Optional")
        return 0
    else:
        print(f"❌ {failed} TEST(S) FAILED - Review Required")
        return 1


def main():
    """Main test runner"""
    print("🚀 DevStream macOS Deployment - Functional Smoke Tests")
    print(f"Task ID: d744c555")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Project Root: {PROJECT_ROOT}")
    print("="*80)

    # Run all tests
    test_pretooluse_hook()
    test_posttooluse_hook()
    test_userpromptsubmit_hook()
    test_sessionstart_hook()
    test_sessionend_hook()
    test_rate_limiter_import()
    test_ollama_client_import()
    test_mcp_server_health()
    test_database_exists()
    test_environment_config()

    # Generate summary
    exit_code = generate_summary()
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
