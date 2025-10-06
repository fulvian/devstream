# DevStream Memory Vector Enhancement - Development Plan

**Project**: Memory Vector Enhancement - Session Summary Fix
**Version**: 1.0.0
**Date**: 2025-10-06
**Status**: Ready for Implementation
**Task ID**: TBA

---

## 🎯 PROJECT OVERVIEW

### Problem Statement
Session summaries show empty data despite previous fixes due to 4 coordinated issues:
1. PostToolUse saves generic checkpoints instead of real activity data
2. Only 9.3% embedding coverage (1,010/10,828 records)
3. Session extractor expects data patterns that don't exist
4. 9,818 existing records need vectorization

### Solution Architecture
4 coordinated fixes using Context7-backed patterns:
- **Fix 1**: PostToolUse real-time data capture (Watchdog pattern)
- **Fix 2**: Session data extraction (SQLite time-window queries)
- **Fix 3**: Real-time embedding generation (Ollama batch processing)
- **Fix 4**: Mass vectorization (adapted scan-codebase.py)

### Success Criteria
- PostToolUse captures real file modifications (not generic checkpoints)
- 100% embedding coverage for all records
- Session summaries show accurate statistics
- Backward compatibility maintained (100%)

---

## 📋 DEVSTREAM IMPLEMENTATION PLAN

### PHASE 1: ENHANCE POSTTOOLUSE (Estimated: 45 minutes)

#### Task 1.1: Install Watchdog Dependencies
**Agent**: @python-specialist
**Estimated**: 10 minutes
**Files**: `.devstream/requirements.txt`

**Implementation**:
```python
# Add to requirements.txt
watchdog>=3.0.0
sqlite-utils>=3.36.0
aiofiles>=23.0.0
```

**Acceptance Criteria**:
- [ ] Dependencies installed successfully
- [ ] No import errors in hooks

#### Task 1.2: Create RealTimeDataCapture Class
**Agent**: @python-specialist
**Estimated**: 20 minutes
**Files**: `.claude/hooks/devstream/memory/real_time_capture.py`

**Implementation**: Context7 Watchdog pattern
```python
from pathlib import Path
import sqlite_utils
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class RealTimeDataCapture(FileSystemEventHandler):
    """Cattura modifiche file reali con pattern Watchdog"""

    def __init__(self, db_path: str, session_id: str):
        self.db_path = db_path
        self.session_id = session_id

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix in ['.py', '.md', '.ts', '.tsx']:
            self.store_file_context(file_path)

    def store_file_context(self, file_path: Path):
        """Store specific file context instead of generic checkpoints"""
        # Context7 sqlite-utils batch insert pattern
        pass
```

**Acceptance Criteria**:
- [ ] Class implements FileSystemEventHandler
- [ ] Filters relevant file types (.py, .md, .ts, .tsx)
- [ ] Stores specific file context in semantic_memory

#### Task 1.3: Update PostToolUse Hook
**Agent**: @python-specialist
**Estimated**: 15 minutes
**Files**: `.claude/hooks/devstream/memory/post_tool_use.py`

**Implementation**: Integrate RealTimeDataCapture
```python
# Replace generic "Task Checkpoint" with real-time capture
def capture_tool_execution(tool_name: str, tool_result: Any, session_id: str):
    """Enhanced PostToolUse with real-time data capture"""
    capture = RealTimeDataCapture(db_path, session_id)
    # Extract real context from tool execution
    # Store specific activity data
```

**Acceptance Criteria**:
- [ ] Generic "Task Checkpoint" messages eliminated
- [ ] Real file modifications captured
- [ ] Session-specific data stored

---

### PHASE 2: CREATE EMBEDDING GENERATOR (Estimated: 60 minutes)

#### Task 2.1: Create EmbeddingGenerator Class
**Agent**: @python-specialist
**Estimated**: 30 minutes
**Files**: `.claude/hooks/devstream/memory/embedding_generator.py`

**Implementation**: Context7 Ollama batch processing pattern
```python
import aiohttp
import asyncio
from typing import List, Dict

class EmbeddingGenerator:
    """Ollama batch processing with retry pattern"""

    async def generate_batch_embeddings(self, records: List[Dict]) -> List[Dict]:
        """Batch embedding generation with exponential backoff"""
        batch_size = 10
        max_retries = 3

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            embeddings = await self.call_ollama_batch(batch, max_retries)
            await self.insert_embeddings_atomic(batch, embeddings)
```

