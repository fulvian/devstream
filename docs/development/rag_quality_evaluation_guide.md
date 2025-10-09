# RAG Quality Evaluation Framework Guide

## Overview

The DevStream RAG Quality Evaluation Framework provides comprehensive evaluation capabilities for Retrieval-Augmented Generation systems based on Context7-Ragas best practices from 2025. This framework enables systematic quality assessment of memory retrieval and answer generation processes.

## Features

### Core RAG Metrics

The framework implements four essential RAG evaluation metrics:

1. **Faithfulness** - Measures factual consistency of generated answers with retrieved context
2. **Context Precision** - Evaluates signal-to-noise ratio in retrieved context
3. **Answer Relevancy** - Assesses relevance of generated answers to original queries
4. **Context Recall** - Measures coverage of ground truth in retrieved context

### Key Capabilities

- **Async Performance Optimization** - Concurrent evaluation for batch processing
- **Ollama Integration** - Uses embeddinggemma:300m for semantic similarity
- **Comprehensive Error Handling** - Graceful failure recovery with detailed logging
- **Context7-Validated Patterns** - Follows 2025 best practices for RAG evaluation
- **Type-Safe Implementation** - Full Pydantic models with validation
- **Structured Reporting** - Detailed evaluation reports with performance metrics

## Architecture

### Components

```
RAGMetricsEvaluator
├── Metric Evaluation
│   ├── FaithfulnessEvaluator
│   ├── ContextPrecisionEvaluator
│   ├── AnswerRelevancyEvaluator
│   └── ContextRecallEvaluator
├── LLM Integration (Ollama gemma2)
├── Embedding Generation (embeddinggemma:300m)
└── Report Generation
```

### Integration Points

- **MemoryStorage** - For context retrieval and storage operations
- **HybridSearchEngine** - For retrieving relevant contexts
- **EmbeddingGenerator** - For semantic similarity calculations
- **MemoryManager** - High-level interface for all operations

## Quick Start

### Basic Usage

```python
from devstream.memory import MemoryManager, MetricType
from devstream.database.connection import ConnectionPool

# Initialize memory manager
connection_pool = ConnectionPool(database_url="sqlite:///devstream.db")
memory_manager = MemoryManager(connection_pool, enable_quality_evaluator=True)
await memory_manager.initialize()

# Store some memories
await memory_manager.store_memory_entry(
    "Python lists are mutable collections defined with square brackets.",
    content_type="documentation",
    keywords=["python", "lists", "mutable"]
)

# Evaluate a single query
result = await memory_manager.evaluate_query_quality(
    query="How do Python lists work?",
    ground_truth_answer="Python lists are mutable, ordered collections that can be modified using methods like append() and remove().",
    generated_answer="Python lists are collections you can change. You use square brackets to create them and can add items with append().",
    metrics=[MetricType.CONTEXT_PRECISION, MetricType.ANSWER_RELEVANCY]
)

print(f"Context Precision: {result['metrics']['context_precision']['score']:.3f}")
print(f"Answer Relevancy: {result['metrics']['answer_relevancy']['score']:.3f}")
```

### Batch Evaluation

```python
# Evaluate multiple queries
queries = [
    "What are Python decorators?",
    "How does exception handling work in Python?",
    "What are virtual environments?"
]

ground_truth_answers = [
    "Decorators are functions that modify other functions without changing their source code.",
    "Python uses try-except blocks for error handling with specific exception types.",
    "Virtual environments isolate Python project dependencies using venv."
]

report = await memory_manager.evaluate_batch_quality(
    queries=queries,
    ground_truth_answers=ground_truth_answers,
    max_contexts=5,
    metrics=list(MetricType)  # All metrics
)

print(f"Overall Score: {report.overall_score:.3f}")
print(f"Faithfulness: {report.faithfulness_score:.3f}")
print(f"Context Precision: {report.context_precision_score:.3f}")
print(f"Answer Relevancy: {report.answer_relevancy_score:.3f}")
print(f"Context Recall: {report.context_recall_score:.3f}")
```

