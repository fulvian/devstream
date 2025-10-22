# Multi-Project Architecture Guide

**DevStream Multi-Project System - Complete Architecture Overview**

---

## 🎯 Overview

DevStream's multi-project architecture allows you to work with multiple independent projects, each with its own configuration, database, and provider settings. You can launch DevStream from any project directory and choose between AI providers.

---

## 🏗️ Architecture Components

### 1. Global Installation (`~/.devstream/`)
- **CLI Tools**: Command-line interface for project management
- **Templates**: Project templates and configuration patterns
- **Registry**: Global project registry tracking all DevStream projects

### 2. Project Isolation (`.devstream/` per project)
- **Database**: Independent SQLite database per project
- **Configuration**: Project-specific settings and provider choice
- **Workspace Metadata**: Project information and type detection
- **Logs**: Project-specific activity logs

### 3. Universal Launcher
- **Location**: `/Users/fulvioventura/devstream/scripts/simple-launcher.sh`
- **Function**: Launch DevStream from any project directory
- **Providers**: Supports both Anthropic Claude and z.ai GLM-4.6

---

## 🚀 Quick Start

### Step 1: Global Installation (One Time)
```bash
# Install DevStream globally
bash /Users/fulvioventura/devstream/scripts/install-devstream-global.sh

# Verify installation
~/.devstream/bin/devstream --version
```

### Step 2: Initialize New Project
```bash
# Navigate to your project
cd /path/to/your-project

# Initialize DevStream (creates database, workspace, and CLAUDE.md)
python3 /Users/fulvioventura/devstream/scripts/devstream-init.py .

# Verify initialization
ls -la .devstream/
ls -la data/devstream.db
ls -la CLAUDE.md
```

**What gets created automatically:**
- ✅ **Project Database**: `data/devstream.db` with memory tables
- ✅ **Workspace Metadata**: `.devstream/workspace.json` with project info
- ✅ **CLAUDE.md**: Complete DevStream protocol adapted for your project
- ✅ **Project Type Detection**: Python, TypeScript, Go, Rust, Java support
- ✅ **Codebase Scanning**: Automatic analysis of existing code

### Step 3: Launch DevStream
```bash
# From your project directory, choose provider:

# Option 1: Anthropic Claude (Sonnet 4.5)
/Users/fulvioventura/devstream/scripts/simple-launcher.sh start anthropic

# Option 2: z.ai GLM-4.6
/Users/fulvioventura/devstream/scripts/simple-launcher.sh start z.ai
```

---

## 📋 Project Management Commands

### Global Project Registry
```bash
# List all DevStream projects
~/.devstream/bin/devstream list

# Show current project status
~/.devstream/bin/devstream status

# Detect project in current directory
~/.devstream/bin/devstream detect
```

### Provider Management
```bash
# Set provider for current project
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py set-provider anthropic .

# Get current provider
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py get-provider .

# Show project configuration
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py show .
```

---

## 🔧 Configuration

### Project Structure
```
your-project/
├── .devstream/
│   ├── db/
│   │   └── devstream.db          # Project database (with vector search)
│   ├── config/
│   │   └── config.json           # Project settings
│   ├── workspace.json            # Project metadata (auto-detected type)
│   ├── logs/                     # Project logs
│   └── templates/                # Project templates
├── data/
│   └── devstream.db              # Project database (Direct DB Architecture)
├── CLAUDE.md                     # Complete DevStream protocol (project-adapted)
└── your-source-code/
```

### Key Files Created

**`CLAUDE.md`** - Project-specific DevStream protocol:
- Complete 7-step workflow
- All system rules and agent delegation
- Project-specific paths and commands
- Automatically updated with latest DevStream version

**`data/devstream.db`** - Project database:
- Direct DB Architecture (no MCP server required)
- Vector search with sqlite-vec
- Memory tables for semantic search
- Project isolation (no data sharing)

**`.devstream/workspace.json`** - Project metadata:
```json
{
  "name": "your-project",
  "project_type": "python",  // auto-detected
  "created": "2025-10-14T...",
  "files_count": 15,         // from codebase scan
  "version": "2.2.0"
}
```

### Provider Configuration
Each project can have its own provider:

**Anthropic Claude**:
- Model: Sonnet 4.5
- Authentication: OAuth via Claude Code CLI
- Best for: Complex reasoning, architecture

**z.ai GLM-4.6**:
- Model: GLM-4.6
- Authentication: API key (ZAI_API_KEY)
- Best for: Fast implementation, cost-effective

### Environment Variables
```bash
# DevStream environment (in /Users/fulvioventura/devstream/.env)
ZAI_API_KEY=your-api-key-here
DEVSTREAM_DEBUG=false
DEVSTREAM_LOG_LEVEL=INFO
```

---

## 🧪 Testing and Validation

### Integration Test
```bash
# Run complete system test
/Users/fulvioventura/devstream/scripts/test-multi-project.sh
```

### Manual Verification
```bash
# From any project directory:
cd /path/to/project

# 1. Verify initialization
ls -la .devstream/

# 2. Check database
ls -la .devstream/db/devstream.db

# 3. Test launcher
/Users/fulvioventura/devstream/scripts/simple-launcher.sh start anthropic
```

---

## 🔄 Workflow Examples

