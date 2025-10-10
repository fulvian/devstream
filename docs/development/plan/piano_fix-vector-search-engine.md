# Implementation Plan: Fix Critical Vector Search Engine Failure

**Task ID**: 6e63cfeb622dc7f16e9b38316589a5a5
**Model**: GLM-4.6 (Execution-optimized)
**Priority**: P0 - BLOCKER
**Estimated Duration**: 30-45 minutes
**Created**: 2025-10-09

---

## 🎯 Objective

Fix critical vector search engine failure in DevStream MCP server. The hybrid search system (RRF) currently returns 0 results due to SQLite's lack of `FULL OUTER JOIN` support. Implement Context7-backed solution using LEFT JOIN + UNION ALL pattern.

---

## 🔍 Root Cause Analysis

### Problem Identified
- **Location**: `mcp-devstream-server/src/tools/hybrid-search.ts:163-202`
- **Issue**: SQL query uses `FULL OUTER JOIN` which is NOT supported in SQLite
- **Impact**: Hybrid search returns 0 results (100% failure rate)
- **Current State**:
  - ✅ Storage working (47,904 memories, 15,588 with embeddings)
  - ✅ FTS5 working (15,589 indexed entries)
  - ✅ vec0 extension loaded (6 virtual tables present)
  - ❌ Hybrid search query fails silently

### Context7 Research Applied
- **Source**: sqlite-vec (Trust Score 9.7, 122 code snippets)
- **Reference**: `nbc-headlines/3_search.ipynb` - Official RRF hybrid search example
- **Finding**: Official example ALSO uses FULL OUTER JOIN (paradox!)
- **Solution**: Alternative pattern "Combining FTS and Vector Search (Keyword-first)" using UNION ALL

---

## 📋 Implementation Plan

### Phase 1: Backup & Preparation (5 min)
**Micro-tasks**:
1. ✅ Read current `hybrid-search.ts` file (COMPLETED in research phase)
2. Create backup copy with timestamp
3. Verify test suite exists for hybrid search
4. Document current query structure

**Acceptance Criteria**:
- Backup file created: `hybrid-search.ts.backup-YYYYMMDD`
- Test files located and documented
- Current SQL query documented with line numbers

---

### Phase 2: SQL Query Refactoring (15 min)
**Micro-tasks**:
1. Replace FULL OUTER JOIN with LEFT JOIN + UNION ALL pattern
2. Maintain RRF scoring formula (COALESCE logic preserved)
3. Add GROUP BY to handle potential duplicates
4. Preserve all existing CTEs (vec_matches, fts_matches, combined)
5. Update SQL comments to reflect SQLite compatibility

**Target SQL Pattern** (Context7-backed):
```sql
WITH vec_matches AS (...),
     fts_matches AS (...),
     combined AS (
       -- FTS results
       SELECT
         fts_matches.memory_id,
         NULL as vec_rank,
         fts_matches.rank_number as fts_rank,
         NULL as vec_distance,
         fts_matches.score as fts_score
       FROM fts_matches

       UNION ALL

       -- Vector results
       SELECT
         vec_matches.memory_id,
         vec_matches.rank_number as vec_rank,
         NULL as fts_rank,
         vec_matches.distance as vec_distance,
         NULL as fts_score
       FROM vec_matches
     )
SELECT
  semantic_memory.id as memory_id,
  semantic_memory.content,
  semantic_memory.content_type,
  semantic_memory.created_at,
  MAX(combined.vec_rank) as vec_rank,
  MAX(combined.fts_rank) as fts_rank,
  (
    COALESCE(1.0 / (? + MAX(combined.fts_rank)), 0.0) * ?
    + COALESCE(1.0 / (? + MAX(combined.vec_rank)), 0.0) * ?
  ) as combined_rank,
  MAX(combined.vec_distance) as vec_distance,
  MAX(combined.fts_score) as fts_score
FROM combined
JOIN semantic_memory ON semantic_memory.id = combined.memory_id
GROUP BY semantic_memory.id
ORDER BY combined_rank DESC
```

**Acceptance Criteria**:
- No FULL OUTER JOIN in query
- RRF formula preserved (COALESCE + weights)
- All 8 parameters correctly positioned
- GROUP BY prevents duplicates
- ORDER BY combined_rank DESC maintained

---

### Phase 3: Code Integration (10 min)
**Micro-tasks**:
1. Update `hybrid-search.ts:163-202` with new SQL
2. Verify parameter binding order (8 params: embeddingBuffer, k, sanitizedQuery, k, rrf_k, weight_fts, rrf_k, weight_vec)
3. Preserve Unicode sanitization logic
4. Maintain memory cleanup (GC trigger)
5. Keep error handling and fallback to FTS5

**Files Modified**:
- `mcp-devstream-server/src/tools/hybrid-search.ts` (lines 163-202)

**Acceptance Criteria**:
- TypeScript compiles without errors
- All 8 parameters correctly bound
- Existing error handling preserved
- No breaking changes to function signature

