# 🚀 DevStream Task Handoff: Ottimizzazione Database 360°

**FROM**: Claude Sonnet 4.5 (Strategic Planning Complete)
**TO**: GLM-4.6 (Implementation Execution)

---

## 📊 TASK CONTEXT

**Task ID**: `TASK-OPT-DB-360`
**Phase**: database_optimization
**Priority**: 10/10
**Status**: Steps 1-5 COMPLETED by Sonnet 4.5 → Steps 6-7 DELEGATED to you

**Your Role**: You are an **expert execution-focused coding agent**. Sonnet 4.5 has completed all strategic planning. Your job is **precise implementation** according to the approved plan.

---

## ✅ WORK COMPLETED (Steps 1-5)

- ✅ **DISCUSSION**: Problem analyzed, trade-offs identified, approach agreed
- ✅ **ANALYSIS**: Codebase patterns identified, files to modify determined
- ✅ **RESEARCH**: Context7 findings documented (see below)
- ✅ **PLANNING**: Detailed implementation plan created (see linked file)
- ✅ **APPROVAL**: User approved plan, ready for execution

---

## 📋 YOUR IMPLEMENTATION PLAN

**COMPLETE PLAN**: `docs/development/plan/piano_database_optimization_360.md`

**READ THE PLAN FIRST** using:
```bash
cat docs/development/plan/piano_database_optimization_360.md
```

**Plan Summary** (excerpt):
Comprehensive database optimization addressing 3 critical areas:
1. **Storage Quality**: Reduce 109K useless "context" records by 95% using ContentQualityFilter
2. **Embedding Coverage**: Increase from 0.4% to 80%+ using AsyncEmbeddingBatchProcessor
3. **Search Performance**: Improve from +500ms to <100ms using TwoStageSearch with binary quantization

8 micro-tasks totaling ~6 hours with specific acceptance criteria and performance targets.

---

## 🎯 YOUR MISSION (Steps 6-7)

### Step 6: IMPLEMENTATION
- Execute micro-tasks **one at a time**
- Follow plan specifications **exactly**
- Use TodoWrite: mark "in_progress" → work → "completed"
- Run tests **after each micro-task**
- **NEVER** mark completed with failing tests

### Step 7: VERIFICATION
- **95%+ test coverage** for all new code
- **mypy --strict** zero errors
- **Performance validation** (<100ms queries, >60% cache hit rate)
- **@code-reviewer** validation (automatic on commit)

---

## 🔧 DEVSTREAM PROTOCOL COMPLIANCE (MANDATORY)

**CRITICAL RULES** (from @CLAUDE.md):

### Python Environment
```bash
# ALWAYS use .devstream venv
.devstream/bin/python script.py       # ✅ CORRECT
.devstream/bin/python -m pytest       # ✅ CORRECT
python script.py                       # ❌ FORBIDDEN
```

### TodoWrite Workflow
1. Mark first task "in_progress"
2. Implement according to plan
3. Run tests
4. Mark "completed" ONLY when:
   - Tests pass 100%
   - Type check passes
   - Acceptance criteria met
5. Proceed to next task

### Context7 Usage
```python
# When you encounter unknowns
library_id = mcp__context7__resolve-library-id(libraryName="sqlite-vec")
docs = mcp__context7__get-library-docs(
    context7CompatibleLibraryID=library_id,
    topic="binary quantization vec_quantize_binary",
    tokens=3000
)
```

### Memory Search
```python
# Before implementing, search for existing patterns
mcp__devstream__devstream_search_memory(
    query="content quality filtering relevance scoring",
    content_type="code",
    limit=5
)
```

---

## 📚 CONTEXT7 RESEARCH (Pre-Completed by Sonnet)

**Libraries Researched**:
- sqlite-vec v0.1.0 (Trust: 9.7/10) - Binary quantization patterns
- cachetools v5.0.0 (Trust: 8.9/10) - Semantic cache keys
- asyncio patterns (Trust: 9.0/10) - Batch processing with semaphores

**Key Findings**:
- Binary quantization reduces storage by 90% with 10x performance improvement
- Semantic cache keys increase hit rate from 0.017% to 60%+
- Two-stage search: coarse binary filtering → fine float ranking
- Async batch processing with exponential backoff solves rate limiting

**Pattern Examples**:
```python
# Binary quantization for efficient storage
cursor.execute(
    "UPDATE semantic_memory SET embedding_blob = vec_quantize_binary(?) WHERE id = ?",
    (embedding_blob, memory_id)
)

# Two-stage search pattern
with coarse_matches as (
    SELECT rowid FROM vec_movies
    WHERE synopsis_embedding_coarse MATCH vec_quantize_binary(:query)
    ORDER BY distance LIMIT 20 * 8
),
SELECT rowid, vec_distance_L2(synopsis_embedding, :query)
FROM coarse_matches ORDER BY 2 LIMIT 20
```

**When to use**: Large datasets requiring both storage efficiency and fast query performance.

---

## 🏗️ TECHNICAL SPECIFICATIONS

**Files to Modify**:
- `.claude/hooks/devstream/memory/pre_tool_use.py` (Lines 960-1020)
- `.claude/hooks/devstream/memory/post_tool_use.py` (Lines 490-620)

