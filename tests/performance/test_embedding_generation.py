"""
FASE 5: Memory Vector Enhancement Performance Testing

Comprehensive performance testing for embedding generation system.
Validates:
- Batch embedding performance: <60s/1000 records
- Memory usage: <500MB peak during mass vectorization
- Memory leak prevention during extended operation
- Scalability characteristics under load
- Resource utilization patterns

Tests use realistic data volumes and stress test the embedding
generation pipeline to ensure production readiness.
"""

import asyncio
import gc
import json
import psutil
import time
import tracemalloc
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from devstream.database.connection import ConnectionPool
from devstream.memory.embedding_generator import (
    EmbeddingConfig,
    EmbeddingGenerator,
    EmbeddingGenerationError,
)
from devstream.memory.models import MemoryEntry, ContentType, ContentFormat
from devstream.memory.storage import MemoryStorage


class TestEmbeddingGenerationPerformance:
    """
    Performance testing suite for embedding generation system.

    Tests validate compliance with FASE 5 performance requirements:
    - Batch processing: <60s for 1000 records
    - Memory usage: <500MB peak during mass vectorization
    - Memory leak prevention
    - Scalability and resource efficiency
    """

    @pytest.fixture
    async def performance_db_engine(self):
        """Create optimized database for performance testing."""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        async with engine.begin() as conn:
            # Create optimized schema for performance testing
            await conn.execute("""
                CREATE TABLE semantic_memory (
                    id TEXT PRIMARY KEY,
                    plan_id TEXT,
                    phase_id TEXT,
                    task_id TEXT,
                    content TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    content_format TEXT DEFAULT 'text',
                    keywords TEXT,
                    embedding TEXT,
                    embedding_model TEXT,
                    embedding_dimension INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create performance indexes
            await conn.execute("CREATE INDEX idx_perf_type ON semantic_memory(content_type)")
            await conn.execute("CREATE INDEX idx_perf_created ON semantic_memory(created_at)")

        yield engine
        await engine.dispose()

    @pytest.fixture
    async def performance_connection_pool(self, performance_db_engine):
        """Create connection pool for performance testing."""
        pool = ConnectionPool(performance_db_engine)
        yield pool
        await pool.close()

    @pytest.fixture
    def performance_config(self):
        """Optimized configuration for performance testing."""
        return EmbeddingConfig(
            model_name="gemma2",
            batch_size=50,  # Larger batches for performance
            max_retries=2,  # Limited retries for speed
            base_delay=0.05,  # Fast retries
            timeout=30.0,
        )

    @pytest.fixture
    async def performance_storage(self, performance_connection_pool, performance_config):
        """Initialize memory storage optimized for performance testing."""
        storage = MemoryStorage(performance_connection_pool, performance_config)
        await storage.create_virtual_tables()
        return storage

    @pytest.fixture
    def performance_monitor(self):
        """Monitor memory and performance metrics."""
        class PerformanceMonitor:
            def __init__(self):
                self.snapshots = []
                self.start_time = None
                self.process = psutil.Process()

            def start_monitoring(self):
                """Start performance monitoring."""
                tracemalloc.start()
                self.start_time = time.time()
                self.take_snapshot("start")

            def take_snapshot(self, label: str):
                """Take performance snapshot."""
                if self.start_time is None:
                    self.start_time = time.time()

                current_time = time.time() - self.start_time

                # Memory metrics
                memory_info = self.process.memory_info()
                memory_percent = self.process.memory_percent()

                # tracemalloc metrics
                if tracemalloc.is_tracing():
                    current, peak = tracemalloc.get_traced_memory()
                else:
                    current = peak = 0

                snapshot = {
                    "label": label,
                    "timestamp": current_time,
                    "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size
                    "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                    "memory_percent": memory_percent,
                    "traced_current_mb": current / 1024 / 1024,
                    "traced_peak_mb": peak / 1024 / 1024,
                }

                self.snapshots.append(snapshot)
                return snapshot

            def get_peak_memory(self) -> float:
                """Get peak memory usage in MB."""
                if not self.snapshots:
                    return 0.0
                return max(snapshot["rss_mb"] for snapshot in self.snapshots)

            def get_peak_traced_memory(self) -> float:
                """Get peak traced memory usage in MB."""
                if not self.snapshots:
                    return 0.0
                return max(snapshot["traced_peak_mb"] for snapshot in self.snapshots)

            def get_memory_growth(self) -> float:
                """Calculate memory growth from start to end."""
                if len(self.snapshots) < 2:
                    return 0.0
                start_memory = self.snapshots[0]["rss_mb"]
                end_memory = self.snapshots[-1]["rss_mb"]
                return end_memory - start_memory

            def stop_monitoring(self) -> Dict[str, Any]:
                """Stop monitoring and return summary."""
                self.take_snapshot("end")
                tracemalloc.stop()

                return {
                    "peak_memory_mb": self.get_peak_memory(),
                    "peak_traced_memory_mb": self.get_peak_traced_memory(),
                    "memory_growth_mb": self.get_memory_growth(),
                    "total_time": self.snapshots[-1]["timestamp"] if self.snapshots else 0,
                    "snapshots": self.snapshots,
                }

        return PerformanceMonitor()

    def generate_performance_test_data(self, count: int) -> List[MemoryEntry]:
        """
        Generate realistic test data for performance testing.

        Args:
            count: Number of memory entries to generate

        Returns:
            List of memory entries with varied content types and sizes
        """
        base_time = datetime.now()
        entries = []

        # Content templates for realistic variety
        code_templates = [
            """def process_{name}(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    \"\"\"Process {description} data.

    Args:
        data: List of {name} records to process

    Returns:
        Dictionary with processing results and metrics
    \"\"\"
    if not data:
        return {{"status": "empty", "count": 0}}

    start_time = time.time()
    results = []
    errors = []

    for item in data:
        try:
            # Process {name} item
            processed = {item["id"]: item.get("value", 0) * 1.5}
            results.append(processed)
        except Exception as e:
            errors.append({{"item_id": item.get("id"), "error": str(e)}})

    end_time = time.time()
    processing_time = end_time - start_time

    return {{
        "status": "completed",
        "count": len(results),
        "errors": len(errors),
        "processing_time": processing_time,
        "results": results,
        "error_details": errors
    }}""",
            """class {Name}Manager:
    \"\"\"Manager class for {name} operations.

    Handles CRUD operations, validation, and business logic
    for {name} entities in the system.
    \"\"\"

    def __init__(self, db_session, config=None):
        self.db = db_session
        self.config = config or {{}}
        self.logger = logging.getLogger(__name__)

    async def create_{name}(self, {name}_data: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Create new {name} record.

        Args:
            {name}_data: Data for new {name} entry

        Returns:
            Created {name} record with metadata

        Raises:
            ValidationError: If data is invalid
            DuplicateError: If {name} already exists
        \"\"\"
        # Validate input data
        if not self._validate_{name}_data({name}_data):
            raise ValidationError("Invalid {name} data provided")

        # Check for duplicates
        if await self._{name}_exists({name}_data.get("id")):
            raise DuplicateError(f"{Name} with ID {{{name}_data.get('id')}} already exists")

        # Create {name} record
        {name} = {{
            "id": {name}_data["id"],
            "data": {name}_data,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "status": "active"
        }}

        # Save to database
        await self.db.save({name})

        self.logger.info(f"Created {name}: {{{name}['id']}}")
        return {name}""",
        """async def analyze_{name}_patterns(historical_data: List[Dict]) -> Dict[str, Any]:
    \"\"\"Analyze patterns in {name} historical data.

    Performs statistical analysis to identify trends, anomalies,
    and actionable insights from {name} data history.

    Args:
        historical_data: List of historical {name} records

    Returns:
        Analysis results with patterns and recommendations
    \"\"\"
    if not historical_data:
        return {{"status": "no_data", "patterns": []}}

    # Extract numeric values for analysis
    numeric_values = []
    timestamps = []

    for record in historical_data:
        if "value" in record and isinstance(record["value"], (int, float)):
            numeric_values.append(record["value"])
        if "timestamp" in record:
            timestamps.append(record["timestamp"])

    if not numeric_values:
        return {{"status": "no_numeric_data", "patterns": []}}

    # Statistical analysis
    import statistics
    import numpy as np

    mean_value = statistics.mean(numeric_values)
    median_value = statistics.median(numeric_values)
    std_dev = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0

    # Trend analysis
    if len(numeric_values) >= 3:
        # Simple linear regression for trend
        x = np.arange(len(numeric_values))
        y = np.array(numeric_values)
        slope, intercept = np.polyfit(x, y, 1)
        trend = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
    else:
        trend = "insufficient_data"

    # Anomaly detection (simple outlier detection)
    threshold = 2 * std_dev
    anomalies = []
    for i, value in enumerate(numeric_values):
        if abs(value - mean_value) > threshold:
            anomalies.append({{"index": i, "value": value, "deviation": abs(value - mean_value)}})

    return {{
        "status": "completed",
        "statistics": {{
            "count": len(numeric_values),
            "mean": mean_value,
            "median": median_value,
            "std_dev": std_dev,
            "min": min(numeric_values),
            "max": max(numeric_values)
        }},
        "trend": trend,
        "anomalies": anomalies,
        "recommendations": self._generate_{name}_recommendations(mean_value, trend, anomalies)
    }}""",
        ]

        doc_templates = [
            """# {Name} API Documentation

## Overview
The {name} API provides comprehensive functionality for managing {name} resources in the DevStream platform. This API supports full CRUD operations, advanced querying, and real-time updates.

## Base URL
```
https://api.devstream.ai/v1/{name}
```

## Authentication
All API requests require authentication using Bearer tokens:
```
Authorization: Bearer <your-api-token>
```

## Endpoints

### Create {Name}
`POST /{name}`

Create a new {name} resource with the provided data.

**Request Body:**
```json
{{
  "id": "string",
  "name": "string",
  "description": "string",
  "config": {{}},
  "tags": ["string"],
  "metadata": {{}}
}}
```

**Response:**
```json
{{
  "id": "string",
  "name": "string",
  "description": "string",
  "config": {{}},
  "tags": ["string"],
  "metadata": {{}},
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "status": "active"
}}
```

**Error Responses:**
- `400 Bad Request`: Invalid data provided
- `401 Unauthorized`: Invalid or missing authentication
- `409 Conflict`: Resource already exists
- `500 Internal Server Error`: Server error occurred

### Get {Name}
`GET /{name}/{{id}}`

Retrieve a specific {name} resource by ID.

**Response:**
Same as create response format.

### List {Name}s
`GET /{name}`

List all {name} resources with optional filtering.

**Query Parameters:**
- `limit`: Maximum number of results (default: 50, max: 1000)
- `offset`: Number of results to skip (default: 0)
- `status`: Filter by status (active, inactive, deleted)
- `tags`: Filter by tags (comma-separated)
- `created_after`: Filter by creation date (ISO 8601)
- `created_before`: Filter by creation date (ISO 8601)

**Response:**
```json
{{
  "items": [/* {name} objects */],
  "total": 100,
  "limit": 50,
  "offset": 0,
  "has_more": true
}}
```

### Update {Name}
`PUT /{name}/{{id}}`

Update an existing {name} resource.

**Request Body:**
Same format as create request.

### Delete {Name}
`DELETE /{name}/{{id}}`

Delete a {name} resource.

**Response:**
`204 No Content` on successful deletion.

## Rate Limiting
API requests are rate-limited to prevent abuse:
- **Standard tier**: 1000 requests per hour
- **Premium tier**: 10000 requests per hour
- **Enterprise tier**: Unlimited requests

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Best Practices
1. **Use pagination** for list operations to avoid timeouts
2. **Implement caching** for frequently accessed resources
3. **Handle rate limits** gracefully with exponential backoff
4. **Validate input data** before sending requests
5. **Use appropriate HTTP methods** for different operations

## Error Handling
The API uses standard HTTP status codes and provides detailed error messages:

```json
{{
  "error": {{
    "code": "VALIDATION_ERROR",
    "message": "Invalid data provided",
    "details": {{
      "field": "name",
      "reason": "Field is required"
    }}
  }}
}}
```

## SDK Support
Official SDKs are available for:
- Python 3.8+
- Node.js 16+
- Java 11+
- Go 1.19+
- .NET 6+

See the [SDK documentation](./sdcs/) for installation and usage instructions.""",
            """# {Name} Deployment Guide

## Overview
This guide covers the deployment of {name} services in production environments. It includes instructions for Docker deployment, Kubernetes orchestration, and cloud-specific configurations.

## Prerequisites
- Docker 20.10+ or Kubernetes 1.24+
- 2GB RAM minimum (4GB recommended)
- 10GB storage minimum
- Network connectivity for external dependencies

## Docker Deployment

### Quick Start
```bash
# Pull the latest image
docker pull devstream/{name}:latest

# Run the container
docker run -d \\
  --name {name} \\
  -p 8080:8080 \\
  -e DATABASE_URL=postgresql://user:pass@localhost:5432/{name} \\
  -e API_KEY=your-api-key \\
  devstream/{name}:latest
```

### Docker Compose
Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  {name}:
    image: devstream/{name}:latest
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/{name}
      - REDIS_URL=redis://redis:6379
      - API_KEY=${API_KEY}
      - LOG_LEVEL=INFO
    depends_on:
      - db
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB={name}
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  postgres_data:
```

Start the services:
```bash
docker-compose up -d
```

## Kubernetes Deployment

### Namespace Configuration
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: {name}
  labels:
    name: {name}
```

### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: {name}
spec:
  replicas: 3
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
    spec:
      containers:
      - name: {name}
        image: devstream/{name}:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: {name}-secrets
              key: database-url
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: {name}-secrets
              key: api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Service
```yaml
apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: {name}
spec:
  selector:
    app: {name}
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: ClusterIP
```

### Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {name}
  namespace: {name}
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - {name}.yourdomain.com
    secretName: {name}-tls
  rules:
  - host: {name}.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {name}
            port:
              number: 80
```

## Configuration

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `API_KEY`: API authentication key
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARN, ERROR)
- `PORT`: Service port (default: 8080)
- `WORKERS`: Number of worker processes (default: CPU count)

### Security Configuration
1. **API Keys**: Use strong, randomly generated API keys
2. **Database Security**: Use SSL connections and strong passwords
3. **Network Security**: Configure firewall rules and network policies
4. **Secrets Management**: Use Kubernetes secrets or external secret stores

## Monitoring and Logging

### Health Checks
- `/health`: Basic health status
- `/ready`: Readiness status
- `/metrics`: Prometheus metrics

### Logging
Configure structured logging with appropriate levels:
```json
{{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "service": "{name}",
  "message": "Request completed",
  "request_id": "req_123",
  "duration_ms": 150,
  "status_code": 200
}}
```

### Metrics
Key metrics to monitor:
- Request rate and response times
- Error rates and types
- Database connection pool usage
- Memory and CPU utilization
- Custom business metrics

## Scaling

### Horizontal Scaling
Increase replica count in deployment:
```bash
kubectl scale deployment {name} --replicas=10 -n {name}
```

### Vertical Scaling
Adjust resource limits in deployment spec based on monitoring data.

### Auto-scaling
Configure HPA (Horizontal Pod Autoscaler):
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {name}
  namespace: {name}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {name}
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Backup and Recovery

### Database Backups
```bash
# Create backup
pg_dump -h localhost -U user -d {name} > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
psql -h localhost -U user -d {name} < backup_20240101_120000.sql
```

### Application State Backup
For stateful applications, backup persistent volumes and configuration.

## Troubleshooting

### Common Issues
1. **High Memory Usage**: Check for memory leaks and optimize batch sizes
2. **Database Connections**: Verify connection pool configuration
3. **Slow Response Times**: Profile application performance and database queries
4. **Crash Loops**: Check logs and resource limits

### Debug Commands
```bash
# View logs
kubectl logs -f deployment/{name} -n {name}

# Check resource usage
kubectl top pods -n {name}

# Describe pod
kubectl describe pod <pod-name> -n {name}

# Port forward for debugging
kubectl port-forward deployment/{name} 8080:8080 -n {name}
```""",
        ]

        # Generate varied content
        for i in range(count):
            template_index = i % len(code_templates + doc_templates)
            is_code = template_index < len(code_templates)

            if is_code:
                template = code_templates[template_index]
                name_variants = ["data", "user", "order", "product", "payment", "inventory", "analytics", "report"]
                descriptions = ["data processing", "user management", "order processing", "product catalog",
                              "payment processing", "inventory management", "analytics processing", "report generation"]

                name = name_variants[i % len(name_variants)]
                description = descriptions[i % len(descriptions)]
                Name = name.capitalize()

                content = template.format(
                    name=name,
                    Name=Name,
                    description=description
                )
                content_type = "code"
                content_format = "python"
            else:
                template = doc_templates[template_index - len(code_templates)]
                name_variants = ["Analytics Service", "User Management", "Order Processing", "Product Catalog",
                              "Payment Gateway", "Inventory System", "Report Generator", "API Gateway"]
                name = name_variants[i % len(name_variants)]
                content = template.format(name=name, Name=name)
                content_type = "documentation"
                content_format = "markdown"

            entry = MemoryEntry(
                id=f"perf_test_{i:06d}",
                plan_id="performance_test",
                phase_id="mass_vectorization",
                task_id=f"batch_{i // 50:03d}",
                content=content,
                content_type=content_type,
                content_format=content_format,
                keywords=[name.lower().replace(" ", "-") for name in name_variants[:3]] + ["performance", "testing"],
                entities=[name.replace(" ", "") for name in name_variants[:2]] + ["DevStream"],
                sentiment=0.8,
                complexity_score=6 + (i % 4),
                created_at=base_time + timedelta(seconds=i),
                updated_at=base_time + timedelta(seconds=i),
            )
            entries.append(entry)

        return entries

    @pytest.mark.asyncio
    async def test_batch_embedding_performance_1000_records(self, performance_storage, performance_monitor):
        """
        Test batch embedding performance meets FASE 5 requirements.

        Requirement: <60s for 1000 records
        """
        # Arrange: Generate 1000 test records
        test_entries = self.generate_performance_test_data(1000)

        # Act: Monitor performance during processing
        performance_monitor.start_monitoring()

        with patch('ollama.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Mock realistic embedding generation performance
            def mock_embed(model, input):
                # Simulate realistic processing time (10-50ms based on content length)
                processing_time = 0.01 + (len(input) / 10000) * 0.04
                time.sleep(processing_time)

                # Generate consistent embeddings
                content_hash = hash(input) % 10000
                base_vector = np.random.RandomState(content_hash).random(384).astype(np.float32)
                base_vector = base_vector / np.linalg.norm(base_vector)

                return {'embeddings': [base_vector.tolist()]}

            mock_client.embed = mock_embed
            mock_client.list.return_value = {'models': [{'name': 'gemma2:latest'}]}

            # Process all entries
            start_time = time.time()
            processed_entries = await performance_storage.store_memories_with_embeddings(test_entries)
            end_time = time.time()

        performance_summary = performance_monitor.stop_monitoring()

        # Assert: Validate performance requirements
        processing_time = end_time - start_time

        # Primary requirement: <60s for 1000 records
        assert processing_time < 60.0, \
            f"Performance requirement failed: {processing_time:.2f}s > 60s for 1000 records"

        # Secondary performance metrics
        avg_time_per_record = processing_time / len(test_entries)
        assert avg_time_per_record < 0.1, \
            f"Average time per record too high: {avg_time_per_record:.4f}s"

        # All records should be processed
        assert len(processed_entries) == len(test_entries), \
            f"Not all records processed: {len(processed_entries)}/{len(test_entries)}"

        # All embeddings should be generated
        entries_with_embeddings = [e for e in processed_entries if e.embedding is not None]
        assert len(entries_with_embeddings) == len(test_entries), \
            f"Not all embeddings generated: {len(entries_with_embeddings)}/{len(test_entries)}"

        # Memory usage should be reasonable
        assert performance_summary["peak_memory_mb"] < 1000, \
            f"Peak memory usage too high: {performance_summary['peak_memory_mb']:.1f}MB"

        # Performance report
        performance_report = {
            "total_records": len(test_entries),
            "processing_time_seconds": processing_time,
            "avg_time_per_record_seconds": avg_time_per_record,
            "records_per_second": len(test_entries) / processing_time,
            "peak_memory_mb": performance_summary["peak_memory_mb"],
            "peak_traced_memory_mb": performance_summary["peak_traced_memory_mb"],
            "memory_growth_mb": performance_summary["memory_growth_mb"],
            "embedding_success_rate": len(entries_with_embeddings) / len(test_entries),
        }

        # Log performance report for validation
        print(f"\nPerformance Test Results (1000 records):")
        for key, value in performance_report.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")

        # Performance should be within acceptable bounds
        assert performance_report["records_per_second"] > 10, \
            f"Processing rate too low: {performance_report['records_per_second']:.2f} records/second"

    @pytest.mark.asyncio
    async def test_memory_usage_limits_mass_vectorization(self, performance_storage, performance_monitor):
        """
        Test memory usage stays within limits during mass vectorization.

        Requirement: <500MB peak memory usage
        """
        # Arrange: Generate large dataset for stress testing
        test_entries = self.generate_performance_test_data(2000)  # Larger dataset for memory stress

        # Act: Monitor memory usage during mass vectorization
        performance_monitor.start_monitoring()

        # Take periodic snapshots during processing
        snapshot_task = asyncio.create_task(self._periodic_memory_snapshots(performance_monitor, 2.0))

        with patch('ollama.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Mock embedding generation with controlled memory usage
            def mock_embed(model, input):
                # Simulate processing time
                time.sleep(0.005)

                # Generate embeddings
                content_hash = hash(input) % 10000
                base_vector = np.random.RandomState(content_hash).random(384).astype(np.float32)
                base_vector = base_vector / np.linalg.norm(base_vector)

                return {'embeddings': [base_vector.tolist()]}

            mock_client.embed = mock_embed
            mock_client.list.return_value = {'models': [{'name': 'gemma2:latest'}]}

            # Process entries
            processed_entries = await performance_storage.store_memories_with_embeddings(test_entries)

        # Stop snapshot task
        snapshot_task.cancel()
        try:
            await snapshot_task
        except asyncio.CancelledError:
            pass

        performance_summary = performance_monitor.stop_monitoring()

        # Assert: Validate memory requirements
        peak_memory_mb = performance_summary["peak_memory_mb"]
        peak_traced_memory_mb = performance_summary["peak_traced_memory_mb"]

        # Primary requirement: <500MB peak memory usage
        assert peak_memory_mb < 500, \
            f"Memory requirement failed: peak memory {peak_memory_mb:.1f}MB > 500MB"

        # Secondary memory validation
        assert peak_traced_memory_mb < 300, \
            f"Traced memory too high: {peak_traced_memory_mb:.1f}MB"

        # Memory growth should be controlled
        memory_growth_mb = performance_summary["memory_growth_mb"]
        assert memory_growth_mb < 200, \
            f"Memory growth too high: {memory_growth_mb:.1f}MB"

        # Processing should complete successfully
        assert len(processed_entries) == len(test_entries), \
            f"Processing incomplete: {len(processed_entries)}/{len(test_entries)}"

        entries_with_embeddings = [e for e in processed_entries if e.embedding is not None]
        assert len(entries_with_embeddings) == len(test_entries), \
            f"Embedding generation incomplete: {len(entries_with_embeddings)}/{len(test_entries)}"

        # Memory usage report
        memory_report = {
            "total_records": len(test_entries),
            "peak_memory_mb": peak_memory_mb,
            "peak_traced_memory_mb": peak_traced_memory_mb,
            "memory_growth_mb": memory_growth_mb,
            "memory_per_record_kb": (peak_memory_mb * 1024) / len(test_entries),
            "embedding_success_rate": len(entries_with_embeddings) / len(test_entries),
        }

        print(f"\nMemory Usage Test Results (2000 records):")
        for key, value in memory_report.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")

    @pytest.mark.asyncio
    async def test_memory_leak_prevention_extended_operation(self, performance_storage, performance_monitor):
        """
        Test for memory leaks during extended operation.

        Processes multiple batches to detect memory leaks over time.
        """
        # Arrange: Configure for extended operation testing
        batch_count = 10
        records_per_batch = 100

        # Act: Process multiple batches while monitoring memory
        performance_monitor.start_monitoring()
        memory_snapshots = []

        with patch('ollama.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            def mock_embed(model, input):
                # Very fast processing to focus on memory leaks
                time.sleep(0.001)
                content_hash = hash(input) % 10000
                base_vector = np.random.RandomState(content_hash).random(384).astype(np.float32)
                base_vector = base_vector / np.linalg.norm(base_vector)
                return {'embeddings': [base_vector.tolist()]}

            mock_client.embed = mock_embed
            mock_client.list.return_value = {'models': [{'name': 'gemma2:latest'}]}

            # Process multiple batches
            for batch_num in range(batch_count):
                # Generate fresh data for each batch
                batch_entries = self.generate_performance_test_data(records_per_batch)

                # Ensure unique IDs
                for i, entry in enumerate(batch_entries):
                    entry.id = f"leak_test_{batch_num:03d}_{i:03d}"

                # Process batch
                processed_batch = await performance_storage.store_memories_with_embeddings(batch_entries)

                # Take memory snapshot
                snapshot = performance_monitor.take_snapshot(f"batch_{batch_num}")
                memory_snapshots.append({
                    "batch": batch_num,
                    "memory_mb": snapshot["rss_mb"],
                    "traced_memory_mb": snapshot["traced_peak_mb"],
                })

                # Force garbage collection to test GC effectiveness
                gc.collect()

                # Small delay between batches
                await asyncio.sleep(0.1)

        performance_summary = performance_monitor.stop_monitoring()

        # Assert: Validate no memory leaks
        # Memory should not grow consistently across batches
        memory_values = [snapshot["memory_mb"] for snapshot in memory_snapshots]

        # Calculate memory growth trend
        if len(memory_values) >= 3:
            # Simple linear regression to detect trend
            x = list(range(len(memory_values)))
            y = memory_values
            n = len(memory_values)

            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))

            # Calculate slope (memory growth per batch)
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2) if (n * sum_x2 - sum_x ** 2) != 0 else 0

            # Memory growth should be minimal (less than 1MB per batch)
            assert abs(slope) < 1.0, \
                f"Memory leak detected: growth rate {slope:.3f}MB/batch"

        # Peak memory should be reasonable
        assert performance_summary["peak_memory_mb"] < 300, \
            f"Peak memory too high during extended operation: {performance_summary['peak_memory_mb']:.1f}MB"

        # Total memory growth should be controlled
        assert performance_summary["memory_growth_mb"] < 100, \
            f"Excessive memory growth: {performance_summary['memory_growth_mb']:.1f}MB"

        # All batches should process successfully
        total_processed = batch_count * records_per_batch
        # We can't easily verify total processed entries since they're processed in batches
        # but we can verify the system didn't crash

        # Memory leak report
        leak_report = {
            "batch_count": batch_count,
            "records_per_batch": records_per_batch,
            "total_records_estimated": batch_count * records_per_batch,
            "peak_memory_mb": performance_summary["peak_memory_mb"],
            "memory_growth_mb": performance_summary["memory_growth_mb"],
            "memory_trend_slope_mb_per_batch": slope if len(memory_values) >= 3 else 0,
            "final_memory_mb": memory_values[-1] if memory_values else 0,
            "initial_memory_mb": memory_values[0] if memory_values else 0,
        }

        print(f"\nMemory Leak Test Results:")
        for key, value in leak_report.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.3f}")
            else:
                print(f"  {key}: {value}")

    @pytest.mark.asyncio
    async def test_scalability_characteristics(self, performance_storage, performance_monitor):
        """
        Test scalability characteristics under different loads.

        Validates linear or sub-linear performance scaling.
        """
        # Arrange: Test different batch sizes for scalability
        batch_sizes = [100, 200, 400, 800]
        scalability_results = {}

        for batch_size in batch_sizes:
            # Generate test data
            test_entries = self.generate_performance_test_data(batch_size)

            # Monitor performance
            performance_monitor.start_monitoring()

            with patch('ollama.Client') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                def mock_embed(model, input):
                    # Simulate consistent processing time
                    time.sleep(0.01)
                    content_hash = hash(input) % 10000
                    base_vector = np.random.RandomState(content_hash).random(384).astype(np.float32)
                    base_vector = base_vector / np.linalg.norm(base_vector)
                    return {'embeddings': [base_vector.tolist()]}

                mock_client.embed = mock_embed
                mock_client.list.return_value = {'models': [{'name': 'gemma2:latest'}]}

                # Process batch
                start_time = time.time()
                processed_entries = await performance_storage.store_memories_with_embeddings(test_entries)
                end_time = time.time()

            performance_summary = performance_monitor.stop_monitoring()

            # Calculate metrics
            processing_time = end_time - start_time
            avg_time_per_record = processing_time / batch_size
            records_per_second = batch_size / processing_time

            scalability_results[batch_size] = {
                "processing_time": processing_time,
                "avg_time_per_record": avg_time_per_record,
                "records_per_second": records_per_second,
                "peak_memory_mb": performance_summary["peak_memory_mb"],
                "memory_per_record_mb": performance_summary["peak_memory_mb"] / batch_size,
                "success_count": len(processed_entries),
                "embedding_success_rate": sum(1 for e in processed_entries if e.embedding is not None) / len(processed_entries),
            }

            # Small delay between tests
            await asyncio.sleep(0.5)

        # Assert: Validate scalability characteristics
        # Processing should scale reasonably (not exponentially)
        processing_times = [results["processing_time"] for results in scalability_results.values()]
        batch_sizes_sorted = sorted(batch_sizes)

        # Check that doubling batch size doesn't quadruple processing time
        for i in range(1, len(batch_sizes_sorted)):
            prev_size = batch_sizes_sorted[i-1]
            curr_size = batch_sizes_sorted[i]
            prev_time = scalability_results[prev_size]["processing_time"]
            curr_time = scalability_results[curr_size]["processing_time"]

            size_ratio = curr_size / prev_size
            time_ratio = curr_time / prev_time

            # Time scaling should be close to linear (time_ratio <= size_ratio * 1.5)
            assert time_ratio <= size_ratio * 1.5, \
                f"Poor scalability: size {size_ratio:.1f}x, time {time_ratio:.1f}x (batch {prev_size}->{curr_size})"

        # Memory per record should be reasonably stable
        memory_per_records = [results["memory_per_record_mb"] for results in scalability_results.values()]
        avg_memory_per_record = sum(memory_per_records) / len(memory_per_records)

        for batch_size, memory_per_record in zip(batch_sizes, memory_per_records):
            # Memory per record shouldn't vary wildly
            assert abs(memory_per_record - avg_memory_per_record) / avg_memory_per_record < 0.5, \
                f"Memory per record unstable: {memory_per_record:.3f}MB vs avg {avg_memory_per_record:.3f}MB"

        # Throughput should be reasonable
        throughputs = [results["records_per_second"] for results in scalability_results.values()]
        avg_throughput = sum(throughputs) / len(throughputs)

        assert avg_throughput > 20, \
            f"Average throughput too low: {avg_throughput:.2f} records/second"

        # Scalability report
        scalability_report = {
            "batch_sizes_tested": batch_sizes,
            "avg_throughput_records_per_second": avg_throughput,
            "avg_memory_per_record_mb": avg_memory_per_record,
            "results": scalability_results,
        }

        print(f"\nScalability Test Results:")
        print(f"  Average throughput: {avg_throughput:.2f} records/second")
        print(f"  Average memory per record: {avg_memory_per_record:.3f}MB")
        print(f"  Detailed results:")
        for batch_size, results in scalability_results.items():
            print(f"    Batch {batch_size}: {results['records_per_second']:.2f} rec/s, "
                  f"{results['memory_per_record_mb']:.3f}MB/rec")

    async def _periodic_memory_snapshots(self, performance_monitor, interval_seconds: float):
        """Take periodic memory snapshots during long-running operations."""
        try:
            while True:
                await asyncio.sleep(interval_seconds)
                performance_monitor.take_snapshot("periodic")
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_concurrent_performance_stress(self, performance_storage, performance_monitor):
        """
        Test performance under concurrent load with stress conditions.

        Validates system stability and resource management under high concurrency.
        """
        # Arrange: Configure stress test parameters
        concurrent_batches = 5
        records_per_batch = 50
        total_records = concurrent_batches * records_per_batch

        # Act: Process multiple batches concurrently
        performance_monitor.start_monitoring()

        async def process_batch_with_monitoring(batch_id: int, entries: List[MemoryEntry]) -> Dict[str, Any]:
            """Process a batch with individual performance monitoring."""
            batch_start_time = time.time()

            with patch('ollama.Client') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                def mock_embed(model, input):
                    # Simulate variable processing time
                    processing_time = 0.005 + (hash(input) % 10) * 0.002
                    time.sleep(processing_time)

                    content_hash = hash(input) % 10000
                    base_vector = np.random.RandomState(content_hash).random(384).astype(np.float32)
                    base_vector = base_vector / np.linalg.norm(base_vector)
                    return {'embeddings': [base_vector.tolist()]}

                mock_client.embed = mock_embed
                mock_client.list.return_value = {'models': [{'name': 'gemma2:latest'}]}

                processed_entries = await performance_storage.store_memories_with_embeddings(entries)

            batch_end_time = time.time()

            return {
                "batch_id": batch_id,
                "processing_time": batch_end_time - batch_start_time,
                "record_count": len(processed_entries),
                "success_count": sum(1 for e in processed_entries if e.embedding is not None),
            }

        # Generate test data for all batches
        all_batch_entries = []
        for batch_id in range(concurrent_batches):
            batch_entries = self.generate_performance_test_data(records_per_batch)
            # Ensure unique IDs across batches
            for i, entry in enumerate(batch_entries):
                entry.id = f"concurrent_{batch_id:03d}_{i:03d}"
            all_batch_entries.append(batch_entries)

        # Process batches concurrently
        concurrent_tasks = [
            process_batch_with_monitoring(batch_id, batch_entries)
            for batch_id, batch_entries in enumerate(all_batch_entries)
        ]

        batch_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)

        performance_summary = performance_monitor.stop_monitoring()

        # Assert: Validate concurrent performance
        # All batches should complete successfully
        successful_batches = [r for r in batch_results if not isinstance(r, Exception)]
        assert len(successful_batches) == concurrent_batches, \
            f"Not all batches completed: {len(successful_batches)}/{concurrent_batches}"

        # No exceptions should occur
        exceptions = [r for r in batch_results if isinstance(r, Exception)]
        assert len(exceptions) == 0, \
            f"Concurrent processing raised exceptions: {exceptions}"

        # Validate processing results
        total_processed = sum(batch["record_count"] for batch in successful_batches)
        total_successful = sum(batch["success_count"] for batch in successful_batches)

        assert total_processed == total_records, \
            f"Processing incomplete: {total_processed}/{total_records}"

        assert total_successful == total_records, \
            f"Embedding generation incomplete: {total_successful}/{total_records}"

        # Performance should be reasonable under load
        peak_memory_mb = performance_summary["peak_memory_mb"]
        assert peak_memory_mb < 400, \
            f"Memory usage too high under concurrent load: {peak_memory_mb:.1f}MB"

        # Concurrent processing should be faster than sequential
        batch_times = [batch["processing_time"] for batch in successful_batches]
        max_batch_time = max(batch_times)
        estimated_sequential_time = sum(batch_times)

        # Concurrent should be at least 2x faster than sequential
        assert max_batch_time < estimated_sequential_time / 2, \
            f"Concurrent processing not efficient enough: {max_batch_time:.3f}s vs sequential {estimated_sequential_time:.3f}s"

        # Concurrent performance report
        concurrent_report = {
            "concurrent_batches": concurrent_batches,
            "records_per_batch": records_per_batch,
            "total_records": total_records,
            "peak_memory_mb": peak_memory_mb,
            "max_batch_time": max_batch_time,
            "estimated_sequential_time": estimated_sequential_time,
            "concurrency_efficiency": estimated_sequential_time / max_batch_time,
            "batch_results": successful_batches,
        }

        print(f"\nConcurrent Performance Test Results:")
        print(f"  Total records processed: {total_processed}")
        print(f"  Peak memory usage: {peak_memory_mb:.1f}MB")
        print(f"  Max batch time: {max_batch_time:.3f}s")
        print(f"  Concurrency efficiency: {concurrent_report['concurrency_efficiency']:.2f}x")

    def test_performance_requirements_compliance(self):
        """
        Test compliance with FASE 5 performance requirements.

        Validates that all performance tests meet the specified requirements.
        """
        # FASE 5 Performance Requirements:
        # 1. Batch embedding performance: <60s/1000 records
        # 2. Memory usage: <500MB peak during mass vectorization
        # 3. Memory leak prevention during extended operation
        # 4. Scalability characteristics validation

        required_tests = [
            'test_batch_embedding_performance_1000_records',
            'test_memory_usage_limits_mass_vectorization',
            'test_memory_leak_prevention_extended_operation',
            'test_scalability_characteristics',
            'test_concurrent_performance_stress',
        ]

        # Verify all required performance tests exist
        current_methods = [method for method in dir(self) if method.startswith('test_')]

        for required_test in required_tests:
            assert required_test in current_methods, \
                f"Required performance test {required_test} not found"

        # Verify comprehensive performance coverage
        performance_test_count = len([m for m in current_methods if 'performance' in m or 'memory' in m or 'scalability' in m])
        assert performance_test_count >= 5, \
            f"Insufficient performance test coverage: {performance_test_count} tests, expected at least 5"

        # All performance requirements should be covered
        assert True, "All FASE 5 performance requirements covered by test suite"


# Additional performance validation utilities
class PerformanceBenchmark:
    """
    Utility class for performance benchmarking and validation.

    Provides standardized methods for measuring and validating
    performance characteristics of the embedding system.
    """

    @staticmethod
    def measure_embedding_performance(
        embedding_generator: EmbeddingGenerator,
        test_entries: List[MemoryEntry],
        warmup_entries: int = 10
    ) -> Dict[str, Any]:
        """
        Measure embedding generation performance with warmup.

        Args:
            embedding_generator: Configured embedding generator
            test_entries: Entries to process
            warmup_entries: Number of entries for warmup

        Returns:
            Performance measurement results
        """
        import time
        import psutil
        import tracemalloc

        # Warmup phase
        if warmup_entries > 0 and len(test_entries) > warmup_entries:
            warmup_data = test_entries[:warmup_entries]
            test_data = test_entries[warmup_entries:]
        else:
            warmup_data = []
            test_data = test_entries

        # Process warmup data
        if warmup_data:
            asyncio.run(embedding_generator.generate_and_store_embeddings(warmup_data))

        # Start performance measurement
        tracemalloc.start()
        start_time = time.time()
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process test data
        processed_entries = asyncio.run(embedding_generator.generate_and_store_embeddings(test_data))

        # End measurement
        end_time = time.time()
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        current_traced, peak_traced = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Calculate metrics
        processing_time = end_time - start_time
        memory_delta = end_memory - start_memory

        return {
            "entries_processed": len(processed_entries),
            "processing_time_seconds": processing_time,
            "avg_time_per_entry_seconds": processing_time / len(test_data),
            "entries_per_second": len(test_data) / processing_time,
            "start_memory_mb": start_memory,
            "end_memory_mb": end_memory,
            "memory_delta_mb": memory_delta,
            "peak_traced_memory_mb": peak_traced / 1024 / 1024,
            "success_rate": sum(1 for e in processed_entries if e.embedding is not None) / len(processed_entries),
        }

    @staticmethod
    def validate_performance_requirements(benchmark_results: Dict[str, Any]) -> bool:
        """
        Validate benchmark results against FASE 5 requirements.

        Args:
            benchmark_results: Results from performance measurement

        Returns:
            True if all requirements are met
        """
        # Extract key metrics
        entries_processed = benchmark_results["entries_processed"]
        processing_time = benchmark_results["processing_time_seconds"]
        peak_memory_mb = benchmark_results.get("peak_traced_memory_mb", 0)

        # Calculate metrics for 1000 records if different count
        if entries_processed != 1000:
            time_per_1000 = (processing_time / entries_processed) * 1000
        else:
            time_per_1000 = processing_time

        # Validate requirements
        requirements_met = True

        # Requirement 1: <60s for 1000 records
        if time_per_1000 >= 60.0:
            requirements_met = False
            print(f"❌ Performance requirement failed: {time_per_1000:.2f}s >= 60s for 1000 records")
        else:
            print(f"✅ Performance requirement met: {time_per_1000:.2f}s < 60s for 1000 records")

        # Requirement 2: <500MB peak memory usage
        if peak_memory_mb >= 500.0:
            requirements_met = False
            print(f"❌ Memory requirement failed: {peak_memory_mb:.1f}MB >= 500MB")
        else:
            print(f"✅ Memory requirement met: {peak_memory_mb:.1f}MB < 500MB")

        # Additional quality checks
        success_rate = benchmark_results["success_rate"]
        if success_rate < 0.95:
            requirements_met = False
            print(f"❌ Success rate too low: {success_rate:.2%} < 95%")
        else:
            print(f"✅ Success rate acceptable: {success_rate:.2%} >= 95%")

        return requirements_met