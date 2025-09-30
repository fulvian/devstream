# DevStream Dashboard & Monitoring System - Task Planning

**Created**: 2025-09-30
**Status**: Planning Phase
**Methodology**: Research-Driven Development

---

## 📋 Executive Summary

Implementation plan per un Dashboard & Monitoring System completo per DevStream, basato su research-driven approach con Context7 validation e best practices da Prometheus, Grafana, e Flask-Admin.

---

## 🎯 Obiettivi del Task

### Primary Goals
1. **Visual Monitoring Interface** - Dashboard real-time per metriche e stato del sistema
2. **Performance Metrics Display** - Visualizzazione tempi esecuzione hook, utilizzo memoria, performance queries
3. **Memory Search Analytics** - Query patterns analysis, relevance scores tracking, search performance

### Success Criteria
- ✅ Dashboard accessibile via web interface
- ✅ Real-time metrics update (< 5s latency)
- ✅ Performance overhead < 5% sul sistema
- ✅ 95%+ uptime del monitoring system
- ✅ Historical data retention (min 30 giorni)

---

## 🔬 Research Findings (Context7)

### Best Practices Identified

#### 1. **Prometheus Python Client** (`/prometheus/client_python`)
**Trust Score**: 7.4 | **Code Snippets**: 114

**Key Patterns Identified**:
- **Metrics Collection**: Counter, Gauge, Histogram, Summary per tracking granulare
- **Custom Collectors**: `prometheus_client.registry.Collector` per metriche domain-specific
- **Multiprocess Support**: `MultiProcessCollector` per environment multi-processo
- **HTTP Exposition**: `start_http_server()` per metrics endpoint
- **Push Gateway**: Support per batch jobs e short-lived processes

**Applicabilità DevStream**:
```python
# Pattern: Custom Collector per Hook Metrics
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY
from prometheus_client.registry import Collector

class DevStreamHookCollector(Collector):
    def collect(self):
        # Hook execution time gauge
        yield GaugeMetricFamily(
            'devstream_hook_execution_seconds',
            'Hook execution time in seconds',
            value=hook_metrics.get_avg_execution_time()
        )

        # Hook invocation counter
        c = CounterMetricFamily(
            'devstream_hook_invocations_total',
            'Total hook invocations',
            labels=['hook_type', 'status']
        )
        for hook_type, status, count in hook_metrics.get_invocations():
            c.add_metric([hook_type, status], count)
        yield c

REGISTRY.register(DevStreamHookCollector())
```

**Best Practices**:
- ✅ Use Summary for latency tracking (p50, p90, p99 percentiles)
- ✅ Initialize labels early to avoid missing metrics
- ✅ Custom collectors per domain logic complesso
- ✅ Exemplars per trace correlation (se needed)

---

#### 2. **Grafana Integration** (`/grafana/grafana`)
**Trust Score**: 9.7 | **Code Snippets**: 6477

**Key Patterns Identified**:
- **Dashboard API**: POST `/api/dashboards/db` per dashboard creation/update
- **Dashboard as Code**: JSON-based dashboard definitions
- **Folder Organization**: `folderUid` per dashboard organization
- **Version Control**: Message field per commit history tracking
- **Overwrite Support**: Safe dashboard updates con version checking

**Applicabilità DevStream**:
```python
# Pattern: Programmatic Dashboard Creation
import requests
import json

def create_devstream_dashboard(grafana_url, api_token):
    dashboard_spec = {
        "dashboard": {
            "id": None,
            "uid": "devstream-monitoring",
            "title": "DevStream System Monitoring",
            "tags": ["devstream", "monitoring"],
            "timezone": "browser",
            "schemaVersion": 16,
            "refresh": "10s",
            "panels": [
                {
                    "title": "Hook Execution Time",
                    "type": "graph",
                    "targets": [{
                        "expr": "devstream_hook_execution_seconds"
                    }]
                },
                {
                    "title": "Memory Search Performance",
                    "type": "graph",
                    "targets": [{
                        "expr": "devstream_memory_search_duration_seconds"
                    }]
                }
            ]
        },
        "folderUid": "devstream-dashboards",
        "message": "Initial DevStream monitoring dashboard",
        "overwrite": False
    }

    response = requests.post(
        f"{grafana_url}/api/dashboards/db",
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        },
        json=dashboard_spec
    )
    return response.json()
```