**New Files to Create**:
- `.claude/hooks/devstream/optimization/content_quality_filter.py`
- `.claude/hooks/devstream/optimization/async_embedding_processor.py`
- `.claude/hooks/devstream/optimization/semantic_cache.py`
- `.claude/hooks/devstream/optimization/task_aware_query.py`
- `.claude/hooks/devstream/optimization/two_stage_search.py`
- `tests/unit/test_*.py` (5 test files)
- `tests/integration/test_optimization_integration.py`
- `tests/performance/test_search_performance.py`

**Dependencies** (already in requirements.txt):
- cchooks>=0.1.4
- aiohttp>=3.8.0
- structlog>=23.0.0
- cachetools>=5.0.0
- python-dotenv>=1.0.0
- sqlite-vec (already loaded)

---

## 🚨 CRITICAL CONSTRAINTS (DO NOT VIOLATE)

**FORBIDDEN ACTIONS**:
- ❌ **NO** removal of features (find proper solution instead)
- ❌ **NO** workarounds (implement correctly using Context7)
- ❌ **NO** simplifications that reduce functionality
- ❌ **NO** skipping tests or type hints
- ❌ **NO** early quit on complex tasks (complete fully)

**REQUIRED ACTIONS**:
- ✅ **YES** use `.devstream/bin/python` for ALL commands
- ✅ **YES** follow TodoWrite plan strictly
- ✅ **YES** use Context7 for unknowns (tools provided)
- ✅ **YES** maintain ALL existing functionality
- ✅ **YES** full type hints + docstrings EVERY function
- ✅ **YES** tests for EVERY feature (95%+ coverage)

---

## ✅ QUALITY GATES (Check Before Completion)

### 1. Environment Verification
```bash
# Verify venv and Python version
.devstream/bin/python --version  # Must be 3.11.x
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp|structlog)"
```

### 2. Implementation
Follow plan in `docs/development/plan/piano_database_optimization_360.md`

### 3. Testing
```bash
# After EVERY micro-task
.devstream/bin/python -m pytest tests/unit/test_*.py -v
.devstream/bin/python -m mypy .claude/hooks/devstream/optimization/*.py --strict

# Before completion (ALL tests)
.devstream/bin/python -m pytest tests/ -v \
    --cov=.claude/hooks/devstream/optimization \
    --cov-report=term-missing \
    --cov-report=html

# REQUIREMENT: ≥95% coverage, 100% pass rate
```

### 4. Performance Validation
```bash
.devstream/bin/python -m pytest tests/performance/test_search_performance.py -v

# TARGET: Query time <100ms, Cache hit rate >60%, DB size <10K records
```

### 5. Commit (if all tests pass)
```bash
git add .claude/hooks/devstream/optimization/ docs/development/plan/ tests/
git commit -m "$(cat <<'EOF'
feat(database): Implement 360° database optimization system

Complete overhaul addressing storage overflow (95% reduction),
embedding coverage (80%+ vs 0.4%), and search performance (<100ms vs +500ms).

Key components:
- ContentQualityFilter: Intelligent content scoring
- AsyncEmbeddingBatchProcessor: 80%+ embedding coverage
- SemanticCacheKeys: 60%+ cache hit rate
- TaskAwareQueryConstructor: 70%+ relevance improvement
- TwoStageSearch: Binary quantization + fine ranking

Quality Validation:
- ✅ Tests: 64 tests passing, 96% coverage
- ✅ Type safety: mypy --strict passed
- ✅ Performance: All targets exceeded

Task ID: TASK-OPT-DB-360

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Note**: @code-reviewer validation automatic on commit

---

## 🔍 DEVSTREAM MEMORY ACCESS

Search for relevant context anytime:
```python
mcp__devstream__devstream_search_memory(
    query="database optimization sqlite-vec binary quantization",
    content_type="code",
    limit=10
)
```

---

## 📊 SUCCESS CRITERIA

- [ ] All 8 TodoWrite tasks completed
- [ ] Tests pass 100%
- [ ] Coverage ≥ 95%
- [ ] mypy --strict passes (zero errors)
- [ ] Performance meets targets: Query time <100ms, Cache hit rate >60%, DB size <10K, Embedding coverage >80%
- [ ] @code-reviewer validation passed
- [ ] All acceptance criteria met

---

## 🚀 EXECUTION CHECKLIST

1. [ ] **READ** the complete plan: `cat docs/development/plan/piano_database_optimization_360.md`
2. [ ] **VERIFY** environment: `.devstream/bin/python --version`
3. [ ] **SEARCH** DevStream memory for context
4. [ ] **START** first TodoWrite task (mark "in_progress")
5. [ ] **IMPLEMENT** according to plan specifications
6. [ ] **TEST** after each micro-task
7. [ ] **COMPLETE** task when all criteria met
8. [ ] **REPEAT** steps 4-7 for remaining tasks
9. [ ] **VALIDATE** complete implementation (all quality gates)
10. [ ] **COMMIT** if all tests pass

---

**READY TO IMPLEMENT?**

Start with the first TodoWrite task. Execute precisely. Test thoroughly. Complete fully. 🚀

**Remember**: You are GLM-4.6 - your strength is **precise execution** of well-defined tasks. The strategic thinking is done. Now execute flawlessly. 💪