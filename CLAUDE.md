# CLAUDE.md - DevStream Project Rules

Questo file definisce la metodologia di lavoro e le best practice per lo sviluppo del progetto DevStream - Sistema Integrato Task Management & Memoria Cross-Session per Claude Code.

## 📋 Metodologia DevStream

### 🎯 Core Principles

**La nostra metodologia si basa su 4 pilastri fondamentali:**

1. **Discussione e Confronto** - Analisi collaborativa di obiettivi e specifiche
2. **Divisione Strutturata** - Breakdown in fasi e micro-task granulari
3. **Research-Driven Development** - Utilizzo Context7 per best practice
4. **Verification & Testing** - Verifiche severe e test completi del codice

### 🔄 Workflow di Sviluppo

#### Phase 1: Discussione e Analisi Obiettivi
```
🎯 OBIETTIVO: Definire chiaramente cosa implementare
📋 ATTIVITÀ:
- Analizzare requisiti e specifiche tecniche
- Discussione su trade-offs architetturali
- Identificazione di vincoli e dipendenze
- Consensus su approccio implementativo

✅ DELIVERABLE: Specifiche chiare e approvate
```

#### Phase 2: Divisione in Fasi e Micro-Task
```
🎯 OBIETTIVO: Breakdown granulare per tracciabilità
📋 ATTIVITÀ:
- Dividere implementazione in fasi logiche (A, B, C, D)
- Creare micro-task da max 10 minuti ciascuno
- Definire dipendenze tra task
- Stabilire criterio di completion per ogni task

✅ DELIVERABLE: Task list strutturata con TodoWrite
```

#### Phase 3: Research con Context7
```
🎯 OBIETTIVO: Identificare best practice e soluzioni validate
📋 ATTIVITÀ:
- Ricerca documentazione tecnica via Context7
- Identificazione di pattern e snippet di codice
- Validazione di approcci architetturali
- Acquisizione di best practice da progetti esistenti

✅ DELIVERABLE: Soluzioni research-backed documentate
```

#### Phase 4: Implementazione Guidata
```
🎯 OBIETTIVO: Sviluppo step-by-step con validazione continua
📋 ATTIVITÀ:
- Implementazione task per task con approval
- Revisione e discussione per ogni step
- Integrazione incrementale con testing
- Documentazione in-line del codice

✅ DELIVERABLE: Codice production-ready implementato
```

#### Phase 5: Verification & Testing
```
🎯 OBIETTIVO: Validazione severa di qualità e funzionalità
📋 ATTIVITÀ:
- Test unitari e di integrazione completi
- Validazione performance e scalabilità
- Code review e quality assurance
- Testing in scenari real-world

✅ DELIVERABLE: Sistema validato e production-ready
```

## 🐍 Python Virtual Environment Management

### 🚨 REGOLA CRITICA: Gestione Ambiente Python

**SEMPRE utilizzare il venv di progetto per TUTTI i comandi Python.**

#### Configurazione Venv Standard
```bash
# Nome venv: .[nome_root_progetto]
# Per DevStream: .devstream
# Python version: 3.11
# Location: project_root/.devstream/
```

#### Workflow Obbligatorio

**1. All'Inizio di OGNI Sessione**
```bash
# Check 1: Verificare esistenza venv
if [ ! -d ".devstream" ]; then
  echo "❌ Venv non trovato - creazione necessaria"
  # Trigger creazione (vedi sotto)
fi

# Check 2: Verificare Python version
.devstream/bin/python --version  # Must be Python 3.11.x

# Check 3: Verificare dipendenze critiche
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp|structlog)"
# Se mancanti → installare
```

**2. Prima Installazione (Se Venv Non Esiste)**
```bash
# Step 1: Creare venv con Python 3.11
python3.11 -m venv .devstream

# Step 2: Upgrade pip
.devstream/bin/python -m pip install --upgrade pip

# Step 3: Installare dipendenze base
.devstream/bin/python -m pip install -r requirements.txt

# Step 4: Installare dipendenze hook system
.devstream/bin/python -m pip install "cchooks>=0.1.4" "aiohttp>=3.8.0" "structlog>=23.0.0" "python-dotenv>=1.0.0"

# Step 5: Verificare installazione
.devstream/bin/python -m pip list | head -20
```

**3. Esecuzione Comandi Python**
```bash
# ❌ MAI usare python globale
python script.py                    # WRONG
python3 script.py                   # WRONG
uv run --script script.py           # WRONG (crea ambiente isolato)

# ✅ SEMPRE usare venv di progetto
.devstream/bin/python script.py     # CORRECT
.devstream/bin/python -m pytest     # CORRECT
.devstream/bin/python -m pip install pkg  # CORRECT
```

