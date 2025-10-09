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
from ollama_client import OllamaEmbeddingClient


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
        self.ollama_client = OllamaEmbeddingClient()

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

    async def generate_summary_only(self, session_id: str) -> Optional[str]:
        """
        Generate session summary WITHOUT MCP storage.

        Extracts session data and generates summary markdown.
        Does NOT store in DevStream memory (decoupled from MCP).

        Args:
            session_id: Session identifier

        Returns:
            Summary markdown text if successful, None otherwise

        Note:
            Reuses SessionDataExtractor and SessionSummaryGenerator
            from session_end.py pattern (Context7 compliant).
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

            return summary_markdown  # Return WITHOUT MCP storage

        except Exception as e:
            self.base.debug_log(f"Summary generation failed: {e}")
            return None

    async def store_summary_direct_db(
        self,
        summary: str,
        session_id: str
    ) -> bool:
        """
        Store summary directly in semantic_memory bypassing MCP.

        Uses Context7 patterns:
        - aiosqlite async context manager (transaction safety)
        - OllamaEmbeddingClient with graceful degradation
        - Explicit commit (no auto-commit)

        Args:
            summary: Summary markdown text
            session_id: Session identifier

        Returns:
            True if successful, False otherwise (non-blocking)

        Note:
            Stores WITHOUT embedding if Ollama unavailable (graceful degradation).
            SQL trigger auto-generates vec_semantic_memory if embedding present.

        Pattern Reference:
            session_summary_manager.py:491-528 (store_summary method)
        """
        try:
            import json
            import hashlib
            from datetime import datetime

            # Step 1: Generate embedding (graceful degradation)
            self.base.debug_log("Generating embedding for summary...")
            embedding = self.ollama_client.generate_embedding(summary)

            if not embedding:
                self.base.debug_log(
                    "Embedding generation failed - storing without embedding"
                )
                embedding_json = None
                embedding_model = None
                embedding_dim = None
            else:
                embedding_json = json.dumps(embedding)
                embedding_model = self.ollama_client.model
                embedding_dim = len(embedding)
                self.base.debug_log(
                    f"Embedding generated: {embedding_dim} dimensions"
                )

            # Step 2: Generate memory ID (SHA256 hash)
            timestamp_str = datetime.now().isoformat()
            memory_id = hashlib.sha256(
                f"pre-compact-{session_id}-{timestamp_str}".encode()
            ).hexdigest()[:32]

            # Step 3: Direct DB write (Context7 aiosqlite pattern + sqlite-vec)
            self.base.debug_log(f"Writing to semantic_memory: {memory_id[:8]}...")

            async with aiosqlite.connect(self.db_path) as db:
                # Load sqlite-vec extension for vec0 support (Context7 pattern)
                # Note: aiosqlite runs operations in thread pool, so we need to load
                # the extension via execute() to run in correct thread context
                try:
                    import sqlite_vec
                    import os

                    # Get sqlite-vec shared library path
                    vec_path = sqlite_vec.loadable_path()

                    # Load extension via SQL (runs in correct thread)
                    await db.enable_load_extension(True)
                    await db.execute(f"SELECT load_extension('{vec_path}')")
                    await db.enable_load_extension(False)

                    self.base.debug_log("sqlite-vec extension loaded successfully")
                except ImportError:
                    self.base.debug_log("sqlite-vec not available - storing without vec0 support")
                except Exception as e:
                    self.base.debug_log(f"Failed to load sqlite-vec: {e}")

                await db.execute(
                    """
                    INSERT INTO semantic_memory (
                        id, content, content_type, keywords,
                        embedding, embedding_model, embedding_dimension,
                        session_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        memory_id,
                        summary,
                        "context",
                        json.dumps(["session", "summary", session_id, "pre-compact"]),
                        embedding_json,
                        embedding_model,
                        embedding_dim,
                        session_id
                    )
                )
                await db.commit()  # Explicit commit (Context7 pattern)

            self.base.debug_log(
                f"✅ Summary stored in DB: {memory_id[:8]}... "
                f"(embedding: {'yes' if embedding_json else 'no'})"
            )
            return True

        except Exception as e:
            self.base.debug_log(f"Direct DB storage failed: {e}")
            return False  # Non-blocking (graceful degradation)

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

    async def process_pre_compact(self, context: Optional[PreCompactContext]) -> None:
        """
        Process PreCompact event workflow.

        Main orchestration method that coordinates summary generation and storage.

        Args:
            context: PreCompact context from cchooks (or None if stdin empty)

        Note:
            Always calls context.output.exit_success() to allow compaction
        """
        try:
            # Get active session ID
            session_id = await self.get_active_session_id()

            if not session_id:
                self.base.debug_log("No active session - skip summary generation")
                if context:
                    context.output.exit_success()
                return

            # Generate summary ONLY (no MCP dependency)
            summary = await self.generate_summary_only(session_id)

            if not summary:
                self.base.debug_log("Summary generation failed")
                if context:
                    context.output.exit_success()
                return

            # ALWAYS write marker file (CRITICAL PATH)
            marker_written = await self.write_marker_file(summary)

            if marker_written:
                self.base.debug_log("✅ Marker file written successfully")
            else:
                self.base.debug_log("⚠️  Marker file write failed")

            # BEST-EFFORT: Store in DB (non-blocking)
            db_written = await self.store_summary_direct_db(summary, session_id)

            if db_written:
                self.base.success_feedback(
                    "Session summary preserved (marker file + DB)"
                )
            else:
                self.base.debug_log(
                    "DB storage failed (marker file OK - SessionStart will work)"
                )

            # Always allow compaction to proceed
            if context:
                context.output.exit_success()

        except Exception as e:
            # Non-blocking error - log and allow compaction
            self.base.debug_log(f"PreCompact error: {e}")
            if context:
                context.output.exit_non_block(f"Hook error: {str(e)[:100]}")
                context.output.exit_success()

    async def process(self, context: Optional[PreCompactContext]) -> None:
        """
        Main hook processing logic.

        Args:
            context: PreCompact context from cchooks (or None if stdin empty)
        """
        # Check if hook should run
        if not self.base.should_run():
            self.base.debug_log("Hook disabled via config")
            if context:
                context.output.exit_success()
            return

        # Process PreCompact workflow
        await self.process_pre_compact(context)


def main():
    """Main entry point for PreCompact hook."""
    # Try to create context using cchooks
    ctx = None
    try:
        ctx = safe_create_context()
    except (Exception, SystemExit) as e:
        # stdin empty or invalid JSON - fallback to manual session lookup
        print(f"⚠️  DevStream: No hook input, using fallback mode", file=sys.stderr)
        ctx = None  # Explicitly set to None for fallback mode

    # Verify it's PreCompact context (if available)
    if ctx and not isinstance(ctx, PreCompactContext):
        print(f"Error: Expected PreCompactContext, got {type(ctx)}", file=sys.stderr)
        sys.exit(1)

    # Create and run hook
    hook = PreCompactHook()

    try:
        # Run async processing (hook will handle missing context internally)
        asyncio.run(hook.process(ctx))
    except Exception as e:
        # Graceful failure - non-blocking
        print(f"⚠️  DevStream: PreCompact error: {str(e)}", file=sys.stderr)
        if ctx:
            ctx.output.exit_non_block(f"Hook error: {str(e)[:100]}")
            ctx.output.exit_success()
        else:
            # No ctx - just exit gracefully
            print("Summary generation attempted despite missing context", file=sys.stderr)
            sys.exit(0)


if __name__ == "__main__":
    main()
