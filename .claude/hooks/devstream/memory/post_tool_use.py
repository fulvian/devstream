#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cchooks>=0.1.4",
#     "aiohttp>=3.8.0",
#     "structlog>=23.0.0",
#     "python-dotenv>=1.0.0",
#     "ollama>=0.1.0",
#     "sqlite-vec>=0.1.0",
# ]
# ///

"""
DevStream PostToolUse Hook - Memory Storage after Write/Edit with Embeddings

Stores modified file content in DevStream semantic memory and generates
embeddings using Ollama for semantic search capabilities.

Phase 2 Enhancement: Inline embedding generation with graceful degradation.
"""

import sys
import asyncio
import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))

from cchooks import safe_create_context, PostToolUseContext
from devstream_base import DevStreamHookBase
from mcp_client import get_mcp_client
from ollama_client import OllamaEmbeddingClient
from sqlite_vec_helper import get_db_connection_with_vec


class PostToolUseHook:
    """
    PostToolUse hook for automatic memory storage with embeddings.

    Stores file modifications in DevStream semantic memory and generates
    embeddings using Ollama for semantic search.

    Phase 2 Enhancement: Inline embedding generation with graceful degradation.
    """

    def __init__(self):
        self.base = DevStreamHookBase("post_tool_use")
        self.mcp_client = get_mcp_client()

        # Initialize Ollama client for embedding generation
        self.ollama_client = OllamaEmbeddingClient()

        # Database path for direct embedding updates
        project_root = Path(__file__).parent.parent.parent.parent.parent
        self.db_path = str(project_root / 'data' / 'devstream.db')

    def extract_content_preview(self, content: str, max_length: int = 300) -> str:
        """
        Extract content preview for memory storage.

        Args:
            content: Full content
            max_length: Maximum preview length

        Returns:
            Content preview string
        """
        if len(content) <= max_length:
            return content

        # Try to break at sentence/line boundary
        preview = content[:max_length]
        last_period = preview.rfind('.')
        last_newline = preview.rfind('\n')

        break_point = max(last_period, last_newline)
        if break_point > max_length * 0.7:  # At least 70% of max length
            return preview[:break_point + 1].strip()

        return preview.strip() + "..."

    def extract_keywords(self, file_path: str, content: str) -> list[str]:
        """
        Extract keywords from file path and content.

        Args:
            file_path: Path to file
            content: File content

        Returns:
            List of keywords
        """
        keywords = []

        # Add file name without extension
        file_name = Path(file_path).stem
        keywords.append(file_name)

        # Add parent directory if relevant
        parent = Path(file_path).parent.name
        if parent and parent not in ['.', '..']:
            keywords.append(parent)

        # Detect language/framework from file extension
        ext = Path(file_path).suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'react',
            '.jsx': 'react',
            '.vue': 'vue',
            '.rs': 'rust',
            '.go': 'golang',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.sh': 'bash',
            '.sql': 'sql',
            '.md': 'documentation',
            '.json': 'config',
            '.yaml': 'config',
            '.yml': 'config',
        }
        if ext in lang_map:
            keywords.append(lang_map[ext])

        # Add "implementation" tag
        keywords.append("implementation")

        return keywords

    async def trigger_checkpoint_for_critical_tool(self, tool_name: str) -> None:
        """
        Trigger immediate checkpoint after critical tool execution.

        Context7 Pattern: Non-blocking checkpoint trigger via MCP.
        Implements B1.3 requirement for immediate task checkpoint saves.

        Critical tools: Write, Edit, MultiEdit, Bash, TodoWrite

        Args:
            tool_name: Name of the critical tool that was executed
        """
        try:
            self.base.debug_log(f"Triggering checkpoint for critical tool: {tool_name}")

            # Call MCP checkpoint trigger (non-blocking)
            result = await self.base.safe_mcp_call(
                self.mcp_client,
                "devstream_trigger_checkpoint",
                {"reason": "tool_trigger"}
            )

            if result:
                # Extract checkpoint count from result
                # MCP returns: {content: [{type: "text", text: "✅ Checkpoint triggered..."}]}
                if isinstance(result, dict) and "content" in result:
                    content_text = result["content"][0]["text"] if result["content"] else ""
                    self.base.debug_log(f"Checkpoint result: {content_text}")
            else:
                self.base.debug_log("Checkpoint trigger returned no result (non-blocking)")

        except Exception as e:
            # Context7 Pattern: Graceful degradation - log but don't fail
            self.base.debug_log(f"Checkpoint trigger failed (non-blocking): {e}")

    def update_memory_embedding(
        self,
        memory_id: str,
        embedding: List[float]
    ) -> bool:
        """
        Update semantic_memory record with embedding vector.

        Direct SQLite UPDATE for embedding storage. Database triggers
        will automatically sync to vec_semantic_memory virtual table.

        Context7 Pattern: Uses sqlite_vec_helper for proper extension loading.

        Args:
            memory_id: Memory record ID
            embedding: Embedding vector (list of floats)

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Convert embedding to JSON string for SQLite storage
            embedding_json = json.dumps(embedding)

            # Context7 Pattern: Use helper for proper vec0 loading
            conn = get_db_connection_with_vec(self.db_path)
            cursor = conn.cursor()

            # Update embedding in semantic_memory
            cursor.execute(
                "UPDATE semantic_memory SET embedding = ? WHERE id = ?",
                (embedding_json, memory_id)
            )

            conn.commit()
            rows_updated = cursor.rowcount
            conn.close()

            if rows_updated > 0:
                self.base.debug_log(
                    f"Embedding updated: {memory_id[:8]}... "
                    f"({len(embedding)} dimensions)"
                )
                return True
            else:
                self.base.debug_log(f"No record found to update: {memory_id}")
                return False

        except Exception as e:
            self.base.debug_log(f"Embedding update error: {e}")
            return False

    async def store_in_memory(
        self,
        file_path: str,
        content: str,
        operation: str
    ) -> Optional[str]:
        """
        Store file modification in DevStream memory with embedding.

        Phase 2 Enhancement: Now generates embedding and stores it inline.

        Args:
            file_path: Path to modified file
            content: File content
            operation: Operation type (Write, Edit, MultiEdit)

        Returns:
            Memory ID if storage successful, None otherwise
        """
        try:
            # Extract content preview
            preview = self.extract_content_preview(content, max_length=500)

            # Build memory content
            memory_content = f"""# File Modified: {Path(file_path).name}