## Metrics Explained

### Faithfulness

**Purpose**: Measures factual consistency between generated answers and retrieved context.

**Score Range**: 0.0 - 1.0

**Evaluation Process**:
1. Extracts factual statements from the generated answer
2. Verifies each statement against retrieved context
3. Calculates ratio of supported statements to total statements
4. Identifies contradictions and unsupported claims

**Scoring Guidelines**:
- 1.0: All statements supported, no contradictions
- 0.8-0.9: Most statements supported, minor unsupported details
- 0.6-0.7: Some statements supported, notable unsupported claims
- 0.4-0.5: Few statements supported, many unsupported claims
- 0.0-0.3: Almost no statements supported or major contradictions

### Context Precision

**Purpose**: Measures signal-to-noise ratio in retrieved context.

**Score Range**: 0.0 - 1.0

**Evaluation Process**:
1. Evaluates relevance of each retrieved context to the query
2. Calculates precision@k for each position k
3. Averages precision scores across all contexts
4. Rewards early appearance of relevant contexts

**Scoring Guidelines**:
- 1.0: All retrieved contexts are highly relevant
- 0.8-0.9: Most contexts relevant, some noise
- 0.6-0.7: Mixed relevance, significant noise
- 0.4-0.5: Few relevant contexts, mostly noise
- 0.0-0.3: Almost no relevant contexts

### Answer Relevancy

**Purpose**: Measures relevance of generated answer to original query.

**Score Range**: 0.0 - 1.0

**Evaluation Process**:
1. Calculates semantic similarity between query and answer
2. Uses LLM to assess topical relevance and completeness
3. Combines semantic and LLM assessments (30%/70% weights)
4. Evaluates whether answer directly addresses the query

**Scoring Guidelines**:
- 1.0: Answer perfectly addresses the query
- 0.8-0.9: Answer addresses query well with minor gaps
- 0.6-0.7: Answer partially addresses the query
- 0.4-0.5: Answer loosely related to the query
- 0.0-0.3: Answer does not address the query

### Context Recall

**Purpose**: Measures coverage of ground truth in retrieved context.

**Score Range**: 0.0 - 1.0

**Evaluation Process**:
1. Identifies key information in ground truth answer
2. Verifies presence of each key point in retrieved context
3. Calculates ratio of covered points to total key points
4. Considers both explicit mentions and strong implications

**Scoring Guidelines**:
- 1.0: All key information from ground truth present in context
- 0.8-0.9: Most key information present, minor details missing
- 0.6-0.7: Some key information present, notable gaps
- 0.4-0.5: Few key points covered, major information missing
- 0.0-0.3: Almost no key information from ground truth in context

## Configuration

### Embedding Configuration

```python
from devstream.memory import EmbeddingConfig

config = EmbeddingConfig(
    model_name="embeddinggemma",  # Ollama model for embeddings
    batch_size=10,                # Batch processing size
    max_retries=3,                # Retry attempts for failed operations
    base_delay=1.0,              # Base delay for exponential backoff
    timeout=30.0                 # Request timeout in seconds
)

memory_manager = MemoryManager(
    connection_pool=connection_pool,
    embedding_config=config,
    enable_quality_evaluator=True
)
```

### LLM Configuration

The framework uses Ollama's gemma2 model by default for LLM-based evaluations. To configure:

```python
# Access the evaluator directly
evaluator = memory_manager.quality_evaluator

# The evaluator uses Ollama client with default configuration
# Custom LLM configuration can be added by extending the evaluator
```

## Performance Considerations

### Batch Processing

- Use `evaluate_batch_quality()` for multiple queries
- Configure `max_concurrent_evaluations` based on system resources
- Default limit is 5 concurrent evaluations to prevent resource exhaustion

### Embedding Caching