### Example 1: New Python Project
```bash
# Create project
mkdir my-new-project
cd my-new-project

# Add some Python code
echo "print('Hello, World!')" > main.py
mkdir tests
echo "def test_main(): assert main() == 'Hello, World!'" > tests/test_main.py

# Initialize DevStream (auto-detects Python type, scans codebase)
python3 /Users/fulvioventura/devstream/scripts/devstream-init.py .

# Results:
# ✅ Project type detected: python
# ✅ Database created: data/devstream.db
# ✅ CLAUDE.md created: Complete protocol with Python-specific commands
# ✅ Codebase scanned: 2 files found
# ✅ Workspace metadata: Python project with 2 files

# Choose provider and start
/Users/fulvioventura/devstream/scripts/simple-launcher.sh start z.ai
```

### Example 2: Switching Providers
```bash
# Currently using Anthropic, want to switch to z.ai
cd my-existing-project

# Change provider
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py set-provider z.ai .

# Launch with new provider
/Users/fulvioventura/devstream/scripts/simple-launcher.sh start z.ai
```

### Example 3: Multiple Projects
```bash
# Project A with Anthropic
cd ~/project-a
/Users/fulvioventura/devstream/scripts/simple-launcher.sh start anthropic

# Project B with z.ai
cd ~/project-b
/Users/fulvioventura/devstream/scripts/simple-launcher.sh start z.ai

# Each project maintains its own configuration and database
```

---

## 🛠️ Troubleshooting

### Common Issues

**1. "Database not found" error**
```bash
# Initialize database manually
cd your-project
mkdir -p .devstream/db
sqlite3 .devstream/db/devstream.db "CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, content_type TEXT NOT NULL, keywords TEXT, embedding BLOB, metadata TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
```

**2. "ZAI_API_KEY not found" error**
```bash
# Add API key to DevStream environment
echo "ZAI_API_KEY='your-api-key'" >> /Users/fulvioventura/devstream/.env
```

**3. "Global CLI not found" error**
```bash
# Reinstall global tools
bash /Users/fulvioventura/devstream/scripts/install-devstream-global.sh
```

**4. Launcher script blocked**
```bash
# Use the simplified launcher
/Users/fulvioventura/devstream/scripts/simple-launcher.sh start anthropic
```

**5. Missing CLAUDE.md or outdated version**
```bash
# Reinitialize to update CLAUDE.md with latest protocol
python3 /Users/fulvioventura/devstream/scripts/devstream-init.py . --force

# This overwrites CLAUDE.md with the latest DevStream protocol
# and adapts all paths to your current project
```

### Verification Commands
```bash
# Check global installation
ls -la ~/.devstream/bin/

# Check project initialization
ls -la .devstream/workspace.json

# Check database
ls -la .devstream/db/devstream.db

# Check provider
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py get-provider .
```

---

## 🎯 Best Practices

### 1. Project Organization
- Each project should have its own `.devstream` directory
- Use descriptive project names during initialization
- Keep project-specific configurations in the project directory

### 2. Provider Choice
- Use **Anthropic** for complex architectural work
- Use **z.ai** for implementation and testing
- Switch providers based on task requirements

### 3. Database Management
- Each project has its own database - no data sharing between projects
- Databases are created automatically during initialization
- Regular backups recommended for important projects

### 4. Environment Management
- Global API keys stored in `/Users/fulvioventura/devstream/.env`
- Project-specific settings in `.devstream/config/`
- Provider choice is per-project, not global

---

## 📚 Reference

### File Locations
- **Global Installation**: `~/.devstream/`
- **DevStream Source**: `/Users/fulvioventura/devstream/`
- **Launcher Script**: `/Users/fulvioventura/devstream/scripts/simple-launcher.sh`
- **Initialization Script**: `/Users/fulvioventura/devstream/scripts/devstream-init.py`
- **Configuration Script**: `/Users/fulvioventura/devstream/scripts/devstream-config.py`

### Key Scripts
- `install-devstream-global.sh` - Global installation
- `devstream-init.py` - Project initialization
- `simple-launcher.sh` - Universal launcher
- `test-multi-project.sh` - Integration testing
- `devstream-config.py` - Configuration management

### Database Schema (Direct DB Architecture)
```sql
-- Memory table for semantic search
CREATE TABLE memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL,
    keywords TEXT,
    embedding BLOB,              -- Vector embeddings for semantic search
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Semantic memory table (compatibility)
CREATE TABLE semantic_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL,
    keywords TEXT,
    embedding BLOB,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_memory_content_type ON memory(content_type);
CREATE INDEX idx_memory_created_at ON memory(created_at);
CREATE INDEX idx_semantic_memory_content_type ON semantic_memory(content_type);
```

### Advanced Features

**🤖 Agent System (17 Specialist Agents)**
- `@tech-lead` - Multi-stack orchestration
- `@python-specialist` - Python 3.11+, FastAPI, async
- `@typescript-specialist` - TypeScript, React, Next.js
- `@database-specialist` - PostgreSQL, MySQL, SQLite
- `@code-reviewer` - MANDATORY quality gates
- ...and 12 more specialized agents

**🧠 Memory System**
- Vector search with Ollama embeddings
- Hybrid semantic + keyword search
- Automatic code context storage
- Project-specific memory isolation

**📋 Protocol Enforcement**
- 7-step mandatory workflow
- Context7 integration for research
- TodoWrite task tracking
- Quality gates with 95%+ coverage requirement

---

**🎉 Your multi-project DevStream architecture is now ready!**

You can work with multiple projects, each with its own configuration and provider choices, all launched from their respective project directories.