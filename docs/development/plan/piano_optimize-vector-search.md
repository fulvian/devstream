# Implementation Plan: DevStream Vector Search Optimization

**Task ID**: e5d9f8c1c232cbbe1fe234fddb532adc  
**Model**: GLM-4.6 (Cost-optimized execution)  
**Priority**: 9/10 (HIGH)  
**Estimated Duration**: 23.5 hours (47 micro-tasks)

---

## 🎯 OBJECTIVE

Fix critical DevStream vector search system with 0% recall rate and implement production-ready optimization across 3 tiers.

---

## 📊 CURRENT STATE

**Critical Issues**:
- P0: Schema dimension mismatch (768 vs 384) → 0% recall
- 40% missing embeddings (8,946/22,274 records)
- 327MB JSON embedding duplication
- Manual sync inefficiency
- No query fallback strategy
- No embedding validation

**Database**: 22,274 records, 780MB size  
**Model**: embeddinggemma:300m (384-dim)

---

## 🔄 TIER 1: EMERGENCY FIXES (8.5h → Recall 0% to 70%+)

### T1.1: Fix Schema Dimension Mismatch (120 min)

**Files**: `schema/schema.sql:204-209`, `scripts/migrations/001_fix_vector_dimensions.py`, `src/devstream/memory/storage.py:176-232`

**Actions**:
1. **Backup & Audit** (10 min): Read schema.sql, document all vector dimension declarations
2. **Update Schema** (15 min): Change `embedding float[768]` → `embedding float[384]` in schema.sql:204
3. **Migration Script** (30 min): Create `scripts/migrations/001_fix_vector_dimensions.py`:
   ```python
   # Drop existing vec_semantic_memory virtual table
   # Recreate with correct 384-dim
   # Rebuild from semantic_memory.embedding
   ```
4. **Runtime Validation** (20 min): Add to storage.py:176-232:
   ```python
   if memory.embedding and len(memory.embedding) != 384:
       raise ValueError(f"Embedding dimension mismatch: expected 384, got {len(memory.embedding)}")
   ```
5. **Model Metadata** (15 min): Add `expected_dimension: int = 384` to MemoryEntry model
6. **Run Migration** (30 min): Execute on data/devstream.db, validate with `PRAGMA table_info(vec_semantic_memory)`

**Acceptance**: Schema declares 384-dim, migration completes, no data loss, queries work

---

### T1.2: Implement Query Fallback Strategy (90 min)

**Files**: `src/devstream/memory/storage.py:359-400`, `src/devstream/memory/search.py:47-149`, `tests/unit/memory/test_search_fallback.py`

**Actions**:
1. **Graceful Degradation** (20 min): Wrap storage.py search_vectors in try-except, return [] on error
2. **Fallback Logic** (25 min): In search.py:47-100, check if semantic_results empty → log warning → use FTS5 only
3. **Exception Handling** (15 min): Catch VectorSearchError in _semantic_search, return []
4. **Logging** (10 min): Add WARNING logs when fallback triggered with reason
5. **Test** (20 min): Create test_search_fallback.py, mock VectorSearchError, verify FTS5 results

**Acceptance**: Vector search failures don't crash, FTS5 fallback returns results

---

### T1.3: Ollama Health Check + Retry Logic (120 min)

**Files**: `src/devstream/memory/embedding_generator.py:116-487`, `src/devstream/memory/memory_manager.py:79-90`, `tests/unit/memory/test_embedding_retry.py`

**Actions**:
1. **Health Check Method** (15 min): Add to embedding_generator.py:433:
   ```python
   async def check_ollama_health(self) -> bool:
       try:
           self._client.list()
           return True
       except Exception:
           return False
   ```
2. **Pre-flight Check** (15 min): Call check_ollama_health() before _process_batch()
3. **Auto-pull on 404** (20 min): In _generate_embedding_with_retry:116-187:
   ```python
   except ollama.ResponseError as e:
       if e.status_code == 404:
           logger.info(f"Model {self.config.model_name} not found, pulling...")
           await self.pull_model_if_needed()
           # Retry
   ```
