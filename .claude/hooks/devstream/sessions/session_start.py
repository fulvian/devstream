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

# Import WorkSessionManager
sys.path.append(str(Path(__file__).parent))
from work_session_manager import WorkSessionManager


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
    try:
        # Check if already in event loop context (Claude Code hooks provide event loop)
        loop = asyncio.get_running_loop()
        # Schedule task in existing loop
        task = loop.create_task(main())
        # Ensure task completes before hook exits
        loop.run_until_complete(task)
    except RuntimeError:
        # No event loop exists - standalone execution
        asyncio.run(main())