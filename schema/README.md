# DevStream Database Schema Documentation

## Overview

This directory contains the database schema for DevStream v2.1.0. The schema is designed for SQLite 3 with the `sqlite-vec` extension for vector similarity search.

## Files

- **schema.sql**: Complete database schema (versioned, executable)
- **README.md**: This documentation file

## Schema Features

### Core Tables

1. **intervention_plans**: Top-level project/feature planning
2. **phases**: Logical breakdown of intervention plans
3. **micro_tasks**: Atomic work units (max 10 minutes)
4. **semantic_memory**: Content storage with vector embeddings
5. **agents**: Agent tracking and performance metrics
6. **hooks**: Automated workflow triggers
7. **work_sessions**: User session tracking
8. **context_injections**: Memory retrieval tracking
9. **learning_insights**: Pattern and best practice tracking
10. **performance_metrics**: System performance tracking

### Virtual Tables (Search)

- **vec_semantic_memory**: Vector similarity search (sqlite-vec extension)
- **fts_semantic_memory**: Full-text keyword search (FTS5 built-in)

### Relationships

```
intervention_plans
    └── phases
        └── micro_tasks
            └── semantic_memory
                ├── vec_semantic_memory (vector search)
                └── fts_semantic_memory (keyword search)
```

## Prerequisites

### Required Extensions

1. **sqlite-vec (vec0)**: Vector similarity search
   - GitHub: https://github.com/asg017/sqlite-vec
   - Installation: Follow repository instructions
   - Required for: `vec_semantic_memory` virtual table

2. **FTS5**: Full-text search (built-in to modern SQLite)
   - Available in: SQLite 3.9.0+
   - No installation needed

### Python Dependencies

```bash
# Install in DevStream virtual environment
.devstream/bin/python -m pip install \
    aiosqlite>=0.19.0 \
    sqlite-vec>=0.1.0
```

## Database Setup

### Option 1: Create from Schema (Fresh Database)

**IMPORTANT**: The schema.sql file requires the sqlite-vec (vec0) extension to be available. If you encounter "no such module: vec0" error when using `sqlite3` command-line tool, use the Python method below:

```bash
# Method 1: Using Python (RECOMMENDED - handles vec0 loading)
.devstream/bin/python << 'EOF'
import sqlite3

# Read schema file
with open('schema/schema.sql', 'r') as f:
    schema_sql = f.read()

# Create new database
conn = sqlite3.connect('data/devstream_new.db')
conn.enable_load_extension(True)

# Load vec0 extension (ensure vec0 is in library path)
try:
    conn.load_extension('vec0')
    print("✅ vec0 extension loaded")
except sqlite3.OperationalError as e:
    print(f"⚠️  vec0 extension not available: {e}")
    print("   Database will be created without vector search capability")

# Execute schema
cursor = conn.cursor()
cursor.executescript(schema_sql)

# Verify tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]
print(f"✅ Created {len(tables)} tables")

conn.close()
EOF

# Method 2: Using sqlite3 CLI (requires vec0 in system library path)
# sqlite3 data/devstream_new.db < schema/schema.sql
```

### Option 2: Verify Existing Database

```bash
# Verify schema version
.devstream/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/devstream.db')
cursor = conn.cursor()
cursor.execute('SELECT version, description FROM schema_version')
print('Schema version:', cursor.fetchone())
conn.close()
"
```

## Schema Validation

### Automated Validation Script

```python
#!/usr/bin/env python3
"""Validate DevStream database schema."""

import sqlite3
import sys

def validate_schema(db_path: str) -> bool:
    """Validate database schema matches expected structure."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Expected tables
    expected_tables = [
        'intervention_plans', 'phases', 'micro_tasks', 'semantic_memory',
        'vec_semantic_memory', 'fts_semantic_memory', 'agents', 'hooks',
        'hook_executions', 'work_sessions', 'context_injections',
        'learning_insights', 'performance_metrics', 'schema_version'
    ]

    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    actual_tables = [row[0] for row in cursor.fetchall() if not row[0].startswith('fts_') and not row[0].startswith('vec_')]

    missing_tables = set(expected_tables) - set(actual_tables)
    if missing_tables:
        print(f"❌ Missing tables: {missing_tables}")
        return False

    print("✅ All core tables present")

    # Check vec0 extension
    try:
        cursor.execute("SELECT COUNT(*) FROM vec_semantic_memory")
        print("✅ sqlite-vec extension loaded")
    except sqlite3.OperationalError:
        print("⚠️  sqlite-vec extension not loaded (vec_semantic_memory unavailable)")
        return False

    # Check FTS5
    try:
        cursor.execute("SELECT COUNT(*) FROM fts_semantic_memory")
        print("✅ FTS5 extension available")
    except sqlite3.OperationalError:
        print("❌ FTS5 extension not available")
        return False

    # Check triggers
    cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    triggers = [row[0] for row in cursor.fetchall()]
    expected_triggers = ['sync_insert_memory', 'sync_update_memory', 'sync_delete_memory']

    if set(expected_triggers) <= set(triggers):
        print("✅ All sync triggers present")
    else:
        print(f"❌ Missing triggers: {set(expected_triggers) - set(triggers)}")
        return False

    # Check schema version
    cursor.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1")
    version = cursor.fetchone()
    if version:
        print(f"✅ Schema version: {version[0]}")
    else:
        print("⚠️  No schema version found")

    conn.close()
    return True

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'data/devstream.db'
    print(f"Validating database: {db_path}\n")

    if validate_schema(db_path):
        print("\n✅ Schema validation passed")
        sys.exit(0)
    else:
        print("\n❌ Schema validation failed")
        sys.exit(1)
```