4. **Backoff Validation** (10 min): Verify current backoff 1s, 2s, 4s (already correct)
5. **Retry Statistics** (15 min): Log retry count, failures, success rate per batch
6. **Startup Validation** (20 min): Add to memory_manager.py:79-90, call check_ollama_health() on init
7. **Test** (25 min): Create test_embedding_retry.py, mock failures, verify retry succeeds

**Acceptance**: Health check works, 404 triggers auto-pull, retries succeed, startup validates Ollama

---

### T1.4: Remove JSON Embedding Duplication (60 min)

**Files**: `src/devstream/memory/storage.py:176-323`, `scripts/migrations/002_remove_json_embeddings.sql`

**Actions**:
1. **Audit** (15 min): Search for `embedding_json = json.dumps(memory.embedding)`
2. **Remove from INSERT** (10 min): Change storage.py:210 `embedding=embedding_json` → `embedding=None`
3. **Remove from UPDATE** (10 min): Remove `embedding=embedding_json` from storage.py:296
4. **Verify BLOB Intact** (10 min): Confirm sync_to_virtual_tables():106-150 still writes BLOB
5. **Cleanup Migration** (15 min): Create 002_remove_json_embeddings.sql:
   ```sql
   UPDATE semantic_memory SET embedding = NULL WHERE embedding IS NOT NULL;
   VACUUM;
   ```

**Acceptance**: semantic_memory.embedding always NULL, vec_semantic_memory BLOB unchanged, -327MB DB size

---

### T1.5: Implement Trigger-Based Sync (90 min)

**Files**: `schema/schema.sql:412-448`, `src/devstream/memory/storage.py:106-175`, `tests/integration/test_trigger_sync.py`

**Actions**:
1. **Review Triggers** (10 min): Analyze schema.sql:412-448, identify BLOB vs JSON format issue
2. **Fix Vec Trigger** (20 min): Modify schema.sql:412-423 to convert JSON → BLOB:
   ```sql
   INSERT INTO vec_semantic_memory(memory_id, content_embedding)
   VALUES (NEW.id, CAST(NEW.embedding AS BLOB));
   ```
3. **Fix FTS Trigger** (15 min): Verify schema.sql:420-423 FTS trigger correct (TEXT → FTS5)
4. **Fix UPDATE Trigger** (15 min): Verify schema.sql:425-440 mirrors INSERT logic
5. **Deprecate Manual Sync** (10 min): Add deprecation comment to storage.py:106-175, log warning
6. **Test** (20 min): Create test_trigger_sync.py, insert memory, verify auto-population

**Acceptance**: Triggers sync automatically, manual sync deprecated, tests pass

---

## 🎯 TIER 2: QUALITY IMPROVEMENTS (7h → Relevance 70% to 85%+)

### T2.1: Implement Confidence Scoring (120 min)

**Files**: `src/devstream/memory/models.py`, `src/devstream/memory/search.py:222-365`, `tests/unit/memory/test_confidence_scoring.py`

**Actions**:
1. **Add Field** (10 min): Add `confidence_score: float = 1.0` to MemoryQueryResult
2. **Calculation Method** (30 min): Create _calculate_confidence_score():
   ```python
   confidence = 1.0
   if not (result.semantic_rank and result.keyword_rank):
       confidence *= 0.7  # Single-source penalty
   if score_range < 0.001:
       confidence *= 0.5  # Low discriminability
   if total_results < 5:
       confidence *= 0.6  # Low result count
   return confidence
   ```
3. **Integrate** (25 min): Call in RRF fusion search.py:222-304
4. **Filter** (15 min): Filter results where confidence < 0.3
5. **Logging** (10 min): Log min/avg/max confidence per search
6. **Test** (30 min): Test edge cases (single-source, low range, few results)

**Acceptance**: Confidence scores populated, low-confidence results filtered, tests pass

---

### T2.2: Schema Versioning for Embeddings (90 min)

**Files**: `schema/schema.sql`, `src/devstream/memory/models.py`, `src/devstream/memory/embedding_generator.py:223-224`, `src/devstream/memory/storage.py`, `tests/unit/memory/test_embedding_versioning.py`

