#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.0.0",
#     "python-dotenv>=1.0.0",
#     "structlog>=23.0.0",
# ]
# ///

"""
DevStream Project Context Hook - Basic Project Context Injection
Context7-compliant basic project context per session initialization.
"""

import json
import sys
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Import DevStream utilities
sys.path.append(str(Path(__file__).parent.parent / 'utils'))
from common import DevStreamHookBase, get_project_context
from logger import get_devstream_logger

class ProjectContextHook(DevStreamHookBase):
    """
    Basic project context hook per session initialization.
    Lightweight context injection per DevStream projects.
    """

    def __init__(self):
        super().__init__('project_context')
        self.structured_logger = get_devstream_logger('project_context')
        self.start_time = time.time()

    async def process_context_injection(self, input_data: dict) -> None:
        """
        Process basic project context injection.

        Args:
            input_data: Session input data
        """
        self.structured_logger.log_hook_start(input_data, {"phase": "project_context"})

        try:
            # Get project context
            context = get_project_context()

            # Generate basic context
            basic_context = self.generate_basic_context(context)

            # Inject if significant
            if basic_context and len(basic_context) > 100:
                self.output_context(basic_context)
                self.logger.info("Basic project context injected")

            # Log performance
            execution_time = (time.time() - self.start_time) * 1000
            self.structured_logger.log_performance_metrics(execution_time)

        except Exception as e:
            self.structured_logger.log_hook_error(e, {"input_data": input_data})
            # Don't raise - context injection is optional
            pass

    def generate_basic_context(self, context: Dict[str, Any]) -> str:
        """
        Generate basic project context.

        Args:
            context: Project context

        Returns:
            Basic context string
        """
        if not context.get('is_devstream_project', False):
            return ""

        context_parts = [
            "📁 DevStream Project Context",
            f"🏗️ Methodology: {context.get('methodology', 'Research-Driven Development')}",
            f"🎯 Focus: Task management + semantic memory",
            ""
        ]

        return '\n'.join(context_parts)

async def main():
    """Main hook execution."""
    hook = ProjectContextHook()

    try:
        # Read input
        input_data = hook.read_stdin_json()

        # Process context injection
        await hook.process_context_injection(input_data)

        # Success exit
        hook.success_exit()

    except Exception as e:
        hook.error_exit(f"Project context hook failed: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())