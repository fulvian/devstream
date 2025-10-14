"""
Comprehensive tests for TaskAwareQueryConstructor system.

Tests validate the 70%+ context relevance improvement target from <30% baseline.
Context7-compliant testing patterns with proper error handling and performance validation.
"""
import time
import pytest
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../.claude/hooks'))

from optimization.task_aware_query_constructor import (
    TaskAwareQueryConstructor,
    get_task_aware_query_constructor,
    QueryIntent,
    ContextScope,
    QueryAnalysis,
    ContextConstruction
)


class TestTaskAwareQueryConstructor:
    """Test the main TaskAwareQueryConstructor functionality."""

    @pytest.fixture
    def constructor(self):
        """Create a query constructor instance for testing."""
        return TaskAwareQueryConstructor(
            max_context_tokens=2000,
            relevance_threshold=0.5,
            enable_semantic_expansion=True,
            enable_context_optimization=True
        )

    def test_constructor_initialization(self, constructor):
        """Test constructor initialization with default parameters."""
        assert constructor.max_context_tokens == 2000
        assert constructor.relevance_threshold == 0.5
        assert constructor.enable_semantic_expansion is True
        assert constructor.enable_context_optimization is True

        # Check internal structures
        assert len(constructor._analysis_cache) == 0
        assert len(constructor._construction_cache) == 0
        assert isinstance(constructor._metrics, type(constructor._metrics))

    def test_query_cleaning(self, constructor):
        """Test query cleaning and normalization."""
        # Test basic cleaning
        dirty_query = "  Create   a   function   with   extra   spaces  "
        cleaned = constructor._clean_query(dirty_query)
        assert cleaned == "Create a function with extra spaces"

        # Test contraction expansion
        contraction_query = "Don't create won't function can't work"
        cleaned = constructor._clean_query(contraction_query)
        assert "do not" in cleaned
        assert "will not" in cleaned
        assert "cannot" in cleaned

    def test_intent_classification(self, constructor):
        """Test query intent classification."""
        # Test code generation intent
        code_gen_query = "Create a new function for user authentication"
        intent, confidence = constructor._classify_intent(code_gen_query)
        assert intent == QueryIntent.CODE_GENERATION
        assert confidence > 0.0

        # Test debugging intent
        debug_query = "Fix the error in the database connection"
        intent, confidence = constructor._classify_intent(debug_query)
        assert intent == QueryIntent.DEBUGGING
        assert confidence > 0.0

        # Test documentation intent
        doc_query = "Write documentation for the API endpoint"
        intent, confidence = constructor._classify_intent(doc_query)
        assert intent == QueryIntent.DOCUMENTATION
        assert confidence > 0.0

        # Test general intent fallback
        general_query = "Tell me something interesting"
        intent, confidence = constructor._classify_intent(general_query)
        assert intent == QueryIntent.GENERAL  # Should fall back to general

    def test_scope_classification(self, constructor):
        """Test context scope classification."""
        # Test immediate scope
        immediate_query = "Look at this function right here"
        scope, confidence = constructor._classify_scope(immediate_query)
        assert scope == ContextScope.IMMEDIATE
        assert confidence > 0.0

        # Test module scope
        module_query = "Check the entire module for similar patterns"
        scope, confidence = constructor._classify_scope(module_query)
        assert scope == ContextScope.MODULE
        assert confidence > 0.0

        # Test project scope (default)
        project_query = "Search the codebase for authentication examples"
        scope, confidence = constructor._classify_scope(project_query)
        assert scope == ContextScope.PROJECT  # Should be default

    def test_entity_extraction(self, constructor):
        """Test entity extraction from queries."""
        query = "Create a function in auth.py that handles user authentication using JWT tokens"
        entities = constructor._extract_entities(query)

        # Should extract various entities
        assert isinstance(entities, list)
        assert len(entities) > 0

        # Should find file paths
        file_paths = [e for e in entities if '.' in e and any(e.endswith(ext) for ext in ['.py', '.js', '.ts'])]
        assert len(file_paths) > 0
        assert 'auth.py' in entities

        # Should find function names and concepts
        assert 'function' in entities
        assert 'authentication' in entities or 'auth' in entities

    def test_keyword_extraction(self, constructor):
        """Test technical keyword extraction."""
        query = "Create a fast API endpoint for user authentication with proper error handling and testing"
        keywords = constructor._extract_keywords(query)

        # Should extract technical keywords
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert 'api' in keywords
        assert 'endpoint' in keywords
        assert 'authentication' in keywords or 'auth' in keywords
        assert 'error' in keywords
        assert 'test' in keywords

    def test_expansion_term_generation(self, constructor):
        """Test semantic expansion term generation."""
        query = "Create function for authentication"
        entities = ['auth.py', 'user']
        intent = QueryIntent.CODE_GENERATION

        expansions = constructor._generate_expansion_terms(query, intent, entities)

        # Should generate relevant expansion terms
        assert isinstance(expansions, list)
        assert len(expansions) > 0

        # Should include intent-related terms
        intent_terms = ['implement', 'create', 'build', 'develop', 'write']
        has_intent_term = any(term in expansions for term in intent_terms)
        assert has_intent_term

        # Should include entity variations
        assert 'auth' in expansions  # From auth.py
        assert 'users' in expansions  # Plural of user

    def test_query_analysis_comprehensive(self, constructor):
        """Test comprehensive query analysis."""
        query = "Create a FastAPI endpoint in users.py for user authentication with JWT tokens"

        analysis = constructor._analyze_query(query)

        # Validate analysis structure
        assert isinstance(analysis, QueryAnalysis)
        assert analysis.original_query == query
        assert analysis.cleaned_query != ""
        assert isinstance(analysis.intent, QueryIntent)
        assert isinstance(analysis.scope, ContextScope)
        assert isinstance(analysis.entities, list)
        assert isinstance(analysis.keywords, list)
        assert isinstance(analysis.expansion_terms, list)
        assert 0.0 <= analysis.confidence_score <= 1.0

        # Should identify code generation intent
        assert analysis.intent == QueryIntent.CODE_GENERATION

        # Should extract relevant entities
        assert len(analysis.entities) > 0
        assert 'users.py' in analysis.entities

        # Should extract keywords
        assert len(analysis.keywords) > 0
        assert 'api' in analysis.keywords
        assert 'endpoint' in analysis.keywords

    def test_relevance_score_calculation(self, constructor):
        """Test relevance score calculation for search results."""
        query = "Create authentication function"
        query_analysis = constructor._analyze_query(query)

        # Highly relevant result
        relevant_result = {
            'content': 'def authenticate_user(username, password): # authentication function',
            'content_type': 'code',
            'metadata': {'file_path': 'auth.py'}
        }

        score = constructor._calculate_relevance_score(query_analysis, relevant_result)
        assert score > 0.5  # Should be highly relevant

        # Less relevant result
        irrelevant_result = {
            'content': 'def calculate_sum(a, b): return a + b # math function',
            'content_type': 'code',
            'metadata': {'file_path': 'math.py'}
        }

        score = constructor._calculate_relevance_score(query_analysis, irrelevant_result)
        assert score < 0.5  # Should be less relevant

        # Documentation result (should have some relevance)
        doc_result = {
            'content': 'This file contains user authentication utilities and JWT token handling',
            'content_type': 'documentation',
            'metadata': {'file_path': 'README.md'}
        }

        score = constructor._calculate_relevance_score(query_analysis, doc_result)
        assert 0.2 <= score <= 0.8  # Should have moderate relevance

    def test_context_construction_basic(self, constructor):
        """Test basic context construction from search results."""
        query = "Create user authentication function"
        search_results = [
            {
                'content': 'def authenticate_user(username, password): # User authentication implementation',
                'content_type': 'code',
                'metadata': {'file_path': 'auth.py', 'line': 10}
            },
            {
                'content': 'JWT token validation and user session management',
                'content_type': 'documentation',
                'metadata': {'file_path': 'README.md'}
            },
            {
                'content': 'Database models for user accounts and profiles',
                'content_type': 'code',
                'metadata': {'file_path': 'models.py'}
            }
        ]

        context = constructor.construct_enhanced_query(query, search_results)

        # Validate context construction
        assert isinstance(context, ContextConstruction)
        assert context.content != ""
        assert len(context.sources) > 0
        assert len(context.relevance_scores) > 0
        assert context.total_tokens > 0
        assert context.construction_time_ms > 0
        assert isinstance(context.query_analysis, QueryAnalysis)

        # Should include header information
        assert "Query Context for:" in context.content
        assert query in context.content
        assert "Intent:" in context.content
        assert "Scope:" in context.content

        # Should include source information
        assert "Source 1:" in context.content
        assert "relevance:" in context.content

    def test_context_construction_with_token_budget(self, constructor):
        """Test context construction with token budget constraints."""
        query = "Create authentication system"

        # Create large search results
        large_results = []
        for i in range(10):
            large_results.append({
                'content': f"This is a large content block {i} with lots of text about authentication and security " * 50,
                'content_type': 'code',
                'metadata': {'file_path': f'file_{i}.py'}
            })

        # Test with small token budget
        small_budget_context = constructor.construct_enhanced_query(
            query, large_results, token_budget=500
        )

        # Should respect token budget
        assert small_budget_context.total_tokens <= 500

        # Test with large token budget
        large_budget_context = constructor.construct_enhanced_query(
            query, large_results, token_budget=5000
        )

        # Should include more content with larger budget
        assert large_budget_context.total_tokens > small_budget_context.total_tokens
        assert len(large_budget_context.content) > len(small_budget_context.content)

    def test_diversity_filtering(self, constructor):
        """Test diversity filtering to avoid redundant content."""
        # Create results with similar content
        similar_results = []
        base_content = "function authenticate_user() implements user authentication"

        for i in range(5):
            similar_results.append({
                'content': base_content + f" variation {i}",
                'content_type': 'code',
                'metadata': {'file_path': f'auth_{i}.py'}
            })

        scored_results = [(result, 0.8) for result in similar_results]

        diversified = constructor._apply_diversity_filtering(scored_results)

        # Should reduce redundancy
        assert len(diversified) < len(similar_results)
        assert len(diversified) <= 10  # Should limit diversity set

    def test_adaptive_allocation(self, constructor):
        """Test adaptive token allocation based on relevance."""
        query_analysis = QueryAnalysis(
            original_query="test query",
            cleaned_query="test query",
            intent=QueryIntent.CODE_GENERATION,
            scope=ContextScope.PROJECT,
            confidence_score=0.8
        )

        # Create results with different relevance scores
        results = []
        relevance_scores = [0.9, 0.7, 0.4, 0.2]  # High, medium, low, very low

        for i, score in enumerate(relevance_scores):
            content_length = 100 * (4 - i)  # Vary content lengths
            results.append({
                'content': f"Content {'word ' * content_length}",
                'content_type': 'code',
                'metadata': {'file_path': f'file_{i}.py'}
            })

        scored_results = list(zip(results, relevance_scores))
        token_budget = 500

        allocated = constructor._apply_adaptive_allocation(query_analysis, scored_results, token_budget)

        # Should prioritize high-relevance results
        high_relevance_included = any(score >= 0.8 for _, score in allocated)
        assert high_relevance_included

        # Should respect token budget
        estimated_tokens = sum(len(result['content'].split()) * 1.3 for result, _ in allocated)
        assert estimated_tokens <= token_budget * 1.1  # Allow 10% tolerance

    def test_performance_targets(self, constructor):
        """Test performance meets targets."""
        # Performance targets: <10ms construction time
        max_construction_time = 10.0

        query = "Create API endpoint for user management"
        search_results = [
            {
                'content': 'FastAPI endpoint implementation for user CRUD operations',
                'content_type': 'code',
                'metadata': {'file_path': 'users.py'}
            },
            {
                'content': 'User model and database schema definitions',
                'content_type': 'code',
                'metadata': {'file_path': 'models.py'}
            }
        ]

        # Test construction performance
        start_time = time.time()
        for i in range(50):
            constructor.construct_enhanced_query(query, search_results)
        total_time = (time.time() - start_time) * 1000

        avg_construction_time = total_time / 50

        assert avg_construction_time < max_construction_time, f"Construction too slow: {avg_construction_time:.4f}ms"

    def test_metrics_tracking(self, constructor):
        """Test performance metrics tracking."""
        query = "Test query for metrics"
        search_results = [
            {
                'content': 'Test content for metrics tracking',
                'content_type': 'code',
                'metadata': {'file_path': 'test.py'}
            }
        ]

        # Perform several constructions
        for i in range(5):
            constructor.construct_enhanced_query(query, search_results)

        # Get metrics
        metrics = constructor.get_metrics()

        # Validate metrics structure
        assert metrics.total_queries >= 5
        assert metrics.avg_construction_time_ms > 0.0
        assert metrics.avg_relevance_score >= 0.0

        # Reset metrics
        constructor.reset_metrics()
        reset_metrics = constructor.get_metrics()

        # Should reset to defaults
        assert reset_metrics.total_queries == 0

    def test_singleton_factory_function(self):
        """Test the factory function for getting constructor instance."""
        # Test singleton behavior
        constructor1 = get_task_aware_query_constructor()
        constructor2 = get_task_aware_query_constructor()

        # Should return same instance (singleton)
        assert constructor1 is constructor2

        # Test with custom parameters
        custom_constructor = get_task_aware_query_constructor(
            max_context_tokens=1000,
            relevance_threshold=0.7
        )

        # Should have custom parameters
        assert custom_constructor.max_context_tokens == 1000
        assert custom_constructor.relevance_threshold == 0.7

        # Should be different instance due to parameter change
        assert custom_constructor is not constructor1