**Actions**:
1. **Schema** (10 min): Add `embedding_version VARCHAR(50)` to schema.sql:167-168
2. **Model** (10 min): Add `embedding_version: Optional[str] = "embeddinggemma-300m-v1"` to MemoryEntry
3. **Populate** (15 min): Set embedding_version in embedding_generator.py:223-224 after generation
4. **Validator** (25 min): Create validate_embedding_compatibility() in storage.py:
   ```python
   expected_version = "embeddinggemma-300m-v1"
   if memory.embedding_version != expected_version:
       raise EmbeddingCompatibilityError(f"Version mismatch")
   ```
5. **Migration Detection** (20 min): Add startup check in memory_manager.py, warn if mixed versions
6. **Test** (10 min): Mock version mismatch, verify error raised

**Acceptance**: Version metadata stored, validator prevents mismatches, startup warns

---

### T2.3: Dynamic RRF Thresholds (60 min)

**Files**: `src/devstream/memory/search.py:222-365`, `tests/unit/memory/test_rrf_thresholds.py`

**Actions**:
1. **Store Raw Score** (10 min): Add `raw_rrf_score` field before normalization in search.py:222-304
2. **Absolute Threshold** (15 min): Implement MIN_RRF_SCORE = 0.01 filter
3. **Dynamic Threshold** (20 min): Adjust based on query length, content_type presence
4. **Logging** (10 min): Log threshold used, results before/after filtering
5. **Test** (5 min): Verify low-score results filtered

**Acceptance**: Raw + normalized scores stored, absolute threshold filters, tests pass

---

### T2.4: Preload sqlite-vec Extension (45 min)

**Files**: `src/devstream/database/connection.py`, `src/devstream/memory/storage.py:359-439`, `tests/integration/test_extension_preload.py`

**Actions**:
1. **Preload** (20 min): Add to connection.py initialize_pool():
   ```python
   async with self.engine.begin() as conn:
       raw_conn = await conn.get_raw_connection()
       if not vec_manager.load_extension(raw_conn):
           raise RuntimeError("Failed to preload sqlite-vec")
   ```
2. **Remove Repeated Loading** (15 min): Delete vec_manager.load_extension() from storage.py:372-373, 404-405
3. **Test** (10 min): Verify vector search works without per-query loading

**Acceptance**: Extension preloaded, per-query loading removed, tests pass

---

### T2.5: Auto-Reembedding Flag (30 min)

**Files**: `schema/schema.sql`, `src/devstream/memory/storage.py:264-323`, `scripts/background_reembedding.py`

**Actions**:
1. **Schema** (5 min): Add `needs_reembedding BOOLEAN DEFAULT FALSE`
2. **Flag on Update** (15 min): In storage.py update_memory(), if content changed, set needs_reembedding = True
3. **Background Script** (10 min): Create background_reembedding.py to query WHERE needs_reembedding = TRUE

**Acceptance**: Flag set on content changes, script processes flagged records

---

## 🎯 TIER 3: PERFORMANCE OPTIMIZATION (8h → Scale >100K)

### T3.1: Binary Quantization Evaluation (180 min)

**Files**: `src/devstream/memory/storage.py`, `scripts/benchmark_quantization.py`, `tests/performance/test_quantization.py`

**Actions**:
1. **Research** (15 min): Read Context7 docs for vec_quantize_binary()
2. **Create Coarse Table** (20 min): CREATE VIRTUAL TABLE vec_semantic_memory_coarse USING vec0(embedding_coarse bit[384])
3. **Quantization** (25 min): Add vec_quantize_binary() in embedding_generator.py
4. **Coarse Search** (30 min): Implement _coarse_search() with k*8 oversampling
5. **Re-scoring** (30 min): Fetch original embeddings, recalculate distances
6. **Benchmark** (30 min): Compare latency + recall on 22K DB
7. **Test** (30 min): Test 100 queries, measure recall@10 change

**Acceptance**: Quantization decision based on latency >100ms P95, recall loss <10%

---

### T3.2: Batch Reindexing System (120 min)

**Files**: `scripts/batch_reindex.py`, `tests/integration/test_batch_reindex.py`