**4. Hook System Configuration**
```json
// .claude/settings.json
{
  "hooks": {
    "PreToolUse": [{
      "hooks": [{
        "command": "\"$CLAUDE_PROJECT_DIR\"/.devstream/bin/python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/devstream/memory/pre_tool_use.py"
      }]
    }]
  }
}
```

#### Troubleshooting Common Issues

**Problema**: `ModuleNotFoundError: No module named 'xxx'`
```bash
# Soluzione:
.devstream/bin/python -m pip install xxx
```

**Problema**: Hook non si eseguono
```bash
# Check 1: Venv esiste?
ls -la .devstream/bin/python

# Check 2: Dipendenze hook presenti?
.devstream/bin/python -m pip list | grep cchooks

# Check 3: Settings.json corretto?
cat .claude/settings.json | grep -A 2 "command"
```

**Problema**: Python version sbagliata
```bash
# Ricreare venv con version corretta
rm -rf .devstream
python3.11 -m venv .devstream
.devstream/bin/python -m pip install -r requirements.txt
```

#### Best Practices

1. **✅ Commit `.python-version`** se usi pyenv
2. **❌ NON committare `.devstream/`** (già in .gitignore)
3. **✅ Documentare dipendenze** in requirements.txt o pyproject.toml
4. **✅ Pin versioni critiche** (e.g., `cchooks==0.1.4`)
5. **✅ Test su venv pulito** prima di commit

---

## 🛠 Tools e Strumenti

### Context7 Integration
```bash
# Utilizzo Context7 per research
1. Identify tecnologia/pattern necessario
2. Use mcp__context7__resolve-library-id per identificare library
3. Use mcp__context7__get-library-docs per documentazione/snippet
4. Validate best practices attraverso research
5. Implement solution basata su findings
```

### TodoWrite Management
```bash
# Gestione task granulari
1. Create todo list con TodoWrite per ogni phase
2. Mark in_progress prima di iniziare task
3. Complete immediatamente dopo finish
4. Update progress con stato dettagliato
5. Track lessons learned per future reference
```

### Testing Strategy
```bash
# Testing severo e completo
1. Unit tests per ogni component
2. Integration tests per workflow end-to-end
3. Performance testing con metrics
4. Error handling validation
5. Real-world scenario testing
```

## 📖 Documentation Standards

### Code Documentation
- **Docstrings completi** per ogni classe e funzione
- **Type hints** per tutti i parametri e return values
- **Inline comments** per logica complessa
- **Architecture decisions** documentate in-code

### Progress Documentation
- **Todo tracking** con TodoWrite tool
- **Implementation notes** per ogni phase
- **Lessons learned** capture per future reference
- **Decision rationale** per scelte architetturali

## 🎯 Quality Standards

### Code Quality
- **Type Safety**: Full typing con mypy compliance
- **Error Handling**: Structured exception hierarchy
- **Performance**: Async operations dove appropriato
- **Maintainability**: Clean code principles
- **Testing**: 95%+ coverage target

### Architecture Quality
- **SOLID Principles**: Single responsibility, open/closed, etc.
- **Separation of Concerns**: Clear module boundaries
- **Dependency Injection**: Loose coupling patterns
- **Configuration Management**: Environment-based config
- **Logging**: Structured logging con context

## 🚀 Implementation Patterns

### Research-Driven Development
```python
# Pattern: Context7 Research → Implementation
1. Research: Use Context7 per best practices
2. Design: Create architecture basata su research
3. Implement: Follow validated patterns
4. Test: Verify con comprehensive testing
5. Document: Capture lessons learned
```

### Micro-Task Execution
```python
# Pattern: Task Breakdown → Execution
1. Analyze: Break down complex feature
2. Plan: Create granular task list (max 10min each)
3. Execute: One task at a time con approval
4. Verify: Test dopo ogni task completion
5. Integrate: Merge con existing codebase
```

### Approval Workflow
```python
# Pattern: Discuss → Approve → Implement
1. Discuss: Present approach e trade-offs
2. Research: Use Context7 per validation
3. Approve: Get consensus prima di implementation
4. Implement: Follow approved approach
5. Review: Validate results insieme
```

## 📊 Success Metrics

### Development Metrics
- **Task Completion Rate**: 100% task marked completed
- **Test Coverage**: 95%+ per tutti i moduli
- **Code Quality**: Zero mypy errors, minimal complexity
- **Documentation**: Complete docstring coverage
- **Performance**: Meet or exceed performance targets

### Process Metrics
- **Research Quality**: Context7 usage per ogni major decision
- **Collaboration**: Clear approval workflow adherence
- **Learning**: Documented lessons learned per phase
- **Innovation**: Research-backed technology choices
- **Delivery**: On-time delivery di production-ready code

## 🔧 DevStream-Specific Rules

### 📁 File Organization & Project Structure