**Acceptance Criteria**:
- [ ] Batch size fixed at 10 records
- [ ] Exponential backoff retry implemented
- [ ] Atomic batch insert pattern

#### Task 2.2: Integrate Ollama API with Error Handling
**Agent**: @python-specialist
**Estimated**: 20 minutes
**Files**: `.claude/hooks/devstream/memory/embedding_generator.py`

**Implementation**: Robust Ollama API calls
```python
async def call_ollama_batch(self, batch: List[Dict], max_retries: int) -> List[List[float]]:
    """Ollama API with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("http://localhost:11434/api/embeddings", json={
                    "model": "gemma2",
                    "prompt": [r["content"] for r in batch]
                }) as response:
                    result = await response.json()
                    return result["embeddings"]
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
```

**Acceptance Criteria**:
- [ ] Ollama gemma2 model integration
- [ ] Exponential backoff: 1s, 2s, 4s
- [ ] Proper error handling and logging

#### Task 2.3: Create Atomic Embedding Insert
**Agent**: @python-specialist
**Estimated**: 10 minutes
**Files**: `.claude/hooks/devstream/memory/embedding_generator.py`

**Implementation**: SQLite atomic operations
```python
async def insert_embeddings_atomic(self, batch: List[Dict], embeddings: List[List[float]]):
    """Atomic batch insert to prevent partial writes"""
    with sqlite_utils.Database(self.db_path) as db:
        for record, embedding in zip(batch, embeddings):
            db["vec_semantic_memory"].insert({
                "record_id": record["id"],
                "embedding": embedding,
                "model": "gemma2"
            })
```

**Acceptance Criteria**:
- [ ] Atomic batch insert implemented
- [ ] Vector table integration working
- [ ] No partial writes possible

---

### PHASE 3: ENHANCE SESSION DATA EXTRACTOR (Estimated: 45 minutes)

#### Task 3.1: Update SessionDataExtractor with Time-Window Queries
**Agent**: @python-specialist
**Estimated**: 25 minutes
**Files**: `.claude/hooks/devstream/sessions/session_data_extractor.py`

**Implementation**: Context7 SQLite time-window pattern
```python
import sqlite_utils
from datetime import datetime, timedelta

class SessionDataExtractor:
    """SQLite time-window queries with sqlite-utils"""

    def extract_session_data(self, session_id: str) -> Dict[str, Any]:
        """Precise time-window data extraction"""
        with sqlite_utils.Database(self.db_path) as db:
            session_data = list(db.execute("""
                SELECT content, content_type, timestamp, file_path
                FROM semantic_memory
                WHERE session_id = ?
                AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
            """, [session_id, self.session_start, self.session_end]))
```

**Acceptance Criteria**:
- [ ] Time-window queries implemented
- [ ] Session-specific filtering working
- [ ] Accurate timestamp boundaries

#### Task 3.2: Implement Pattern Recognition for Real Data
**Agent**: @python-specialist
**Estimated**: 20 minutes
**Files**: `.claude/hooks/devstream/sessions/session_data_extractor.py`

**Implementation**: Analyze real data patterns
```python
def analyze_real_patterns(self, session_data: List[Dict]) -> Dict[str, Any]:
    """Analyze actual patterns in saved data"""
    file_modifications = [r for r in session_data if r["content_type"] == "code_change"]
    task_completions = [r for r in session_data if "completed" in r["content"].lower()]

    return {
        "files_modified": len(set(r["file_path"] for r in file_modifications)),
        "tasks_completed": len(task_completions),
        "total_activities": len(session_data)
    }
```

**Acceptance Criteria**:
- [ ] Pattern recognition for code_change entries
- [ ] Task completion detection working
- [ ] Unique file counting implemented

---

### PHASE 4: CREATE MASS VECTORIZER (Estimated: 90 minutes)

#### Task 4.1: Create MassVectorizer Class
**Agent**: @python-specialist
**Estimated**: 30 minutes
**Files**: `scripts/mass_vectorizer.py`