**Best Practices**:
- ✅ Dashboard as code per version control
- ✅ Folder organization per logical grouping
- ✅ Refresh intervals appropriati (10s-30s per real-time)
- ✅ Version messages per audit trail

---

#### 3. **Flask-Admin Dashboard** (`/pallets-eco/flask-admin`)
**Trust Score**: 8.0 | **Code Snippets**: 193

**Key Patterns Identified**:
- **BaseView Extension**: Custom views via `BaseView` e `@expose`
- **Theme Support**: Bootstrap4Theme con swatch customization
- **Real-time Updates**: Template-based rendering con AJAX support
- **Custom Actions**: `@action` decorator per batch operations
- **File Management**: FileAdmin per static files management

**Applicabilità DevStream**:
```python
# Pattern: Custom Monitoring View
from flask_admin import BaseView, expose
from flask_admin.theme.bootstrap4 import Bootstrap4Theme

class DevStreamMonitoringView(BaseView):
    @expose('/')
    def index(self):
        # Fetch real-time metrics
        metrics = {
            'hook_metrics': get_hook_metrics(),
            'memory_metrics': get_memory_metrics(),
            'system_health': get_system_health()
        }
        return self.render('devstream_monitoring.html', **metrics)

    @expose('/api/metrics')
    def api_metrics(self):
        # JSON endpoint for AJAX updates
        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': collect_current_metrics()
        })

# Initialize admin with custom theme
admin = Admin(
    app,
    name='DevStream',
    theme=Bootstrap4Theme(swatch='darkly'),
    template_mode='bootstrap4'
)
admin.add_view(DevStreamMonitoringView(
    name='Monitoring',
    endpoint='monitoring'
))
```

**Best Practices**:
- ✅ Custom views per monitoring pages specifiche
- ✅ AJAX endpoints per real-time updates senza page reload
- ✅ Theme customization per branding consistency
- ✅ Template inheritance per UI consistency

---

## 🗄️ DevStream Memory Search Results

**Query**: "monitoring metrics dashboard performance tracking"
**Results**: 10 memories found (LOW relevance)

### Analysis
La ricerca in memoria non ha trovato codice di monitoring esistente in DevStream. Questo conferma che il dashboard è una feature completamente nuova da implementare from scratch.

**Key Observations**:
- ❌ No existing monitoring code
- ❌ No dashboard implementations
- ❌ No metrics collection infrastructure
- ✅ Opportunity per clean implementation seguendo best practices

---

## 🏗️ Architettura Proposta

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                   DevStream Dashboard                    │
│                    (Flask-Admin UI)                      │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Hook        │ │  Memory      │ │  System      │
│  Metrics     │ │  Metrics     │ │  Health      │
│  Collector   │ │  Collector   │ │  Collector   │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  Prometheus      │
              │  Registry        │
              │  (In-Memory)     │
              └──────────────────┘
