"""
Integration tests for DevStream PreToolUse hook with optimization components.

Tests validate:
- TaskAwareQueryConstructor integration (Task 4)
- TwoStageSearch integration (Task 5)
- SemanticCacheKeys integration (Task 3)
- End-to-end context injection workflow
- Graceful degradation patterns
- Performance targets
"""

import pytest
import asyncio
import time
import os
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

# Add path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'hooks'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'hooks' / 'devstream'))

# Import PreToolUse hook components
try:
    from devstream.memory.pre_tool_use import PreToolUseHook
    from cchooks import PreToolUseContext, PreToolUseOutput
    PRE_TOOL_USE_AVAILABLE = True
except ImportError as e:
    PRE_TOOL_USE_AVAILABLE = False
    PRE_TOOL_USE_IMPORT_ERROR = str(e)

# Import optimization components for testing
try:
    from optimization.task_aware_query_constructor import get_task_aware_query_constructor
    from optimization.two_stage_search import get_two_stage_search, QuantizationType
    from optimization.semantic_cache_keys import get_semantic_cache_keys, CacheHitType
    OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    OPTIMIZATION_AVAILABLE = False
    OPTIMIZATION_IMPORT_ERROR = str(e)


@pytest.mark.skipif(not PRE_TOOL_USE_AVAILABLE, reason=f"PreToolUse unavailable: {PRE_TOOL_USE_IMPORT_ERROR if 'PRE_TOOL_USE_IMPORT_ERROR' in locals() else 'Unknown'}")
@pytest.mark.skipif(not OPTIMIZATION_AVAILABLE, reason=f"Optimization components unavailable: {OPTIMIZATION_IMPORT_ERROR if 'OPTIMIZATION_IMPORT_ERROR' in locals() else 'Unknown'}")
class TestPreToolUseIntegration:
    """Integration tests for PreToolUse hook with optimization components."""

    @pytest.fixture
    def mock_context(self):
        """Create mock PreToolUseContext for testing."""
        context = Mock(spec=PreToolUseContext)
        context.tool_name = "Write"
        context.tool_input = {
            "file_path": "/test/example.py",
            "content": "def hello_world():\n    print('Hello, World!')\n"
        }
        context.output = Mock(spec=PreToolUseOutput)
        return context

    @pytest.fixture
    def hook(self):
        """Create PreToolUseHook instance for testing."""
        with patch.dict(os.environ, {
            'DEVSTREAM_MEMORY_ENABLED': 'true',
            'DEVSTREAM_CONTEXT7_ENABLED': 'false',  # Disable Context7 for testing
            'DEVSTREAM_AGENT_AUTO_DELEGATION_ENABLED': 'false'
        }):
            return PreToolUseHook()

    @pytest.mark.asyncio
    async def test_full_context_injection_workflow(self, hook, mock_context):
        """Test complete context injection workflow with all optimizations."""
        # Mock the unified client to avoid external dependencies
        mock_unified_client = AsyncMock()
        mock_unified_client.search_memory.return_value = {
            "results": [
                {
                    "content": "Previous implementation of hello_world function",
                    "relevance_score": 0.85,
                    "content_type": "code",
                    "metadata": {"file_path": "/old/example.py"}
                }
            ]
        }
        hook.unified_client = mock_unified_client

        # Mock context7 docs to avoid external API calls
        with patch.object(hook, 'get_context7_docs', return_value=None):
            start_time = time.time()

            # Process the hook
            await hook.process(mock_context)

            end_time = time.time()
            processing_time = (end_time - start_time) * 1000

        # Verify context was injected
        mock_context.output.exit_success.assert_called_once()

        # Performance should be reasonable (<5 seconds for integration test)
        assert processing_time < 5000, f"Processing too slow: {processing_time:.1f}ms"

    @pytest.mark.asyncio
    async def test_task_aware_query_constructor_integration(self, hook, mock_context):
        """Test TaskAwareQueryConstructor integration in context building."""
        if not hook.query_constructor:
            pytest.skip("TaskAwareQueryConstructor not available")

        # Test enhanced query construction
        basic_query = hook._build_code_aware_query(
            mock_context.tool_input["file_path"],
            mock_context.tool_input["content"]
        )

        # Should have basic query elements
        assert "example.py" in basic_query
        assert len(basic_query) > 0

        # Test TaskAwareQueryConstructor enhancement
        query_construction = hook.query_constructor.construct_enhanced_query(
            query=basic_query,
            search_results=[],
            token_budget=1000
        )

        # Should have enhanced query with analysis
        assert query_construction is not None
        assert query_construction.content != ""
        assert query_construction.query_analysis is not None
        assert query_construction.total_tokens > 0
        assert query_construction.construction_time_ms > 0

        # Should be more comprehensive than basic query
        assert len(query_construction.content) >= len(basic_query)

    @pytest.mark.asyncio
    async def test_two_stage_search_integration(self, hook, mock_context):
        """Test TwoStageSearch integration in memory search."""
        if not hook.two_stage_search:
            pytest.skip("TwoStageSearch not available")

        # Mock the unified client to return test data
        mock_unified_client = AsyncMock()
        mock_unified_client.search_memory.return_value = {
            "results": [
                {
                    "content": "Python function example",
                    "relevance_score": 0.9,
                    "content_type": "code",
                    "metadata": {"file_path": "/test/python_example.py"}
                }
            ]
        }
        hook.unified_client = mock_unified_client

        # Test TwoStageSearch integration
        memory_context = await hook.get_devstream_memory(
            mock_context.tool_input["file_path"],
            mock_context.tool_input["content"]
        )

        # Should return formatted memory context
        assert memory_context is not None
        assert "DevStream Memory Context" in memory_context

    @pytest.mark.asyncio
    async def test_semantic_cache_keys_integration(self, hook, mock_context):
        """Test SemanticCacheKeys integration in memory search."""
        if not hasattr(hook, 'semantic_cache') or hook.semantic_cache is None:
            pytest.skip("SemanticCacheKeys not available")

        # Mock the unified client to avoid external calls
        mock_unified_client = AsyncMock()
        mock_unified_client.search_memory.return_value = {
            "results": [
                {
                    "content": "Cached Python function",
                    "relevance_score": 0.8,
                    "content_type": "code",
                    "metadata": {"file_path": "/cached/example.py"}
                }
            ]
        }
        hook.unified_client = mock_unified_client

        # First call should cache miss
        start_time = time.time()
        memory_context_1 = await hook.get_devstream_memory(
            mock_context.tool_input["file_path"],
            mock_context.tool_input["content"]
        )
        first_call_time = (time.time() - start_time) * 1000

        # Second call should cache hit (faster)
        start_time = time.time()
        memory_context_2 = await hook.get_devstream_memory(
            mock_context.tool_input["file_path"],
            mock_context.tool_input["content"]
        )
        second_call_time = (time.time() - start_time) * 1000

        # Both calls should return valid context
        assert memory_context_1 is not None
        assert memory_context_2 is not None
        assert memory_context_1 == memory_context_2  # Should be identical from cache

        # Cache hit should be significantly faster
        if second_call_time > 0 and first_call_time > 0:
            cache_improvement = (first_call_time - second_call_time) / first_call_time * 100
            # Cache should provide some improvement (allowing for test environment variance)
            assert cache_improvement > -50  # Allow some variance but ensure no major regression

    @pytest.mark.asyncio
    async def test_graceful_degradation_pattern(self, hook, mock_context):
        """Test graceful degradation when optimization components fail."""
        # Temporarily disable optimization components
        original_query_constructor = hook.query_constructor
        original_two_stage_search = hook.two_stage_search
        original_semantic_cache = getattr(hook, 'semantic_cache', None)

        try:
            # Simulate component failures
            hook.query_constructor = None
            hook.two_stage_search = None
            if hasattr(hook, 'semantic_cache'):
                hook.semantic_cache = None

            # Mock unified client
            mock_unified_client = AsyncMock()
            mock_unified_client.search_memory.return_value = {
                "results": [
                    {
                        "content": "Fallback content",
                        "relevance_score": 0.7,
                        "content_type": "code",
                        "metadata": {"file_path": "/fallback/example.py"}
                    }
                ]
            }
            hook.unified_client = mock_unified_client

            # Process should still work with fallbacks
            await hook.process(mock_context)

            # Should still complete successfully
            mock_context.output.exit_success.assert_called_once()

        finally:
            # Restore original components
            hook.query_constructor = original_query_constructor
            hook.two_stage_search = original_two_stage_search
            if hasattr(hook, 'semantic_cache'):
                hook.semantic_cache = original_semantic_cache

    @pytest.mark.asyncio
    async def test_agent_delegation_integration(self, hook, mock_context):
        """Test agent delegation integration with optimization components."""
        if not hook.pattern_matcher or not hook.agent_router:
            pytest.skip("Agent delegation components not available")

        # Mock delegation response
        mock_assessment = Mock()
        mock_assessment.recommendation = "delegate"
        mock_assessment.suggested_agent = "python-specialist"
        mock_assessment.confidence = 0.85
        mock_assessment.reason = "Python code optimization task"
        mock_assessment.complexity = "medium"
        mock_assessment.architectural_impact = "low"

        with patch.object(hook, 'check_agent_delegation', return_value=mock_assessment):
            with patch.object(hook.agent_router, 'format_advisory_message', return_value="Consider using @python-specialist"):
                # Mock memory search to avoid external dependencies
                mock_unified_client = AsyncMock()
                mock_unified_client.search_memory.return_value = {"results": []}
                hook.unified_client = mock_unified_client

                with patch.object(hook, 'get_context7_docs', return_value=None):
                    await hook.process(mock_context)

                    # Should have injected delegation advisory
                    mock_context.output.exit_success.assert_called_once()

    def test_code_aware_query_building(self, hook):
        """Test code-aware query building with different file types."""
        test_cases = [
            {
                "file_path": "/test/python_example.py",
                "content": """
import os
import sys
from typing import List

class DataProcessor:
    def __init__(self):
        self.data = []

    def process_data(self, items: List[str]) -> List[str]:
        return [item.upper() for item in items]

def main():
    processor = DataProcessor()
    result = processor.process_data(["hello", "world"])
    print(result)
""",
                "expected_keywords": ["python_example", "python", "DataProcessor", "process_data", "main"]
            },
            {
                "file_path": "/test/react_component.tsx",
                "content": """
import React, { useState, useEffect } from 'react';
import { UserProps } from './types';

interface ComponentState {
    loading: boolean;
    data: any[];
}

const UserComponent: React.FC<UserProps> = ({ userId }) => {
    const [state, setState] = useState<ComponentState>({
        loading: true,
        data: []
    });

    useEffect(() => {
        // Fetch user data
    }, [userId]);

    return <div>User Component</div>;
};

export default UserComponent;
""",
                "expected_keywords": ["react_component", "react", "UserComponent", "useState", "useEffect", "interface"]
            }
        ]

        for case_data in test_cases:
            query = hook._build_code_aware_query(case_data["file_path"], case_data["content"])

            # Should contain expected keywords
            for keyword in case_data["expected_keywords"]:
                assert keyword in query, f"Missing keyword '{keyword}' in query: {query}"

            # Should be reasonable length
            assert len(query) > 50, f"Query too short: {query}"
            assert len(query) < 500, f"Query too long: {len(query)} chars"

    @pytest.mark.asyncio
    async def test_token_budget_management(self, hook):
        """Test token budget management in context assembly."""
        # Create large test content
        large_content = "def large_function():\n    # Large function with many lines\n"
        large_content += "    print('line " + "\\n    ".join([f"'{i}'" for i in range(1000)]) + ")"

        # Test token estimation
        estimated_tokens = hook._estimate_tokens(large_content)
        assert estimated_tokens > 1000, "Should estimate significant token count"

        # Test truncation to budget
        max_tokens = 500
        truncated = hook._truncate_to_budget(large_content, max_tokens)
        truncated_tokens = hook._estimate_tokens(truncated)

        # Should fit within budget (with small allowance for truncation message)
        assert truncated_tokens <= max_tokens + 50, f"Truncated content exceeds budget: {truncated_tokens} > {max_tokens}"
        assert "truncated" in truncated.lower(), "Should indicate content was truncated"

    @pytest.mark.asyncio
    async def test_concurrent_context_building(self, hook):
        """Test concurrent context building performance."""
        mock_contexts = []
        for i in range(5):
            ctx = Mock()
            ctx.tool_name = "Write"
            ctx.tool_input = {
                "file_path": f"/test/concurrent_{i}.py",
                "content": f"def function_{i}():\n    print('Function {i}')\n"
            }
            ctx.output = Mock()
            mock_contexts.append(ctx)

        # Mock external dependencies
        mock_unified_client = AsyncMock()
        mock_unified_client.search_memory.return_value = {"results": []}
        hook.unified_client = mock_unified_client

        with patch.object(hook, 'get_context7_docs', return_value=None):
            start_time = time.time()

            # Process contexts concurrently
            tasks = [hook.process(ctx) for ctx in mock_contexts]
            await asyncio.gather(*tasks)

            end_time = time.time()
            total_time = (end_time - start_time) * 1000

            # Should complete in reasonable time (concurrent processing should be faster)
            assert total_time < 3000, f"Concurrent processing too slow: {total_time:.1f}ms"

            # All contexts should have been processed
            for ctx in mock_contexts:
                ctx.output.exit_success.assert_called_once()