---

### Phase 4: Testing & Validation (10 min)
**Micro-tasks**:
1. Rebuild MCP server: `npm run build` in mcp-devstream-server/
2. Restart MCP server
3. Test hybrid search with known query: "session summary"
4. Verify results returned (should be >0)
5. Compare RRF scores with expected values
6. Test edge cases (query with no FTS matches, query with no vec matches)
7. Run existing test suite (if available)

**Test Cases**:
```bash
# Test 1: Known query with results
Query: "session summary"
Expected: >0 results with combined_rank scores

# Test 2: FTS-only match (no vector match)
Query: "unique-keyword-xyz123"
Expected: Results from FTS5 only, vec_rank = NULL

# Test 3: Vector-only match (no FTS match)
Query: "semantic-concept-embedding-test"
Expected: Results from vec0 only, fts_rank = NULL

# Test 4: Hybrid match (both FTS + vec)
Query: "Context7 integration"
Expected: Results with BOTH vec_rank AND fts_rank populated
```

**Acceptance Criteria**:
- All test cases pass
- Search returns results (>0% success rate vs current 0%)
- RRF scores are reasonable (0.01 - 1.0 range)
- No TypeScript errors
- No runtime exceptions

---

### Phase 5: Documentation & Cleanup (5 min)
**Micro-tasks**:
1. Update code comments explaining SQLite compatibility fix
2. Document Context7 research source (sqlite-vec example)
3. Add inline comment explaining UNION ALL pattern
4. Update CHANGELOG or commit message
5. Remove backup file if tests pass

**Documentation Requirements**:
```typescript
/**
 * Hybrid search combining vector and keyword search with RRF
 *
 * Context7 Fix (2025-10-09): Replaced FULL OUTER JOIN with LEFT JOIN + UNION ALL
 * pattern for SQLite compatibility. Based on sqlite-vec official example:
 * https://github.com/asg017/sqlite-vec/blob/main/examples/nbc-headlines/3_search.ipynb
 *
 * Pattern: "Combining FTS and Vector Search (Keyword-first)" with UNION ALL
 * to simulate FULL OUTER JOIN behavior in SQLite.
 */
```

**Acceptance Criteria**:
- Code comments updated with Context7 reference
- UNION ALL pattern explained in comments
- Git commit message follows DevStream format
- Backup removed (if tests passed)

---

## 🧪 Testing Strategy

### Unit Tests (if test suite exists)
- Verify hybrid search returns results
- Test RRF scoring formula correctness
- Validate parameter binding

### Integration Tests
- E2E: store memory → search → verify retrieval
- Cross-session: store in session 1, retrieve in session 2
- Performance: measure query latency (<500ms target)

### Regression Prevention
- Add test case for FULL OUTER JOIN detection (should fail CI)
- Monitor search success rate (target: 95%+)

---

## 📊 Success Metrics

**Before Fix**:
- Search success rate: 0%
- Results returned: 0 (universal failure)
- User impact: 100% loss of semantic memory

**After Fix** (Target):
- Search success rate: 95%+
- Results returned: >0 for known queries
- RRF scores: Accurate (0.01-1.0 range)
- Query latency: <500ms
- Zero TypeScript errors
- Zero runtime exceptions

---

## 🚨 Rollback Plan

If implementation fails:
1. Restore backup: `cp hybrid-search.ts.backup-YYYYMMDD hybrid-search.ts`
2. Rebuild MCP server: `npm run build`
3. Restart MCP server
4. Verify FTS5-only fallback works
5. Report failure to Sonnet for alternative approach

---

## 🔗 References

**Context7 Research**:
- sqlite-vec (Trust Score 9.7): `/asg017/sqlite-vec`
- Example: `nbc-headlines/3_search.ipynb` - "Combining FTS and Vector Search (Keyword-first)"
- Pattern: LEFT JOIN + UNION ALL for SQLite FULL OUTER JOIN simulation

**Files to Modify**:
- `mcp-devstream-server/src/tools/hybrid-search.ts` (lines 163-202)

**Related Documentation**:
- Issue Report: `docs/issues/issue_ricerca_vector.md`
- Architecture: DevStream Semantic Memory System

---

## ⏱️ Time Estimates

| Phase | Duration | Complexity |
|-------|----------|------------|
| Phase 1: Backup & Preparation | 5 min | Low |
| Phase 2: SQL Refactoring | 15 min | Medium |
| Phase 3: Code Integration | 10 min | Low |
| Phase 4: Testing & Validation | 10 min | Medium |
| Phase 5: Documentation | 5 min | Low |
| **TOTAL** | **45 min** | **Medium** |

**Tier Classification**: TIER 1 (Monolithic - single file, <50K tokens, straightforward)

---

**Generated by**: Sonnet 4.5 (Research & Planning)
**Execution Model**: GLM-4.6 (Cost-optimized implementation)
**Protocol**: DevStream v2.2.0 Strategic Choice Gate
