# DevStream Multi-Project Setup Guide

## Overview

DevStream supports multi-project environments where each project maintains its own database and task management system. This guide explains how to configure and use DevStream across multiple projects.

## Problem Solved

**Issue**: In multi-project setups, hooks were always using the DevStream main project database instead of the current project's database.

**Solution**: Updated hook configuration to use the current working directory for database operations.

## Configuration

### 1. Settings Configuration

Update `.claude/settings.json` in each project to include:

```json
{
  "env": {
    "DEVSTREAM_DB_PATH": "data/devstream.db",
    "DEVSTREAM_PROJECT_ROOT": "."
  },
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"$DEVSTREAM_PROJECT_ROOT\" && ./.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/context/user_query_context_enhancer.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

### 2. Key Changes Made

1. **Added `DEVSTREAM_PROJECT_ROOT`: "."** - Points to current working directory
2. **Updated hook commands** - All hooks now use `cd "$DEVSTREAM_PROJECT_ROOT"` before execution
3. **Maintained `CLAUDE_PROJECT_DIR`** - Still points to DevStream installation for hook scripts

## How It Works

### Database Path Resolution

The direct client uses this priority order for database path resolution:

1. **Explicit db_path** parameter (programmatic usage)
2. **`DEVSTREAM_DB_PATH`** environment variable
3. **Default**: `"data/devstream.db"` (relative to project root)

### Project Root Resolution

When resolving relative paths, the client uses:

1. **`DEVSTREAM_PROJECT_ROOT`** environment variable (current directory)
2. **Fallback**: Current working directory (`os.getcwd()`)

### Hook Execution

Hooks execute with this pattern:
```bash
cd "$DEVSTREAM_PROJECT_ROOT" && ./.devstream/bin/python "$CLAUDE_PROJECT_DIR"/.claude/hooks/devstream/...
```

This ensures:
- Hook runs from current project directory
- Database operations use current project's database
- Hook scripts are loaded from DevStream installation

## Setup Requirements

### For Each Project

1. **Virtual Environment**: Each project needs `.devstream/bin/python`
2. **Database Directory**: Ensure `data/` directory exists
3. **DevStream Hooks**: Copy or link to DevStream hook scripts

### Directory Structure

```
project-a/
├── .claude/settings.json     # Project-specific settings
├── .devstream/               # Project virtual environment
├── data/devstream.db        # Project database
└── (project files)

project-b/
├── .claude/settings.json     # Project-specific settings
├── .devstream/               # Project virtual environment
├── data/devstream.db        # Project database
└── (project files)

devstream/                    # DevStream installation
├── .claude/hooks/devstream/  # Hook scripts
└── (DevStream core files)
```

## Testing Multi-Project Setup

### Verify Database Isolation

```bash
# From project-a
cd project-a
python -c "
from direct_client import get_direct_client
client = get_direct_client()
print(f'Database: {client.db_path}')
"

# From project-b
cd project-b
python -c "
from direct_client import get_direct_client
client = get_direct_client()
print(f'Database: {client.db_path}')
"
```

Expected output:
```
project-a: Database: /path/to/project-a/data/devstream.db
project-b: Database: /path/to/project-b/data/devstream.db
```

### Test Task Creation

```bash
# From project-a
cd project-a
python -c "
import asyncio
from direct_client import get_direct_client

async def test():
    client = get_direct_client()
    result = await client.create_task(
        title='Project A Task',
        description='Test task for project A',
        task_type='testing',
        priority=5,
        phase_name='Testing'
    )
    print(f'Task created: {result.get(\"task_id\")}')

asyncio.run(test())
"
```

## Troubleshooting

### Common Issues

1. **Tasks saved in wrong database**
   - Check `DEVSTREAM_PROJECT_ROOT` environment variable
   - Verify working directory when running commands

2. **Hook execution failures**
   - Ensure `.devstream/bin/python` exists in current project
   - Check hook script paths in settings.json

3. **Database permission errors**
   - Verify `data/` directory exists and is writable
   - Check SQLite file permissions

### Debug Commands

```bash
# Check current environment
echo "DEVSTREAM_PROJECT_ROOT: $DEVSTREAM_PROJECT_ROOT"
echo "DEVSTREAM_DB_PATH: $DEVSTREAM_DB_PATH"
echo "Current directory: $(pwd)"

# Test database connection
python -c "
import os
from direct_client import get_direct_client
client = get_direct_client()
print(f'Database path: {client.db_path}')
print(f'Health check: {client.health_check()}')
"
```

## Migration Guide

### From Single-Project to Multi-Project

1. **Update settings.json** in each project:
   ```json
   {
     "env": {
       "DEVSTREAM_PROJECT_ROOT": "."
     }
   }
   ```

2. **Update hook commands** to use `cd "$DEVSTREAM_PROJECT_ROOT"`

3. **Create virtual environments** for each project:
   ```bash
   python3.11 -m venv .devstream
   .devstream/bin/pip install -r requirements.txt
   ```

4. **Initialize databases** for each project:
   ```bash
   mkdir -p data
   # Database will be created automatically on first use
   ```

## Best Practices

1. **Consistent Setup**: Use the same DevStream version across all projects
2. **Separate Databases**: Each project should have its own database
3. **Regular Backups**: Backup each project's database separately
4. **Environment Variables**: Use `.env` files for project-specific configuration
5. **Documentation**: Keep project-specific documentation updated

## Example Projects Setup

### Project A (exc-to-pdf)
```
/exc-to-pdf/
├── .claude/settings.json     # DEVSTREAM_PROJECT_ROOT = "."
├── .devstream/               # Virtual environment
├── data/devstream.db        # Excel PDF tasks
└── exc-to-pdf/              # Project files
```

### Project B (another-project)
```
/another-project/
├── .claude/settings.json     # DEVSTREAM_PROJECT_ROOT = "."
├── .devstream/               # Virtual environment
├── data/devstream.db        # Another project tasks
└── src/                     # Project files
```

Each project maintains complete isolation of:
- Tasks and memory storage
- Database files
- Hook execution context
- Project-specific configuration

## Summary

The multi-project setup ensures:
- ✅ Each project uses its own database
- ✅ Hooks execute in correct project context
- ✅ Tasks are isolated per project
- ✅ Memory storage is project-specific
- ✅ Configuration remains flexible

This solution resolves the critical issue where all projects were incorrectly using the DevStream main database, ensuring proper data isolation and management across multiple projects.