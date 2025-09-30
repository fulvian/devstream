# Phase 3 Real-World Testing Guide

**Version**: 1.0.0
**Date**: 2025-09-30
**Purpose**: Manual testing protocol for SessionEnd implementation

---

## 🚀 STEP 1: Deployment

### 1.1 Verify Current Configuration

Prima di tutto, verifica che tutto sia configurato correttamente:

```bash
# Check settings.json (SessionEnd hook)
cat .claude/settings.json | grep -A 8 "SessionEnd"

# Expected output:
# "SessionEnd": [
#   {
#     "matcher": "",
#     "hooks": [
#       {
#         "type": "command",
#         "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/sessions/session_end.py",
#         "timeout": 45
```

**✅ Se vedi session_end.py con timeout 45 → OK, procedi**
**❌ Se vedi stop.py o altro → Aggiorna settings.json prima**

### 1.2 Verify Hook Files Exist

```bash
# Check all Phase 3 files exist
ls -lh .claude/hooks/devstream/sessions/

# Expected output:
# session_data_extractor.py (363 lines)
# session_summary_generator.py (477 lines)
# session_end.py (386 lines)
# session_start.py (existing)
# work_session_manager.py (existing)
```

### 1.3 Verify Database State

```bash
# Check work_sessions table
.devstream/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/devstream.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM work_sessions')
print(f'work_sessions records: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM semantic_memory WHERE embedding IS NOT NULL')
print(f'memories with embeddings: {cursor.fetchone()[0]}')
conn.close()
"
```

**Expected**:
- work_sessions: 1+ records (at least the test session)
- memories with embeddings: 100+ records

---

## 🧪 STEP 2: Real-World Testing Protocol

### Test Session Structure

Simuleremo una vera sessione di lavoro DevStream con:
1. **Fase iniziale**: Creazione task e discussione
2. **Fase di sviluppo**: Scrittura codice
3. **Fase di testing**: Test e validazione
4. **Chiusura sessione**: Trigger SessionEnd hook

---

## 📝 PROMPT SEQUENCE (Copia-incolla questi prompt uno alla volta)

### PROMPT 1: Session Initialization (Simula SessionStart)

```
Crea un nuovo file di test per validare il sistema di session summary.

Crea: test_session_validation.py

Contenuto:
- Funzione test_session_workflow() che stampa "Session test started"
- Funzione validate_summary() che ritorna True
- Main block che chiama entrambe

Usa best practices Python con docstrings.
```

**Cosa aspettarci**:
- File creato via Write tool
- PostToolUse hook si attiva (memoria automatica)
- Log in ~/.claude/logs/devstream/post_tool_use.log

**DOPO IL PROMPT, INSERISCI QUI IL LOG DI RISPOSTA**:
```
[TU INSERISCI L'OUTPUT DI CLAUDE]
```

---

### PROMPT 2: Architectural Decision (Simula decision recording)

```
Analizza il codice che abbiamo appena scritto e suggerisci un miglioramento architetturale.

Poi implementa il miglioramento modificando il file test_session_validation.py aggiungendo:
- Error handling con try/except
- Logging strutturato
- Return codes appropriati
```

**Cosa aspettarci**:
- Edit tool utilizzato
- PostToolUse hook registra la modifica
- Decision registrata in semantic_memory

**DOPO IL PROMPT, INSERISCI QUI IL LOG DI RISPOSTA**:
```
[TU INSERISCI L'OUTPUT DI CLAUDE]
```

---

### PROMPT 3: Code Implementation (Simula implementazione)

```
Ora implementa una classe SessionValidator in un nuovo file validators.py che:
- Valida session_id (non vuoto, lunghezza corretta)
- Valida timestamps (started_at < ended_at)
- Valida duration (> 0 minuti)
- Ritorna ValidationResult con success: bool e errors: List[str]
```

**Cosa aspettarci**:
- Nuovo file creato
- PostToolUse hook si attiva
- Memory storage con content_type="code"

**DOPO IL PROMPT, INSERISCI QUI IL LOG DI RISPOSTA**:
```
[TU INSERISCI L'OUTPUT DI CLAUDE]
```

---

### PROMPT 4: Testing & Validation (Simula testing)

```
Crea unit test per SessionValidator in test_validators.py con pytest:
- test_valid_session_id()
- test_invalid_session_id_empty()
- test_invalid_timestamps()
- test_negative_duration()

Usa pytest fixtures e assert statements appropriati.
```

**Cosa aspettarci**:
- File di test creato
- PostToolUse hook registra
- Learning potenzialmente catturato

