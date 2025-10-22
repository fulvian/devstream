#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cchooks>=0.1.4",
#     "structlog>=23.0.0",
#     "aiosqlite>=0.19.0",
# ]
# ///
"""SessionStart adapter bridging Codex integration and simplified hook logic."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / ".claude"))

import structlog

from hooks.devstream.sessions import session_start_simplified as simplified_module

logger = structlog.get_logger(__name__).bind(component="SessionStartAdapter")


class SessionStartHook:
    """Adapter exposing a stable API for SessionStart events."""

    def __init__(self) -> None:
        self._logger = logger

    async def process_session_start(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a SessionStart event using the simplified hook implementation."""
        data: Dict[str, Any] = dict(payload or {})
        cwd_override = data.get("cwd")
        session_id = data.get("session_id")

        original_root = simplified_module.project_root
        added_sys_path = False
        resolved_cwd: Optional[Path] = None

        try:
            if cwd_override:
                resolved_cwd = Path(cwd_override).expanduser().resolve()
                if resolved_cwd.exists():
                    simplified_module.project_root = resolved_cwd
                    if str(resolved_cwd) not in sys.path:
                        sys.path.insert(0, str(resolved_cwd))
                        added_sys_path = True
                else:
                    self._logger.warning(
                        "SessionStart received non-existent cwd, falling back to default root",
                        cwd=cwd_override,
                    )

            hook = simplified_module.SimplifiedSessionStartHook()
            await hook._initialize_components()

            derived_session_id = session_id or hook._get_session_id(data)
            data.setdefault("hook_event_name", "SessionStart")

            results = await hook._initialize_session(derived_session_id)

            if not results.get("success"):
                error_message = results.get("error") or "SessionStart initialization failed"
                self._logger.error("SessionStart hook execution failed", error=error_message)
                raise RuntimeError(error_message)

            self._logger.info(
                "SessionStart hook completed",
                session_id=results.get("session_id"),
                created=results.get("session_created", False),
                resumed=results.get("session_resumed", False),
            )
            return results

        except Exception:
            self._logger.exception("SessionStart hook raised an exception")
            raise

        finally:
            simplified_module.project_root = original_root
            if added_sys_path and resolved_cwd is not None:
                try:
                    sys.path.remove(str(resolved_cwd))
                except ValueError:
                    pass


async def cli_main() -> int:
    """Entry point for executing the SessionStart hook as a command."""
    hook = simplified_module.SimplifiedSessionStartHook()

    try:
        results = await hook.run_hook()
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("SessionStart CLI execution failed", error=str(exc))
        return _emit_failure({"error": str(exc)})

    if results.get("success"):
        return _emit_success(results)
    return _emit_failure(results)


def _emit_success(results: Dict[str, Any]) -> int:
    session_id = results.get("session_id", "unknown-session")

    if simplified_module.CCHOOKS_AVAILABLE:
        print(json.dumps({"decision": "allow", "reason": f"Session initialized: {session_id}"}))
    else:
        print(f"✅ Session initialized: {session_id}")
        if results.get("session_created"):
            print("   📝 New session created")
        elif results.get("session_resumed"):
            print("   🔄 Existing session resumed")
        if results.get("tracking_started"):
            print("   📊 Tracking started")

    return 0


def _emit_failure(results: Dict[str, Any]) -> int:
    error_msg = results.get("error", "Unknown error")

    if simplified_module.CCHOOKS_AVAILABLE:
        print(json.dumps({"decision": "block", "reason": f"SessionStart failed: {error_msg}"}))
    else:
        print(f"❌ SessionStart failed: {error_msg}", file=sys.stderr)

    return 2


def run_main() -> None:
    """Run the CLI entry point and exit with appropriate code."""
    exit_code = 2
    try:
        exit_code = asyncio.run(cli_main())
    except KeyboardInterrupt:  # pragma: no cover - interactive safety
        exit_code = 130
    finally:
        sys.exit(exit_code)


__all__ = ["SessionStartHook", "cli_main", "run_main"]

