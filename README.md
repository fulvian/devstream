# DevStream: Integrated Task Management & Cross-Session Memory System

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://github.com/yourusername/devstream)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/dependency%20management-poetry-blue.svg)](https://python-poetry.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: ruff](https://img.shields.io/badge/linting-ruff-red.svg)](https://github.com/astral-sh/ruff)
[![Type checking: mypy](https://img.shields.io/badge/type%20checking-mypy-blue.svg)](https://mypy.readthedocs.io/)
[![CI Status](https://img.shields.io/badge/CI-passing-brightgreen.svg)](https://github.com/yourusername/devstream/actions)

A revolutionary framework that transforms user-AI interaction by enforcing a structured workflow based on granular tasks with persistent semantic memory for Claude Code.

## 🎯 Key Features

### Task-Forced Workflow
- **Every user interaction** must flow through task creation
- **Granular micro-tasks**: max 10 minutes, 256K tokens
- **Structured plans**: Goals → Phases → Micro-tasks
- **Automatic validation** to maintain granularity

### Cross-Session Semantic Memory
- **Vector embeddings** with Ollama embeddinggemma
- **Hybrid search** semantic + keyword with weighted scoring
- **Automatic context injection** from relevant memory
- **Incremental learning** from every completed task

### Virtual Agent Team
- **Architect**: System design and technology selection
- **Coder**: Implementation and debugging
- **Reviewer**: Quality assurance and testing
- **Documenter**: Technical writing and API docs

### Advanced Hook System
- **Event-driven**: Hooks on user interaction, task completion, context limits
- **Auto-enforcement**: Enforces task-based workflow
- **Memory automation**: Automatic save and retrieval

## 🛠 Technology Stack

- **Python 3.11+** with complete type hints
- **SQLite + FTS5** for storage and full-text search
- **Ollama + embeddinggemma** for local semantic embeddings
- **Pydantic v2** for data validation and configuration
- **Poetry** for dependency management
- **AsyncIO** for non-blocking operations

## 📚 Development Methodology

DevStream uses a **research-driven methodology** with 4 fundamental phases:

1. **🎯 Discussion & Analysis** - Align on objectives and technical specifications
2. **📋 Structured Division** - Breakdown into phases and granular micro-tasks
3. **🔍 Context7 Research** - Best practices and technical documentation
4. **✅ Verification & Testing** - Rigorous testing and complete validation

### Quick Reference
```bash
# Complete workflow
Discuss → Divide → Research → Implement → Test → Validate

# Main tools
- Context7: Research and best practices
- TodoWrite: Granular task management
- Testing: 95%+ coverage target
```

**Complete details**: See [`CLAUDE.md`](./CLAUDE.md) and [`CLAUDE.quick-reference.md`](./CLAUDE.quick-reference.md)

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.11+
python --version

# Poetry for dependency management
curl -sSL https://install.python-poetry.org | python3 -

# Ollama for embedding generation
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve
ollama pull nomic-embed-text
```

### Installation

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

### First Use

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

### Development Environment Setup

```bash
# Complete development setup
make dev

# Install pre-commit hooks
make install-hooks

# Check environment
make check-env
```

### Development Commands

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

## 📖 Architecture

### Project Structure

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

### Main Components

1. **Database Layer** (`devstream.database`)
   - SQLite with FTS5 and optional vector search
   - Async connection management
   - Schema migrations

2. **Memory System** (`devstream.memory`)
   - Ollama integration for embeddings
   - Hybrid search (semantic + keyword)
   - Context assembly and injection

3. **Task Management** (`devstream.tasks`)
   - InterventionPlan → Phase → MicroTask hierarchy
   - Agent dispatcher with capability matching
   - Task state tracking

4. **Hook System** (`devstream.hooks`)
   - Event-driven automation
   - Claude Code integration
   - Configurable hook chains

## ⚙️ Configuration

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

- **Ollama**: Mock embedding generation for unit tests
- **Database**: In-memory SQLite for fast tests
- **File System**: Temporary directories
- **Time**: Freezegun for time-dependent tests

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
- **Search**: Hybrid search with relevance thresholds
- **Tasks**: Parallel micro-task execution when possible

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

Structured logging with flexible configuration:

```python
import structlog

logger = structlog.get_logger()
logger.info("Task completed", task_id="123", duration_ms=1500)
```

## 🤝 Contributing

### Code Quality Standards

- **Type Hints**: All parameters and return types
- **Docstrings**: Google-style docstrings
- **Testing**: 90%+ coverage for new code
- **Linting**: Automatic pre-commit hooks

### Development Process

1. Fork repository and create feature branch
2. Implement changes with test coverage
3. Run `make check` for code quality
4. Submit pull request with detailed description

### Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat: add semantic search with Ollama integration
fix: resolve memory leak in embedding cache
docs: update configuration examples
test: add integration tests for hook system
```

## 📚 Documentation

- **[Architecture](docs/architecture.md)**: Detailed system design
- **[Database Schema](docs/database.md)**: Schema and migrations
- **[API Reference](docs/api/)**: Complete API documentation
- **[Configuration](docs/configuration.md)**: Configuration options
- **[Deployment](docs/deployment.md)**: Production deployment guide

### Generate Documentation

```bash
# Serve locally with hot reload
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

- **Structured Logging**: JSON logs for aggregation
- **Performance Metrics**: Task completion times, memory usage
- **Health Checks**: Database connectivity, Ollama availability
- **Alerts**: Failed tasks, memory threshold exceeded

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Claude Code Team** for the vision of task-forced workflow
- **Ollama Project** for local embedding capabilities
- **SQLite Team** for FTS5 and performance optimizations
- **Python Community** for excellent typing and async support

---

**Note**: This system represents a paradigm shift in AI development tool interaction, transforming Claude Code from a reactive tool to a proactive project management system with permanent memory.