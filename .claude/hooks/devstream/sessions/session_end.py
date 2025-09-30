#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cchooks>=0.1.4",
#     "aiohttp>=3.8.0",
#     "structlog>=23.0.0",
#     "python-dotenv>=1.0.0",
#     "ollama>=0.1.0",
#     "aiosqlite>=0.19.0",
# ]
# ///

"""
DevStream SessionEnd Hook - Context7 Compliant

Captures comprehensive session summaries using triple-source data extraction.
Implements Context7 async patterns for data extraction and aggregation.

Workflow:
1. Detect session end trigger (Claude Code SessionEnd event)
2. Extract session data from work_sessions table
3. Extract memory stats from semantic_memory (time-range query)
4. Extract task stats from micro_tasks (time-range query)
5. Aggregate into unified summary
6. Generate markdown-formatted summary
7. Store summary in memory with embedding
8. Update session status to "completed"

Triple Sources:
- work_sessions → Session metadata, timestamps, tokens
- semantic_memory → Files modified, decisions, learnings
- micro_tasks → Task completion, status changes

Context7 Patterns:
- aiosqlite: async with context managers, row_factory
- Structured logging with context
- Graceful degradation on errors
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
sys.path.insert(0, str(Path(__file__).parent))

from cchooks import safe_create_context, SessionEndContext
from devstream_base import DevStreamHookBase
from mcp_client import get_mcp_client
from ollama_client import OllamaEmbeddingClient

# Import session components
from session_data_extractor import SessionDataExtractor
from session_summary_generator import SessionSummaryGenerator, format_session_for_storage
from work_session_manager import WorkSessionManager


class SessionEndHook:
    """
    SessionEnd hook for comprehensive session summary capture.

    Orchestrates triple-source data extraction and summary generation.
    Stores summaries in semantic memory with embeddings for future retrieval.

    Context7 Pattern: Clear separation of concerns across components:
    - SessionDataExtractor: Data extraction layer
    - SessionSummaryGenerator: Aggregation and formatting layer
    - SessionEnd: Orchestration and storage layer
    """

    def __init__(self):
        self.base = DevStreamHookBase("session_end")
        self.mcp_client = get_mcp_client()

        # Initialize components
        self.data_extractor = SessionDataExtractor()
        self.summary_generator = SessionSummaryGenerator()
        self.session_manager = WorkSessionManager()
        self.ollama_client = OllamaEmbeddingClient()

        # Database path
        project_root = Path(__file__).parent.parent.parent.parent.parent
        self.db_path = str(project_root / 'data' / 'devstream.db')

    async def get_active_session_id(self) -> Optional[str]:
        """
        Get currently active session ID.

        Returns:
            Active session ID or None if no active session
        """
        try:
            # Query work_sessions for active session
            import aiosqlite

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
                        return row['id']
                    else:
                        self.base.debug_log("No active session found")
                        return None

        except Exception as e:
            self.base.debug_log(f"Failed to get active session: {e}")
            return None

    async def store_summary_in_memory(
        self,
        summary_markdown: str,
        session_id: str
    ) -> Optional[str]:
        """
        Store session summary in DevStream memory with embedding.

        Args:
            summary_markdown: Markdown-formatted summary
            session_id: Session identifier

        Returns:
            Memory ID if storage successful, None otherwise
        """
        try:
            self.base.debug_log(
                f"Storing summary in memory: {len(summary_markdown)} chars"
            )

            # Store via MCP
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
                        "session-end"
                    ]
                }
            )

            if not result:
                self.base.debug_log("Memory storage returned no result")
                return None

            # Extract memory_id
            memory_id = None
            if isinstance(result, dict):
                memory_id = result.get('memory_id')

            if not memory_id:
                self.base.debug_log("No memory_id in MCP response")
                return None

            self.base.debug_log(f"Summary stored: {memory_id[:8]}...")

            # Generate and store embedding (graceful degradation)
            try:
                self.base.debug_log("Generating embedding for summary...")

                embedding = self.ollama_client.generate_embedding(summary_markdown)

                if embedding:
                    # Update memory record with embedding
                    from sqlite_vec_helper import get_db_connection_with_vec
                    import json

                    conn = get_db_connection_with_vec(self.db_path)
                    cursor = conn.cursor()

                    cursor.execute(
                        "UPDATE semantic_memory SET embedding = ? WHERE id = ?",
                        (json.dumps(embedding), memory_id)
                    )

                    conn.commit()
                    conn.close()

                    self.base.debug_log(
                        f"✓ Embedding stored: {len(embedding)}D"
                    )

            except Exception as embed_error:
                # Graceful degradation - log but don't fail
                self.base.debug_log(
                    f"Embedding generation failed (non-blocking): {embed_error}"
                )

            return memory_id

        except Exception as e:
            self.base.debug_log(f"Failed to store summary in memory: {e}")
            return None

    async def process_session_end(self, session_id: str) -> bool:
        """
        Process session end workflow.

        Main orchestration method that coordinates all components.

        Args:
            session_id: Session identifier to process

        Returns:
            True if successful, False otherwise
        """
        try:
            self.base.debug_log(f"Processing session end: {session_id}")

            # Step 1: Extract session metadata
            self.base.debug_log("Step 1: Extracting session metadata...")
            session_data = await self.data_extractor.get_session_metadata(session_id)

            if not session_data:
                self.base.debug_log(f"Session not found: {session_id}")
                return False

            self.base.debug_log(
                f"Session metadata extracted: {session_data.session_name or session_id}"
            )

            # Step 2: Extract memory stats (time-range query)
            self.base.debug_log("Step 2: Extracting memory stats...")

            if session_data.started_at:
                memory_stats = await self.data_extractor.get_memory_stats(
                    session_data.started_at,
                    session_data.ended_at or datetime.now()
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
                task_stats = await self.data_extractor.get_task_stats(
                    session_data.started_at,
                    session_data.ended_at or datetime.now()
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

            memory_id = await self.store_summary_in_memory(
                summary_markdown,
                session_id
            )

            if memory_id:
                self.base.debug_log(f"Summary stored: {memory_id[:8]}...")
            else:
                self.base.warning_feedback("Summary storage failed (non-blocking)")

            # Step 6: Update session status to "completed"
            self.base.debug_log("Step 6: Updating session status...")

            # Use WorkSessionManager to end session properly
            session_ended = await self.session_manager.end_session(
                session_id=session_id,
                summary=summary_markdown[:500]  # First 500 chars as summary
            )

            if session_ended:
                self.base.debug_log("Session status updated to completed")
            else:
                self.base.warning_feedback("Session status update failed")

            # Success feedback
            self.base.success_feedback(
                f"Session ended: {task_stats.completed} tasks, "
                f"{memory_stats.files_modified} files"
            )

            return True

        except Exception as e:
            self.base.debug_log(f"Session end processing error: {e}")
            return False

    async def process(self, context: SessionEndContext) -> None:
        """
        Main hook processing logic.

        Args:
            context: SessionEnd context from cchooks
        """
        # Check if hook should run
        if not self.base.should_run():
            self.base.debug_log("Hook disabled via config")
            context.output.exit_success()
            return

        try:
            # Get active session ID
            session_id = await self.get_active_session_id()

            if not session_id:
                self.base.debug_log("No active session to end")
                context.output.exit_success()
                return

            # Process session end
            success = await self.process_session_end(session_id)

            if not success:
                # Non-blocking warning
                self.base.warning_feedback("Session end processing failed")

            # Always allow session to end (graceful degradation)
            context.output.exit_success()

        except Exception as e:
            # Non-blocking error - log and continue
            self.base.warning_feedback(f"SessionEnd error: {str(e)[:50]}")
            context.output.exit_success()


def main():
    """Main entry point for SessionEnd hook."""
    # Create context using cchooks
    ctx = safe_create_context()

    # Verify it's SessionEnd context
    if not isinstance(ctx, SessionEndContext):
        print(f"Error: Expected SessionEndContext, got {type(ctx)}", file=sys.stderr)
        sys.exit(1)

    # Create and run hook
    hook = SessionEndHook()

    try:
        # Run async processing
        asyncio.run(hook.process(ctx))
    except Exception as e:
        # Graceful failure - non-blocking
        print(f"⚠️  DevStream: SessionEnd error", file=sys.stderr)
        ctx.output.exit_non_block(f"Hook error: {str(e)[:100]}")


if __name__ == "__main__":
    main()