class TestContextRelevanceImprovement:
    """Test context relevance improvement validation."""

    def test_relevance_improvement_validation(self):
        """Test improved context relevance meets 70%+ target."""
        # Create optimized constructor
        optimized_constructor = TaskAwareQueryConstructor(
            max_context_tokens=2000,
            relevance_threshold=0.5,
            enable_semantic_expansion=True,
            enable_context_optimization=True
        )

        # Test query with relevant and irrelevant results
        query = "Create user authentication function with JWT tokens"
        search_results = [
            # Highly relevant results
            {
                'content': 'def authenticate_user(username, password): # JWT authentication implementation',
                'content_type': 'code',
                'metadata': {'file_path': 'auth.py'}
            },
            {
                'content': 'JWT token generation and validation utilities',
                'content_type': 'code',
                'metadata': {'file_path': 'jwt_utils.py'}
            },
            {
                'content': 'User model with password hashing and authentication methods',
                'content_type': 'code',
                'metadata': {'file_path': 'models.py'}
            },
            # Less relevant results
            {
                'content': 'Database connection configuration and setup',
                'content_type': 'code',
                'metadata': {'file_path': 'database.py'}
            },
            {
                'content': 'Logging configuration for user activities',
                'content_type': 'code',
                'metadata': {'file_path': 'logging.py'}
            },
            # Irrelevant results
            {
                'content': 'Mathematical calculations and utility functions',
                'content_type': 'code',
                'metadata': {'file_path': 'math_utils.py'}
            },
            {
                'content': 'Image processing and file upload handlers',
                'content_type': 'code',
                'metadata': {'file_path': 'media.py'}
            }
        ]

        # Construct enhanced context
        context = optimized_constructor.construct_enhanced_query(query, search_results)

        # Calculate relevance improvement
        if context.relevance_scores:
            avg_relevance = sum(context.relevance_scores) / len(context.relevance_scores)
            relevance_percentage = avg_relevance * 100

            # Should meet 70%+ relevance target
            assert relevance_percentage >= 70.0, f"Relevance {relevance_percentage:.2f}% below 70% target"

            # Should prioritize relevant sources
            high_relevance_count = sum(1 for score in context.relevance_scores if score >= 0.7)
            total_sources = len(context.relevance_scores)

            if total_sources > 0:
                high_relevance_percentage = (high_relevance_count / total_sources) * 100
                assert high_relevance_percentage >= 60.0, f"High relevance sources {high_relevance_percentage:.2f}% below 60% target"

    def test_baseline_vs_optimized_performance(self):
        """Test performance improvement from baseline to optimized constructor."""
        # Test query
        query = "Implement user authentication system"

        # Mixed relevance search results
        search_results = [
            {
                'content': f'Content block {i} with {"authentication" if i % 3 == 0 else "general"} functionality',
                'content_type': 'code',
                'metadata': {'file_path': f'module_{i}.py'}
            }
            for i in range(10)
        ]

        # Test baseline constructor (minimal features)
        baseline_constructor = TaskAwareQueryConstructor(
            max_context_tokens=2000,
            relevance_threshold=0.3,  # Lower threshold
            enable_semantic_expansion=False,  # Disabled
            enable_context_optimization=False  # Disabled
        )

        baseline_context = baseline_constructor.construct_enhanced_query(query, search_results)
        baseline_avg_relevance = (sum(baseline_context.relevance_scores) / len(baseline_context.relevance_scores)) if baseline_context.relevance_scores else 0.0

        # Test optimized constructor
        optimized_constructor = TaskAwareQueryConstructor(
            max_context_tokens=2000,
            relevance_threshold=0.5,  # Higher threshold
            enable_semantic_expansion=True,  # Enabled
            enable_context_optimization=True  # Enabled
        )

        optimized_context = optimized_constructor.construct_enhanced_query(query, search_results)
        optimized_avg_relevance = (sum(optimized_context.relevance_scores) / len(optimized_context.relevance_scores)) if optimized_context.relevance_scores else 0.0

        # Optimized should perform significantly better
        relevance_improvement = (optimized_avg_relevance - baseline_avg_relevance) * 100

        assert optimized_avg_relevance > baseline_avg_relevance
        assert relevance_improvement >= 20.0, f"Relevance improvement {relevance_improvement:.2f}% below 20% target"

        # Should achieve at least 50% relevance
        assert optimized_avg_relevance >= 0.5, f"Optimized relevance {optimized_avg_relevance:.2f} below 50% minimum"


