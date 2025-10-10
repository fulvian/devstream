# GLM-4.6 Handoff Prompt: Fix Critical Vector Search Engine Failure

**Task ID**: 6e63cfeb622dc7f16e9b38316589a5a5
**Handoff From**: Sonnet 4.5 (Research & Planning)
**Handoff To**: GLM-4.6 (Execution)
**Date**: 2025-10-09
**Protocol**: DevStream v2.2.0 Strategic Choice Gate

---

## 📋 COPY THIS ENTIRE PROMPT TO NEW GLM-4.6 SESSION

```
Sono GLM-4.6 e sto ricevendo un handoff da Sonnet 4.5 per un task DevStream CRITICO.

**Task DevStream**:
- **ID**: 6e63cfeb622dc7f16e9b38316589a5a5
- **Title**: Fix Critical Vector Search Engine Failure
- **Status**: active (approvato per implementazione)
- **Priority**: P0 - BLOCKER
- **Type**: coding
- **Phase**: Core Engine & Infrastructure

**Fase Corrente**: STEP 6 - IMPLEMENTATION (Sonnet ha completato Steps 1-5: DISCUSSION, ANALYSIS, RESEARCH, PLANNING, APPROVAL)

---

## 🎯 CONTESTO CRITICO

### Problema
Il sistema di ricerca semantica DevStream è **completamente non funzionante**:
- Storage: ✅ FUNZIONA (47,904 memorie, 15,588 con embeddings)
- FTS5 keyword search: ✅ FUNZIONA (15,589 entries indicizzate)
- Hybrid search (RRF): ❌ FALLISCE (0% success rate - 0 risultati SEMPRE)

### Root Cause (identificata da Sonnet)
**Location**: `mcp-devstream-server/src/tools/hybrid-search.ts:163-202`
**Issue**: SQL query usa `FULL OUTER JOIN` che SQLite NON supporta
**Impact**: Query fallisce silenziosamente → 0 risultati

### Esempio Query Fallita
```sql
-- CORRENTE (NON FUNZIONA in SQLite)
FROM fts_matches
FULL OUTER JOIN vec_matches ON vec_matches.memory_id = fts_matches.memory_id
JOIN semantic_memory ON semantic_memory.id = COALESCE(fts_matches.memory_id, vec_matches.memory_id)
```

---

## 🔬 RICERCA CONTEXT7 COMPLETATA (da Sonnet)

**Fonte**: sqlite-vec (Trust Score 9.7, 122 code snippets)
**Reference**: `/asg017/sqlite-vec` - Official example `nbc-headlines/3_search.ipynb`
**Pattern Approvato**: "Combining FTS and Vector Search (Keyword-first)" con UNION ALL

**Paradosso scoperto**: L'esempio UFFICIALE sqlite-vec usa FULL OUTER JOIN, MA SQLite non lo supporta! Soluzione: pattern alternativo UNION ALL dello stesso autore.

---

## 📝 PIANO DI IMPLEMENTAZIONE (già approvato)

Leggi il piano completo qui: `/Users/fulvioventura/devstream/docs/development/plan/piano_fix-vector-search-engine.md`

**Summary delle 5 Fasi**:
1. **Backup & Preparation** (5 min) - Backup file, locate tests
2. **SQL Query Refactoring** (15 min) - Replace FULL OUTER JOIN con UNION ALL
3. **Code Integration** (10 min) - Update hybrid-search.ts
4. **Testing & Validation** (10 min) - E2E tests, verify results
5. **Documentation & Cleanup** (5 min) - Update comments, cleanup

**Total**: 45 minuti stimati

---

## 🛠️ TUO COMPITO (GLM-4.6)

### STEP 6: IMPLEMENTATION - Esegui il piano

**CRITICAL RULES**:
1. ✅ **Segui il piano ESATTAMENTE** (`piano_fix-vector-search-engine.md`)
2. ✅ **TodoWrite OBBLIGATORIO** - Crea todo list dalle 5 fasi PRIMA di iniziare
3. ✅ **Un micro-task alla volta** - Mark "in_progress" → lavora → mark "completed"
4. ✅ **Test DOPO ogni fase** - Valida prima di procedere
5. ✅ **DevStream Protocol Compliance** - Follow CLAUDE.md rules
6. ⚠️ **NO improvvisazione** - Se il piano non è chiaro, CHIEDI all'utente
7. ⚠️ **NO skip testing** - Testing è MANDATORY (DevStream rule)

### File da Modificare
**Path esatto**: `/Users/fulvioventura/devstream/mcp-devstream-server/src/tools/hybrid-search.ts`
**Lines to change**: 163-202 (SQL query con FULL OUTER JOIN)

### SQL Query Target (Context7-backed)
```typescript
// Context7 pattern: LEFT JOIN + UNION ALL per simulare FULL OUTER JOIN in SQLite
const sql = `
  WITH vec_matches AS (
    SELECT
      memory_id,
      ROW_NUMBER() OVER (ORDER BY distance) as rank_number,
      distance
    FROM vec_semantic_memory
    WHERE embedding MATCH ?
      AND k = ?
  ),
  fts_matches AS (
    SELECT
      memory_id,
      ROW_NUMBER() OVER (ORDER BY rank) as rank_number,
      rank as score
    FROM fts_semantic_memory
    WHERE fts_semantic_memory MATCH ?
    LIMIT ?
  ),
  combined AS (
    -- FTS results
    SELECT
      memory_id,
      NULL as vec_rank,
      rank_number as fts_rank,
      NULL as vec_distance,
      score as fts_score
    FROM fts_matches

    UNION ALL

    -- Vector results
    SELECT
      memory_id,
      rank_number as vec_rank,
      NULL as fts_rank,
      distance as vec_distance,
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
`;
```

**IMPORTANTE**:
- Mantieni gli 8 parametri nell'ORDINE ESATTO: `[embeddingBuffer, k, sanitizedQuery, k, rrf_k, weight_fts, rrf_k, weight_vec]`
- GROUP BY è CRITICO per evitare duplicati
- MAX() per vec_rank/fts_rank gestisce NULL correttamente

### Comandi da Eseguire
```bash
# 1. Backup (Fase 1)
cp mcp-devstream-server/src/tools/hybrid-search.ts mcp-devstream-server/src/tools/hybrid-search.ts.backup-20251009

