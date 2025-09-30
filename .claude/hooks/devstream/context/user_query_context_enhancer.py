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
DevStream UserPromptSubmit Hook - Context Enhancement before User Query
Combines Context7 library docs, DevStream memory, and task detection.
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))

from cchooks import safe_create_context, UserPromptSubmitContext
from devstream_base import DevStreamHookBase
from context7_client import Context7Client
from mcp_client import get_mcp_client


class UserPromptSubmitHook:
    """
    UserPromptSubmit hook for intelligent query enhancement.
    Combines Context7 research + DevStream memory + task lifecycle detection.
    """

    def __init__(self):
        self.base = DevStreamHookBase("user_prompt_submit")
        self.mcp_client = get_mcp_client()
        self.context7 = Context7Client(self.mcp_client)

    async def detect_context7_trigger(self, user_input: str) -> bool:
        """
        Detect if Context7 should be triggered for this query.

        Args:
            user_input: User input text

        Returns:
            True if Context7 should search for library docs
        """
        return await self.context7.should_trigger_context7(user_input)

    async def get_context7_research(self, user_input: str) -> Optional[str]:
        """
        Get Context7 research for user query.

        Args:
            user_input: User input text

        Returns:
            Formatted Context7 docs or None
        """
        try:
            self.base.debug_log("Context7 triggered - searching for docs")

            # Search and retrieve documentation
            result = await self.context7.search_and_retrieve(user_input)

            if result.success and result.docs:
                self.base.success_feedback(f"Context7 docs: {result.library_id}")
                return self.context7.format_docs_for_context(result)
            else:
                self.base.debug_log(f"Context7 search failed: {result.error}")
                return None

        except Exception as e:
            self.base.debug_log(f"Context7 error: {e}")
            return None

    async def search_devstream_memory(self, user_input: str) -> Optional[str]:
        """
        Search DevStream memory for relevant context.

        Args:
            user_input: User input text

        Returns:
            Formatted memory context or None
        """
        try:
            self.base.debug_log(f"Searching DevStream memory: {user_input[:50]}...")

            # Search memory via MCP
            result = await self.base.safe_mcp_call(
                self.mcp_client,
                "devstream_search_memory",
                {
                    "query": user_input,
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

    async def detect_task_lifecycle_event(self, user_input: str) -> Optional[Dict[str, str]]:
        """
        Detect task lifecycle events from user input.

        Args:
            user_input: User input text

        Returns:
            Event data if detected, None otherwise
        """
        input_lower = user_input.lower()

        # Task creation patterns
        if any(pattern in input_lower for pattern in [
            "create task",
            "new task",
            "add task",
            "start working on"
        ]):
            return {
                "event_type": "task_creation",
                "pattern": "User initiated new task",
                "query": user_input[:100]
            }

        # Task completion patterns
        elif any(pattern in input_lower for pattern in [
            "complete",
            "finished",
            "done with",
            "completed the",
            "task complete"
        ]):
            return {
                "event_type": "task_completion",
                "pattern": "User indicated task completion",
                "query": user_input[:100]
            }

        # Implementation progress patterns
        elif any(pattern in input_lower for pattern in [
            "implement",
            "build",
            "create",
            "working on"
        ]):
            return {
                "event_type": "implementation_progress",
                "pattern": "User starting implementation work",
                "query": user_input[:100]
            }

        return None

    async def assemble_enhanced_context(
        self,
        user_input: str
    ) -> Optional[str]:
        """
        Assemble enhanced context from multiple sources.

        Args:
            user_input: User input text

        Returns:
            Assembled enhanced context or None
        """
        context_parts = []

        # Check if Context7 should trigger
        if await self.detect_context7_trigger(user_input):
            context7_docs = await self.get_context7_research(user_input)
            if context7_docs:
                context_parts.append(context7_docs)

        # Search DevStream memory
        memory_context = await self.search_devstream_memory(user_input)
        if memory_context:
            context_parts.append(memory_context)

        # Detect task lifecycle events
        task_event = await self.detect_task_lifecycle_event(user_input)
        if task_event:
            event_context = f"""# Task Lifecycle Event Detected

**Event Type**: {task_event['event_type']}
**Pattern**: {task_event['pattern']}

This query appears to be related to task management. Consider using TodoWrite for tracking progress.
"""
            context_parts.append(event_context)

        if not context_parts:
            return None

        # Assemble final context
        assembled = "\n\n---\n\n".join(context_parts)
        return f"# Enhanced Context for Query\n\n{assembled}"

    async def process(self, context: UserPromptSubmitContext) -> None:
        """
        Main hook processing logic.

        Args:
            context: UserPromptSubmit context from cchooks
        """
        # Check if hook should run
        if not self.base.should_run():
            self.base.debug_log("Hook disabled via config")
            context.output.exit_success()
            return

        # Extract user input
        user_input = context.user_input

        if not user_input or len(user_input) < 10:
            self.base.debug_log("User input too short for enhancement")
            context.output.exit_success()
            return

        self.base.debug_log(f"Processing user query: {len(user_input)} chars")

        try:
            # Assemble enhanced context
            enhanced_context = await self.assemble_enhanced_context(user_input)

            if enhanced_context:
                # Inject context
                self.base.inject_context(enhanced_context)
                self.base.success_feedback("Query context enhanced")
            else:
                self.base.debug_log("No relevant context found")

            # Always allow the operation to proceed
            context.output.exit_success()

        except Exception as e:
            # Non-blocking error - log and continue
            self.base.warning_feedback(f"Context enhancement failed: {str(e)[:50]}")
            context.output.exit_success()


def main():
    """Main entry point for UserPromptSubmit hook."""
    # Create context using cchooks
    ctx = safe_create_context()

    # Verify it's UserPromptSubmit context
    if not isinstance(ctx, UserPromptSubmitContext):
        print(f"Error: Expected UserPromptSubmitContext, got {type(ctx)}", file=sys.stderr)
        sys.exit(1)

    # Create and run hook
    hook = UserPromptSubmitHook()

    try:
        # Run async processing
        asyncio.run(hook.process(ctx))
    except Exception as e:
        # Graceful failure - non-blocking
        print(f"⚠️  DevStream: UserPromptSubmit error", file=sys.stderr)
        ctx.output.exit_non_block(f"Hook error: {str(e)[:100]}")


if __name__ == "__main__":
    main()