**Actions**:
1. **Skeleton** (15 min): Create async main(), argument parsing (--batch-size, --model)
2. **Batch Fetcher** (20 min): Implement get_memories_batch(offset, limit)
3. **Regeneration** (30 min): Generate embeddings for batch, update in transaction
4. **Progress** (15 min): Add tqdm progress bar (processed/total, ETA)
5. **Error Handling** (25 min): Save checkpoint, resume from last batch
6. **Test** (15 min): Reindex 1K sample, verify embedding_version updated

**Acceptance**: Reindex script works, progress tracked, resume capability, tests pass

---

### T3.3: Monitoring Dashboard (120 min)

**Files**: `src/devstream/memory/monitoring.py`, `src/devstream/memory/search.py`, `tests/unit/memory/test_monitoring.py`

**Actions**:
1. **Metrics Class** (20 min): Create VectorSearchMetrics with recall, latency, errors tracking
2. **Integration** (25 min): Call metrics.track_search(query, results, latency) in search.py after each search
3. **Recall Calculator** (30 min): Implement _calculate_recall_at_k() (stub for ground truth)
4. **P95 Tracker** (15 min): Store latencies, calculate np.percentile(latencies, 95)
5. **Summary** (15 min): Create get_summary() returning dict with avg recall, P95 latency
6. **Prometheus Export** (15 min - optional): Export metrics as Prometheus text format

**Acceptance**: Metrics tracked, summary returns aggregates, Prometheus compatible

---

## ✅ ACCEPTANCE CRITERIA

**TIER 1**:
- ✅ Schema dimension = 384 (matches embeddinggemma:300m)
- ✅ Migration runs without data loss
- ✅ Query fallback to FTS5 on vector search failure
- ✅ Ollama health check on startup
- ✅ 404 triggers auto-pull
- ✅ JSON embeddings removed, -327MB DB size
- ✅ Triggers sync automatically

**TIER 2**:
- ✅ Confidence scores filter low-quality results
- ✅ Embedding version validation prevents mismatches
- ✅ RRF absolute threshold filters low scores
- ✅ sqlite-vec extension preloaded (no per-query loading)
- ✅ Auto-reembedding flag set on content updates

**TIER 3**:
- ✅ Binary quantization evaluated (decision point: latency >100ms)
- ✅ Batch reindex script with progress + resume
- ✅ Monitoring tracks recall, latency, errors

---

## 📊 EXPECTED RESULTS

| Metric | Current | TIER 1 | TIER 2 | TIER 3 | Target |
|--------|---------|--------|--------|--------|--------|
| **Recall@10** | 0% | 70-75% | 80-85% | 85-90% | 75-85% ✅ |
| **Precision@10** | N/A | 55-60% | 65-75% | 70-80% | 65-80% ✅ |
| **Latency P95** | N/A | <100ms | <80ms | <50ms | <100ms ✅ |
| **Embedding Success** | 60% | 95%+ | 97%+ | 98%+ | >90% ✅ |
| **DB Size** | 780MB | 453MB | 450MB | 445MB | -42% ✅ |

---

## 🔧 CRITICAL CONTEXT

**Modified Files (Do NOT revert)**:
- `src/devstream/memory/storage.py`: Now uses BLOB format (tobytes()), has embedding_generator
- `src/devstream/memory/search.py`: Context7-optimized RRF (k=60, weight_keyword=1.5)

**Key Patterns**:
- sqlite-vec: BLOB format via `np.array(embedding, dtype=np.float32).tobytes()`
- RRF formula: `weight / (k + rank)` where k=60 (industry standard)
- Ollama retry: exponential backoff 1s, 2s, 4s (Context7 validated)

**Testing Strategy**:
- Test each TIER on devstream.db (22K records) before next TIER
- Run migration scripts on DB copy first
- Validate backward compatibility

---

## 🚀 EXECUTION ORDER

1. **TIER 1** (sequential, 5 sub-tasks) → Test on devstream.db → Verify recall >70%
2. **TIER 2** (sequential, 5 sub-tasks) → Test on devstream.db → Verify relevance >80%
3. **TIER 3** (can parallelize 3.1, 3.2, 3.3) → Test on devstream.db → Verify latency <100ms

**Total**: 47 micro-tasks, 23.5 hours, 3 tiers