**DOPO IL PROMPT, INSERISCI QUI IL LOG DI RISPOSTA**:
```
[TU INSERISCI L'OUTPUT DI CLAUDE]
```

---

### PROMPT 5: Documentation (Simula documentazione)

```
Crea un README.md nella cartella tests/integration/sessions/ che documenta:
- Cosa fanno questi test
- Come eseguirli
- Cosa validano
- Expected output

Mantienilo conciso (max 50 righe).
```

**Cosa aspettarci**:
- README creato
- PostToolUse hook si attiva
- Content_type="documentation"

**DOPO IL PROMPT, INSERISCI QUI IL LOG DI RISPOSTA**:
```
[TU INSERISCI L'OUTPUT DI CLAUDE]
```

---

### 🎯 PROMPT 6: SESSION CLOSE (Trigger SessionEnd)

**IMPORTANTE**: Questo è il prompt chiave che testerà SessionEnd hook

```
Perfetto! Abbiamo completato il lavoro su questa feature.

Fammi un summary di quello che abbiamo fatto in questa sessione:
- Quanti file abbiamo creato/modificato?
- Quali decisioni architetturali abbiamo preso?
- Cosa abbiamo imparato?

Poi chiudi la sessione.
```

**Cosa aspettarci**:
- Claude genera un summary manuale
- **POI** quando chiudi Claude Code (Command+Q o chiusura finestra)
- SessionEnd hook si attiva automaticamente
- Summary viene generato e salvato in semantic_memory

**DOPO LA CHIUSURA, ESEGUI QUESTI COMANDI**:

```bash
# 1. Check session was created
.devstream/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/devstream.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT id, session_name, status, started_at, ended_at
    FROM work_sessions
    ORDER BY started_at DESC
    LIMIT 1
''')
row = cursor.fetchone()
if row:
    print(f'Last Session:')
    print(f'  ID: {row[0]}')
    print(f'  Name: {row[1]}')
    print(f'  Status: {row[2]}')
    print(f'  Started: {row[3]}')
    print(f'  Ended: {row[4]}')
else:
    print('No sessions found')
conn.close()
"

# 2. Check SessionEnd summary was created
.devstream/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/devstream.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT id, content, created_at, embedding IS NOT NULL as has_embedding
    FROM semantic_memory
    WHERE content_type = 'context'
    AND content LIKE '%DevStream Session Summary%'
    ORDER BY created_at DESC
    LIMIT 1
''')
row = cursor.fetchone()
if row:
    print(f'\nSessionEnd Summary Found:')
    print(f'  ID: {row[0][:20]}...')
    print(f'  Created: {row[2]}')
    print(f'  Has Embedding: {\"✅\" if row[3] else \"❌\"}')
    print(f'\nSummary Preview (first 500 chars):')
    print('-' * 60)
    print(row[1][:500])
    print('...')
else:
    print('\n❌ No SessionEnd summary found!')
conn.close()
"

# 3. Check SessionEnd logs
tail -50 ~/.claude/logs/devstream/session_end.log 2>/dev/null || echo "No session_end.log yet"
```

**INSERISCI QUI L'OUTPUT DEI COMANDI SOPRA**:
```
[TU INSERISCI L'OUTPUT]
```

---

## 📊 STEP 3: Validation Checks

Dopo aver completato tutti i prompt e chiuso la sessione, verifica:

### Check 1: Session Record Created

```bash
sqlite3 data/devstream.db "SELECT id, session_name, status FROM work_sessions ORDER BY started_at DESC LIMIT 1;"
```

**Expected**:
- Session con status="completed"
- ended_at popolato

### Check 2: Files Recorded in Memory

```bash
.devstream/bin/python -c "
import sqlite3
from datetime import datetime, timedelta
conn = sqlite3.connect('data/devstream.db')
cursor = conn.cursor()

# Get session start time
cursor.execute('SELECT started_at FROM work_sessions ORDER BY started_at DESC LIMIT 1')
session_start = cursor.fetchone()[0]

# Count files modified in this session
cursor.execute('''
    SELECT COUNT(*)
    FROM semantic_memory
    WHERE content_type = 'code'
    AND created_at >= ?
''', (session_start,))

print(f'Files recorded: {cursor.fetchone()[0]}')
conn.close()
"
```

**Expected**: 4-5 files (test_session_validation.py, validators.py, test_validators.py, README.md)

### Check 3: Summary Generated

