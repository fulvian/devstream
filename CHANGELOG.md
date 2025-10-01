# Changelog

All notable changes to DevStream will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- CI/CD pipeline automation
- Automated migration system
- Performance profiling tools
- Additional language specialists (Java, C++, PHP)

---

## [0.1.0-beta] - 2025-10-01

### 🎉 Initial Beta Release

First public beta release of DevStream - AI-Assisted Development Workflow System.

### Added

#### Core System
- **Task Lifecycle Management**: Complete intervention planning system with phases, micro-tasks, and progress tracking
- **Semantic Memory System**: Vector-based memory storage with hybrid search (RRF algorithm combining semantic + keyword search)
- **Context Injection**: Automatic context assembly from Context7 documentation + DevStream memory with token budget management
- **Hook System**: Three core hooks (PreToolUse, PostToolUse, UserPromptSubmit) with graceful degradation and non-blocking execution

#### Agent System (8 Agents)
- **Orchestrator**: `@tech-lead` - Multi-stack coordination and architectural decisions
- **Domain Specialists** (6):
  - `@python-specialist` - Python 3.11+, FastAPI, async, pytest
  - `@typescript-specialist` - TypeScript, React, Next.js, Server Components
  - `@rust-specialist` - Ownership, async/await, memory safety
  - `@go-specialist` - Goroutines, channels, cloud-native
  - `@database-specialist` - PostgreSQL/MySQL/SQLite, schema design, query optimization
  - `@devops-specialist` - Docker, Kubernetes, CI/CD, IaC
- **Quality Assurance**: `@code-reviewer` - OWASP Top 10, performance analysis (mandatory before commits)

#### Database
- SQLite 3 with extensions (sqlite-vec for vector search, FTS5 for full-text search)
- 14 core tables (intervention_plans, phases, micro_tasks, semantic_memory, agents, hooks, work_sessions, etc.)
- Virtual tables for vector search (vec_semantic_memory) and keyword search (fts_semantic_memory)
- 3 automatic sync triggers for memory consistency
- 37 performance indexes

#### MCP Server
- 6 MCP tools for Claude Code integration:
  - `devstream_list_tasks` - List and filter tasks
  - `devstream_create_task` - Create new tasks with auto-infrastructure
  - `devstream_update_task` - Update task status and properties
  - `devstream_list_plans` - List intervention plans
  - `devstream_store_memory` - Manual memory storage
  - `devstream_search_memory` - Hybrid search with RRF
- TypeScript implementation with async operations
- Ollama integration for embedding generation (embeddinggemma:300m, 768 dimensions)

#### Installation System
- **install.sh**: Automated installation script with prerequisites check
- **scripts/setup-db.py**: Database initialization from schema.sql
- **scripts/scan-codebase.py**: Async codebase scanner with progress tracking (scans docs/ + source code)
- **scripts/verify-install.py**: 21 post-installation checks across 5 categories

#### Documentation (Complete English Documentation)
- **User Guide** (6 files): getting-started, core-concepts, configuration, agents-guide, troubleshooting, faq
- **Developer Guide** (7 files): architecture, setup-development, testing, hook-system, mcp-server, release-process, README
- **API Reference** (3 files): mcp-tools, database-schema, hooks-api
- **Tutorials** (4 files): first-project, existing-project, custom-agent, multi-stack-workflow
- **GitHub Standards**: CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md
- **Installation Guide**: INSTALLATION.md with quick start and troubleshooting

#### Configuration
- `.env.devstream`: Environment-based configuration with 20+ options
- Memory system controls (enable/disable, feedback level)
- Context7 integration (auto-detect, token budget)
- Context injection (relevance threshold, max tokens)
- Ollama settings (base URL, model, timeout)
- Logging configuration (level, path)

### Features

#### Automatic Features (No User Intervention Required)
- **Memory Storage**: PostToolUse hook automatically stores code, documentation, context, outputs, errors, decisions, learnings
- **Context Injection**: PreToolUse hook automatically injects Context7 docs + DevStream memory with priority ordering
- **Context7 Detection**: Automatic library detection from imports, mentions, code patterns
- **Infrastructure Creation**: Tasks automatically create phases, agents, and supporting records
- **Hybrid Search**: RRF algorithm combines semantic (60%) + keyword (40%) search for optimal relevance

