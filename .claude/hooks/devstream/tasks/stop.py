#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cchooks>=0.1.4",
#     "aiohttp>=3.8.0",
#     "structlog>=23.0.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
DevStream Stop Hook - Session Summary & Task Completion Detection
Lightweight session summary with optional task completion detection.
"""

import sys
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))

from cchooks import safe_create_context, StopContext
from devstream_base import DevStreamHookBase
from mcp_client import get_mcp_client


class StopHook:
    """
    Stop hook for session summary and task completion detection.
    Provides lightweight session wrap-up functionality.
    """

    def __init__(self):
        self.base = DevStreamHookBase("stop")
        self.mcp_client = get_mcp_client()

    async def generate_session_summary(self) -> str:
        """
        Generate session completion summary.

        Returns:
            Session summary text
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        summary = f"""# Session Completed

**Timestamp**: {timestamp}

DevStream session ended. All changes have been tracked in semantic memory.

For task status, use TodoWrite to review completion status.
"""

        return summary

    async def store_session_end(self, session_summary: str) -> None:
        """
        Store session end marker in memory.

        Args:
            session_summary: Session summary text
        """
        try:
            await self.base.safe_mcp_call(
                self.mcp_client,
                "devstream_store_memory",
                {
                    "content": session_summary,
                    "content_type": "context",
                    "keywords": ["session-end", "summary", "devstream"]
                }
            )

            self.base.debug_log("Session end stored in memory")

        except Exception as e:
            self.base.debug_log(f"Failed to store session end: {e}")

    async def process(self, context: StopContext) -> None:
        """
        Main hook processing logic.

        Args:
            context: Stop context from cchooks
        """
        # Check if hook should run
        if not self.base.should_run():
            self.base.debug_log("Hook disabled via config")
            context.output.exit_success()
            return

        self.base.debug_log("Session ending - generating summary")

        try:
            # Generate session summary
            summary = await self.generate_session_summary()

            # Store session end marker
            await self.store_session_end(summary)

            # Inject summary as context (optional)
            self.base.inject_context(summary)
            self.base.success_feedback("Session summary generated")

            # Always allow the operation to proceed
            context.output.exit_success()

        except Exception as e:
            # Non-blocking error - log and continue
            self.base.warning_feedback(f"Session summary failed: {str(e)[:50]}")
            context.output.exit_success()


def main():
    """Main entry point for Stop hook."""
    # Create context using cchooks
    ctx = safe_create_context()

    # Verify it's Stop context
    if not isinstance(ctx, StopContext):
        print(f"Error: Expected StopContext, got {type(ctx)}", file=sys.stderr)
        sys.exit(1)

    # Create and run hook
    hook = StopHook()

    try:
        # Run async processing
        asyncio.run(hook.process(ctx))
    except Exception as e:
        # Graceful failure - non-blocking
        print(f"⚠️  DevStream: Stop error", file=sys.stderr)
        ctx.output.exit_non_block(f"Hook error: {str(e)[:100]}")


if __name__ == "__main__":
    main()