**Implementation**: Adapted from scan-codebase.py
```python
import sqlite_utils
from scripts.scan_codebase import EmbeddingGenerator

class MassVectorizer:
    """Mass vectorization for existing semantic_memory records"""

    def vectorize_missing_records(self):
        """Process existing records without embeddings"""
        with sqlite_utils.Database(self.db_path) as db:
            missing_records = list(db.execute("""
                SELECT id, content, content_type, timestamp
                FROM semantic_memory
                WHERE id NOT IN (SELECT record_id FROM vec_semantic_memory)
                ORDER BY timestamp DESC
                LIMIT 10000
            """))

            print(f"Found {len(missing_records)} records without embeddings")
```

**Acceptance Criteria**:
- [ ] Query identifies records without embeddings
- [ ] 10,000 record limit implemented
- [ ] Ordered by timestamp (newest first)

#### Task 4.2: Implement Chunking Strategy
**Agent**: @python-specialist
**Estimated**: 20 minutes
**Files**: `scripts/mass_vectorizer.py`

**Implementation**: Context7 chunking pattern
```python
def chunk_records(self, records: List[Dict], chunk_size: int) -> List[List[Dict]]:
    """Memory-efficient chunking for large datasets"""
    for i in range(0, len(records), chunk_size):
        yield records[i:i + chunk_size]

def process_chunks(self, missing_records: List[Dict]):
    """Process records in 1000-record chunks"""
    for chunk in self.chunk_records(missing_records, 1000):
        embeddings = self.generate_embeddings_batch(chunk)
        self.insert_embeddings_batch(chunk, embeddings)
        print(f"Processed {len(chunk)} records")
```

**Acceptance Criteria**:
- [ ] Chunk size of 1000 records
- [ ] Memory management implemented
- [ ] Progress reporting working

#### Task 4.3: Integrate with Existing Ollama Infrastructure
**Agent**: @python-specialist
**Estimated**: 25 minutes
**Files**: `scripts/mass_vectorizer.py`

**Implementation**: Reuse existing patterns
```python
def generate_embeddings_batch(self, chunk: List[Dict]) -> List[List[float]]:
    """Reuse existing Ollama batch processing"""
    # Leverage EmbeddingGenerator from scan-codebase.py
    generator = EmbeddingGenerator()
    return asyncio.run(generator.generate_batch_embeddings(chunk))
```

**Acceptance Criteria**:
- [ ] Reuses existing EmbeddingGenerator
- [ ] Consistent with scan-codebase.py patterns
- [ ] Error handling inherited

#### Task 4.4: Create CLI Interface
**Agent**: @python-specialist
**Estimated**: 15 minutes
**Files**: `scripts/mass_vectorizer.py`

**Implementation**: Command-line interface
```python
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mass vectorize semantic_memory records")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    parser.add_argument("--batch-size", type=int, default=1000, help="Chunk size")

    args = parser.parse_args()

    vectorizer = MassVectorizer()
    if args.dry_run:
        vectorizer.dry_run()
    else:
        vectorizer.vectorize_missing_records()
```

**Acceptance Criteria**:
- [ ] CLI interface implemented
- [ ] --dry-run option available
- [ ] Customizable batch size

---

### PHASE 5: INTEGRATION & TESTING (Estimated: 60 minutes)

#### Task 5.1: Create Integration Tests
**Agent**: @testing-specialist
**Estimated**: 30 minutes
**Files**: `tests/integration/test_memory_vector_enhancement.py`

**Implementation**: End-to-end testing
```python
def test_post_tool_use_real_data_capture():
    """Test PostToolUse captures real data"""
    # Simulate tool execution
    # Verify real data stored instead of checkpoints

def test_embedding_generation_coverage():
    """Test 100% embedding coverage"""
    # Process sample records
    # Verify all records receive embeddings

def test_session_extraction_accuracy():
    """Test session data extraction accuracy"""
    # Create sample session data
    # Verify extraction matches stored data
```

**Acceptance Criteria**:
- [ ] All 4 fixes tested in isolation
- [ ] End-to-end integration test
- [ ] 95%+ test coverage

#### Task 5.2: Performance Testing
**Agent**: @performance-optimizer
**Estimated**: 20 minutes
**Files**: `tests/performance/test_embedding_generation.py`

**Implementation**: Performance validation
```python
def test_batch_embedding_performance():
    """Validate batch embedding performance"""
    # Test 1000 record processing time
    # Target: <60 seconds per 1000 records

def test_memory_usage():
    """Validate memory usage during mass vectorization"""
    # Monitor memory during chunking
    # Target: <500MB peak usage
```

