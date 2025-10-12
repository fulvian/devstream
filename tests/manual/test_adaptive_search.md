# Test Plan: Adaptive Threshold System

**Date**: 2025-10-11
**Status**: Ready for Testing
**Prerequisites**: Claude Code restart required to load new MCP build

## Phase 1+2+3 Implementation Complete ✅

### Built Files
- `mcp-devstream-server/dist/tools/query-analyzer.js` (NEW)
- `mcp-devstream-server/dist/tools/hybrid-search.js` (UPDATED)
- `mcp-devstream-server/dist/tools/memory.js` (UPDATED)

### Build Status
```bash
npm run build
# Output: 0 errors, 0 warnings ✅
```

---

## Test Suite

### Test 1: TECHNICAL Query (Expected: 0.5% threshold, vector-weighted)

**Query**: `"session summary fixing atomic write marker file cross-session preservation SessionEnd SessionStart"`

**Expected Analysis**:
- Complexity: TECHNICAL
- Terms: 10 total, 6-8 technical terms
- Specificity: 75-85%
- Threshold: 0.5% (adaptive)
- Weights: Vector 1.5, Keyword 0.7
- Results: 5-10 relevant memories

**Why Technical**:
- High specificity terms: "SessionEnd", "SessionStart", "atomic write", "marker file"
- Multiple technical terms with high IDF scores
- Long query (10 terms)

**Database Validation**:
```sql
SELECT COUNT(*) FROM semantic_memory
WHERE content LIKE '%atomic%' OR content LIKE '%SessionEnd%' OR content LIKE '%marker file%';
-- Result: 512 records ✅
```

**MCP Command**:
```
devstream_search_memory:
  query: "session summary fixing atomic write marker file cross-session preservation SessionEnd SessionStart"
  limit: 10
```

---

### Test 2: SIMPLE Query (Expected: 3% threshold, keyword-weighted)

**Query**: `"test"`

**Expected Analysis**:
- Complexity: SIMPLE
- Terms: 1 total, 0 technical terms
- Specificity: 20-30% (common word)
- Threshold: 3% (adaptive)
- Weights: Vector 1.0, Keyword 1.2
- Results: 1-5 generic results (if any pass 3% threshold)

**Why Simple**:
- Single common term
- Low specificity (appears in many documents)
- Short query

**MCP Command**:
```
devstream_search_memory:
  query: "test"
  limit: 5
```

---

### Test 3: COMPLEX Query (Expected: 1% threshold, balanced)

**Query**: `"RRF hybrid search combining vector similarity and keyword matching"`

**Expected Analysis**:
- Complexity: COMPLEX
- Terms: 8 total, 3-4 technical terms
- Specificity: 60-70%
- Threshold: 1% (adaptive)
- Weights: Vector 1.2, Keyword 1.0 (slight vector preference)
- Results: 3-8 relevant memories about hybrid search

**Why Complex**:
- Multiple terms (8)
- Mix of technical ("RRF", "vector similarity") and common ("combining", "and")
- Medium-high specificity

**MCP Command**:
```
devstream_search_memory:
  query: "RRF hybrid search combining vector similarity and keyword matching"
  limit: 10
```

---

### Test 4: MEDIUM Query (Expected: 2% threshold, balanced)

**Query**: `"async database query performance"`

**Expected Analysis**:
- Complexity: MEDIUM
- Terms: 4 total, 2 technical terms
- Specificity: 45-55%
- Threshold: 2% (adaptive)
- Weights: Vector 1.0, Keyword 1.0 (balanced)
- Results: 2-6 relevant memories

**Why Medium**:
- Moderate length (4 terms)
- Mix of technical and common terms
- Average specificity

**MCP Command**:
```
devstream_search_memory:
  query: "async database query performance"
  limit: 8
```

---

## Expected Output Format

### With Adaptive System (Phase 3)

```
🔍 **DevStream Adaptive Hybrid Search Results**

Query: "session summary fixing atomic write..."
Complexity: TECHNICAL (10 terms, 80% specificity)
Method: Hybrid (Vector + Keyword)
Threshold: 0.5% (adaptive)
Weights: Vector 1.5 / Keyword 0.7
Found: 8 results

1. 🧠 **LEARNING** Memory
   📊 Relevance: HIGH (RRF Score: 2.3)
   🔬 Vector Rank: #1 (distance: 0.4150) • Keyword Rank: #3
   💾 Content: Implemented atomic write pattern for cross-session...
   🆔 ID: `abc123def456`
   📅 Created: 10/10/2025

...
```

### Console Logs (stderr)

```
📊 Analyzing query complexity...
📊 Query Analysis: technical complexity
   Terms: 10 total, 7 technical
   Specificity: 82%
   Recommended Threshold: 0.5%
   Recommended Weights: vec=1.5 fts=0.7
   Technical query: 7/10 technical terms, 82% specificity. Using minimal threshold (0.5%) and vector-weighted search.
🔍 Performing hybrid search for: "session summary fixing..."
📊 Filtering results with threshold: 0.5% (adaptive)
✅ Hybrid search completed: 12 results
✅ After filtering: 8 results passed threshold
```

---

## Validation Checklist

### Before Testing
- [ ] Restart Claude Code to load new MCP build
- [ ] Verify MCP server connects: `mcp__devstream__devstream_list_tasks`
- [ ] Check database: 105K semantic_memory records, 89K vectors

### During Testing
- [ ] **Test 1 (Technical)**: Returns 5-10 results, threshold 0.5%, vector-weighted
- [ ] **Test 2 (Simple)**: Returns 0-5 results, threshold 3%, keyword-weighted
- [ ] **Test 3 (Complex)**: Returns 3-8 results, threshold 1%, balanced
- [ ] **Test 4 (Medium)**: Returns 2-6 results, threshold 2%, balanced

### Success Criteria
- [ ] QueryAnalyzer initializes without errors
- [ ] IDF cache builds from corpus (105K records)
- [ ] Complexity classification works for all 4 levels
- [ ] Adaptive thresholds override default (0.01)
- [ ] Adaptive weights applied in search
- [ ] Output shows analysis summary
- [ ] **MOST IMPORTANT**: Test 1 returns results (was failing before Phase 1-3)

---

## Troubleshooting

### Issue: "No Memory Results Found" for Test 1
**Diagnosis**:
1. Check if QueryAnalyzer initialized: Look for "✅ QueryAnalyzer initialized" in logs
2. Check threshold used: Should show "0.5% (adaptive)" not "1.0% (user-specified)"
3. Check RRF scores: Vector-only results at rank #1 = 1.64% should pass 0.5% threshold

**Fix**:
- If threshold is wrong: Check `analysis.recommendedThreshold` in memory.ts:212
- If IDF cache empty: Check QueryAnalyzer initialization in query-analyzer.ts:80-113
- If weights wrong: Check WEIGHT_MAP in query-analyzer.ts:58-63

### Issue: TypeScript compilation errors
**Fix**: Rebuild with `npm run build` in mcp-devstream-server/

### Issue: MCP server not responding
**Fix**: Restart Claude Code completely

---

## Documentation Updates (After Testing)

Once all tests pass, update:
- [ ] `docs/implementation/HYBRID_SEARCH.md` - Add Phase 3 section
- [ ] `docs/verification/adaptive-threshold-test-results.md` - Create test report
- [ ] `CLAUDE.md` - Update vector search optimization section

---

**Next Action**: Restart Claude Code and run Test 1 first (the original failing query).