#### 7-Step Mandatory Workflow
1. **DISCUSSION**: Present problem, discuss trade-offs, identify constraints
2. **ANALYSIS**: Analyze codebase patterns, identify files to modify
3. **RESEARCH**: Use Context7 for best practices, document findings
4. **PLANNING**: Create TodoWrite list, define micro-tasks (10-15 min)
5. **APPROVAL**: Present plan, get explicit approval
6. **IMPLEMENTATION**: One micro-task at a time, mark progress
7. **VERIFICATION/TEST**: Test every feature, 95%+ coverage

#### Research-Driven Development
- Context7 integration for up-to-date library documentation
- Hybrid context assembly (official docs + memory + current context)
- Token budget management (Context7: 5000 tokens, Memory: 2000 tokens)
- Automatic library detection and documentation retrieval

#### Quality Standards
- **Type Safety**: Full type hints, mypy --strict compliance (zero errors)
- **Test Coverage**: 95%+ for new code, 100% pass rate before commits
- **Code Quality**: Max function length 50 lines, max cyclomatic complexity 10, SOLID principles
- **Documentation**: Docstrings for all public APIs, inline comments for complex logic

### Technical Specifications

#### Performance Characteristics
- **Memory Search**: <50ms for hybrid search (10 results)
- **Context Injection**: <200ms for Context7 + Memory assembly
- **Hook Execution**: <100ms for lightweight hooks
- **Embedding Generation**: ~1-2s per batch (10 items via Ollama)
- **Database Queries**: <10ms with proper indexing

#### Dependencies
- **Python**: 3.11+ (type hints, async/await, structural pattern matching)
- **Node.js**: 16+ (MCP server)
- **SQLite**: 3.35+ (vec0 extension optional, FTS5 required)
- **Ollama**: Optional (embeddings generation, graceful degradation if unavailable)
- **Claude Code**: Required (hook system, MCP integration)

#### Tested Environments
- macOS 14+ (Darwin 24.5.0)
- Python 3.11.13
- Node.js 16+
- SQLite 3.43+

### Known Limitations

- **Beta Software**: Not recommended for production-critical projects
- **Local Only**: No cloud synchronization or remote collaboration features
- **Single User**: Designed for individual developer workflows
- **Manual Updates**: No automatic update mechanism (manual git pull required)
- **Limited Language Support**: 6 language specialists (Python, TypeScript, Rust, Go, SQL, DevOps)
- **Ollama Optional**: Embeddings generation requires local Ollama installation (graceful degradation if unavailable)

### Breaking Changes

N/A - Initial release

### Security

- Local execution model (no remote API exposure)
- File-based SQLite database (user responsible for file permissions)
- Hooks execute with user permissions (sandboxed to user account)
- Ollama integration is local-only by default
- Context7 integration transmits library names only (no code or sensitive data)

See [SECURITY.md](SECURITY.md) for complete security policy.

### Migration Guide

N/A - Initial release

For future migrations, see [docs/developer-guide/release-process.md](docs/developer-guide/release-process.md)

---

## Version History

- **0.1.0-beta** (2025-10-01) - Initial beta release

---

## How to Upgrade

### From Source (Beta Phase)

```bash
# 1. Backup database
cp data/devstream.db data/devstream.db.backup

# 2. Pull latest version
git pull origin main

# 3. Reinstall dependencies
.devstream/bin/pip install -r requirements.txt --upgrade

# 4. Rebuild MCP server
cd mcp-devstream-server
npm install
npm run build

# 5. Verify installation
cd ..
./scripts/verify-install.py
```

---

## Links

- [Documentation](docs/)
- [Installation Guide](INSTALLATION.md)
- [Contributing](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)
- [GitHub Repository](https://github.com/yourusername/devstream)

---

**Note**: This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format and [Semantic Versioning](https://semver.org/spec/v2.0.0.html) principles.
