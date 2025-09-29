# Sistema Integrato Task Management & Memoria Cross-Session
## Architettura Software Dettagliata

### 1. OVERVIEW SISTEMA

Il sistema si compone di 4 layer principali:

1. **Interface Layer**: Claude Code CLI + Hook System
2. **Task Management Layer**: Gestione piani, fasi, micro-task
3. **Memory Layer**: Storage semantico + retrieval intelligente
4. **Data Layer**: SQLite + File System + Embedding Store

### 2. COMPONENTI CORE

#### 2.1 Task Management Core
```python
# Struttura dati principale
@dataclass
class InterventionPlan:
    id: str
    title: str
    objectives: List[str]
    technical_specs: Dict[str, Any]
    expected_outcome: str
    phases: List[Phase]
    created_at: datetime
    updated_at: datetime
    status: PlanStatus

@dataclass
class Phase:
    id: str
    plan_id: str
    name: str
    description: str
    sequence_order: int
    is_parallel: bool
    micro_tasks: List[MicroTask]
    dependencies: List[str]
    status: PhaseStatus

@dataclass
class MicroTask:
    id: str
    phase_id: str
    title: str
    description: str
    max_duration_minutes: int = 10
    max_context_tokens: int = 256000
    assigned_agent: Optional[str]
    status: TaskStatus
    output_files: List[str]
    documentation: Optional[str]
```

#### 2.2 Memory System
```python
# Sistema di memoria semantica
class MemoryStore:
    def __init__(self, db_path: str, ollama_endpoint: str):
        self.db = SQLiteMemoryDB(db_path)
        self.embedder = OllamaEmbedder(ollama_endpoint, "embeddinggemma")

    async def store_task_memory(self, task: MicroTask, context: str) -> None:
        """Salva task + contesto con embedding semantico"""

    async def retrieve_relevant_memory(self, query: str, limit: int = 5) -> List[MemoryItem]:
        """Retrieval semantico di memoria rilevante"""

    async def inject_context(self, current_task: str) -> str:
        """Iniezione automatica contesto nel prompt Claude"""
```

#### 2.3 Hook System
```python
# Sistema di hook per Claude Code
class HookManager:
    def __init__(self, config_path: str):
        self.hooks = self._load_hooks(config_path)

    @hook("user_interaction_start")
    async def force_task_creation(self, interaction: dict) -> dict:
        """Forza creazione task per ogni interazione"""

    @hook("micro_task_completion")
    async def save_task_output(self, task: MicroTask, output: str) -> None:
        """Salvataggio automatico output + aggiornamento memoria"""

    @hook("context_injection_needed")
    async def inject_memory(self, current_context: str) -> str:
        """Iniezione memoria rilevante"""
```

### 3. DATABASE SCHEMA

#### 3.1 Schema SQLite Principale
```sql
-- Piani di intervento
CREATE TABLE intervention_plans (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    objectives JSON NOT NULL,
    technical_specs JSON,
    expected_outcome TEXT,
    status TEXT CHECK(status IN ('draft', 'active', 'completed', 'archived')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fasi dei piani
CREATE TABLE phases (
    id TEXT PRIMARY KEY,
    plan_id TEXT REFERENCES intervention_plans(id),
    name TEXT NOT NULL,
    description TEXT,
    sequence_order INTEGER,
    is_parallel BOOLEAN DEFAULT FALSE,
    dependencies JSON,
    status TEXT CHECK(status IN ('pending', 'active', 'completed', 'blocked')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Micro-task
CREATE TABLE micro_tasks (
    id TEXT PRIMARY KEY,
    phase_id TEXT REFERENCES phases(id),
    title TEXT NOT NULL,
    description TEXT,
    max_duration_minutes INTEGER DEFAULT 10,
    max_context_tokens INTEGER DEFAULT 256000,
    assigned_agent TEXT,
    status TEXT CHECK(status IN ('pending', 'active', 'completed', 'failed')),
    output_files JSON,
    documentation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Memoria semantica
CREATE TABLE semantic_memory (
    id TEXT PRIMARY KEY,
    task_id TEXT REFERENCES micro_tasks(id),
    content TEXT NOT NULL,
    content_type TEXT CHECK(content_type IN ('code', 'documentation', 'context', 'output')),
    embedding BLOB, -- Vector embedding
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FTS5 per ricerca testuale
CREATE VIRTUAL TABLE memory_fts USING fts5(
    content,
    task_id UNINDEXED,
    content_type UNINDEXED
);

-- Indice per ricerca vettoriale (estensione)
CREATE TABLE vector_index (
    memory_id TEXT REFERENCES semantic_memory(id),
    vector_data BLOB,
    dimension INTEGER DEFAULT 384
);
```

#### 3.2 Estensioni SQLite Richieste
- **FTS5**: Full-Text Search
- **JSON1**: Manipolazione JSON nativa
- **Vector**: Estensione per similarity search (es. sqlite-vss)

