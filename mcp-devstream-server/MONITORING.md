# DevStream Monitoring & Observability

**Context7-Compliant Production Monitoring**
**Version**: 1.0
**Status**: ✅ Production Ready
**Date**: 2025-09-30

---

## 📋 Executive Summary

DevStream features a **production-ready monitoring system** with:

- **Performance Metrics** via prom-client (Prometheus-compatible)
- **Search Quality Tracking** with IR metrics (MRR, Recall@K)
- **Error Tracking** with categorization and severity levels
- **HTTP Metrics Endpoint** for Prometheus scraping
- **Real-time Dashboards** support (Grafana-ready)

**Key Features:**
- 20+ custom metrics for hybrid search monitoring
- Automatic quality assessment for search results
- Error categorization and alerting thresholds
- HTTP endpoint on port 9090 (/metrics)
- JSON API for programmatic access

---

## 🏗️ Architecture

### Metrics Collection Flow

```
┌─────────────────────────────────────────────────────────┐
│              HybridSearchEngine                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │  MetricsCollector.trackQuery('hybrid', async()=>  │  │
│  │    ├─ Query Duration Histogram                    │  │
│  │    ├─ Active Queries Gauge                        │  │
│  │    └─ Query Counter                               │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │  QualityMetricsCollector.analyzeResults()        │  │
│  │    ├─ Top Result Score Histogram                  │  │
│  │    ├─ Result Diversity Gauge                      │  │
│  │    ├─ Hybrid Coverage Gauge                       │  │
│  │    └─ Zero Results Counter                        │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│          Prometheus Metrics Registry                     │
│  ┌─ Performance Metrics (histograms, counters, gauges)  │
│  ├─ Quality Metrics (search quality, diversity, MRR)    │
│  └─ Error Metrics (by category, severity, operation)    │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│          HTTP Metrics Server (Port 9090)                 │
│  GET /metrics        → Prometheus format                 │
│  GET /metrics/json   → JSON format                       │
│  GET /health         → Health check                      │
│  GET /quality        → Quality summary                   │
│  GET /errors         → Error statistics                  │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Available Metrics

### Performance Metrics

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `devstream_query_duration_seconds` | Histogram | `query_type`, `status` | Query execution time |
| `devstream_queries_total` | Counter | `query_type`, `status` | Total query count |
| `devstream_active_queries` | Gauge | `query_type` | Currently executing queries |
| `devstream_embedding_generation_duration_seconds` | Histogram | `status`, `model` | Embedding generation time |
| `devstream_database_operations_total` | Counter | `operation`, `status` | Database operations |
| `devstream_query_results_count` | Histogram | `query_type` | Number of results returned |
| `devstream_rrf_score` | Histogram | - | RRF combined ranking scores |

### Quality Metrics

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `devstream_search_quality_score` | Histogram | `query_type` | Top result quality (RRF score) |
| `devstream_zero_results_total` | Counter | `query_type` | Queries with no results |
| `devstream_result_diversity` | Gauge | `query_type` | Unique content types in results |
| `devstream_hybrid_coverage` | Gauge | - | % results from both methods |
| `devstream_mean_reciprocal_rank` | Histogram | - | MRR across queries |
| `devstream_recall_at_k` | Histogram | `k_value` | Recall@K metrics |
| `devstream_query_length_chars` | Histogram | `query_type` | Query length distribution |

### Error Metrics

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `devstream_errors_total` | Counter | `category`, `severity`, `operation` | Errors by type |

**Error Categories:** `database`, `embedding`, `vector_search`, `fts_search`, `validation`, `network`, `unknown`
**Severity Levels:** `low`, `medium`, `high`, `critical`

### Index Health Metrics

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `devstream_vector_index_size` | Gauge | - | vec0 index size |
| `devstream_fts5_index_size` | Gauge | - | FTS5 index size |
| `devstream_memory_storage_total` | Counter | `content_type`, `has_embedding` | Memories stored |

---

## 🚀 Usage

### Starting the Metrics Server

```typescript
import { globalMetricsServer } from './monitoring/metrics-server.js';

// Start server on default port 9090
await globalMetricsServer.start();

// Or with custom port
import { MetricsServer } from './monitoring/metrics-server.js';
const server = new MetricsServer({ port: 8080 });
await server.start();
```

### Accessing Metrics

```bash
# Prometheus format (for scraping)
curl http://localhost:9090/metrics

# JSON format (for programmatic access)
curl http://localhost:9090/metrics/json

# Health check
curl http://localhost:9090/health

# Quality metrics summary
curl http://localhost:9090/quality

# Error statistics
curl http://localhost:9090/errors
```

### Querying Metrics (PromQL Examples)

```promql
# Average query duration by type
rate(devstream_query_duration_seconds_sum[5m]) / rate(devstream_query_duration_seconds_count[5m])

# Query success rate
rate(devstream_queries_total{status="success"}[5m]) / rate(devstream_queries_total[5m])

# Top result quality (95th percentile)
histogram_quantile(0.95, rate(devstream_search_quality_score_bucket[5m]))