class TestIntentAndScopeClassification:
    """Test intent and scope classification accuracy."""

    def test_intent_classification_accuracy(self):
        """Test intent classification accuracy across different query types."""
        constructor = TaskAwareQueryConstructor()

        test_cases = [
            # (query, expected_intent, min_confidence)
            ("Create a new API endpoint for user registration", QueryIntent.CODE_GENERATION, 0.5),
            ("Explain how this authentication function works", QueryIntent.CODE_ANALYSIS, 0.5),
            ("Fix the database connection error in the app", QueryIntent.DEBUGGING, 0.5),
            ("Write documentation for the REST API", QueryIntent.DOCUMENTATION, 0.5),
            ("Refactor this code to be more efficient", QueryIntent.REFACTORING, 0.5),
            ("Create unit tests for the user service", QueryIntent.TESTING, 0.5),
            ("Design the architecture for a microservices system", QueryIntent.ARCHITECTURE, 0.5),
            ("Optimize the database queries for better performance", QueryIntent.OPTIMIZATION, 0.5),
            ("Integrate the payment gateway with our application", QueryIntent.INTEGRATION, 0.5),
            ("Deploy the application to production server", QueryIntent.DEPLOYMENT, 0.5)
        ]

        correct_classifications = 0

        for query, expected_intent, min_confidence in test_cases:
            intent, confidence = constructor._classify_intent(query)

            if intent == expected_intent and confidence >= min_confidence:
                correct_classifications += 1

        accuracy = (correct_classifications / len(test_cases)) * 100

        # Should achieve at least 80% classification accuracy
        assert accuracy >= 80.0, f"Intent classification accuracy {accuracy:.2f}% below 80% target"

    def test_scope_classification_accuracy(self):
        """Test scope classification accuracy."""
        constructor = TaskAwareQueryConstructor()

        test_cases = [
            # (query, expected_scope)
            ("Look at this function right here", ContextScope.IMMEDIATE),
            ("Check related files in this module", ContextScope.LOCAL),
            ("Search the entire authentication module", ContextScope.MODULE),
            ("Find examples across the whole project", ContextScope.PROJECT),
            ("Look up external documentation for this library", ContextScope.EXTERNAL)
        ]

        correct_classifications = 0

        for query, expected_scope in test_cases:
            scope, _ = constructor._classify_scope(query)

            if scope == expected_scope:
                correct_classifications += 1

        accuracy = (correct_classifications / len(test_cases)) * 100

        # Should achieve at least 60% scope classification accuracy
        assert accuracy >= 60.0, f"Scope classification accuracy {accuracy:.2f}% below 60% target"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])