#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cchooks>=0.1.4",
#     "aiosqlite>=0.19.0",
#     "structlog>=23.0.0",
#     "python-dotenv>=1.0.0",
#     "aiohttp>=3.8.0",
# ]
# ///

"""
DevStream PreCompact Hook - Context7 Compliant

Executes BEFORE /compact command to preserve session summary.
Generates and stores session summary before context compaction.

Workflow:
1. Detect PreCompact event (cchooks PreCompactContext)
2. Get active session ID from work_sessions table
3. Extract session data using SessionDataExtractor
4. Generate summary using SessionSummaryGenerator
5. Store summary in DevStream memory with embedding
6. Write marker file to ~/.claude/state/devstream_last_session.txt
7. Allow compaction to proceed (exit_success)

Context7 Patterns:
- Async/await throughout (aiosqlite, asyncio)
- Structured logging via DevStreamHookBase
- Graceful degradation on all errors
- Non-blocking execution (always exit_success)
- Reuse existing SessionSummaryGenerator (no duplication)
"""

import sys
import asyncio
import aiosqlite
from pathlib import Path
from typing import Optional

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
sys.path.insert(0, str(Path(__file__).parent))

from cchooks import safe_create_context, PreCompactContext
from devstream_base import DevStreamHookBase
from mcp_client import get_mcp_client

# Import session components
from session_data_extractor import SessionDataExtractor
from session_summary_generator import SessionSummaryGenerator
from atomic_file_writer import write_atomic