**Operation**: {operation}
**File**: {file_path}

## Content Preview

{preview}
"""

            # Extract keywords
            keywords = self.extract_keywords(file_path, content)

            self.base.debug_log(f"Storing memory: {len(preview)} chars, {len(keywords)} keywords")

            # Store via MCP (without embedding initially)
            result = await self.base.safe_mcp_call(
                self.mcp_client,
                "devstream_store_memory",
                {
                    "content": memory_content,
                    "content_type": "code",
                    "keywords": keywords
                }
            )

            if not result:
                self.base.debug_log("Memory storage returned no result")
                return None

            # Extract memory_id from MCP result
            # MCP returns: {"success": true, "memory_id": "...", ...}
            memory_id = None
            if isinstance(result, dict):
                memory_id = result.get('memory_id')

            if not memory_id:
                self.base.debug_log("No memory_id in MCP response")
                return None

            self.base.success_feedback(f"Memory stored: {Path(file_path).name}")

            # Phase 2: Generate and store embedding (graceful degradation)
            try:
                self.base.debug_log("Generating embedding via Ollama...")

                # Generate embedding for full content (not just preview)
                embedding = self.ollama_client.generate_embedding(content)

                if embedding:
                    # Update memory record with embedding
                    if self.update_memory_embedding(memory_id, embedding):
                        self.base.debug_log(
                            f"✓ Embedding stored: {len(embedding)}D"
                        )
                    else:
                        self.base.debug_log("Embedding update failed")
                else:
                    self.base.debug_log("Embedding generation returned None")

            except Exception as embed_error:
                # Graceful degradation - log but don't fail
                self.base.debug_log(
                    f"Embedding generation failed (non-blocking): {embed_error}"
                )

            return memory_id

        except Exception as e:
            self.base.debug_log(f"Memory storage error: {e}")
            return None

    async def process(self, context: PostToolUseContext) -> None:
        """
        Main hook processing logic.

        Args:
            context: PostToolUse context from cchooks
        """
        # Check if hook should run
        if not self.base.should_run():
            self.base.debug_log("Hook disabled via config")
            context.output.exit_success()
            return

        # Check if memory storage enabled
        if not self.base.is_memory_store_enabled():
            self.base.debug_log("Memory storage disabled")
            context.output.exit_success()
            return

        # Extract tool information
        tool_name = context.tool_name
        tool_input = context.tool_input

        self.base.debug_log(f"Processing {tool_name} for {tool_input.get('file_path', 'unknown')}")

        # Define critical tools that trigger checkpoints
        critical_tools = ["Write", "Edit", "MultiEdit", "Bash", "TodoWrite"]
        is_critical_tool = tool_name in critical_tools

        # Only process Write/Edit operations for memory storage
        if tool_name not in ["Write", "Edit", "MultiEdit"]:
            # Check if it's another critical tool (Bash, TodoWrite)
            if is_critical_tool:
                # Trigger checkpoint for critical non-file tools
                await self.trigger_checkpoint_for_critical_tool(tool_name)
            context.output.exit_success()
            return

        # Extract file information
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("content", "") or tool_input.get("new_string", "")

        if not file_path or not content:
            self.base.debug_log("Missing file path or content")
            context.output.exit_success()
            return

        # Skip if file is in excluded paths
        excluded_paths = [
            ".git/",
            "node_modules/",
            ".venv/",
            ".devstream/",
            "__pycache__/",
            "dist/",
            "build/",
        ]
        if any(excluded in file_path for excluded in excluded_paths):
            self.base.debug_log(f"Skipping excluded path: {file_path}")
            context.output.exit_success()
            return

        try:
            # Store in memory with embedding (Phase 2 enhanced)
            memory_id = await self.store_in_memory(file_path, content, tool_name)

            if not memory_id:
                # Non-blocking warning
                self.base.warning_feedback("Memory storage unavailable")

            # B1.3: Trigger checkpoint for critical tool execution
            if is_critical_tool:
                await self.trigger_checkpoint_for_critical_tool(tool_name)

            # Always allow the operation to proceed (graceful degradation)
            context.output.exit_success()

        except Exception as e:
            # Non-blocking error - log and continue
            self.base.warning_feedback(f"Memory storage failed: {str(e)[:50]}")
            context.output.exit_success()


def main():
    """Main entry point for PostToolUse hook."""
    # Create context using cchooks
    ctx = safe_create_context()

    # Verify it's PostToolUse context
    if not isinstance(ctx, PostToolUseContext):
        print(f"Error: Expected PostToolUseContext, got {type(ctx)}", file=sys.stderr)
        sys.exit(1)

    # Create and run hook
    hook = PostToolUseHook()

    try:
        # Run async processing
        asyncio.run(hook.process(ctx))
    except Exception as e:
        # Graceful failure - non-blocking
        print(f"⚠️  DevStream: PostToolUse error", file=sys.stderr)
        ctx.output.exit_non_block(f"Hook error: {str(e)[:100]}")


if __name__ == "__main__":
    main()