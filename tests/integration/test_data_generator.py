"""
Test Data Generator for RAG Metrics Evaluation

Utility module for generating comprehensive test datasets and ground truth
for DevStream memory quality evaluation. Supports various content types,
query patterns, and complexity levels.

Usage:
    generator = TestDataGenerator()
    dataset = await generator.create_comprehensive_dataset(
        num_queries=50,
        content_types=[ContentType.CODE, ContentType.DOCUMENTATION]
    )
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel

# Add memory system modules to path
import sys
project_root = Path(__file__).parent.parent.parent
memory_system_path = project_root / "src" / "devstream" / "memory"
if str(memory_system_path) not in sys.path:
    sys.path.insert(0, str(memory_system_path))

from src.devstream.memory.models import (
    MemoryEntry, ContentType, ContentFormat
)
from src.devstream.memory.quality_evaluator import (
    EvaluationDataset, EvaluationQuery
)


class QueryComplexity(BaseModel):
    """Query complexity levels for test generation."""
    level: str
    description: str
    min_contexts: int
    max_contexts: int
    answer_length_range: Tuple[int, int]


class QueryDomain(BaseModel):
    """Query domains for categorizing test data."""
    name: str
    keywords: List[str]
    content_types: List[ContentType]
    sample_topics: List[str]


class TestDataGenerator:
    """
    Comprehensive test data generator for RAG metrics evaluation.

    Generates diverse test datasets covering:
    - Multiple content types (code, documentation, context, decisions, learnings, errors)
    - Various query complexities (simple, medium, complex)
    - Different domains (authentication, search, architecture, debugging, API)
    - Ground truth answers with varying detail levels
    """

    # Query complexity definitions
    COMPLEXITY_LEVELS = {
        "low": QueryComplexity(
            level="low",
            description="Simple factual retrieval with direct answers",
            min_contexts=1,
            max_contexts=3,
            answer_length_range=(50, 150)
        ),
        "medium": QueryComplexity(
            level="medium",
            description="Procedural or comparative queries requiring synthesis",
            min_contexts=2,
            max_contexts=5,
            answer_length_range=(100, 300)
        ),
        "high": QueryComplexity(
            level="high",
            description="Complex analytical queries requiring deep understanding",
            min_contexts=3,
            max_contexts=7,
            answer_length_range=(200, 500)
        )
    }

    # Query domains with associated content types and topics
    QUERY_DOMAINS = {
        "authentication": QueryDomain(
            name="authentication",
            keywords=["auth", "login", "password", "jwt", "security", "bcrypt", "session"],
            content_types=[ContentType.CODE, ContentType.DOCUMENTATION, ContentType.LEARNING],
            sample_topics=[
                "JWT token implementation",
                "Password hashing with bcrypt",
                "Session management best practices",
                "OAuth2 flow implementation",
                "Security considerations"
            ]
        ),
        "search": QueryDomain(
            name="search",
            keywords=["search", "rrf", "vector", "embedding", "semantic", "ranking"],
            content_types=[ContentType.DOCUMENTATION, ContentType.LEARNING, ContentType.DECISION],
            sample_topics=[
                "RRF algorithm implementation",
                "Vector search optimization",
                "Semantic similarity calculation",
                "Search result ranking",
                "Hybrid search approaches"
            ]
        ),
        "architecture": QueryDomain(
            name="architecture",
            keywords=["architecture", "design", "system", "database", "storage", "patterns"],
            content_types=[ContentType.DOCUMENTATION, ContentType.DECISION, ContentType.CONTEXT],
            sample_topics=[
                "Database design patterns",
                "System architecture decisions",
                "Storage optimization strategies",
                "API design principles",
                "Microservices architecture"
            ]
        ),
        "debugging": QueryDomain(
            name="debugging",
            keywords=["error", "debug", "fix", "issue", "problem", "troubleshoot"],
            content_types=[ContentType.ERROR, ContentType.LEARNING, ContentType.CONTEXT],
            sample_topics=[
                "Connection pool exhaustion",
                "Memory leak debugging",
                "Async context issues",
                "Performance bottlenecks",
                "Error handling patterns"
            ]
        ),
        "api": QueryDomain(
            name="api",
            keywords=["api", "endpoint", "request", "response", "rest", "http"],
            content_types=[ContentType.CODE, ContentType.DOCUMENTATION, ContentType.CONTEXT],
            sample_topics=[
                "REST API design",
                "Request validation patterns",
                "Response formatting",
                "Error response handling",
                "API versioning strategies"
            ]
        )
    }

    # Content templates for generating realistic memory entries
    CONTENT_TEMPLATES = {
        ContentType.CODE: {
            "python": [
                "def {function_name}({params}) -> {return_type}:\n    \"\"\"{description}\"\"\"\n    {implementation}",
                "class {class_name}:\n    def __init__(self, {init_params}):\n        {initialization}\n    \n    def {method_name}(self, {method_params}):\n        {method_implementation}",
                "async def {async_function_name}({params}) -> {return_type}:\n    \"\"\"{description}\"\"\"\n    async with {context_manager}:\n        {async_implementation}"
            ],
            "typescript": [
                "interface {interface_name} {{\n    {properties}\n}}",
                "export class {class_name} {{\n    constructor({constructor_params}) {{\n        {constructor_body}\n    }}\n    \n    {methods}\n}}",
                "const {function_name} = ({params}): {return_type} => {{\n    {implementation}\n}};"
            ],
            "sql": [
                "SELECT {columns} FROM {table} WHERE {conditions} {additional_clauses}",
                "CREATE TABLE {table_name} (\n    {columns}\n);",
                "INSERT INTO {table_name} ({columns}) VALUES ({values});"
            ]
        },
        ContentType.DOCUMENTATION: {
            "api": [
                "# {endpoint_title}\n\n**Method:** {http_method}\n**Endpoint:** `{path}`\n\n**Description:**\n{description}\n\n**Parameters:**\n{parameters}\n\n**Response:**\n{response_example}",
                "## {section_title}\n\n{content}\n\n### {subsection_title}\n\n{subsection_content}\n\n**Example:**\n```{language}\n{example_code}\n```"
            ],
            "architecture": [
                "# Architecture Overview\n\n## System Components\n\n{components_description}\n\n## Data Flow\n\n{data_flow_description}\n\n## Key Design Decisions\n\n{design_decisions}"
            ]
        },
        ContentType.DECISION: {
            "technical": [
                "Decision: {decision_title}\n\n**Context:** {context}\n\n**Options Considered:**\n{options_considered}\n\n**Chosen Solution:** {chosen_solution}\n\n**Rationale:** {rationale}\n\n**Implementation Notes:** {implementation_notes}"
            ],
            "architectural": [
                "Architectural Decision: {decision_title}\n\n**Problem Statement:** {problem}\n\n**Trade-offs Analysis:**\n{trade_offs}\n\n**Decision:** {decision}\n\n**Impact Assessment:** {impact}"
            ]
        },
        ContentType.LEARNING: {
            "technical": [
                "Learning: {learning_title}\n\n**Key Insights:**\n{insights}\n\n**Best Practices Identified:**\n{best_practices}\n\n**Future Considerations:**\n{future_considerations}"
            ],
            "performance": [
                "Performance Learning: {topic}\n\n**Optimization Technique:** {technique}\n\n**Before:** {before_state}\n\n**After:** {after_state}\n\n**Performance Gains:** {performance_gains}\n\n**Lessons Learned:** {lessons}"
            ]
        },
        ContentType.ERROR: {
            "bug": [
                "Error: {error_title}\n\n**Description:** {error_description}\n\n**Root Cause:** {root_cause}\n\n**Symptoms:** {symptoms}\n\n**Resolution:** {resolution}\n\n**Prevention:** {prevention_measures}"
            ],
            "system": [
                "System Error: {error_type}\n\n**Timestamp:** {timestamp}\n**Component:** {component}\n**Error Code:** {error_code}\n\n**Error Details:**\n{error_details}\n\n**Impact:** {impact}\n\n**Recovery Actions:** {recovery_actions}"
            ]
        },
        ContentType.CONTEXT: {
            "user_request": [
                "Context: User requested {request_type}\n\n**User Requirements:**\n{requirements}\n\n**Constraints:**\n{constraints}\n\n**User Background:**\n{user_background}\n\n**Success Criteria:**\n{success_criteria}"
            ],
            "system_state": [
                "Context: System state during {operation}\n\n**Current State:**\n{current_state}\n\n**Environmental Factors:**\n{environmental_factors}\n\n**Active Components:**\n{active_components}\n\n**Recent Changes:**\n{recent_changes}"
            ]
        }
    }

    def __init__(self, seed: Optional[int] = None):
        """Initialize test data generator with optional random seed."""
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

    def generate_memory_entries(
        self,
        count: int = 100,
        content_types: Optional[List[ContentType]] = None,
        domains: Optional[List[str]] = None
    ) -> List[MemoryEntry]:
        """
        Generate realistic memory entries for testing.

        Args:
            count: Number of memory entries to generate
            content_types: Specific content types to include (default: all)
            domains: Specific domains to focus on (default: all)

        Returns:
            List of generated memory entries
        """
        if content_types is None:
            content_types = list(ContentType)

        if domains is None:
            domains = list(self.QUERY_DOMAINS.keys())

        entries = []
        base_time = datetime.utcnow()

        for i in range(count):
            # Randomly select content type and domain
            content_type = random.choice(content_types)
            domain = random.choice(domains)

            # Generate content based on type and domain
            content = self._generate_content(content_type, domain)
            keywords = self._extract_keywords(content, domain)
            entities = self._extract_entities(content, content_type)

            entry = MemoryEntry(
                id=f"generated_mem_{i+1:06d}",
                content=content,
                content_type=content_type,
                content_format=self._get_content_format(content_type),
                keywords=keywords,
                entities=entities,
                sentiment=random.uniform(-0.5, 0.8),
                complexity_score=random.randint(2, 8),
                context_snapshot=self._generate_context_snapshot(domain),
                created_at=base_time - timedelta(hours=random.randint(0, 168)),
                access_count=random.randint(0, 50),
                relevance_score=random.uniform(0.3, 1.0)
            )

            entries.append(entry)

        return entries

    def generate_evaluation_queries(
        self,
        count: int = 50,
        complexity_distribution: Optional[Dict[str, float]] = None,
        domains: Optional[List[str]] = None
    ) -> List[EvaluationQuery]:
        """
        Generate evaluation queries with ground truth answers.

        Args:
            count: Number of queries to generate
            complexity_distribution: Distribution of complexity levels
            domains: Specific domains to focus on

        Returns:
            List of evaluation queries with ground truth
        """
        if complexity_distribution is None:
            complexity_distribution = {"low": 0.4, "medium": 0.4, "high": 0.2}

        if domains is None:
            domains = list(self.QUERY_DOMAINS.keys())

        queries = []

        for i in range(count):
            # Select complexity level based on distribution
            complexity = self._select_complexity(complexity_distribution)
            domain = random.choice(domains)

            # Generate query, ground truth, and contexts
            query_data = self._generate_query_data(complexity, domain)

            query = EvaluationQuery(
                query_text=query_data["query"],
                ground_truth_answer=query_data["ground_truth"],
                retrieved_contexts=query_data["contexts"],
                generated_answer=query_data.get("generated_answer"),
                query_id=f"eval_query_{i+1:06d}"
            )

            queries.append(query)

        return queries

    async def create_comprehensive_dataset(
        self,
        memory_entries_count: int = 100,
        evaluation_queries_count: int = 50,
        complexity_distribution: Optional[Dict[str, float]] = None,
        content_types: Optional[List[ContentType]] = None,
        domains: Optional[List[str]] = None
    ) -> Tuple[List[MemoryEntry], EvaluationDataset]:
        """
        Create comprehensive test dataset with memory entries and evaluation queries.

        Args:
            memory_entries_count: Number of memory entries to generate
            evaluation_queries_count: Number of evaluation queries to generate
            complexity_distribution: Distribution of query complexity levels
            content_types: Content types to include
            domains: Domains to focus on

        Returns:
            Tuple of (memory_entries, evaluation_dataset)
        """
        # Generate memory entries
        memory_entries = self.generate_memory_entries(
            count=memory_entries_count,
            content_types=content_types,
            domains=domains
        )

        # Generate evaluation queries
        queries = self.generate_evaluation_queries(
            count=evaluation_queries_count,
            complexity_distribution=complexity_distribution,
            domains=domains
        )

        # Create evaluation dataset
        dataset = EvaluationDataset(
            queries=queries,
            name=f"Comprehensive RAG Test Dataset ({evaluation_queries_count} queries)",
            description=f"Generated dataset with {len(memory_entries)} memory entries and {len(queries)} evaluation queries"
        )

        return memory_entries, dataset

    def save_dataset_to_file(
        self,
        dataset: EvaluationDataset,
        file_path: str,
        format: str = "json"
    ) -> None:
        """
        Save evaluation dataset to file for persistence.

        Args:
            dataset: Evaluation dataset to save
            file_path: Path to save the dataset
            format: File format ('json' or 'jsonl')
        """
        if format.lower() == "json":
            with open(file_path, 'w') as f:
                json.dump(dataset.dict(), f, indent=2, default=str)
        elif format.lower() == "jsonl":
            with open(file_path, 'w') as f:
                for query in dataset.queries:
                    query_dict = {
                        "query_id": query.query_id,
                        "query_text": query.query_text,
                        "ground_truth_answer": query.ground_truth_answer,
                        "generated_answer": query.generated_answer,
                        "retrieved_contexts": query.retrieved_contexts
                    }
                    f.write(json.dumps(query_dict) + '\n')
        else:
            raise ValueError(f"Unsupported format: {format}")

    def load_dataset_from_file(self, file_path: str, format: str = "json") -> EvaluationDataset:
        """
        Load evaluation dataset from file.

        Args:
            file_path: Path to load dataset from
            format: File format ('json' or 'jsonl')

        Returns:
            Loaded evaluation dataset
        """
        if format.lower() == "json":
            with open(file_path, 'r') as f:
                data = json.load(f)
            return EvaluationDataset(**data)
        elif format.lower() == "jsonl":
            queries = []
            with open(file_path, 'r') as f:
                for line in f:
                    query_dict = json.loads(line.strip())
                    query = EvaluationQuery(
                        query_id=query_dict["query_id"],
                        query_text=query_dict["query_text"],
                        ground_truth_answer=query_dict["ground_truth_answer"],
                        generated_answer=query_dict.get("generated_answer"),
                        retrieved_contexts=query_dict["retrieved_contexts"]
                    )
                    queries.append(query)

            return EvaluationDataset(
                queries=queries,
                name=f"Loaded Dataset from {Path(file_path).name}",
                description=f"Dataset loaded from {file_path}"
            )
        else:
            raise ValueError(f"Unsupported format: {format}")

    # Private helper methods

    def _generate_content(self, content_type: ContentType, domain: str) -> str:
        """Generate realistic content based on type and domain."""
        templates = self.CONTENT_TEMPLATES.get(content_type, {})

        # Select appropriate template
        if content_type == ContentType.CODE:
            language = random.choice(["python", "typescript", "sql"])
            template = random.choice(templates.get(language, templates.get("python", [])))
        else:
            category = random.choice(list(templates.keys()))
            template = random.choice(templates[category])

        # Fill template with domain-specific content
        return self._fill_template(template, content_type, domain)

    def _fill_template(self, template: str, content_type: ContentType, domain: str) -> str:
        """Fill template with realistic content based on domain."""
        domain_info = self.QUERY_DOMAINS.get(domain, self.QUERY_DOMAINS["authentication"])

        # Domain-specific content generators
        content_generators = {
            "authentication": self._generate_auth_content,
            "search": self._generate_search_content,
            "architecture": self._generate_architecture_content,
            "debugging": self._generate_debugging_content,
            "api": self._generate_api_content
        }

        generator = content_generators.get(domain, self._generate_generic_content)
        return generator(template, content_type, domain_info)

    def _generate_auth_content(self, template: str, content_type: ContentType, domain_info: QueryDomain) -> str:
        """Generate authentication-related content."""
        replacements = {
            "{function_name}": random.choice(["authenticate_user", "hash_password", "verify_token", "create_session"]),
            "{method_name}": random.choice(["login", "logout", "refresh_token", "validate_session"]),
            "{class_name}": random.choice(["AuthManager", "UserService", "TokenService", "SessionManager"]),
            "{endpoint_title}": random.choice(["User Authentication", "Token Validation", "Session Management"]),
            "{decision_title}": random.choice(["JWT Implementation", "Password Hashing Strategy", "Session Storage"]),
            "{learning_title}": random.choice(["Security Best Practices", "Authentication Patterns", "Token Management"])
        }

        return self._apply_replacements(template, replacements)

    def _generate_search_content(self, template: str, content_type: ContentType, domain_info: QueryDomain) -> str:
        """Generate search-related content."""
        replacements = {
            "{function_name}": random.choice(["hybrid_search", "semantic_search", "calculate_rrf", "vector_search"]),
            "{algorithm_name}": random.choice(["RRF", "TF-IDF", "BM25", "Cosine Similarity"]),
            "{class_name}": random.choice(["SearchEngine", "VectorIndex", "RankingAlgorithm"]),
            "{learning_title}": random.choice(["Search Optimization", "Ranking Algorithms", "Vector Similarity"]),
            "{decision_title}": random.choice(["Search Architecture", "Indexing Strategy", "Ranking Approach"])
        }

        return self._apply_replacements(template, replacements)

    def _generate_architecture_content(self, template: str, content_type: ContentType, domain_info: QueryDomain) -> str:
        """Generate architecture-related content."""
        replacements = {
            "{component_name}": random.choice(["DatabaseLayer", "ServiceLayer", "APIGateway", "CacheManager"]),
            "{pattern_name}": random.choice(["Repository Pattern", "Observer Pattern", "Factory Pattern"]),
            "{decision_title}": random.choice(["Database Selection", "Microservices vs Monolith", "Caching Strategy"]),
            "{learning_title}": random.choice(["System Design", "Scalability Patterns", "Performance Optimization"])
        }

        return self._apply_replacements(template, replacements)

    def _generate_debugging_content(self, template: str, content_type: ContentType, domain_info: QueryDomain) -> str:
        """Generate debugging-related content."""
        replacements = {
            "{error_title}": random.choice(["Memory Leak", "Connection Timeout", "Race Condition", "Deadlock"]),
            "{component}": random.choice(["Database Connection", "Async Task", "Memory Manager", "Cache Layer"]),
            "{resolution}": random.choice(["Connection Pool Reset", "Memory Cleanup", "Async Context Fix", "Lock Release"]),
            "{learning_title}": random.choice(["Error Prevention", "Debugging Techniques", "Performance Troubleshooting"])
        }

        return self._apply_replacements(template, replacements)

    def _generate_api_content(self, template: str, content_type: ContentType, domain_info: QueryDomain) -> str:
        """Generate API-related content."""
        replacements = {
            "{endpoint_title}": random.choice(["User Creation", "Data Retrieval", "Authentication"]),
            "{http_method}": random.choice(["GET", "POST", "PUT", "DELETE"]),
            "{path}": random.choice(["/api/users", "/api/auth/login", "/api/data", "/api/health"]),
            "{function_name}": random.choice(["create_user", "get_data", "validate_request", "handle_response"]),
            "{class_name}": random.choice(["APIController", "RequestHandler", "ResponseFormatter"])
        }

        return self._apply_replacements(template, replacements)

    def _generate_generic_content(self, template: str, content_type: ContentType, domain_info: QueryDomain) -> str:
        """Generate generic content when no specific generator is available."""
        # Use domain keywords to create realistic content
        keyword = random.choice(domain_info.keywords)

        replacements = {
            "{function_name}": f"{keyword}_function",
            "{class_name}": f"{keyword.title()}Manager",
            "{decision_title}": f"{keyword.title()} Implementation Decision",
            "{learning_title}": f"{keyword.title()} Best Practices"
        }

        return self._apply_replacements(template, replacements)

    def _apply_replacements(self, template: str, replacements: Dict[str, str]) -> str:
        """Apply template replacements with realistic content."""
        result = template

        for placeholder, replacement in replacements.items():
            if placeholder in result:
                result = result.replace(placeholder, replacement)

        # Fill remaining placeholders with generic content
        import re

        # Fill function parameters
        result = re.sub(r'\{params\}', 'param1: str, param2: int', result)
        result = re.sub(r'\{return_type\}', 'ResultType', result)
        result = re.sub(r'\{description\}', 'Function description', result)
        result = re.sub(r'\{implementation\}', '# Implementation here', result)

        # Fill class content
        result = re.sub(r'\{properties\}', 'name: string;\n    id: number;', result)
        result = re.sub(r'\{methods\}', 'method1(): void { /* implementation */ }', result)

        # Fill general placeholders
        result = re.sub(r'\{[^}]+\}', 'placeholder_content', result)

        return result

    def _extract_keywords(self, content: str, domain: str) -> List[str]:
        """Extract keywords from content based on domain."""
        domain_info = self.QUERY_DOMAINS.get(domain, self.QUERY_DOMAINS["authentication"])

        # Start with domain keywords
        keywords = domain_info.keywords.copy()

        # Extract some words from content (simple implementation)
        words = content.lower().split()
        for word in words:
            if len(word) > 4 and word not in keywords and len(keywords) < 8:
                keywords.append(word)

        return keywords[:8]  # Limit to 8 keywords

    def _extract_entities(self, content: str, content_type: ContentType) -> List[Dict[str, str]]:
        """Extract entities from content based on type."""
        entities = []

        if content_type == ContentType.CODE:
            # Extract function names, class names, etc.
            import re

            # Function names
            func_matches = re.findall(r'def\s+(\w+)', content)
            for func_name in func_matches[:3]:
                entities.append({"type": "function", "value": func_name})

            # Class names
            class_matches = re.findall(r'class\s+(\w+)', content)
            for class_name in class_matches[:3]:
                entities.append({"type": "class", "value": class_name})

        elif content_type == ContentType.DOCUMENTATION:
            # Extract section headers, endpoints, etc.
            if "API" in content:
                entities.append({"type": "documentation_type", "value": "API"})
            if "authentication" in content.lower():
                entities.append({"type": "topic", "value": "authentication"})

        return entities[:5]  # Limit to 5 entities

    def _get_content_format(self, content_type: ContentType) -> ContentFormat:
        """Get appropriate content format for content type."""
        format_mapping = {
            ContentType.CODE: ContentFormat.CODE,
            ContentType.DOCUMENTATION: ContentFormat.MARKDOWN,
            ContentType.DECISION: ContentFormat.TEXT,
            ContentType.LEARNING: ContentFormat.TEXT,
            ContentType.ERROR: ContentFormat.TEXT,
            ContentType.CONTEXT: ContentFormat.TEXT
        }
        return format_mapping.get(content_type, ContentFormat.TEXT)

    def _generate_context_snapshot(self, domain: str) -> Dict[str, Any]:
        """Generate realistic context snapshot."""
        return {
            "domain": domain,
            "session_id": f"session_{random.randint(1000, 9999)}",
            "user_intent": random.choice(["implementation", "debugging", "documentation", "testing"]),
            "environment": random.choice(["development", "testing", "staging"]),
            "timestamp": datetime.utcnow().isoformat()
        }

    def _select_complexity(self, distribution: Dict[str, float]) -> QueryComplexity:
        """Select complexity level based on distribution."""
        rand_val = random.random()
        cumulative = 0.0

        for level, prob in distribution.items():
            cumulative += prob
            if rand_val <= cumulative:
                return self.COMPLEXITY_LEVELS[level]

        return self.COMPLEXITY_LEVELS["medium"]  # Default

    def _generate_query_data(self, complexity: QueryComplexity, domain: str) -> Dict[str, Any]:
        """Generate query data with ground truth and contexts."""
        domain_info = self.QUERY_DOMAINS[domain]
        topic = random.choice(domain_info.sample_topics)

        # Generate query based on complexity and domain
        query_generators = {
            "low": self._generate_simple_query,
            "medium": self._generate_medium_query,
            "high": self._generate_complex_query
        }

        query_generator = query_generators[complexity.level]
        query_data = query_generator(topic, domain_info)

        # Add generated answer for some queries
        if random.random() < 0.7:  # 70% chance of having generated answer
            query_data["generated_answer"] = self._generate_simulated_answer(
                query_data["query"],
                query_data["ground_truth"],
                complexity
            )

        return query_data

    def _generate_simple_query(self, topic: str, domain_info: QueryDomain) -> Dict[str, Any]:
        """Generate simple factual query."""
        query = f"What is {topic.lower()}?"
        ground_truth = f"{topic} is a key concept in {domain_info.name} that involves {random.choice(domain_info.keywords)}."

        contexts = [
            f"{topic} implementation involves best practices and standard patterns.",
            f"The {topic} approach provides reliable solutions for common scenarios.",
            f"Understanding {topic} is essential for effective development."
        ][:2]  # Simple queries need fewer contexts

        return {
            "query": query,
            "ground_truth": ground_truth,
            "contexts": contexts
        }

    def _generate_medium_query(self, topic: str, domain_info: QueryDomain) -> Dict[str, Any]:
        """Generate medium complexity procedural query."""
        actions = ["How to implement", "What are the steps for", "How does", "What is the process for"]
        action = random.choice(actions)

        query = f"{action} {topic.lower()}?"
        ground_truth = f"To implement {topic}, you need to follow these steps: first {random.choice(domain_info.keywords)}, then ensure proper {random.choice(domain_info.keywords)}, and finally validate the {random.choice(domain_info.keywords)} implementation."

        contexts = [
            f"Step-by-step guide for {topic} implementation",
            f"Best practices and patterns for {topic}",
            f"Common pitfalls and solutions when working with {topic}",
            f"Performance considerations for {topic}",
            f"Testing strategies for {topic} implementations"
        ][:4]

        return {
            "query": query,
            "ground_truth": ground_truth,
            "contexts": contexts
        }

    def _generate_complex_query(self, topic: str, domain_info: QueryDomain) -> Dict[str, Any]:
        """Generate complex analytical query."""
        question_types = [
            "Compare and contrast different approaches to",
            "Analyze the trade-offs between",
            "What are the architectural implications of",
            "How does {topic} integrate with",
            "What are the long-term considerations for"
        ]

        question = random.choice(question_types).replace("{topic}", topic)
        query = f"{question} {topic.lower()}?"

        ground_truth = f"The analysis of {topic} reveals multiple considerations: architectural aspects include {random.choice(domain_info.keywords)}, performance impacts involve {random.choice(domain_info.keywords)}, and scalability concerns center around {random.choice(domain_info.keywords)}. The optimal approach depends on specific requirements and constraints."

        contexts = [
            f"Architectural patterns and design considerations for {topic}",
            f"Performance analysis and optimization techniques for {topic}",
            f"Scalability implications and growth strategies for {topic}",
            f"Security considerations and best practices for {topic}",
            f"Integration patterns and compatibility issues with {topic}",
            f"Case studies and real-world implementations of {topic}",
            f"Future trends and evolving standards for {topic}"
        ]

        return {
            "query": query,
            "ground_truth": ground_truth,
            "contexts": contexts
        }

    def _generate_simulated_answer(
        self,
        query: str,
        ground_truth: str,
        complexity: QueryComplexity
    ) -> str:
        """Generate simulated answer based on query and ground truth."""
        # Create a realistic answer that's similar but not identical to ground truth
        answer_length = random.randint(*complexity.answer_length_range)

        # Start with part of ground truth
        base_answer = ground_truth[:answer_length//2]

        # Add some variation
        variations = [
            "Additionally, it's important to consider",
            "This approach ensures",
            "The implementation follows best practices",
            "Key considerations include"
        ]

        if len(base_answer) < answer_length:
            variation = random.choice(variations)
            additional_text = f" {variation} {random.choice(['reliability', 'performance', 'maintainability', 'scalability'])}."
            base_answer += additional_text

        return base_answer[:answer_length]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_benchmark_dataset(
    name: str = "DevStream RAG Benchmark",
    memory_entries: int = 200,
    evaluation_queries: int = 100
) -> Tuple[List[MemoryEntry], EvaluationDataset]:
    """
    Create a comprehensive benchmark dataset for DevStream RAG evaluation.

    Args:
        name: Name for the benchmark dataset
        memory_entries: Number of memory entries to generate
        evaluation_queries: Number of evaluation queries to generate

    Returns:
        Tuple of (memory_entries, evaluation_dataset)
    """
    generator = TestDataGenerator(seed=42)  # Use fixed seed for reproducibility

    # Create comprehensive dataset
    memory_entries_list, dataset = asyncio.run(
        generator.create_comprehensive_dataset(
            memory_entries_count=memory_entries,
            evaluation_queries_count=evaluation_queries,
            complexity_distribution={"low": 0.3, "medium": 0.5, "high": 0.2}
        )
    )

    dataset.name = name
    dataset.description = f"Comprehensive benchmark with {memory_entries} memory entries and {evaluation_queries} evaluation queries covering multiple domains and complexity levels."

    return memory_entries_list, dataset


if __name__ == "__main__":
    # Example usage
    generator = TestDataGenerator()

    # Generate sample dataset
    memory_entries, dataset = asyncio.run(
        generator.create_comprehensive_dataset(
            memory_entries_count=50,
            evaluation_queries_count=20
        )
    )

    print(f"Generated {len(memory_entries)} memory entries")
    print(f"Generated {len(dataset.queries)} evaluation queries")

    # Save dataset to file
    generator.save_dataset_to_file(dataset, "test_dataset.json", "json")
    print("Dataset saved to test_dataset.json")