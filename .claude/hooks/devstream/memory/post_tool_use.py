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
DevStream PostToolUse Hook - Memory Storage after Write/Edit
Stores modified file content in DevStream semantic memory with embeddings.
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))

from cchooks import safe_create_context, PostToolUseContext
from devstream_base import DevStreamHookBase
from mcp_client import get_mcp_client


class PostToolUseHook:
    """
    PostToolUse hook for automatic memory storage.
    Stores file modifications in DevStream semantic memory.
    """

    def __init__(self):
        self.base = DevStreamHookBase("post_tool_use")
        self.mcp_client = get_mcp_client()

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

    async def store_in_memory(
        self,
        file_path: str,
        content: str,
        operation: str
    ) -> bool:
        """
        Store file modification in DevStream memory.

        Args:
            file_path: Path to modified file
            content: File content
            operation: Operation type (Write, Edit, MultiEdit)

        Returns:
            True if storage successful, False otherwise
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

            # Store via MCP
            result = await self.base.safe_mcp_call(
                self.mcp_client,
                "devstream_store_memory",
                {
                    "content": memory_content,
                    "content_type": "code",
                    "keywords": keywords
                }
            )

            if result:
                self.base.success_feedback(f"Memory stored: {Path(file_path).name}")
                return True
            else:
                self.base.debug_log("Memory storage returned no result")
                return False

        except Exception as e:
            self.base.debug_log(f"Memory storage error: {e}")
            return False

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

        # Only process Write/Edit operations
        if tool_name not in ["Write", "Edit", "MultiEdit"]:
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
            # Store in memory
            success = await self.store_in_memory(file_path, content, tool_name)

            if not success:
                # Non-blocking warning
                self.base.warning_feedback("Memory storage unavailable")

            # Always allow the operation to proceed
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