```bash
.devstream/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/devstream.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT content
    FROM semantic_memory
    WHERE content_type = 'context'
    AND content LIKE '%DevStream Session Summary%'
    ORDER BY created_at DESC
    LIMIT 1
''')
row = cursor.fetchone()
if row:
    print('✅ Summary Generated!')
    print(row[0])
else:
    print('❌ No summary found')
conn.close()
"
```

**Expected**: Markdown summary con sezioni:
- Work Accomplished
- Key Decisions
- Lessons Learned

### Check 4: Embedding Generated

```bash
.devstream/bin/python -c "
import sqlite3
import json
conn = sqlite3.connect('data/devstream.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT embedding
    FROM semantic_memory
    WHERE content_type = 'context'
    AND content LIKE '%DevStream Session Summary%'
    ORDER BY created_at DESC
    LIMIT 1
''')
row = cursor.fetchone()
if row and row[0]:
    embedding = json.loads(row[0])
    print(f'✅ Embedding found: {len(embedding)} dimensions')
    print(f'   First 5 values: {embedding[:5]}')
else:
    print('❌ No embedding found')
conn.close()
"
```

**Expected**:
- 768 dimensions (embeddinggemma:300m)
- Valid float values

---

## 🐛 STEP 4: Troubleshooting

### Se SessionEnd non si attiva:

```bash
# Check hook configuration
cat .claude/settings.json | grep -A 10 "SessionEnd"

# Check hook file exists
ls -lh .claude/hooks/devstream/sessions/session_end.py

# Check permissions
chmod +x .claude/hooks/devstream/sessions/session_end.py

# Test hook manually
.devstream/bin/python .claude/hooks/devstream/sessions/session_end.py
```

### Se Summary non viene generato:

```bash
# Check for errors in logs
cat ~/.claude/logs/devstream/session_end.log

# Check database connection
.devstream/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/devstream.db')
print('✅ Database connection OK')
conn.close()
"

# Test SessionDataExtractor manually
.devstream/bin/python .claude/hooks/devstream/sessions/session_data_extractor.py
```

### Se Embedding non viene generato:

```bash
# Check Ollama is running
curl http://localhost:11434/api/version

# Test embedding generation manually
.devstream/bin/python .claude/hooks/devstream/utils/ollama_client.py

# Check embedding dimensions
.devstream/bin/python -c "
from pathlib import Path
import sys
sys.path.insert(0, str(Path('.claude/hooks/devstream/utils')))
from ollama_client import OllamaEmbeddingClient
client = OllamaEmbeddingClient()
if client.test_connection():
    print('✅ Ollama connection OK')
    embedding = client.generate_embedding('test')
    if embedding:
        print(f'✅ Embedding generated: {len(embedding)}D')
else:
    print('❌ Ollama connection failed')
"
```

---

## ✅ Success Criteria

**Phase 3 deployment is successful if**:

1. ✅ **Session created**: work_sessions table has new record
2. ✅ **Files recorded**: 4-5 files in semantic_memory (content_type="code")
3. ✅ **Summary generated**: Markdown summary in semantic_memory (content_type="context")
4. ✅ **Embedding created**: Summary has 768D embedding
5. ✅ **Session closed**: work_sessions status="completed"
6. ✅ **No errors**: No blocking errors in logs

---

## 📝 REPORTING FORMAT

Dopo aver completato il testing, riporta i risultati in questo formato:

```markdown
## Phase 3 Real-World Testing Results

**Date**: 2025-09-30
**Duration**: [XX minuti]

### Prompt Sequence Results

✅/❌ Prompt 1 (Session Init): [RESULT]
✅/❌ Prompt 2 (Decision): [RESULT]
✅/❌ Prompt 3 (Implementation): [RESULT]
✅/❌ Prompt 4 (Testing): [RESULT]
✅/❌ Prompt 5 (Documentation): [RESULT]
✅/❌ Prompt 6 (Session Close): [RESULT]

### Validation Results

✅/❌ Session Record: [ID, status]
✅/❌ Files Recorded: [N files]
✅/❌ Summary Generated: [Yes/No]
✅/❌ Embedding Created: [768D/None]
✅/❌ No Errors: [Clean/Errors found]

### Issues Found

1. [Issue description]
2. [Issue description]

### Overall Result

✅ SUCCESS / ❌ FAILED

**Recommendation**: [DEPLOY / FIX ISSUES / INVESTIGATE]
```

---

**Ready to start testing?**

Inizia con PROMPT 1 e procedi sequenzialmente. Dopo ogni prompt, inserisci qui la risposta di Claude e i log per validazione. 🚀