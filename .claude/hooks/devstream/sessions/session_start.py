#!/usr/bin/env python3
"""
DevStream SessionStart Hook - Session Initialization

Initializes work session in work_sessions table using WorkSessionManager.
Integrates with Claude Code SessionStart hook system.

Flow:
1. Extract session_id from environment or hook payload
2. Call WorkSessionManager.resume_session() (creates or resumes)
3. Bind session context using structlog (automatic log inheritance)
4. Store initialization event in memory
5. Return success

Context7 Patterns:
- WorkSessionManager uses aiosqlite async patterns
- structlog context binding for automatic session_id in logs
"""

import sys
import os
import asyncio
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Import DevStream utilities
sys.path.append(str(Path(__file__).parent.parent / 'utils'))
from common import DevStreamHookBase, get_project_context
from logger import get_devstream_logger
from session_coordinator import get_session_coordinator

# Import WorkSessionManager and cleanup utilities
sys.path.append(str(Path(__file__).parent))
from work_session_manager import WorkSessionManager
from session_cleanup_utils import SessionCleanupManager


class SessionStartHook:
    """
    SessionStart hook for DevStream session initialization.

    Responsibilities:
    - Initialize or resume work session in work_sessions table
    - Bind session context for automatic log propagation
    - Track session start in memory system
    - Provide session info to other hooks
    """

    def __init__(self):
        self.hook_type = 'session_start'
        self.structured_logger = get_devstream_logger('session_start')
        self.logger = self.structured_logger.logger  # Compatibility
        self.session_manager = WorkSessionManager()

        # Session coordinator for multi-session management
        self.coordinator = get_session_coordinator()

        # Enhanced cleanup manager for zombie session handling
        self.cleanup_manager = SessionCleanupManager(self.coordinator)

    def get_session_id(self) -> str:
        """
        Get session ID from environment or generate new one.

        Returns:
            str: Session identifier
        """
        # Try to get from environment (Claude Code may provide this)
        session_id = os.environ.get('CLAUDE_SESSION_ID')

        if not session_id:
            # Generate new session ID
            session_id = f"sess-{uuid.uuid4().hex[:16]}"
            self.logger.debug(f"Generated new session ID: {session_id}")

        return session_id

    async def initialize_session(self, session_id: str) -> Dict[str, Any]:
        """
        Initialize work session using WorkSessionManager.

        Args:
            session_id: Session identifier

        Returns:
            Dict with session initialization results
        """
        results = {
            "success": False,
            "session_id": session_id,
            "session_created": False,
            "session_resumed": False,
            "error": None
        }

        try:
            # Proactive cleanup of zombie sessions before checking limits
            self.logger.info("Performing proactive session cleanup...")
            cleanup_stats = self.cleanup_manager.aggressive_cleanup()

            if cleanup_stats.zombie_sessions_cleaned > 0 or cleanup_stats.stale_sessions_cleaned > 0:
                self.logger.info(
                    f"Proactive cleanup removed {cleanup_stats.zombie_sessions_cleaned} zombie "
                    f"and {cleanup_stats.stale_sessions_cleaned} stale sessions"
                )

            # Validate registry integrity
            if not self.cleanup_manager.validate_and_fix_registry():
                self.logger.warning("Registry validation failed, attempting emergency repair")
                if not self.cleanup_manager.force_cleanup_all_sessions():
                    raise RuntimeError("Failed to repair session registry")

            # Check session limits via coordinator (after cleanup)
            if self.coordinator.is_session_limit_reached():
                # Emergency override if still at limit after cleanup
                if self.cleanup_manager.EMERGENCY_OVERRIDE:
                    self.logger.warning(
                        f"Session limit still reached after cleanup, using emergency override"
                    )
                    # Force cleanup of all sessions as last resort
                    if not self.cleanup_manager.force_cleanup_all_sessions():
                        raise RuntimeError(
                            f"Session limit reached ({self.coordinator.MAX_SESSIONS} sessions) "
                            f"and emergency cleanup failed. "
                            f"Please manually delete {self.coordinator.registry_path}"
                        )
                else:
                    raise RuntimeError(
                        f"Session limit reached ({self.coordinator.MAX_SESSIONS} sessions). "
                        f"Please close an existing session before starting a new one."
                    )

            # Register session with coordinator
            db_path = self.session_manager.db_path
            if not self.coordinator.register_session(session_id, db_path):
                raise RuntimeError("Failed to register session with coordinator")

            self.logger.info(
                f"Session registered with coordinator: {session_id}",
                extra={"active_sessions": self.coordinator.get_session_count()}
            )

            # Resume or create session
            self.logger.info(f"Initializing session: {session_id}")
            session = await self.session_manager.resume_session(session_id)

            # Bind context for automatic log propagation
            self.session_manager.bind_session_context(
                session_id=session.id,
                session_name=session.session_name
            )

            # Determine if created or resumed
            if session.tokens_used == 0:
                results["session_created"] = True
                self.logger.info(f"Created new work session: {session_id}")
            else:
                results["session_resumed"] = True
                self.logger.info(f"Resumed existing work session: {session_id}, tokens_used={session.tokens_used}")

            results["success"] = True
            results["session_data"] = {
                "id": session.id,
                "status": session.status,
                "started_at": session.started_at.isoformat(),
                "tokens_used": session.tokens_used
            }

        except Exception as e:
            results["error"] = str(e)
            self.structured_logger.log_hook_error(e, {
                "session_id": session_id,
                "operation": "initialize_session"
            })

        return results

    async def display_previous_summary(self) -> None:
        """
        Display previous session summary if available.

        B2 Behavioral Refinement: Shows summary from marker file.
        """
        summary_file = Path.home() / ".claude" / "state" / "devstream_last_session.txt"

        if not summary_file.exists():
            return

        try:
            with open(summary_file, "r") as f:
                summary = f.read()

            if summary and len(summary.strip()) > 0:
                # Display summary to user
                print("\n" + "=" * 70)
                print("📋 PREVIOUS SESSION SUMMARY")
                print("=" * 70)
                print(summary)
                print("=" * 70 + "\n")

                self.logger.info("Displayed previous session summary")

                # Delete marker file after display
                summary_file.unlink()
                self.logger.debug("Deleted summary marker file")

        except Exception as e:
            self.logger.error(f"Failed to display previous summary: {e}")

    async def run_hook(self, hook_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute SessionStart hook.

        Args:
            hook_data: Optional hook execution data

        Returns:
            Hook execution results
        """
        self.structured_logger.log_hook_start(hook_data or {}, {
            "phase": "session_start"
        })

        # Display previous session summary (if available)
        await self.display_previous_summary()

        # Get session ID
        session_id = self.get_session_id()

        # Initialize session
        results = await self.initialize_session(session_id)

        # Log completion
        if results["success"]:
            self.structured_logger.log_hook_success({
                "session_id": session_id,
                "created": results.get("session_created", False),
                "resumed": results.get("session_resumed", False)
            })
        else:
            self.logger.error(f"SessionStart failed: {results.get('error')}")

        return results


async def main():
    """
    Main entry point for SessionStart hook.

    Called by Claude Code hook system.
    """
    hook = SessionStartHook()
    results = await hook.run_hook()

    # Output results for hook system
    if results["success"]:
        print(f"✅ Session initialized: {results['session_id']}")
        if results.get("session_created"):
            print("   📝 New session created in work_sessions table")
        elif results.get("session_resumed"):
            print("   🔄 Existing session resumed")
    else:
        print(f"❌ SessionStart failed: {results.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    """
    SessionStart hook entry point with asyncio loop safety.

    Handles two execution contexts:
    1. Claude Code hooks (event loop already running)
    2. Standalone execution (no event loop)

    Fix: Never call run_until_complete() on running loop.
    Reference: https://docs.python.org/3/library/asyncio-task.html#asyncio.get_running_loop

    Exception Handling:
    - CancelledError: Task cancelled during execution (graceful warning)
    - RuntimeError: No loop vs loop closed/thread mismatch (distinguish)
    - Generic Exception: Catch-all with detailed logging + re-raise
    """
    import structlog

    logger = structlog.get_logger()

    try:
        # Attempt to get existing running loop
        loop = asyncio.get_running_loop()

        # CORRECT: Schedule task in existing loop WITHOUT running it
        # The loop is already running, task will execute automatically
        task = loop.create_task(main())

        logger.debug("SessionStart scheduled in existing event loop",
                    loop_id=id(loop), task_repr=str(task))

        # NOTE: Do NOT await or run_until_complete here!
        # The hook framework will handle task completion.

    except RuntimeError as e:
        # Distinguish between "no running loop" vs other RuntimeErrors
        if "no running event loop" in str(e).lower():
            # Expected case: standalone execution without event loop
            logger.debug("SessionStart creating new event loop")
            try:
                asyncio.run(main())
            except asyncio.CancelledError:
                logger.warning("SessionStart task cancelled during execution")
            except Exception as ex:
                logger.error("SessionStart execution failed",
                           error=str(ex), error_type=type(ex).__name__)
                raise
        else:
            # Other RuntimeError: loop closed, thread mismatch, etc.
            logger.error("SessionStart asyncio runtime error",
                        error=str(e), error_type="RuntimeError")
            raise

    except asyncio.CancelledError:
        # Task cancelled in existing loop (non-critical)
        logger.warning("SessionStart task cancelled in existing loop")

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error("SessionStart unexpected error",
                    error=str(e), error_type=type(e).__name__)
        raise