- Embeddings are cached during evaluation sessions
- Semantic similarity calculations reuse embeddings where possible
- Consider embedding cache size for large-scale evaluations

### Resource Requirements

- **Memory**: ~500MB base + ~100MB per concurrent evaluation
- **CPU**: Moderate usage for embedding generation
- **Ollama**: Requires running Ollama service with gemma2 and embeddinggemma models

## Error Handling

### Common Issues

1. **Model Not Available**
   ```python
   status = await memory_manager.get_system_status()
   if not status['quality_evaluator']['evaluator_ready']:
       print("Quality evaluator not ready - check Ollama models")
   ```

2. **Empty Contexts**
   ```python
   # The evaluator handles empty contexts gracefully
   # Context Precision will return 0.0 with appropriate reasoning
   ```

3. **Timeout Issues**
   ```python
   # Configure longer timeouts for complex evaluations
   config = EmbeddingConfig(timeout=60.0)  # 60 seconds
   ```

### Debugging

Enable detailed logging:

```python
import structlog

# Configure logging for debugging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```

## Advanced Usage

### Custom Evaluation Datasets

```python
from devstream.memory import EvaluationQuery, EvaluationDataset

# Create custom evaluation queries
queries = [
    EvaluationQuery(
        query_text="What is async programming?",
        ground_truth_answer="Async programming allows non-blocking execution...",
        retrieved_contexts=["Context 1...", "Context 2..."],
        generated_answer="Async programming enables non-blocking code..."
    )
]

dataset = EvaluationDataset(
    queries=queries,
    name="Custom Async Programming Evaluation",
    description="Evaluating async programming concepts"
)

# Evaluate custom dataset
report = await memory_manager.quality_evaluator.evaluate_dataset(dataset)
```

### Metric-Specific Configuration

```python
# Evaluate only specific metrics
metrics = [
    MetricType.FAITHFULNESS,
    MetricType.CONTEXT_PRECISION
]

result = await memory_manager.evaluate_query_quality(
    query="Your query here",
    ground_truth_answer="Expected answer",
    metrics=metrics
)
```

### Performance Monitoring

```python
# Monitor evaluation performance
import time

start_time = time.time()
report = await memory_manager.evaluate_batch_quality(
    queries=queries,
    ground_truth_answers=ground_truth_answers
)

print(f"Evaluation completed in {time.time() - start_time:.2f} seconds")
print(f"Average time per query: {report.average_query_time_ms:.0f}ms")
```

## Best Practices

### Evaluation Design

1. **Use Representative Queries** - Select queries that match your use case
2. **Provide Quality Ground Truth** - Ensure reference answers are accurate and complete
3. **Balance Query Types** - Include both simple and complex queries
4. **Consider Context Coverage** - Test different levels of context relevance

### Integration with Development

1. **Continuous Evaluation** - Integrate quality metrics into CI/CD pipelines
2. **Performance Baselines** - Establish baseline scores for regression testing
3. **Metric Thresholds** - Set minimum acceptable scores for production deployment
4. **Regular Assessment** - Schedule periodic evaluations to track quality over time

### Troubleshooting

1. **Low Scores**: Check if contexts are relevant and answers address queries
2. **Timeout Issues**: Increase timeout settings or reduce batch size
3. **Model Unavailable**: Ensure Ollama models are properly installed
4. **Memory Issues**: Reduce concurrent evaluations or increase system resources

## Examples

See the test script `test_rag_quality_evaluation.py` for comprehensive examples of:

- Setting up test data
- Running single and batch evaluations
- Interpreting results
- Error handling
- Performance monitoring

## References

- [Context7-Ragas Documentation](https://github.com/explodinggradients/ragas)
- [Ollama Documentation](https://github.com/ollama/ollama)
- [Semantic Kernel Patterns](https://github.com/microsoft/semantic-kernel)
- [DevStream Memory System Architecture](./memory_system_architecture.md)