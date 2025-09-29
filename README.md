# DevStream: Sistema Integrato Task Management & Memoria Cross-Session

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/dependency%20management-poetry-blue.svg)](https://python-poetry.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: ruff](https://img.shields.io/badge/linting-ruff-red.svg)](https://github.com/astral-sh/ruff)
[![Type checking: mypy](https://img.shields.io/badge/type%20checking-mypy-blue.svg)](https://mypy.readthedocs.io/)

Un framework rivoluzionario che trasforma l'interazione utente-AI imponendo un workflow strutturato basato su task granulari con memoria semantica persistente per Claude Code.

## 🎯 Caratteristiche Principali

### Task-Forced Workflow
- **Ogni interazione** utente deve passare attraverso task creation
- **Micro-task granulari**: max 10 minuti, 256K token
- **Piani strutturati**: Obiettivi → Fasi → Micro-task
- **Validazione automatica** per mantenere granularità

### Memoria Semantica Cross-Session
- **Embedding vettoriali** con Ollama embeddinggemma
- **Ricerca ibrida** semantic + keyword con scoring pesato
- **Context injection automatico** dalla memoria rilevante
- **Learning incrementale** da ogni task completato

### Team Virtuale Agenti
- **Architect**: System design e technology selection
- **Coder**: Implementation e debugging
- **Reviewer**: Quality assurance e testing
- **Documenter**: Technical writing e API docs

### Hook System Avanzato
- **Event-driven**: Hook su user interaction, task completion, context limits
- **Auto-enforcement**: Forza workflow task-based
- **Memory automation**: Salvataggio e retrieval automatico

## 🛠 Stack Tecnologico

- **Python 3.11+** con type hints completi
- **SQLite + FTS5** per storage e full-text search
- **Ollama + embeddinggemma** per embedding semantici locali
- **Pydantic v2** per validazione dati e configuration
- **Poetry** per dependency management
- **AsyncIO** per operazioni non-blocking

## 📚 Metodologia di Sviluppo

DevStream utilizza una **metodologia research-driven** con 4 fasi fondamentali:

1. **🎯 Discussione & Analisi** - Confronto su obiettivi e specifiche tecniche
2. **📋 Divisione Strutturata** - Breakdown in fasi e micro-task granulari
3. **🔍 Research Context7** - Best practice e documentazione tecnica
4. **✅ Verification & Testing** - Test severi e validazione completa

### Quick Reference
```bash
# Workflow completo
Discuss → Divide → Research → Implement → Test → Validate

# Tools principali
- Context7: Research e best practice
- TodoWrite: Task management granulare
- Testing: 95%+ coverage target
```

**Dettagli completi**: Vedi [`CLAUDE.md`](./CLAUDE.md) e [`CLAUDE.quick-reference.md`](./CLAUDE.quick-reference.md)

## 🚀 Quick Start

### Prerequisiti

```bash
# Python 3.11+
python --version

# Poetry per dependency management
curl -sSL https://install.python-poetry.org | python3 -

# Ollama per embedding generation
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve
ollama pull nomic-embed-text
```

### Installazione

```bash
# Clone repository
git clone <repository-url>
cd devstream

# Install dependencies
make install

# Setup development environment
make setup

# Verify installation
make check-env
```

### Primo Utilizzo

```bash
# Start DevStream CLI
poetry run devstream --help

# Create your first intervention plan
poetry run devstream plan "Implement REST API for user management"

# Execute micro-task with context injection
poetry run devstream execute <task-id>

# Search semantic memory
poetry run devstream search "authentication patterns"
```

## 📋 Development Workflow

### Setup Ambiente di Sviluppo

```bash
# Complete development setup
make dev

# Install pre-commit hooks
make install-hooks

# Check environment
make check-env
```

### Comandi di Sviluppo

```bash
# Code quality
make format           # Format with black + isort
make lint            # Run ruff + mypy + bandit
make check           # Format + lint

# Testing
make test            # All tests
make test-unit       # Unit tests only
make test-integration # Integration tests
make test-coverage   # Coverage report

# Database
make db-init         # Initialize database
make db-migrate      # Run migrations
make db-reset        # Reset database (⚠️ destroys data)

# Documentation
make docs            # Serve docs locally
make docs-build      # Build static docs
```

### Testing Strategy

```bash
# Unit tests (fast, mocked)
pytest tests/unit -v

# Integration tests (requires Ollama)
pytest tests/integration -m "requires_ollama" -v

# End-to-end tests (requires Docker)
pytest tests/e2e -m "requires_docker" -v

# Performance benchmarks
pytest tests/ --benchmark-only
```

## 📖 Architettura

### Struttura del Progetto

```
devstream/
├── src/devstream/           # Main package
│   ├── core/               # Core abstractions
│   ├── database/           # Database layer
│   ├── memory/             # Memory system
│   ├── tasks/              # Task management
│   ├── hooks/              # Hook system
│   └── cli/                # CLI interface
├── tests/                  # Test suite
├── config/                 # Configuration templates
├── docs/                   # Documentation
└── scripts/                # Utility scripts
```

### Componenti Principali

1. **Database Layer** (`devstream.database`)
   - SQLite con FTS5 e optional vector search
   - Async connection management
   - Schema migrations

2. **Memory System** (`devstream.memory`)
   - Ollama integration per embedding
   - Hybrid search (semantic + keyword)
   - Context assembly e injection

3. **Task Management** (`devstream.tasks`)
   - InterventionPlan → Phase → MicroTask hierarchy
   - Agent dispatcher con capability matching
   - Task state tracking

4. **Hook System** (`devstream.hooks`)
   - Event-driven automation
   - Claude Code integration
   - Configurable hook chains

## ⚙️ Configurazione

### Environment Variables

```bash
# Database
DEVSTREAM_DB_PATH=./data/devstream.db
DEVSTREAM_DB_ENABLE_VECTOR_SEARCH=false

# Ollama
DEVSTREAM_OLLAMA_ENDPOINT=http://localhost:11434
DEVSTREAM_OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Memory
DEVSTREAM_MEMORY_SIMILARITY_THRESHOLD=0.7
DEVSTREAM_MEMORY_MAX_CONTEXT_TOKENS=2000

# Tasks
DEVSTREAM_TASK_MAX_DURATION_MINUTES=10
DEVSTREAM_TASK_FORCE_CREATION=true
```

### Configuration Files

- `config/development.yml` - Development settings
- `config/production.yml` - Production settings
- `config/testing.yml` - Test environment

```bash
# Load configuration
poetry run devstream --config config/development.yml
```

## 🧪 Testing

### Test Categories

- **Unit Tests** (`tests/unit/`) - Fast, isolated, mocked
- **Integration Tests** (`tests/integration/`) - Real Ollama + SQLite
- **End-to-End Tests** (`tests/e2e/`) - Full workflow testing

### Test Markers

```bash
# Run specific test categories
pytest -m "unit"                    # Unit tests only
pytest -m "integration"             # Integration tests
pytest -m "requires_ollama"         # Tests needing Ollama
pytest -m "slow"                    # Long-running tests
pytest -m "not slow"                # Skip slow tests
```

### Mocking Strategy

- **Ollama**: Mock embedding generation per unit tests
- **Database**: In-memory SQLite per fast tests
- **File System**: Temporary directories
- **Time**: Freezegun per time-dependent tests

## 📈 Performance

### Benchmarks

```bash
# Run performance benchmarks
make test-performance

# Memory profiling
make memory-profile

# CPU profiling
make profile
```

### Optimization Guidelines

- **Database**: Use WAL mode, appropriate indexes
- **Memory**: Batch embedding generation, context caching
- **Search**: Hybrid search con relevance thresholds
- **Tasks**: Parallel micro-task execution quando possibile

## 🔍 Debugging

### Debug Tools

```bash
# Show current configuration
make debug-config

# Check dependency tree
make debug-deps

# Environment information
make debug-env

# Database inspection
sqlite3 data/devstream.db ".schema"
```

### Logging

Structured logging con configurazione flessibile:

```python
import structlog

logger = structlog.get_logger()
logger.info("Task completed", task_id="123", duration_ms=1500)
```

## 🤝 Contributing

### Code Quality Standards

- **Type Hints**: Tutti i parametri e return types
- **Docstrings**: Google-style docstrings
- **Testing**: 90%+ coverage per nuovo codice
- **Linting**: Pre-commit hooks automatici

### Development Process

1. Fork repository e create feature branch
2. Implement changes con test coverage
3. Run `make check` per code quality
4. Submit pull request con description dettagliata

### Commit Convention

Usa [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat: add semantic search with Ollama integration
fix: resolve memory leak in embedding cache
docs: update configuration examples
test: add integration tests for hook system
```

## 📚 Documentation

- **[Architecture](docs/architecture.md)**: System design dettagliato
- **[Database Schema](docs/database.md)**: Schema e migrations
- **[API Reference](docs/api/)**: Complete API documentation
- **[Configuration](docs/configuration.md)**: Configuration options
- **[Deployment](docs/deployment.md)**: Production deployment guide

### Generate Documentation

```bash
# Serve locally con hot reload
make docs

# Build static documentation
make docs-build
```

## 🚢 Production Deployment

### Docker

```bash
# Build production image
docker build -t devstream:latest .

# Run with Docker Compose
docker-compose up -d
```

### Environment Variables

```bash
# Production settings
DEVSTREAM_ENVIRONMENT=production
DEVSTREAM_DEBUG=false
DEVSTREAM_DB_PATH=/data/devstream.db
DEVSTREAM_OLLAMA_ENDPOINT=http://ollama:11434
```

### Monitoring

- **Structured Logging**: JSON logs per aggregation
- **Performance Metrics**: Task completion times, memory usage
- **Health Checks**: Database connectivity, Ollama availability
- **Alerts**: Failed tasks, memory threshold exceeded

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Claude Code Team** per la vision del task-forced workflow
- **Ollama Project** per local embedding capabilities
- **SQLite Team** per FTS5 e performance optimizations
- **Python Community** per excellent typing e async support

---

**Nota**: Questo sistema rappresenta un paradigm shift nell'interazione con AI development tools, trasformando Claude Code da tool reattivo a sistema proattivo di project management con memoria permanente.