Save as `schema/validate_schema.py` and run:

```bash
.devstream/bin/python schema/validate_schema.py data/devstream.db
```

## Schema Migration

### Version Tracking

The `schema_version` table tracks all applied migrations:

```sql
-- Check current version
SELECT version, applied_at, description
FROM schema_version
ORDER BY applied_at DESC;

-- Add new version after migration
INSERT INTO schema_version (version, description)
VALUES ('2.2.0', 'Add new feature columns');
```

### Migration Best Practices

1. **Always backup before migration**:
   ```bash
   cp data/devstream.db data/devstream_backup_$(date +%Y%m%d_%H%M%S).db
   ```

2. **Test on copy first**:
   ```bash
   cp data/devstream.db data/devstream_test.db
   # Apply migration to test database
   # Validate with validate_schema.py
   ```

3. **Use transactions**:
   ```sql
   BEGIN TRANSACTION;
   -- Migration statements
   COMMIT; -- or ROLLBACK on error
   ```

4. **Update schema version**:
   ```sql
   INSERT INTO schema_version (version, description)
   VALUES ('2.2.0', 'Description of changes');
   ```

## Common Operations

### Query Examples

```sql
-- Get all active intervention plans
SELECT id, title, status, priority
FROM intervention_plans
WHERE status = 'active'
ORDER BY priority DESC;

-- Get tasks for a specific phase
SELECT t.id, t.title, t.status, t.assigned_agent
FROM micro_tasks t
JOIN phases p ON t.phase_id = p.id
WHERE p.id = 'PHASE-001'
ORDER BY t.priority DESC;

-- Search semantic memory (hybrid search)
-- Vector search
SELECT memory_id, distance
FROM vec_semantic_memory
WHERE embedding MATCH <query_vector>
  AND k = 10
ORDER BY distance;

-- Keyword search
SELECT memory_id, rank
FROM fts_semantic_memory
WHERE fts_semantic_memory MATCH 'fastapi AND async'
ORDER BY rank;
```

### Maintenance

```sql
-- Analyze tables for query optimization
ANALYZE;

-- Vacuum to reclaim space (offline only)
VACUUM;

-- Check database integrity
PRAGMA integrity_check;

-- Get database statistics
SELECT
    name,
    (SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND tbl_name=tables.name) as index_count
FROM sqlite_master tables
WHERE type='table'
ORDER BY name;
```

## Performance Optimization

### Indexes

The schema includes comprehensive indexes for common query patterns:

- **intervention_plans**: status, priority, created_at
- **phases**: plan_id, status, sequence_order
- **micro_tasks**: phase_id, status, assigned_agent, priority
- **semantic_memory**: content_type, plan_id, phase_id, task_id, created_at

### Query Optimization Tips

1. **Use indexes**: Queries filtering on indexed columns are faster
2. **Limit results**: Use `LIMIT` for large result sets
3. **Analyze queries**: Use `EXPLAIN QUERY PLAN` to verify index usage
4. **Batch operations**: Use transactions for multiple inserts/updates
5. **Partition searches**: Use `content_type` partition key for vec0 queries

## Troubleshooting

### Issue: "no such module: vec0"

**Cause**: sqlite-vec extension not loaded

**Solution**:
```python
import sqlite3
conn = sqlite3.connect('data/devstream.db')
conn.enable_load_extension(True)
conn.load_extension('vec0')  # Ensure vec0.so/dylib is in library path
```

### Issue: Triggers not firing

**Cause**: Foreign keys not enabled

**Solution**:
```python
conn.execute("PRAGMA foreign_keys = ON")
```

### Issue: Slow queries

**Solution**:
1. Check query plan: `EXPLAIN QUERY PLAN SELECT ...`
2. Verify indexes are used
3. Run `ANALYZE` to update statistics
4. Consider adding covering indexes for frequent queries

## Support & Resources

- **DevStream Documentation**: `/Users/fulvioventura/devstream/CLAUDE.md`
- **sqlite-vec Repository**: https://github.com/asg017/sqlite-vec
- **SQLite FTS5 Documentation**: https://www.sqlite.org/fts5.html
- **Project Structure**: `/Users/fulvioventura/devstream/PROJECT_STRUCTURE.md`

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 2.1.0 | 2025-10-01 | Initial production schema with vector search and full-text search |

---

**Last Updated**: 2025-10-01
**Schema Version**: 2.1.0
**Status**: Production Ready