**Acceptance Criteria**:
- [ ] Batch embedding: <60s/1000 records
- [ ] Memory usage: <500MB peak
- [ ] No memory leaks detected

#### Task 5.3: Code Review
**Agent**: @code-reviewer
**Estimated**: 10 minutes
**Files**: All modified files

**Review Checklist**:
- [ ] OWASP Top 10 security validation
- [ ] Type hints and docstrings complete
- [ ] Error handling robust
- [ ] Performance characteristics acceptable
- [ ] Architecture patterns followed

---

### PHASE 6: DEPLOYMENT (Estimated: 30 minutes)

#### Task 6.1: Database Migration
**Agent**: @database-specialist
**Estimated**: 15 minutes
**Files**: `migrations/001_add_session_tracking.sql`

**Implementation**: Backward-compatible schema changes
```sql
-- Add session tracking to existing records
ALTER TABLE semantic_memory ADD COLUMN session_id TEXT;
CREATE INDEX IF NOT EXISTS idx_semantic_memory_session_id ON semantic_memory(session_id);
```

**Acceptance Criteria**:
- [ ] Migration script created
- [ ] Backward compatibility maintained
- [ ] Indexes created for performance

#### Task 6.2: Mass Vectorization Execution
**Agent**: @devops-specialist
**Estimated**: 15 minutes
**Command**: `.devstream/bin/python scripts/mass_vectorizer.py`

**Deployment Steps**:
1. Backup database: `cp data/devstream.db data/devstream.db.backup`
2. Run migration: `.devstream/bin/python scripts/migrate.py`
3. Execute mass vectorization: `.devstream/bin/python scripts/mass_vectorizer.py`
4. Verify results: Check embedding coverage

**Acceptance Criteria**:
- [ ] Database backed up successfully
- [ ] Migration completes without errors
- [ ] 100% embedding coverage achieved
- [ ] No data corruption

---

## 📊 SUCCESS METRICS

### Technical Metrics
- **Embedding Coverage**: 100% (10,828/10,828 records)
- **PostToolUse Data Quality**: 0% generic checkpoints
- **Session Summary Accuracy**: Real statistics displayed
- **Performance**: <60s per 1000 embeddings
- **Memory Usage**: <500MB peak during mass vectorization

### Process Metrics
- **Backward Compatibility**: 100% (no breaking changes)
- **Test Coverage**: 95%+ for new code
- **Code Review**: All files approved by @code-reviewer
- **Documentation**: Complete for all new components

### Business Metrics
- **Session Summary Effectiveness**: Real data displayed to users
- **Context Retrieval Quality**: Improved due to 100% embedding coverage
- **System Reliability**: Enhanced atomic operations prevent corruption

---

## 🚀 ROLLBACK PLAN

### Immediate Rollback (<5 minutes)
1. Restore database: `cp data/devstream.db.backup data/devstream.db`
2. Restart session: New session uses original hooks
3. Verify functionality: Basic session tracking works

### Full Rollback (<30 minutes)
1. Revert all hook files to original versions
2. Remove new dependencies from requirements.txt
3. Restart DevStream system
4. Validate all functionality working

---

## 📋 IMPLEMENTATION CHECKLIST

### Pre-Implementation
- [ ] Database backed up
- [ ] Dependencies installed
- [ ] Environment prepared
- [ ] Rollback procedures documented

### Implementation
- [ ] Phase 1: PostToolUse enhanced (45m)
- [ ] Phase 2: EmbeddingGenerator created (60m)
- [ ] Phase 3: SessionDataExtractor updated (45m)
- [ ] Phase 4: MassVectorizer created (90m)
- [ ] Phase 5: Integration testing (60m)
- [ ] Phase 6: Deployment (30m)

### Post-Implementation
- [ ] All tests passing
- [ ] Performance metrics met
- [ ] 100% embedding coverage verified
- [ ] Session summaries showing real data
- [ ] Documentation updated

---

**Total Estimated Time**: 5.5 hours
**Risk Level**: Medium (database operations involved)
**Backward Compatibility**: 100% maintained
**Quality Gates**: @code-reviewer approval mandatory before commit

---

*Generated by DevStream Planning Process*
*Architecture based on Context7 best practices research*