class PreCompactHook:
    """
    PreCompact hook for session summary preservation.

    Captures session summary before /compact command to ensure work
    is documented even when context window is reset.

    Context7 Pattern: Reuse SessionSummaryGenerator and SessionDataExtractor
    for consistency with session_end hook.
    """

    def __init__(self):
        """Initialize PreCompact hook with required components."""
        self.base = DevStreamHookBase("pre_compact")
        self.mcp_client = get_mcp_client()

        # Initialize components (reuse from session_end)
        self.data_extractor = SessionDataExtractor()
        self.summary_generator = SessionSummaryGenerator()

        # Database path
        project_root = Path(__file__).parent.parent.parent.parent.parent
        self.db_path = str(project_root / 'data' / 'devstream.db')

    async def get_active_session_id(self) -> Optional[str]:
        """
        Get currently active session ID.

        Queries work_sessions table for most recent active session.

        Returns:
            Active session ID or None if no active session

        Note:
            Reuses pattern from session_end.py lines 144-176
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                async with db.execute(
                    """
                    SELECT id FROM work_sessions
                    WHERE status = 'active'
                    ORDER BY started_at DESC
                    LIMIT 1
                    """
                ) as cursor:
                    row = await cursor.fetchone()

                    if row:
                        session_id = row['id']
                        self.base.debug_log(f"Active session found: {session_id[:8]}...")
                        return session_id
                    else:
                        self.base.debug_log("No active session found")
                        return None

        except Exception as e:
            self.base.debug_log(f"Failed to get active session: {e}")
            return None

    async def generate_and_store_summary(self, session_id: str) -> Optional[str]:
        """
        Generate session summary and store in DevStream memory.

        Orchestrates data extraction, summary generation, and storage.
        Reuses existing components from session_end hook.

        Args:
            session_id: Session identifier

        Returns:
            Summary markdown text if successful, None otherwise

        Note:
            Graceful degradation - returns None on any error
        """
        try:
            self.base.debug_log(f"Generating summary for session: {session_id[:8]}...")

            # Step 1: Extract session metadata
            self.base.debug_log("Step 1: Extracting session metadata...")
            session_data = await self.data_extractor.get_session_metadata(session_id)

            if not session_data:
                self.base.debug_log(f"Session not found: {session_id}")
                return None

            self.base.debug_log(
                f"Session metadata extracted: {session_data.session_name or session_id[:8]}"
            )

            # Step 2: Extract memory stats (time-range query)
            self.base.debug_log("Step 2: Extracting memory stats...")

            if session_data.started_at:
                from datetime import datetime
                memory_stats = await self.data_extractor.get_memory_stats(
                    session_data.started_at,
                    datetime.now()  # Use current time for PreCompact
                )
                self.base.debug_log(
                    f"Memory stats: {memory_stats.total_records} records, "
                    f"{memory_stats.files_modified} files"
                )
            else:
                self.base.debug_log("No start time - skipping memory stats")
                from session_data_extractor import MemoryStats
                memory_stats = MemoryStats()

            # Step 3: Extract task stats (time-range query)
            self.base.debug_log("Step 3: Extracting task stats...")

            if session_data.started_at:
                from datetime import datetime
                task_stats = await self.data_extractor.get_task_stats(
                    session_data.started_at,
                    datetime.now()  # Use current time for PreCompact
                )
                self.base.debug_log(
                    f"Task stats: {task_stats.total_tasks} total, "
                    f"{task_stats.completed} completed"
                )
            else:
                self.base.debug_log("No start time - skipping task stats")
                from session_data_extractor import TaskStats
                task_stats = TaskStats()

            # Step 4: Generate summary
            self.base.debug_log("Step 4: Generating summary...")

            summary_markdown = self.summary_generator.generate_summary(
                session_data,
                memory_stats,
                task_stats
            )

            self.base.debug_log(
                f"Summary generated: {len(summary_markdown)} chars"
            )

            # Step 5: Store summary in memory with embedding
            self.base.debug_log("Step 5: Storing summary in memory...")

            # Store via MCP (reuses pattern from session_end.py lines 178-261)
            result = await self.base.safe_mcp_call(
                self.mcp_client,
                "devstream_store_memory",
                {
                    "content": summary_markdown,
                    "content_type": "context",
                    "keywords": [
                        "session",
                        "summary",
                        session_id,
                        "pre-compact"
                    ]
                }
            )

            if result:
                self.base.debug_log("Summary stored in memory successfully")
            else:
                self.base.debug_log("Summary storage failed (non-blocking)")

            return summary_markdown

        except Exception as e:
            self.base.debug_log(f"Failed to generate/store summary: {e}")
            return None

    async def write_marker_file(self, summary: str) -> bool:
        """
        Write summary to marker file atomically for SessionStart hook.

        Creates ~/.claude/state/devstream_last_session.txt with summary text.

        Args:
            summary: Summary markdown text

        Returns:
            True if successful, False otherwise

        Note:
            Uses atomic write pattern to prevent partial writes.
            Source tagged as "pre_compact" for debugging.
            Non-blocking - logs errors but doesn't raise exceptions.
        """
        # Path: ~/.claude/state/devstream_last_session.txt
        marker_file = Path.home() / ".claude" / "state" / "devstream_last_session.txt"

        # Ensure parent directory exists
        marker_file.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write
        write_success = await write_atomic(marker_file, summary)

        if write_success:
            self.base.debug_log(
                f"✅ Marker file written atomically: {marker_file} "
                f"(source=pre_compact, size={len(summary)} chars)"
            )

            # Log marker file creation for telemetry
            self.base.debug_log(
                f"📊 Marker file telemetry: "
                f"exists={marker_file.exists()}, "
                f"size={marker_file.stat().st_size if marker_file.exists() else 0}, "
                f"source=pre_compact"
            )
        else:
            self.base.debug_log(
                f"❌ Marker file write failed: {marker_file} (source=pre_compact)"
            )

        return write_success

    async def process_pre_compact(self, context: PreCompactContext) -> None:
        """
        Process PreCompact event workflow.

        Main orchestration method that coordinates summary generation and storage.

        Args:
            context: PreCompact context from cchooks

        Note:
            Always calls context.output.exit_success() to allow compaction
        """
        try:
            # Get active session ID
            session_id = await self.get_active_session_id()

            if not session_id:
                self.base.debug_log("No active session - skip summary generation")
                context.output.exit_success()
                return

            # Generate and store summary
            summary = await self.generate_and_store_summary(session_id)

            if not summary:
                self.base.debug_log("Summary generation failed (non-blocking)")
                context.output.exit_non_block("Summary generation failed")
                # Still allow compaction to proceed
                context.output.exit_success()
                return

            # Write marker file
            marker_written = await self.write_marker_file(summary)

            if marker_written:
                self.base.success_feedback(
                    "Session summary preserved before compaction"
                )
            else:
                self.base.debug_log("Marker file write failed (non-blocking)")

            # Always allow compaction to proceed
            context.output.exit_success()

        except Exception as e:
            # Non-blocking error - log and allow compaction
            self.base.debug_log(f"PreCompact error: {e}")
            context.output.exit_non_block(f"Hook error: {str(e)[:100]}")
            context.output.exit_success()

    async def process(self, context: PreCompactContext) -> None:
        """
        Main hook processing logic.

        Args:
            context: PreCompact context from cchooks
        """
        # Check if hook should run
        if not self.base.should_run():
            self.base.debug_log("Hook disabled via config")
            context.output.exit_success()
            return

        # Process PreCompact workflow
        await self.process_pre_compact(context)


def main():
    """Main entry point for PreCompact hook."""
    # Create context using cchooks
    ctx = safe_create_context()

    # Verify it's PreCompact context
    if not isinstance(ctx, PreCompactContext):
        print(f"Error: Expected PreCompactContext, got {type(ctx)}", file=sys.stderr)
        sys.exit(1)

    # Create and run hook
    hook = PreCompactHook()

    try:
        # Run async processing
        asyncio.run(hook.process(ctx))
    except Exception as e:
        # Graceful failure - non-blocking
        print(f"⚠️  DevStream: PreCompact error", file=sys.stderr)
        ctx.output.exit_non_block(f"Hook error: {str(e)[:100]}")
        ctx.output.exit_success()


if __name__ == "__main__":
    main()