# Zero result rate
rate(devstream_zero_results_total[5m]) / rate(devstream_queries_total[5m])

# Error rate by severity
sum(rate(devstream_errors_total[5m])) by (severity)
```

---

## 🎯 Monitoring Best Practices

### Key Metrics to Watch

1. **Query Success Rate**: Should be >99%
   ```promql
   rate(devstream_queries_total{status="success"}[5m]) / rate(devstream_queries_total[5m])
   ```

2. **P95 Query Latency**: Should be <200ms
   ```promql
   histogram_quantile(0.95, rate(devstream_query_duration_seconds_bucket[5m]))
   ```

3. **Zero Result Rate**: Should be <5%
   ```promql
   rate(devstream_zero_results_total[5m]) / rate(devstream_queries_total[5m])
   ```

4. **Critical Errors**: Should be 0
   ```promql
   rate(devstream_errors_total{severity="critical"}[5m])
   ```

5. **Hybrid Coverage**: Should be >50% for good hybrid performance
   ```promql
   devstream_hybrid_coverage
   ```

### Alert Rules (Prometheus)

```yaml
groups:
  - name: devstream_alerts
    rules:
      - alert: HighQueryLatency
        expr: histogram_quantile(0.95, rate(devstream_query_duration_seconds_bucket[5m])) > 0.2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High query latency detected"
          description: "P95 query latency is {{ $value }}s (threshold: 0.2s)"

      - alert: HighZeroResultRate
        expr: rate(devstream_zero_results_total[5m]) / rate(devstream_queries_total[5m]) > 0.1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High zero-result rate"
          description: "{{ $value | humanizePercentage }} of queries return no results"

      - alert: CriticalErrors
        expr: rate(devstream_errors_total{severity="critical"}[5m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Critical errors detected"
          description: "{{ $value }} critical errors per second"

      - alert: LowHybridCoverage
        expr: devstream_hybrid_coverage < 30
        for: 15m
        labels:
          severity: info
        annotations:
          summary: "Low hybrid search coverage"
          description: "Only {{ $value }}% of results matched by both methods"
```

---

## 📈 Grafana Dashboard

### Sample Dashboard JSON

Create a Grafana dashboard with these panels:

**Panel 1: Query Rate**
```json
{
  "targets": [{
    "expr": "rate(devstream_queries_total[5m])",
    "legendFormat": "{{query_type}} - {{status}}"
  }]
}
```

**Panel 2: Query Duration P50/P95/P99**
```json
{
  "targets": [
    {"expr": "histogram_quantile(0.50, rate(devstream_query_duration_seconds_bucket[5m]))", "legendFormat": "p50"},
    {"expr": "histogram_quantile(0.95, rate(devstream_query_duration_seconds_bucket[5m]))", "legendFormat": "p95"},
    {"expr": "histogram_quantile(0.99, rate(devstream_query_duration_seconds_bucket[5m]))", "legendFormat": "p99"}
  ]
}
```

**Panel 3: Search Quality Score**
```json
{
  "targets": [{
    "expr": "histogram_quantile(0.50, rate(devstream_search_quality_score_bucket[5m]))",
    "legendFormat": "{{query_type}}"
  }]
}
```

**Panel 4: Error Rate by Severity**
```json
{
  "targets": [{
    "expr": "sum(rate(devstream_errors_total[5m])) by (severity)",
    "legendFormat": "{{severity}}"
  }]
}
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Metrics server port
METRICS_PORT=9090

# Enable/disable default Node.js metrics
COLLECT_DEFAULT_METRICS=true
```

### Prometheus Configuration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'devstream'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:9090']
```

---

## 🐛 Troubleshooting

### Metrics Not Showing

**Issue**: Metrics endpoint returns empty or missing metrics
**Solution**:
1. Ensure metrics server is started: `await globalMetricsServer.start()`
2. Perform some queries to generate metrics
3. Check metrics are registered: `await getMetrics()`

### High Memory Usage

**Issue**: Metrics collection causing memory growth
**Solution**:
1. Reduce histogram bucket count for high-cardinality metrics
2. Increase Prometheus scrape interval (currently 15s)
3. Use aggregation rules in Prometheus to reduce retention

### Missing Custom Metrics

**Issue**: Only default Node.js metrics visible
**Solution**:
1. Verify metrics are being incremented in code
2. Check metrics are registered to `metricsRegistry`
3. Ensure metric names follow Prometheus naming conventions

---

## ✅ Deployment Checklist

- [x] Metrics collection implemented (Performance, Quality, Errors)
- [x] HTTP metrics server created (port 9090)
- [x] Prometheus-compatible /metrics endpoint
- [x] JSON API for programmatic access
- [x] Health check endpoint
- [x] Error tracking with categorization
- [x] Quality metrics (MRR, Recall@K, diversity)
- [x] Alert threshold configuration
- [ ] Grafana dashboard JSON (user-customizable)
- [ ] Prometheus scrape config (user-configurable)
- [ ] Alertmanager rules (optional)

---

**Status**: ✅ **PRODUCTION READY**
**Generated**: 2025-09-30
**Context7 Compliant**: Yes
**Version**: 1.0