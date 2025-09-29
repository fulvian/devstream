#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.0.0",
#     "python-dotenv>=1.0.0",
#     "aiohttp>=3.8.0",
# ]
# ///

"""
DevStream PostToolUse Hook - Results & Learning Capture
Context7-compliant automatic capture di tool results, outputs, errors, learning.
"""

import json
import sys
import os
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Import DevStream utilities
sys.path.append(str(Path(__file__).parent.parent / 'utils'))
from common import DevStreamHookBase, get_project_context
from logger import get_devstream_logger

class PostToolUseHook(DevStreamHookBase):
    """
    PostToolUse hook per automatic capture di tool results e learning.
    Implementa Context7-validated patterns per memory automation.
    """

    def __init__(self):
        super().__init__('post_tool_use')
        self.structured_logger = get_devstream_logger('post_tool_use')
        self.start_time = time.time()

    async def process_tool_result(self, input_data: dict) -> None:
        """
        Process tool result e capture learning/outputs.

        Args:
            input_data: JSON input from Claude Code PostToolUse
        """
        self.structured_logger.log_hook_start(input_data, {"phase": "post_tool_use"})

        try:
            # Extract tool information
            tool_name = input_data.get('tool_name', 'unknown')
            tool_input = input_data.get('tool_input', {})
            tool_result = input_data.get('tool_result', {})
            session_id = input_data.get('session_id', 'unknown')

            # Analyze tool result for learning capture
            analysis = await self.analyze_tool_result(tool_name, tool_input, tool_result)

            # Store different types of learning/results
            await self.capture_results(session_id, tool_name, analysis)

            # Log performance metrics
            execution_time = (time.time() - self.start_time) * 1000
            self.structured_logger.log_performance_metrics(execution_time)

            self.logger.info(f"Captured results for tool: {tool_name}")

        except Exception as e:
            self.structured_logger.log_hook_error(e, {"tool_name": tool_name})
            raise

    async def analyze_tool_result(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze tool result per intelligent categorization.

        Args:
            tool_name: Name of executed tool
            tool_input: Tool input parameters
            tool_result: Tool execution result

        Returns:
            Analysis of tool result con categorization
        """
        analysis = {
            "tool_name": tool_name,
            "timestamp": datetime.now().isoformat(),
            "success": not tool_result.get('error', False),
            "content_type": self.classify_tool_result(tool_name, tool_result),
            "learning_value": self.assess_learning_value(tool_name, tool_result),
            "keywords": self.extract_tool_keywords(tool_name, tool_input, tool_result)
        }

        # Specific analysis based on tool type
        if tool_name in ['Edit', 'MultiEdit', 'Write']:
            analysis.update(await self.analyze_code_tool(tool_input, tool_result))
        elif tool_name in ['Bash']:
            analysis.update(await self.analyze_bash_tool(tool_input, tool_result))
        elif tool_name.startswith('mcp__devstream__'):
            analysis.update(await self.analyze_mcp_tool(tool_name, tool_input, tool_result))
        elif tool_name in ['Read', 'Glob', 'Grep']:
            analysis.update(await self.analyze_search_tool(tool_name, tool_input, tool_result))

        return analysis

    def classify_tool_result(self, tool_name: str, tool_result: Dict[str, Any]) -> str:
        """
        Classify tool result per DevStream content types.

        Args:
            tool_name: Tool name
            tool_result: Tool result data

        Returns:
            DevStream content type
        """
        # Error results
        if tool_result.get('error') or 'error' in str(tool_result).lower():
            return 'error'

        # Code generation/editing tools
        if tool_name in ['Edit', 'MultiEdit', 'Write', 'NotebookEdit']:
            return 'code'

        # Documentation tools
        if tool_name in ['Read'] and any(ext in str(tool_result) for ext in ['.md', '.txt', '.rst']):
            return 'documentation'

        # Command execution results
        if tool_name in ['Bash']:
            return 'output'

        # MCP DevStream operations
        if tool_name.startswith('mcp__devstream__'):
            return 'context'

        # Learning/research tools
        if tool_name in ['Glob', 'Grep', 'WebFetch', 'WebSearch']:
            return 'learning'

        # Default
        return 'output'

    def assess_learning_value(self, tool_name: str, tool_result: Dict[str, Any]) -> float:
        """
        Assess learning value del tool result (0.0-1.0).

        Args:
            tool_name: Tool name
            tool_result: Tool result data

        Returns:
            Learning value score
        """
        score = 0.5  # Base score

        # High learning value tools
        if tool_name in ['WebFetch', 'WebSearch', 'mcp__context7__get-library-docs']:
            score += 0.3

        # Code creation has high learning value
        if tool_name in ['Write', 'MultiEdit']:
            score += 0.2

        # Error results have learning value
        if tool_result.get('error'):
            score += 0.2

        # Large outputs have potential learning value
        result_size = len(str(tool_result))
        if result_size > 1000:
            score += 0.1
        elif result_size > 5000:
            score += 0.2

        return min(score, 1.0)

    def extract_tool_keywords(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_result: Dict[str, Any]
    ) -> list:
        """
        Extract keywords from tool execution.

        Args:
            tool_name: Tool name
            tool_input: Tool input
            tool_result: Tool result

        Returns:
            List of extracted keywords
        """
        keywords = [tool_name.lower()]

        # Extract from file paths
        if 'file_path' in tool_input:
            file_path = tool_input['file_path']
            keywords.append(Path(file_path).suffix.lstrip('.'))
            keywords.extend(Path(file_path).stem.split('_'))

        # Extract from commands
        if tool_name == 'Bash' and 'command' in tool_input:
            command = tool_input['command']
            keywords.extend(command.split()[:3])  # First 3 words

        # Extract from patterns
        if 'pattern' in tool_input:
            keywords.append('search')
            keywords.append('pattern')

        # Clean and deduplicate
        keywords = [k.strip('.,!?;:()[]{}') for k in keywords if len(k) > 2]
        return list(set(keywords))[:10]

    async def analyze_code_tool(
        self,
        tool_input: Dict[str, Any],
        tool_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze code editing tools.

        Args:
            tool_input: Tool input
            tool_result: Tool result

        Returns:
            Code-specific analysis
        """
        analysis = {
            "file_path": tool_input.get('file_path', ''),
            "language": self.detect_language(tool_input.get('file_path', '')),
            "lines_modified": self.estimate_lines_modified(tool_input),
            "modification_type": self.classify_code_modification(tool_input)
        }

        return analysis

    async def analyze_bash_tool(
        self,
        tool_input: Dict[str, Any],
        tool_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze bash command execution.

        Args:
            tool_input: Tool input
            tool_result: Tool result

        Returns:
            Bash-specific analysis
        """
        command = tool_input.get('command', '')

        analysis = {
            "command": command,
            "command_type": self.classify_bash_command(command),
            "exit_code": self.extract_exit_code(tool_result),
            "output_size": len(str(tool_result))
        }

        return analysis

    async def analyze_mcp_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze MCP DevStream tool calls.

        Args:
            tool_name: MCP tool name
            tool_input: Tool input
            tool_result: Tool result

        Returns:
            MCP-specific analysis
        """
        analysis = {
            "mcp_server": "devstream",
            "mcp_operation": tool_name.replace('mcp__devstream__', ''),
            "devstream_integration": True
        }

        # Specific analysis for DevStream operations
        if 'store_memory' in tool_name:
            analysis["memory_operation"] = "store"
            analysis["content_type"] = tool_input.get('content_type', 'unknown')
        elif 'search_memory' in tool_name:
            analysis["memory_operation"] = "search"
            analysis["query"] = tool_input.get('query', '')

        return analysis

    async def analyze_search_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze search/read tools.

        Args:
            tool_name: Tool name
            tool_input: Tool input
            tool_result: Tool result

        Returns:
            Search-specific analysis
        """
        analysis = {
            "search_type": tool_name.lower(),
            "results_count": self.count_results(tool_result),
            "search_successful": not tool_result.get('error', False)
        }

        if tool_name == 'Grep':
            analysis["pattern"] = tool_input.get('pattern', '')
        elif tool_name == 'Glob':
            analysis["glob_pattern"] = tool_input.get('pattern', '')
        elif tool_name == 'Read':
            analysis["file_path"] = tool_input.get('file_path', '')

        return analysis

    def detect_language(self, file_path: str) -> str:
        """Detect programming language from file path."""
        if not file_path:
            return 'unknown'

        ext = Path(file_path).suffix.lower()
        lang_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.jsx': 'javascript', '.tsx': 'typescript', '.java': 'java',
            '.cpp': 'cpp', '.c': 'c', '.h': 'c', '.hpp': 'cpp',
            '.rs': 'rust', '.go': 'go', '.php': 'php', '.rb': 'ruby',
            '.sh': 'bash', '.bash': 'bash', '.zsh': 'zsh',
            '.md': 'markdown', '.txt': 'text', '.json': 'json',
            '.yaml': 'yaml', '.yml': 'yaml', '.xml': 'xml',
            '.html': 'html', '.css': 'css', '.scss': 'scss'
        }
        return lang_map.get(ext, 'unknown')

    def estimate_lines_modified(self, tool_input: Dict[str, Any]) -> int:
        """Estimate number of lines modified."""
        if 'new_string' in tool_input:
            return len(tool_input['new_string'].split('\n'))
        elif 'content' in tool_input:
            return len(tool_input['content'].split('\n'))
        return 0

    def classify_code_modification(self, tool_input: Dict[str, Any]) -> str:
        """Classify type of code modification."""
        if 'old_string' in tool_input and 'new_string' in tool_input:
            return 'edit'
        elif 'content' in tool_input:
            return 'create'
        return 'unknown'

    def classify_bash_command(self, command: str) -> str:
        """Classify bash command type."""
        command = command.strip().split()[0] if command.strip() else ''

        if command in ['ls', 'find', 'grep', 'rg', 'cat', 'head', 'tail']:
            return 'read'
        elif command in ['mkdir', 'touch', 'cp', 'mv', 'rm']:
            return 'filesystem'
        elif command in ['git']:
            return 'version_control'
        elif command in ['python', 'node', 'npm', 'pip', 'uv']:
            return 'development'
        elif command in ['chmod', 'chown', 'sudo']:
            return 'system'
        else:
            return 'other'

    def extract_exit_code(self, tool_result: Dict[str, Any]) -> int:
        """Extract exit code from bash result."""
        # Try to extract exit code from tool result
        if isinstance(tool_result, dict) and 'exit_code' in tool_result:
            return tool_result['exit_code']
        elif 'error' in tool_result:
            return 1
        return 0

    def count_results(self, tool_result: Dict[str, Any]) -> int:
        """Count results from search tools."""
        result_str = str(tool_result)
        # Simple heuristic - count lines that look like results
        lines = result_str.split('\n')
        return len([line for line in lines if line.strip() and not line.startswith('error')])

    async def capture_results(
        self,
        session_id: str,
        tool_name: str,
        analysis: Dict[str, Any]
    ) -> None:
        """
        Capture results in DevStream memory via MCP.

        Args:
            session_id: Claude session ID
            tool_name: Tool name
            analysis: Tool analysis results
        """
        content_type = analysis.get('content_type', 'output')
        learning_value = analysis.get('learning_value', 0.5)

        # Only capture if learning value is significant
        if learning_value < 0.3:
            self.logger.debug(f"Skipping low-value result: {tool_name}")
            return

        # Prepare memory content
        memory_content = self.format_memory_content(session_id, tool_name, analysis)
        keywords = analysis.get('keywords', [])

        # Store via MCP (placeholder - actual MCP integration needed)
        response = await self.call_devstream_mcp(
            'devstream_store_memory',
            {
                'content': memory_content,
                'content_type': content_type,
                'keywords': keywords
            }
        )

        # Log memory operation
        self.structured_logger.log_memory_operation(
            operation="store",
            content_type=content_type,
            content_size=len(memory_content),
            keywords=keywords
        )

        if response:
            self.logger.info(f"Captured {tool_name} result in memory")
        else:
            self.logger.error(f"Failed to capture {tool_name} result")

    def format_memory_content(
        self,
        session_id: str,
        tool_name: str,
        analysis: Dict[str, Any]
    ) -> str:
        """
        Format content per memory storage.

        Args:
            session_id: Session ID
            tool_name: Tool name
            analysis: Analysis results

        Returns:
            Formatted memory content
        """
        content_parts = [
            f"TOOL RESULT [{session_id}]: {tool_name}",
            f"Timestamp: {analysis.get('timestamp', 'unknown')}",
            f"Success: {analysis.get('success', True)}",
            f"Learning Value: {analysis.get('learning_value', 0.5):.2f}"
        ]

        # Add specific details based on tool type
        if analysis.get('file_path'):
            content_parts.append(f"File: {analysis['file_path']}")
        if analysis.get('language'):
            content_parts.append(f"Language: {analysis['language']}")
        if analysis.get('command'):
            content_parts.append(f"Command: {analysis['command']}")
        if analysis.get('mcp_operation'):
            content_parts.append(f"MCP Operation: {analysis['mcp_operation']}")

        # Add keywords
        keywords = analysis.get('keywords', [])
        if keywords:
            content_parts.append(f"Keywords: {', '.join(keywords)}")

        return "\n".join(content_parts)

async def main():
    """Main hook execution following Context7 patterns."""
    hook = PostToolUseHook()

    try:
        # Read JSON input from stdin (Context7 pattern)
        input_data = hook.read_stdin_json()

        # Process the tool result
        await hook.process_tool_result(input_data)

        # Success exit
        hook.success_exit()

    except Exception as e:
        hook.error_exit(f"PostToolUse hook failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())