### 4. API INTERNE

#### 4.1 Task Management API
```python
class TaskManager:
    async def create_intervention_plan(
        self,
        title: str,
        objectives: List[str],
        technical_specs: Dict,
        expected_outcome: str
    ) -> InterventionPlan:
        """Crea nuovo piano di intervento"""

    async def decompose_to_phases(self, plan: InterventionPlan) -> List[Phase]:
        """Scompone piano in fasi"""

    async def generate_micro_tasks(self, phase: Phase) -> List[MicroTask]:
        """Genera micro-task da fase"""

    async def execute_micro_task(self, task: MicroTask) -> TaskResult:
        """Esegue micro-task con agente appropriato"""
```

#### 4.2 Memory Management API
```python
class MemoryManager:
    async def store_execution_memory(
        self,
        task: MicroTask,
        code_output: str,
        documentation: str,
        context: str
    ) -> None:
        """Memorizza risultato esecuzione task"""

    async def semantic_search(
        self,
        query: str,
        content_types: List[str] = None,
        limit: int = 5
    ) -> List[MemoryItem]:
        """Ricerca semantica nella memoria"""

    async def get_contextual_memory(
        self,
        current_task: MicroTask
    ) -> str:
        """Recupera memoria contestuale per task corrente"""
```

### 5. INTEGRAZIONE AGENTI

#### 5.1 Configurazione Agenti JSON
```json
{
  "agents": {
    "project_architect": {
      "role": "Architetto di sistema",
      "capabilities": ["system_design", "technology_selection", "architecture_planning"],
      "triggers": ["new_project", "architecture_decision"],
      "context_injection": true,
      "memory_access": "full"
    },
    "code_generator": {
      "role": "Generatore di codice",
      "capabilities": ["code_generation", "implementation", "refactoring"],
      "triggers": ["implementation_task", "code_review_required"],
      "context_injection": true,
      "memory_access": "code_focused"
    },
    "documentation_writer": {
      "role": "Technical Writer",
      "capabilities": ["documentation", "api_docs", "readme_generation"],
      "triggers": ["documentation_needed", "task_completion"],
      "context_injection": true,
      "memory_access": "documentation_focused"
    }
  }
}
```

#### 5.2 Agent Dispatcher
```python
class AgentDispatcher:
    def __init__(self, agent_config: dict, memory_manager: MemoryManager):
        self.agents = agent_config
        self.memory = memory_manager

    async def dispatch_task(self, task: MicroTask) -> TaskResult:
        """Assegna task all'agente più appropriato"""
        agent = self._select_agent(task)
        context = await self.memory.get_contextual_memory(task)
        return await agent.execute(task, context)

    def _select_agent(self, task: MicroTask) -> Agent:
        """Selezione automatica agente basata su task type"""
```

### 6. INTEGRAZIONE CONTEXT7

```python
class Context7Integration:
    def __init__(self, context7_client):
        self.client = context7_client

    async def get_best_practices(self, technology: str) -> str:
        """Recupera best practices per tecnologia"""
        return await self.client.resolve_library_id(technology)

    async def get_reference_docs(self, library_id: str, topic: str) -> str:
        """Recupera documentazione di riferimento"""
        return await self.client.get_library_docs(library_id, topic=topic)

    async def enrich_task_context(self, task: MicroTask) -> str:
        """Arricchisce contesto task con docs external"""
```

### 7. ROADMAP MVP

#### Milestone 1: Core Database & Schema
- [ ] Setup SQLite con estensioni
- [ ] Implementazione schema base
- [ ] Test CRUD operations
- [ ] Setup Ollama + embeddinggemma

#### Milestone 2: Task Management Core
- [ ] Implementazione TaskManager
- [ ] Sistema creazione piani di intervento
- [ ] Decomposizione in fasi/micro-task
- [ ] Validazione vincoli (10min, 256k tokens)

#### Milestone 3: Memory System
- [ ] MemoryStore con embedding semantico
- [ ] Retrieval system
- [ ] Context injection automatico
- [ ] Testing similarity search

#### Milestone 4: Hook System
- [ ] Hook manager per Claude Code
- [ ] Integration con existing workflow
- [ ] Force task creation su ogni interazione
- [ ] Auto-save task output

#### Milestone 5: Agent Integration
- [ ] Agent dispatcher
- [ ] JSON config per agenti
- [ ] Context7 integration
- [ ] Team virtuale di sviluppo

### 8. STACK TECNOLOGICO MINIMALE

```python
# requirements.txt
sqlite3                 # Core DB
sqlite-vss             # Vector similarity search
ollama-python          # Ollama client
sentence-transformers  # Fallback embedding
asyncio                # Async support
pydantic               # Data validation
typer                  # CLI framework
rich                   # Terminal UI
```

Questo design fornisce una base solida per un sistema di task management completamente integrato con memoria semantica cross-session.