# DevStream Project Structure

This document outlines the organized structure of the DevStream project following Python best practices and Context7 research findings.

## 📁 Root Directory Structure

```
devstream/
├── .archive/                    # Archived files (prototypes, deprecated, temp)
├── .benchmarks/                 # Performance benchmarks data
├── .claude/                     # Claude Code session state
├── .config/                     # Tool-specific configurations
├── config/                      # Application configuration files
├── data/                        # Runtime data (databases, logs)
├── docs/                        # Documentation (organized by category)
├── logs/                        # Application logs
├── scripts/                     # Utility scripts
├── src/                         # Source code (src-layout pattern)
├── tests/                       # Test suite (organized by type)
├── CLAUDE.md                    # Claude Code project instructions
├── Makefile                     # Development automation
├── pyproject.toml              # Project configuration and dependencies
├── README.md                   # Project overview and quick start
└── .env                        # Environment variables (not in git)
```

## 📚 Documentation Structure (`docs/`)

Following Context7 best practices for documentation organization:

```
docs/
├── README.md                   # Documentation index and navigation
├── architecture/              # System design and technical decisions
│   ├── architecture.md        # Complete system architecture
│   └── database_schema.sql    # Database schema documentation
├── api/                       # API reference documentation
│   └── json_schemas.json      # JSON schema definitions
├── development/               # Developer guides and methodologies
│   ├── roadmap.md            # Development roadmap
│   └── methodology-example.md # DevStream methodology examples
├── deployment/               # Production deployment guides
├── guides/                   # Practical guides and references
│   └── CLAUDE.quick-reference.md # Claude Code quick reference
├── tutorials/                # Hands-on tutorials
└── idee_fondanti/           # Foundational concepts and vision
    └── idee_fondanti_piano_fondazione.md # Foundation plan
```

## 🧪 Test Structure (`tests/`)

Organized by test type following pytest best practices:

```
tests/
├── conftest.py                # Shared test configuration
├── fixtures/                  # Test fixtures and data
├── unit/                     # Fast, isolated unit tests
│   ├── memory/               # Memory system unit tests
│   └── ollama/               # Ollama integration unit tests
├── integration/              # Integration tests
│   ├── memory/               # Memory system integration tests
│   └── ollama/               # Ollama service integration tests
├── standalone/               # Standalone validation tests
│   ├── test_memory_standalone.py
│   └ test_ollama_standalone.py
└── test_ai_planning_comprehensive.py # Comprehensive AI planning tests
```

## 💻 Source Code Structure (`src/`)

Following Python src-layout pattern for clean imports:

```
src/devstream/
├── __init__.py
├── core/                     # Core abstractions and interfaces
├── database/                 # Database layer and ORM
├── memory/                   # Memory system and embedding search
├── tasks/                    # Task management system
├── planning/                 # AI planning engine
│   ├── models.py            # Pydantic models
│   ├── protocols.py         # Abstract interfaces
│   ├── planner.py           # Core planner implementation
│   ├── validation.py        # Guardrails validation
│   ├── testing.py           # Giskard testing framework
│   └── production_validation.py # Production readiness checks
├── ollama/                   # Ollama client integration
├── hooks/                    # Hook system for automation
└── cli/                      # Command-line interface
```

## 🗄️ Archive Structure (`.archive/`)

Organized deprecated and prototype files:

```
.archive/
├── README.md                 # Archive documentation
├── prototypes/              # Early prototypes and POCs
│   ├── hook_system_api.py   # Early hook system prototype
│   ├── memory_system.py     # Initial memory implementation
│   └── mvp_implementation.py # MVP exploration
├── deprecated/              # Deprecated code (kept for reference)
└── temp/                    # Temporary development artifacts
    └── memory_system_test_results.md
```

## 🔧 Configuration Files

### Core Configuration
- `pyproject.toml` - Project metadata, dependencies, tool configuration
- `CLAUDE.md` - Claude Code project instructions and methodology
- `Makefile` - Development task automation
- `.env` - Environment variables (local development)

### Development Tools
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `.gitignore` - Git ignore patterns
- `.mcp.json` - Model Context Protocol configuration

## 📊 Key Improvements Made

### ✅ Documentation Organization
- **Before**: Scattered `.md` files in root directory
- **After**: Organized in `docs/` with clear categories and navigation

### ✅ Test Organization
- **Before**: Test files mixed in root directory
- **After**: Structured `tests/` with unit/integration/standalone separation

### ✅ Archive Management
- **Before**: Prototype files cluttering root directory
- **After**: Clean `.archive/` with organized prototypes and deprecated files

### ✅ API Documentation
- **Before**: JSON schemas in root directory
- **After**: Organized in `docs/api/` with proper structure

### ✅ Architecture Documentation
- **Before**: Database schema in root directory
- **After**: Moved to `docs/architecture/` with system design docs

## 🎯 Benefits of New Structure

1. **Clean Root Directory**: Essential files only, easy navigation
2. **Logical Documentation**: Category-based organization for easy discovery
3. **Professional Test Structure**: Follows pytest and Python community standards
4. **Historical Preservation**: Prototypes archived but accessible
5. **Deployment Ready**: Structure suitable for production deployment
6. **Developer Friendly**: Clear separation of concerns and responsibilities

## 🚀 Next Steps

This clean structure is now ready for:

1. **Production Deployment**: Clear separation of source/config/docs
2. **Team Collaboration**: Organized structure for multiple developers
3. **CI/CD Integration**: Standard layout for automated testing/deployment
4. **Package Distribution**: Src-layout ready for PyPI publication
5. **Documentation Generation**: Structured docs for automated generation

---

**Structure Validated**: 2025-09-28
**Methodology**: Context7 Research-Driven Best Practices
**Compliance**: Python Community Standards, FastAPI Patterns, pytest Organization