# 2. Edit file (Fase 2-3)
# Usa Edit tool per modificare hybrid-search.ts:163-202

# 3. Rebuild MCP server (Fase 4)
cd mcp-devstream-server && npm run build

# 4. Test (Fase 4)
# Usa mcp__devstream__devstream_search_memory per testare
# Query: "session summary" - Expected: >0 results
```

### Acceptance Criteria (MANDATORY)
- [ ] No FULL OUTER JOIN in query
- [ ] TypeScript compila senza errori
- [ ] npm run build completa con successo
- [ ] Test query "session summary" ritorna >0 risultati
- [ ] RRF scores ragionevoli (0.01-1.0 range)
- [ ] Tutti i TODO marcati "completed"
- [ ] Code comments aggiornati con Context7 reference

---

## 📊 STATO ATTUALE TASK DEVSTREAM

```bash
# Verifica stato task
mcp__devstream__devstream_list_tasks con task_id: 6e63cfeb622dc7f16e9b38316589a5a5

# Dopo ogni fase, aggiorna con:
mcp__devstream__devstream_update_task con notes: "Fase X completata - [risultato]"
```

**Status Corrente**: active (in implementazione)
**Next Step**: Inizia Fase 1 (Backup & Preparation) con TodoWrite

---

## 🚨 REGOLE DEVSTREAM CRITICHE

Dal file CLAUDE.md (MANDATORY):

1. **TodoWrite OBBLIGATORIO** (line 587-590)
   - Crea TodoWrite list PRIMA di iniziare implementazione
   - Micro-task 10-15 min max
   - Mark in_progress → work → completed
   - ONE task in_progress at a time

2. **Testing MANDATORY** (line 592-595)
   - 95%+ coverage for NEW code
   - 100% pass rate before marking completed
   - NO commit with failing tests

3. **Python Environment** (line 544-578)
   - SEMPRE usa `.devstream/bin/python` (NOT system python)
   - Hook system usa venv

4. **Research-Driven Development** (line 654-656)
   - Context7 findings già applicati (sqlite-vec pattern)
   - NO deviazioni dal piano approvato

5. **Micro-Task Execution** (line 658-660)
   - ONE task at a time
   - Verify integration dopo OGNI task
   - Update docs in real-time

---

## 🎯 SUCCESS METRICS (da raggiungere)

**Before Fix** (stato attuale):
- Search success rate: 0%
- Results returned: 0
- User impact: 100% loss of semantic memory

**After Fix** (target):
- Search success rate: 95%+
- Results returned: >0 for known queries
- RRF scores: 0.01-1.0 range
- Query latency: <500ms
- TypeScript: zero errors
- Runtime: zero exceptions

---

## 📞 ESCALATION

Se incontri problemi:
1. **Blockers tecnici**: Chiedi all'utente (non improvvisare)
2. **Plan ambiguità**: Richiedi chiarimenti
3. **Test failures**: Document error, rollback con backup, report

**Rollback Command**:
```bash
cp mcp-devstream-server/src/tools/hybrid-search.ts.backup-20251009 mcp-devstream-server/src/tools/hybrid-search.ts
cd mcp-devstream-server && npm run build
```

---

## ✅ START IMPLEMENTATION

**Your first action as GLM-4.6**:

1. ✅ Conferma ricezione handoff (rispondi "Handoff ricevuto, inizio implementazione")
2. ✅ Crea TodoWrite list dalle 5 fasi del piano
3. ✅ Mark Fase 1 todo "in_progress"
4. ✅ Inizia Fase 1: Backup & Preparation

**Remember**: Segui il piano ESATTAMENTE. No improvvisazioni. Ask if unclear.

---

**Handoff generato da**: Sonnet 4.5
**Data**: 2025-10-09 18:45
**Protocol**: DevStream v2.2.0 Strategic Choice Gate
**Quality**: Research-backed (Context7 Trust Score 9.7)
```

---

## 🔄 ISTRUZIONI PER L'UTENTE - Come Completare l'Handoff

1. **Copia il prompt** (tutto il blocco ``` sopra)
2. **Chiudi questa sessione Sonnet**
3. **Apri nuova sessione GLM-4.6**
4. **Incolla il prompt completo**
5. **GLM inizierà l'implementazione** seguendo il piano

**Alternative**: Se preferisci, posso salvare il prompt in un file che puoi copiare più facilmente.

---

**Generated by**: Sonnet 4.5 (Planning & Research Phase)
**For**: GLM-4.6 (Execution Phase)
**Protocol**: DevStream v2.2.0 Strategic Choice Gate
