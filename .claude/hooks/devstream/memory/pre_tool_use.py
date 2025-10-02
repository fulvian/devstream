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
Agent Auto-Delegation System integration for intelligent agent routing.
"""

import sys
import asyncio
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
sys.path.insert(0, str(Path(__file__).parent.parent))  # Add devstream hooks dir to path

from cchooks import safe_create_context, PreToolUseContext
from devstream_base import DevStreamHookBase
from mcp_client import get_mcp_client

# Agent Auto-Delegation imports (with graceful degradation)
try:
    from agents.pattern_matcher import PatternMatcher
    from agents.agent_router import AgentRouter, TaskAssessment
    AGENT_DELEGATION_AVAILABLE = True
except ImportError as e:
    AGENT_DELEGATION_AVAILABLE = False
    _IMPORT_ERROR = str(e)
    # Provide fallback type for type hints when delegation unavailable
    TaskAssessment = Any  # type: ignore


class PreToolUseHook:
    """
    PreToolUse hook for intelligent context injection.
    Combines Context7 library docs + DevStream semantic memory + Agent Auto-Delegation.
    """

    def __init__(self):
        self.base = DevStreamHookBase("pre_tool_use")
        self.mcp_client = get_mcp_client()

        # Agent Auto-Delegation components (graceful degradation)
        self.pattern_matcher: Optional[PatternMatcher] = None
        self.agent_router: Optional[AgentRouter] = None

        if AGENT_DELEGATION_AVAILABLE:
            try:
                self.pattern_matcher = PatternMatcher()
                self.agent_router = AgentRouter()
                self.base.debug_log("Agent Auto-Delegation enabled")
            except Exception as e:
                self.base.debug_log(f"Agent Auto-Delegation init failed: {e}")
        else:
            self.base.debug_log(f"Agent Auto-Delegation unavailable: {_IMPORT_ERROR}")

        # Token budget configuration
        self.memory_token_budget = int(
            os.getenv("DEVSTREAM_CONTEXT_MAX_TOKENS", "2000")
        )

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count using chars/4 approximation.

        Claude tokenization: ~4 chars per token average.
        Conservative estimate ensures budget compliance.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        return len(text) // 4

    def _detect_libraries(self, content: str, file_path: str) -> List[str]:
        """
        Extract library names from imports and usage patterns.

        Args:
            content: File content to analyze
            file_path: File path for extension-based detection

        Returns:
            List of lowercase library names (Context7-compatible)

        Note:
            All names normalized to lowercase for Context7 compatibility.
            Example: "FastAPI" → "fastapi", "SQLAlchemy" → "sqlalchemy"
        """
        libraries = []
        file_ext = Path(file_path).suffix.lower()

        # Python imports
        if file_ext == '.py':
            import_pattern = r'^(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            for match in re.finditer(import_pattern, content, re.MULTILINE):
                lib = match.group(1)
                # Skip stdlib
                if lib not in ['os', 'sys', 're', 'json', 'typing', 'pathlib',
                              'datetime', 'asyncio', 'subprocess', 'logging']:
                    libraries.append(lib)

        # JavaScript/TypeScript imports
        elif file_ext in ['.js', '.ts', '.jsx', '.tsx']:
            import_pattern = r'(?:import|require)\s*\(?[\'"]([^\'"\)]+)[\'"]'
            for match in re.finditer(import_pattern, content):
                lib = match.group(1).split('/')[0]  # Get package name
                if not lib.startswith('.'):  # Skip relative imports
                    libraries.append(lib)

        # Framework detection patterns (cross-language)
        # Note: Patterns are file-extension aware to reduce false positives
        framework_patterns = {
            'fastapi': (r'(?:from\s+fastapi|FastAPI\()', ['.py']),
            'django': (r'(?:from\s+django|django\.)', ['.py']),
            'flask': (r'(?:from\s+flask|@app\.route)', ['.py']),
            'react': (r'(?:import.*React|useState|useEffect|createContext)', ['.js', '.jsx', '.ts', '.tsx']),
            'vue': (r'(?:import.*Vue|createApp|defineComponent)', ['.js', '.ts', '.vue']),
            'next': (r'(?:import.*next|getServerSideProps|getStaticProps)', ['.js', '.jsx', '.ts', '.tsx']),
            'express': (r'(?:express\(\)|app\.get\(|app\.post\()', ['.js', '.ts']),
            'pytest': (r'(?:import\s+pytest|@pytest\.)', ['.py']),
            'jest': (r'(?:describe\(|test\(|expect\()', ['.js', '.ts', '.jsx', '.tsx']),
            'sqlalchemy': (r'(?:from\s+sqlalchemy|declarative_base|relationship)', ['.py']),
        }

        for lib, (pattern, extensions) in framework_patterns.items():
            # Only check if file extension matches
            if file_ext in extensions and re.search(pattern, content, re.IGNORECASE):
                libraries.append(lib)

        # Normalize to lowercase and remove duplicates for Context7 compatibility
        return list(set(lib.lower() for lib in libraries))

    def _build_code_aware_query(self, file_path: str, content: str) -> str:
        """
        Build intelligent query from code structure.

        Extracts:
        - Imports (libraries/modules being used)
        - Class names (key abstractions)
        - Function names (main operations)
        - Decorators (framework patterns like @app.get, @pytest.fixture)

        Args:
            file_path: Path to file being edited
            content: File content

        Returns:
            Structured query string with code elements

        Performance:
            Target: <50ms for typical files (99th percentile)
        """
        import time
        start_time = time.time()

        filename = Path(file_path).name
        ext = Path(file_path).suffix.lower()

        elements = [filename]

        # Python code analysis
        if ext == '.py':
            # Extract imports
            import_pattern = r'^(?:from\s+(\S+)|import\s+(\S+))'
            imports = re.findall(import_pattern, content, re.MULTILINE)
            imports = [i[0] or i[1] for i in imports if i[0] or i[1]]
            # Filter out stdlib and builtins, split dotted imports
            filtered_imports = []
            stdlib = {'os', 'sys', 're', 'json', 'typing', 'pathlib', 'datetime',
                     'asyncio', 'subprocess', 'logging', 'time', 'collections'}
            for imp in imports:
                base = imp.split('.')[0]  # Get root module
                if base not in stdlib:
                    filtered_imports.append(base)
            elements.extend(filtered_imports[:5])  # Max 5 imports

            # Extract class names
            class_pattern = r'^class\s+(\w+)'
            classes = re.findall(class_pattern, content, re.MULTILINE)
            elements.extend(classes[:3])  # Max 3 classes

            # Extract function/method names
            func_pattern = r'^(?:async\s+)?def\s+(\w+)'
            funcs = re.findall(func_pattern, content, re.MULTILINE)
            elements.extend(funcs[:5])  # Max 5 functions

            # Extract decorators (framework indicators)
            decorator_pattern = r'^@(\w+(?:\.\w+)?)'
            decorators = re.findall(decorator_pattern, content, re.MULTILINE)
            elements.extend(decorators[:3])  # Max 3 decorators

        # TypeScript/JavaScript analysis
        elif ext in ['.ts', '.tsx', '.js', '.jsx']:
            # Extract imports
            import_pattern = r'(?:import|from)\s+[\'"]([^\'"]+)[\'"]'
            imports = re.findall(import_pattern, content)
            # Filter relative imports and get package names
            filtered_imports = []
            for imp in imports:
                if not imp.startswith('.'):
                    # Get package name (before first /)
                    pkg = imp.split('/')[0]
                    filtered_imports.append(pkg)
            elements.extend(filtered_imports[:5])

            # Extract class/component names
            class_pattern = r'(?:class|function|const)\s+(\w+)'
            names = re.findall(class_pattern, content)
            elements.extend(names[:5])

        # Rust analysis
        elif ext == '.rs':
            # Extract use statements
            use_pattern = r'^use\s+([a-zA-Z_][a-zA-Z0-9_:]*)'
            uses = re.findall(use_pattern, content, re.MULTILINE)
            elements.extend([u.split('::')[0] for u in uses[:5]])

            # Extract struct/enum/trait names
            type_pattern = r'^(?:struct|enum|trait|impl)\s+(\w+)'
            types = re.findall(type_pattern, content, re.MULTILINE)
            elements.extend(types[:5])

        # Go analysis
        elif ext == '.go':
            # Extract imports
            import_pattern = r'import\s+(?:"([^"]+)"|`([^`]+)`)'
            imports = re.findall(import_pattern, content)
            imports = [i[0] or i[1] for i in imports]
            elements.extend([imp.split('/')[-1] for imp in imports[:5]])

            # Extract type/struct/interface names
            type_pattern = r'^type\s+(\w+)'
            types = re.findall(type_pattern, content, re.MULTILINE)
            elements.extend(types[:5])

        # Build query with code structure
        query = " ".join(elements)

        # Fallback to content prefix if no elements extracted
        if len(query) < 50:
            query = f"{filename} {content[:300]}"

        # Log performance metrics
        elapsed_ms = (time.time() - start_time) * 1000
        self.base.debug_log(
            f"Code-aware query built in {elapsed_ms:.1f}ms: {query[:80]}..."
        )

        return query

    async def get_context7_docs(self, file_path: str, content: str) -> Optional[str]:
        """
        Detect libraries and emit Context7 advisory for Claude.

        Instead of directly calling Context7 MCP tools (which doesn't work with
        stdio MCP servers), this method detects libraries and emits an advisory
        message that Claude can act upon using its native MCP access.

        Args:
            file_path: Path to file being edited
            content: File content

        Returns:
            Context7 advisory message or None
        """
        try:
            # Detect libraries from imports/usage
            libraries = self._detect_libraries(content, file_path)

            if not libraries:
                self.base.debug_log("No external libraries detected for Context7")
                return None

            self.base.debug_log(f"Context7 advisory - detected libraries: {', '.join(libraries)}")

            # Emit advisory message for Claude
            advisory = "# Context7 Advisory\n\n"
            advisory += f"**File**: {Path(file_path).name}\n\n"
            advisory += f"**Detected Libraries**: {', '.join(libraries)}\n\n"
            advisory += "**Recommendation**: Retrieve up-to-date documentation using Context7:\n\n"

            for lib in libraries[:3]:  # Limit to top 3 to avoid context bloat
                advisory += f"### {lib}\n\n"
                advisory += "1. Resolve library ID:\n"
                advisory += f"```\nmcp__context7__resolve-library-id\n"
                advisory += f"libraryName: {lib}\n```\n\n"
                advisory += "2. Retrieve documentation:\n"
                advisory += f"```\nmcp__context7__get-library-docs\n"
                advisory += f"context7CompatibleLibraryID: <resolved_id_from_step_1>\n"
                advisory += f"tokens: 5000\n```\n\n"

            if len(libraries) > 3:
                advisory += f"*Additional libraries detected: {', '.join(libraries[3:])}*\n\n"

            advisory += "---\n"
            advisory += "*Context7 advisory generated by DevStream PreToolUse hook*\n"

            self.base.success_feedback(f"Context7 advisory generated for {len(libraries)} libraries")
            return advisory

        except Exception as e:
            self.base.debug_log(f"Context7 advisory generation error: {e}")
            return None

    def _format_memory_with_budget(
        self,
        memory_items: List[Dict],
        max_tokens: int = 2000
    ) -> str:
        """
        Format memory results within token budget.

        Args:
            memory_items: Search results
            max_tokens: Maximum tokens to use (default: 2000)

        Returns:
            Formatted memory context within budget
        """
        formatted = "# DevStream Memory Context\n\n"
        used_tokens = self._estimate_tokens(formatted)

        for i, item in enumerate(memory_items, 1):
            content = item.get("content", "")
            score = item.get("relevance_score", 0.0)

            # Create result header
            header = f"## Result {i} (relevance: {score:.2f})\n"

            # Calculate available tokens for this result
            header_tokens = self._estimate_tokens(header)
            available = max_tokens - used_tokens - header_tokens - 20  # Buffer

            if available < 50:  # Minimum useful content
                break

            # Truncate content to fit budget
            max_chars = available * 4
            truncated_content = content[:max_chars]

            # Add result
            result_block = f"{header}{truncated_content}\n\n"
            result_tokens = self._estimate_tokens(result_block)

            if used_tokens + result_tokens > max_tokens:
                break

            formatted += result_block
            used_tokens += result_tokens

        formatted += f"\n*Total tokens used: ~{used_tokens}/{max_tokens}*\n"
        return formatted

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
            # Build code-aware search query
            query = self._build_code_aware_query(file_path, content)

            self.base.debug_log(f"Searching DevStream memory: {query[:50]}...")

            # Search memory via MCP
            result = await self.mcp_client.search_memory(
                query=query,
                limit=3
            )

            if not result or not result.get("results"):
                self.base.debug_log("No relevant memory found")
                return None

            # Format memory results with token budget enforcement
            memory_items = result.get("results", [])
            if not memory_items:
                return None

            formatted = self._format_memory_with_budget(
                memory_items,
                max_tokens=self.memory_token_budget
            )

            self.base.success_feedback(f"Found {len(memory_items)} relevant memories")
            return formatted

        except Exception as e:
            self.base.debug_log(f"Memory search error: {e}")
            return None

    async def check_agent_delegation(
        self,
        file_path: Optional[str],
        content: Optional[str],
        tool_name: Optional[str],
        user_query: Optional[str] = None
    ) -> Optional[TaskAssessment]:
        """
        Check if task should be delegated to specialized agent.

        Args:
            file_path: Optional file path being worked on
            content: Optional file content
            tool_name: Optional tool name (e.g., 'Write', 'Edit')
            user_query: Optional user query string

        Returns:
            TaskAssessment if delegation match found, None otherwise

        Note:
            Gracefully degrades if Agent Auto-Delegation unavailable
        """
        # Check if Agent Auto-Delegation is enabled via config
        if not os.getenv("DEVSTREAM_AGENT_AUTO_DELEGATION_ENABLED", "true").lower() == "true":
            self.base.debug_log("Agent Auto-Delegation disabled via config")
            return None

        # Check if components available
        if not self.pattern_matcher or not self.agent_router:
            return None

        try:
            # Match patterns
            pattern_match = self.pattern_matcher.match_patterns(
                file_path=file_path,
                content=content,
                user_query=user_query,
                tool_name=tool_name
            )

            if not pattern_match:
                self.base.debug_log("No agent pattern match found")
                return None

            # Assess task complexity
            context = {
                "file_path": file_path,
                "content": content,
                "user_query": user_query or "",
                "tool_name": tool_name,
                "affected_files": [file_path] if file_path else []
            }

            assessment = await self.agent_router.assess_task_complexity(
                pattern_match=pattern_match,
                context=context
            )

            self.base.debug_log(
                f"Agent delegation assessment: {assessment.recommendation} "
                f"({assessment.suggested_agent}, confidence={assessment.confidence:.2f})"
            )

            # Log delegation decision to DevStream memory (non-blocking)
            await self._log_delegation_decision(assessment, pattern_match)

            return assessment

        except Exception as e:
            # Non-blocking error - log and continue
            self.base.debug_log(f"Agent delegation check failed: {e}")
            return None

    async def _log_delegation_decision(
        self,
        assessment: TaskAssessment,
        pattern_match: Dict[str, Any]
    ) -> None:
        """
        Log delegation decision to DevStream memory.

        Args:
            assessment: Task assessment with delegation recommendation
            pattern_match: Pattern match information

        Note:
            Non-blocking - errors are logged but do not interrupt execution
        """
        # Check if memory is enabled
        if not os.getenv("DEVSTREAM_MEMORY_ENABLED", "true").lower() == "true":
            return

        try:
            # Format delegation decision log
            agent = assessment.suggested_agent
            confidence = assessment.confidence
            recommendation = assessment.recommendation
            reason = assessment.reason
            complexity = assessment.complexity
            impact = assessment.architectural_impact

            content = (
                f"Agent Delegation: @{agent} (confidence {confidence:.2f}, {recommendation})\n"
                f"Reason: {reason}\n"
                f"Complexity: {complexity} | Impact: {impact}"
            )

            # Extract keywords
            keywords = [
                "agent-delegation",
                agent,
                recommendation.lower(),
                complexity.lower()
            ]

            # Store in memory via MCP
            await self.mcp_client.store_memory(
                content=content,
                content_type="decision",
                keywords=keywords
            )

            self.base.debug_log(f"Delegation decision logged to memory: @{agent}")

        except Exception as e:
            # Non-blocking error - log and continue
            self.base.debug_log(f"Failed to log delegation decision: {e}")

    async def assemble_context(
        self,
        file_path: str,
        content: str
    ) -> Optional[str]:
        """
        Assemble hybrid context from Context7 + DevStream memory.

        Uses parallel execution via asyncio.gather() to reduce latency.
        Both retrievals execute concurrently, with independent error handling.

        Args:
            file_path: File being edited
            content: File content

        Returns:
            Assembled context string or None

        Performance:
            Target: <800ms (55% improvement from sequential 1772ms)
            Context7: 5000 token budget max
            Memory: 2000 token budget max
        """
        import time
        start_time = time.time()

        context_parts = []

        # Execute both retrievals in parallel (independent error handling)
        # Each method has try/except returning None on failure
        context7_task = self.get_context7_docs(file_path, content)
        memory_task = self.get_devstream_memory(file_path, content)

        context7_docs, memory_context = await asyncio.gather(
            context7_task,
            memory_task,
            return_exceptions=False  # Let individual methods handle errors
        )

        # Collect successful retrievals
        if context7_docs:
            context_parts.append(context7_docs)
        if memory_context:
            context_parts.append(memory_context)

        # Log performance metrics
        elapsed_ms = (time.time() - start_time) * 1000
        self.base.debug_log(
            f"Parallel context retrieval completed in {elapsed_ms:.0f}ms "
            f"(Context7: {'✓' if context7_docs else '✗'}, "
            f"Memory: {'✓' if memory_context else '✗'})"
        )

        if not context_parts:
            return None

        # Assemble final context
        assembled = "\n\n---\n\n".join(context_parts)
        return f"# Enhanced Context for {Path(file_path).name}\n\n{assembled}"

    async def process(self, context: PreToolUseContext) -> None:
        """
        Main hook processing logic.
        Integrates Agent Auto-Delegation + Context7 + DevStream memory.

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
            context_parts = []

            # PHASE 1: Agent Auto-Delegation (BEFORE Context7/memory injection)
            try:
                assessment = await self.check_agent_delegation(
                    file_path=file_path,
                    content=content,
                    tool_name=tool_name,
                    user_query=None  # user_query not available in PreToolUse context
                )

                if assessment and self.agent_router:
                    # Format advisory message
                    advisory_message = self.agent_router.format_advisory_message(assessment)

                    # Prepend advisory to context injection
                    advisory_header = (
                        "# Agent Auto-Delegation Advisory\n\n"
                        f"{advisory_message}\n\n"
                        "---\n\n"
                    )
                    context_parts.append(advisory_header)

                    self.base.success_feedback(
                        f"Agent delegation: {assessment.recommendation} "
                        f"({assessment.suggested_agent})"
                    )

            except Exception as e:
                # Non-blocking error - log and continue
                self.base.debug_log(f"Agent delegation failed: {e}")

            # PHASE 2: Context7 + DevStream memory injection
            enhanced_context = await self.assemble_context(file_path, content)
            if enhanced_context:
                context_parts.append(enhanced_context)

            # PHASE 3: Inject assembled context
            if context_parts:
                final_context = "\n".join(context_parts)
                self.base.inject_context(final_context)
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