```

### Technology Stack

**Backend**:
- `prometheus_client` - Metrics collection & exposition
- `Flask` - Web framework per dashboard
- `Flask-Admin` - Admin interface framework
- `SQLAlchemy` (existing) - Metrics persistence

**Frontend**:
- `Bootstrap 4` - UI framework (via Flask-Admin)
- `Chart.js` / `Plotly` - Real-time charts
- `AJAX/Fetch API` - Real-time updates senza reload

**Optional (Future)**:
- `Grafana` - Advanced visualization (se needed)
- `InfluxDB` - Time-series database per historical data

---

## 📦 Implementation Phases

### Phase A: Metrics Collection Infrastructure (2-3 ore)
**Obiettivo**: Implementare Prometheus-based metrics collection

**Micro-Tasks**:
1. Setup Prometheus client e registry (10 min)
2. Implementare HookMetricsCollector (20 min)
3. Implementare MemoryMetricsCollector (20 min)
4. Implementare SystemHealthCollector (20 min)
5. Hook integration nel sistema esistente (30 min)
6. Testing collectors standalone (30 min)

**Deliverables**:
- `devstream/monitoring/collectors.py` - Custom collectors
- `devstream/monitoring/registry.py` - Prometheus registry setup
- `tests/unit/monitoring/test_collectors.py` - Unit tests

---

### Phase B: Flask-Admin Dashboard UI (2-3 ore)
**Obiettivo**: Implementare web interface per monitoring

**Micro-Tasks**:
1. Setup Flask-Admin application (15 min)
2. Create MonitoringView base class (20 min)
3. Implement real-time metrics endpoint (30 min)
4. Design dashboard HTML template (45 min)
5. Integrate Chart.js per visualizations (30 min)
6. Implement AJAX auto-refresh (20 min)
7. Testing UI rendering (20 min)

**Deliverables**:
- `devstream/monitoring/dashboard.py` - Flask-Admin views
- `devstream/monitoring/templates/monitoring.html` - Dashboard template
- `devstream/monitoring/static/` - CSS/JS assets

---

### Phase C: Historical Data & Analytics (2-3 ore)
**Obiettivo**: Persistent storage e trend analysis

**Micro-Tasks**:
1. Design metrics storage schema (20 min)
2. Implement SQLAlchemy models (30 min)
3. Create periodic metrics snapshot job (30 min)
4. Implement historical data queries (30 min)
5. Add trend charts to dashboard (30 min)
6. Testing data persistence (20 min)

**Deliverables**:
- `devstream/monitoring/models.py` - DB models per metrics
- `devstream/monitoring/storage.py` - Persistence layer
- Migration script per schema

---

### Phase D: Advanced Features & Polish (1-2 ore)
**Obiettivo**: Alerting, export, optimization

**Micro-Tasks**:
1. Implement threshold-based alerts (30 min)
2. Add metrics export (CSV/JSON) (20 min)
3. Performance optimization (20 min)
4. Documentation (20 min)
5. End-to-end testing (20 min)

**Deliverables**:
- `devstream/monitoring/alerts.py` - Alert system
- `devstream/monitoring/export.py` - Export functionality
- `docs/guides/monitoring-dashboard.md` - User guide

---

## 📊 Metrics to Track

### Hook System Metrics
```python
# Counter: Total hook invocations
devstream_hook_invocations_total{hook_type="pre_tool_use", status="success"}
devstream_hook_invocations_total{hook_type="pre_tool_use", status="error"}

# Histogram: Hook execution duration
devstream_hook_execution_seconds{hook_type="pre_tool_use", quantile="0.5"}  # p50
devstream_hook_execution_seconds{hook_type="pre_tool_use", quantile="0.9"}  # p90
devstream_hook_execution_seconds{hook_type="pre_tool_use", quantile="0.99"} # p99

# Gauge: Last execution timestamp
devstream_hook_last_execution_timestamp{hook_type="pre_tool_use"}

# Counter: Hook errors by type
devstream_hook_errors_total{hook_type="pre_tool_use", error_type="timeout"}
```

### Memory System Metrics
```python
# Histogram: Search duration
devstream_memory_search_duration_seconds{search_type="hybrid", quantile="0.5"}

# Gauge: Current memory store size
devstream_memory_store_size_bytes
devstream_memory_store_entries_total

# Histogram: Relevance scores distribution
devstream_memory_search_relevance_score{quantile="0.5"}

# Counter: Embedding generation operations
devstream_embeddings_generated_total{model="embeddinggemma:300m"}

# Histogram: Embedding generation time
devstream_embedding_generation_seconds{model="embeddinggemma:300m"}
```

### System Health Metrics
```python
# Gauge: MCP server status
devstream_mcp_server_up{server="devstream"}

# Gauge: Database connection pool
devstream_db_connections_active
devstream_db_connections_idle

# Counter: API requests
devstream_api_requests_total{endpoint="/devstream_search_memory", status="200"}