**CRITICAL: SEMPRE seguire la struttura definita in PROJECT_STRUCTURE.md**

#### Documentation Files
- **NEVER create .md files in project root** (eccetto README.md, CLAUDE.md, PROJECT_STRUCTURE.md)
- **USE docs/ directory** con struttura organizzata per categoria:
  ```
  docs/
  ├── architecture/     # System design, technical decisions, schema
  ├── api/             # API reference, JSON schemas
  ├── development/     # Developer guides, roadmap, methodology
  ├── deployment/      # Production deployment, validation reports
  ├── guides/          # Practical guides, quick references
  ├── tutorials/       # Hands-on tutorials
  └── idee_fondanti/   # Foundational concepts, vision
  ```

**Esempi corretti**:
- ✅ `docs/deployment/post-restart-validation-issues.md`
- ✅ `docs/architecture/hook-system-design.md`
- ✅ `docs/development/phase-completion-report.md`
- ❌ `POST_RESTART_VALIDATION_ISSUES.md` (root)
- ❌ `hook_system_design.md` (root)

#### Test Files
- **NEVER create test files in project root**
- **USE tests/ directory** con struttura per tipo:
  ```
  tests/
  ├── unit/           # Fast, isolated unit tests
  ├── integration/    # Integration tests
  ├── standalone/     # Standalone validation tests
  └── fixtures/       # Test fixtures and data
  ```

**Esempi corretti**:
- ✅ `tests/unit/hooks/test_pre_tool_use.py`
- ✅ `tests/integration/memory/test_hybrid_search.py`
- ✅ `tests/standalone/test_mcp_server.py`
- ❌ `test_hooks.py` (root)
- ❌ `validation_test.py` (root)

#### Before Creating ANY File
1. **Check PROJECT_STRUCTURE.md** per la struttura corretta
2. **Identify correct directory** basato sul tipo di file
3. **Use appropriate naming convention** (kebab-case per docs, snake_case per code)
4. **Create in correct location** seguendo la struttura definita

### Python Environment
- **ALWAYS use .devstream virtual environment** per tutti i test e execution
- **Activate venv** con `source .devstream/bin/activate` prima di ogni operazione Python
- **Use correct Python executable** dalla venv: `.devstream/bin/python`
- **Install dependencies** nella venv corretta con pip o poetry

### Memory System Development
- **Always use Context7** per research di NLP e vector search patterns
- **Validate embeddings** con test data reali
- **Test hybrid search** con multiple query types
- **Verify token budget** calculations accuracy

### 🚨 REGOLA FONDAMENTALE - NON SEMPLIFICARE, RISOLVERE
# ⚡⚡⚡ USA CONTEXT7 PER RISOLVERE I PROBLEMI - MAI SEMPLIFICARE! ⚡⚡⚡
- **QUANDO si incontra un problema tecnico complesso → USA CONTEXT7**
- **NON disabilitare features, NON rimuovere funzionalità**
- **NON creare workaround temporanei**
- **RICERCA la soluzione corretta con Context7**
- **IMPLEMENTA la soluzione research-backed**
- **MANTIENI tutte le feature funzionali**

### Database Integration
- **SQLAlchemy 2.0 async patterns** obbligatori
- **Migration scripts** per ogni schema change
- **Connection pooling** configuration
- **Transaction management** best practices

### Error Handling
- **Structured exceptions** con error context
- **Logging integration** per debugging
- **Graceful degradation** per external dependencies
- **User-friendly error messages**

## 🎉 Success Stories

### Phase 1.4 Memory System (Esempio)
```
✅ RISULTATO: Production-ready memory system
📊 METRICS: 6 moduli, 95% test coverage, Context7-validated
🎯 METODOLOGIA: Research → Design → Implement → Test
⏱️ TIMELINE: Completato in anticipo rispetto a planning
🔧 TOOLS: Context7, TodoWrite, comprehensive testing

LESSONS LEARNED:
- Context7 research cruciale per technology selection
- Micro-task breakdown improved focus e tracciabilità
- Approval workflow prevented refactoring posteriori
- Testing severo identified edge cases early
```

## 🚀 Future Development

### Step 2: Sprint 1 Ready
Con Phase 1.4 completata, siamo ready per:
- **Task Manager Implementation** con AI-powered plan generation
- **Hook System** per Claude Code integration
- **Context Injection** automatico dalla memoria
- **Production Deployment** con database migrations

### Continuous Improvement
- **Methodology refinement** basata su lessons learned
- **Tool optimization** per efficiency improvements
- **Quality standards** evolution con project growth
- **Research integration** per cutting-edge practices

---

*Documento creato: 2025-09-28*
*Basato su: Phase 1.4 Memory System Implementation Success*
*Metodologia: Research-Driven Development con Context7*