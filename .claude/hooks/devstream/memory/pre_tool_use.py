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
DevStream PreToolUse Hook - Context Injection before Write/Edit
Context7 + DevStream hybrid context assembly con graceful fallback.
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))

from cchooks import safe_create_context, PreToolUseContext
from devstream_base import DevStreamHookBase
from context7_client import Context7Client
from mcp_client import get_mcp_client


class PreToolUseHook:
    """
    PreToolUse hook for intelligent context injection.
    Combines Context7 library docs + DevStream semantic memory.
    """

    def __init__(self):
        self.base = DevStreamHookBase("pre_tool_use")
        self.mcp_client = get_mcp_client()
        self.context7 = Context7Client(self.mcp_client)

    async def get_context7_docs(self, file_path: str, content: str) -> Optional[str]:
        """
        Get Context7 documentation if relevant library detected.

        Args:
            file_path: Path to file being edited
            content: File content

        Returns:
            Formatted Context7 docs or None
        """
        try:
            # Build query from file path and content preview
            query = f"{file_path} {content[:500]}"

            # Check if Context7 should trigger
            if not await self.context7.should_trigger_context7(query):
                self.base.debug_log("Context7 not triggered for this file")
                return None

            self.base.debug_log("Context7 triggered - searching for docs")

            # Search and retrieve documentation
            result = await self.context7.search_and_retrieve(query)

            if result.success and result.docs:
                self.base.success_feedback(f"Context7 docs retrieved: {result.library_id}")
                return self.context7.format_docs_for_context(result)
            else:
                self.base.debug_log(f"Context7 search failed: {result.error}")
                return None

        except Exception as e:
            self.base.debug_log(f"Context7 error: {e}")
            return None

    async def get_devstream_memory(self, file_path: str, content: str) -> Optional[str]:
        """
        Search DevStream memory for relevant context.

        Args:
            file_path: Path to file being edited
            content: File content preview

        Returns:
            Formatted memory context or None
        """
        try:
            # Build search query
            query = f"{Path(file_path).name} {content[:300]}"

            self.base.debug_log(f"Searching DevStream memory: {query[:50]}...")

            # Search memory via MCP
            result = await self.base.safe_mcp_call(
                self.mcp_client,
                "devstream_search_memory",
                {
                    "query": query,
                    "limit": 3
                }
            )

            if not result or not result.get("results"):
                self.base.debug_log("No relevant memory found")
                return None

            # Format memory results
            memory_items = result.get("results", [])
            if not memory_items:
                return None

            formatted = "# DevStream Memory Context\n\n"
            for i, item in enumerate(memory_items[:3], 1):
                content = item.get("content", "")[:300]
                score = item.get("relevance_score", 0.0)
                formatted += f"## Result {i} (relevance: {score:.2f})\n{content}\n\n"

            self.base.success_feedback(f"Found {len(memory_items)} relevant memories")
            return formatted

        except Exception as e:
            self.base.debug_log(f"Memory search error: {e}")
            return None

    async def assemble_context(
        self,
        file_path: str,
        content: str
    ) -> Optional[str]:
        """
        Assemble hybrid context from Context7 + DevStream memory.

        Args:
            file_path: File being edited
            content: File content

        Returns:
            Assembled context string or None
        """
        context_parts = []

        # Get Context7 docs (if relevant)
        context7_docs = await self.get_context7_docs(file_path, content)
        if context7_docs:
            context_parts.append(context7_docs)

        # Get DevStream memory
        memory_context = await self.get_devstream_memory(file_path, content)
        if memory_context:
            context_parts.append(memory_context)

        if not context_parts:
            return None

        # Assemble final context
        assembled = "\n\n---\n\n".join(context_parts)
        return f"# Enhanced Context for {Path(file_path).name}\n\n{assembled}"

    async def process(self, context: PreToolUseContext) -> None:
        """
        Main hook processing logic.

        Args:
            context: PreToolUse context from cchooks
        """
        # Check if hook should run
        if not self.base.should_run():
            self.base.debug_log("Hook disabled via config")
            context.output.exit_success()
            return

        # Extract tool information
        tool_name = context.tool_name
        tool_input = context.tool_input

        self.base.debug_log(f"Processing {tool_name} for {tool_input.get('file_path', 'unknown')}")

        # Only process Write/Edit operations
        if tool_name not in ["Write", "Edit", "MultiEdit"]:
            context.output.exit_success()
            return

        # Extract file information
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("content", "") or tool_input.get("new_string", "")

        if not file_path:
            self.base.debug_log("No file path in tool input")
            context.output.exit_success()
            return

        try:
            # Assemble context from multiple sources
            enhanced_context = await self.assemble_context(file_path, content)

            if enhanced_context:
                # Inject context
                self.base.inject_context(enhanced_context)
                self.base.success_feedback(f"Context injected for {Path(file_path).name}")
            else:
                self.base.debug_log("No relevant context found")

            # Always allow the operation to proceed
            context.output.exit_success()

        except Exception as e:
            # Non-blocking error - log and continue
            self.base.warning_feedback(f"Context injection failed: {str(e)[:50]}")
            context.output.exit_success()


def main():
    """Main entry point for PreToolUse hook."""
    # Create context using cchooks
    ctx = safe_create_context()

    # Verify it's PreToolUse context
    if not isinstance(ctx, PreToolUseContext):
        print(f"Error: Expected PreToolUseContext, got {type(ctx)}", file=sys.stderr)
        sys.exit(1)

    # Create and run hook
    hook = PreToolUseHook()

    try:
        # Run async processing
        asyncio.run(hook.process(ctx))
    except Exception as e:
        # Graceful failure - non-blocking
        print(f"⚠️  DevStream: PreToolUse error", file=sys.stderr)
        ctx.output.exit_non_block(f"Hook error: {str(e)[:100]}")


if __name__ == "__main__":
    main()