# Histogram: API response time
devstream_api_response_duration_seconds{endpoint="/devstream_search_memory"}
```

---

## 🧪 Testing Strategy

### Unit Tests
- ✅ Collector initialization e registration
- ✅ Metrics collection logic
- ✅ Dashboard view rendering
- ✅ API endpoint responses

### Integration Tests
- ✅ End-to-end metrics flow (collection → storage → display)
- ✅ Real-time update mechanism
- ✅ Historical data queries
- ✅ Alert triggering

### Performance Tests
- ✅ Metrics collection overhead < 5%
- ✅ Dashboard load time < 2s
- ✅ AJAX update latency < 500ms
- ✅ Historical query performance < 1s

### Real-World Scenarios
- ✅ High-load testing (100+ hook invocations/min)
- ✅ Long-running monitoring (24h+ uptime)
- ✅ Database growth over time
- ✅ Browser compatibility (Chrome, Firefox, Safari)

---

## 🚀 Deployment Considerations

### Configuration
```python
# devstream/monitoring/config.py
MONITORING_CONFIG = {
    'enabled': True,
    'metrics_port': 8000,  # Prometheus metrics endpoint
    'dashboard_port': 8001, # Flask-Admin dashboard
    'update_interval': 10,  # seconds
    'retention_days': 30,
    'alert_thresholds': {
        'hook_execution_max': 5.0,  # seconds
        'memory_search_max': 2.0,   # seconds
        'error_rate_max': 0.05      # 5%
    }
}
```

### Security
- ✅ Authentication per dashboard access (optional)
- ✅ Rate limiting su API endpoints
- ✅ Input validation per query parameters
- ✅ CORS configuration per external access

### Performance
- ✅ Metrics aggregation per ridurre overhead
- ✅ Database indexing per historical queries
- ✅ Caching per frequently accessed metrics
- ✅ Async operations per non-blocking collection

---

## 📚 Dependencies

### New Dependencies Required
```toml
# pyproject.toml additions
[tool.poetry.dependencies]
prometheus-client = "^0.20.0"  # Metrics collection
flask-admin = "^1.6.1"         # Dashboard UI
flask-cors = "^4.0.0"          # CORS support (optional)
```

### Existing Dependencies Used
- `flask` (already in project)
- `sqlalchemy` (already in project)
- `asyncio` (stdlib)

---

## 🎯 Success Metrics

### Functional Requirements
- ✅ Dashboard displays all key metrics
- ✅ Real-time updates working
- ✅ Historical data accessible
- ✅ Alerts triggering correctly

### Performance Requirements
- ✅ < 5% overhead on hook execution
- ✅ < 2s dashboard initial load
- ✅ < 500ms AJAX update latency
- ✅ 95%+ monitoring uptime

### Quality Requirements
- ✅ 95%+ test coverage
- ✅ Zero mypy errors
- ✅ Complete documentation
- ✅ Production-ready code quality

---

## 🔄 Next Steps

### Immediate Actions
1. **Review & Approve Plan** - Discussione e consensus su approach
2. **Setup Development Environment** - Install dependencies
3. **Create Task in DevStream** - Use `devstream_create_task` tool
4. **Begin Phase A Implementation** - Start with metrics collectors

### Future Enhancements (Post-MVP)
- Grafana integration per advanced dashboards
- InfluxDB per long-term metrics storage
- Distributed tracing con OpenTelemetry
- Machine learning per anomaly detection
- Mobile-responsive dashboard design
- Slack/Email notifications per alerts

---

## 📖 References

### Context7 Research
- **Prometheus Python Client**: `/prometheus/client_python` (Trust: 7.4)
- **Grafana**: `/grafana/grafana` (Trust: 9.7)
- **Flask-Admin**: `/pallets-eco/flask-admin` (Trust: 8.0)

### Best Practice Sources
- Prometheus Client Python Documentation
- Grafana Dashboard API Reference
- Flask-Admin Official Documentation
- DevStream CLAUDE.md Methodology

---

**Planning Completed**: 2025-09-30
**Ready for Implementation**: ✅
**Estimated Total Time**: 7-11 hours (4 phases)
**Methodology Compliance**: ✅ Research-Driven Development