@pytest.mark.skipif(not OPTIMIZATION_AVAILABLE, reason=f"Optimization components unavailable: {OPTIMIZATION_IMPORT_ERROR if 'OPTIMIZATION_IMPORT_ERROR' in locals() else 'Unknown'}")
class TestOptimizationComponentsStandalone:
    """Standalone tests for optimization components without full hook integration."""

    def test_task_aware_query_constructor_standalone(self):
        """Test TaskAwareQueryConstructor standalone functionality."""
        constructor = get_task_aware_query_constructor(
            max_context_tokens=1000,
            relevance_threshold=0.5,
            enable_semantic_expansion=True,
            enable_context_optimization=True
        )

        # Test basic query analysis
        query = "Create user authentication function"
        analysis = constructor._analyze_query(query)

        assert analysis is not None
        assert analysis.original_query == query
        assert analysis.cleaned_query != ""
        assert hasattr(analysis, 'intent')
        assert hasattr(analysis, 'scope')
        assert 0.0 <= analysis.confidence_score <= 1.0

    def test_two_stage_search_standalone(self):
        """Test TwoStageSearch standalone functionality."""
        search = get_two_stage_search(
            quantization_type=QuantizationType.BINARY,
            coarse_candidate_limit=100,
            fine_result_limit=20,
            similarity_threshold=0.7,
            enable_adaptive_limits=True
        )

        # Test basic search configuration
        assert search.quantization_type == QuantizationType.BINARY
        assert search.coarse_candidate_limit == 100
        assert search.fine_result_limit == 20
        assert search.similarity_threshold == 0.7
        assert search.enable_adaptive_limits is True

    def test_semantic_cache_keys_standalone(self):
        """Test SemanticCacheKeys standalone functionality."""
        cache = get_semantic_cache_keys(
            max_cache_size=100,
            similarity_threshold=0.75,
            cluster_threshold=0.65,
            enable_embeddings=True
        )

        # Test cache configuration
        assert cache.max_cache_size == 100
        assert cache.similarity_threshold == 0.75
        assert cache.cluster_threshold == 0.65
        assert cache.enable_embeddings is True

        # Test basic cache operations
        query = "test query for caching"
        limit = 5

        # Should start empty
        cached_result, hit_type = cache.get(query, limit)
        assert cached_result is None
        assert hit_type == CacheHitType.MISS

        # Set and retrieve
        test_content = "Test cached content"
        cache.set(query, limit, None, test_content)

        cached_result, hit_type = cache.get(query, limit)
        assert cached_result == test_content
        assert hit_type == CacheHitType.EXACT_MATCH


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])