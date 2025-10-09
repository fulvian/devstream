# Piano: Enhancement Protocollo DevStream 7-Step e Gestione Task Robusta

**Task ID**: 16f5433792ee63a8414582a67cadb792
**Phase**: Protocollo e Task Management Enhancement
**Priority**: 9/10
**Created**: 2025-10-07

---

## Executive Summary

Questo documento definisce l'implementazione completa per risolvere due criticità fondamentali:
1. Protocollo 7-step non rispettato (task creation allo step 1, non 5)
2. Gestione task inaffidabile con crash recovery
3. Enforcement automatico con validazione interattiva obbligatoria

---

## Architettura Soluzione

### Component 1: Protocol State Manager
**Location**: `.claude/hooks/devstream/protocol/`
- `protocol_state_manager.py` - Gestione stato persistente del protocollo
- `step_validator.py` - Validazione obbligatoria di ogni step
- `enforcement_gate.py` - Interfaccia utente forzata con opzioni

### Component 2: Task-First Creation System
**Location**: `.claude/hooks/devstream/tasks/`
- `task_first_handler.py` - Creazione task come PRIMA azione obbligatoria
- `task_state_sync.py` - Sincronizzazione automatica stato con hooks
- `task_recovery.py` - Recovery automatico da crash con stato persistente

### Component 3: Interactive Confirmation System
**Location**: `.claude/hooks/devstream/ui/`
- `interactive_validator.py` - Conferme utente obbligatorie
- `approval_workflow.py` - Workflow approvazione interattivo
- `commit_automation.py` - Commit/push automatici alle milestone

---

## Implementazione Dettagliata

### FASE 1: Protocol State Manager (2 ore)

#### 1.1 Protocol State Persistence
```python
# protocol_state_manager.py
class ProtocolState:
    def __init__(self):
        self.state_file = "~/.claude/state/protocol_state.json"
        self.session_id = self.generate_session_id()

    async def create_protocol_session(self, task_id: str):
        """Crea nuova sessione protocol con task creation come step 1"""
        state = {
            "session_id": self.session_id,
            "task_id": task_id,
            "current_step": "TASK_CREATION",  # NUOVO: prima di DISCUSSION
            "steps_completed": [],
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "status": "active"
        }
        await self.atomic_write_state(state)
```

#### 1.2 Step Validation Engine
```python
# step_validator.py
class StepValidator:
    STEPS = [
        "TASK_CREATION",  # NUOVO: Step 0 obbligatoria
        "DISCUSSION",
        "ANALYSIS",
        "RESEARCH",
        "PLANNING",
        "APPROVAL",
        "IMPLEMENTATION",
        "VERIFICATION"
    ]

    async def validate_step_completion(self, step: str) -> bool:
        """Valida completamento step con check obbligatori"""
        if step == "TASK_CREATION":
            return await self.check_task_created()
        elif step == "DISCUSSION":
            return await self.check_discussion_in_memory()
        # ... altre validazioni
```

### FASE 2: Task-First Creation System (1.5 ore)

#### 2.1 Task Creation Hook
```python
# task_first_handler.py
class TaskFirstHandler:
    async def enforce_task_creation(self, user_request: str) -> str:
        """Enforce task creation come PRIMA azione"""
        if not await self.has_active_task():
            # Analisi automatica per determinare se task è necessario
            complexity = await self.analyze_complexity(user_request)
            if complexity >= 0.7:  # Soglia per task requirement
                task_id = await self.create_task_interactive(user_request)
                return task_id
        return None

    async def create_task_interactive(self, user_request: str) -> str:
        """Creazione task con conferma utente obbligatoria"""
        # Prompt utente per conferma task creation
        user_choice = await self.prompt_task_creation(user_request)
        if user_choice == "approve":
            return await self.mcp_create_task(user_request)
        raise ProtocolException("Task creation required by protocol")
```

#### 2.2 Task State Synchronization
```python
# task_state_sync.py
class TaskStateSync:
    async def sync_task_progress(self, tool_execution: Dict[str, Any]):
        """Sincronizza automaticamente stato task con ogni tool execution"""
        if tool_execution["tool"] in ["Write", "Edit", "TodoWrite"]:
            progress_update = await self.analyze_progress_impact(tool_execution)
            await self.mcp_update_task(progress_update)

    async def crash_recovery(self) -> Optional[str]:
        """Recupera task interrotto da crash"""
        last_state = await self.load_last_protocol_state()
        if last_state and last_state["status"] == "active":
            return await self.restore_task_session(last_state)
        return None
```

### FASE 3: Interactive Confirmation System (1.5 ore)

#### 3.1 Interactive Step Validation
```python
# interactive_validator.py
class InteractiveValidator:
    async def enforce_step_transition(self, from_step: str, to_step: str):
        """Enforce conferma utente obbligatoria per transizioni"""
        validation_result = await self.validate_step_completion(from_step)
        if not validation_result.valid:
            raise ProtocolException(f"Step {from_step} not completed: {validation_result.reason}")

        # Mostra riepilogo e chiede conferma
        summary = await self.generate_step_summary(from_step)
        user_approval = await self.prompt_step_approval(summary, to_step)

        if user_approval != "approved":
            raise ProtocolException("User approval required for step transition")
```

#### 3.2 Automatic Commit/Push System
```python
# commit_automation.py
class CommitAutomation:
    async def auto_commit_step_completion(self, step: str, task_id: str):
        """Commit automatico al completamento step significativi"""
        if step in ["APPROVAL", "IMPLEMENTATION_PHASE", "VERIFICATION"]:
            commit_message = await self.generate_commit_message(step, task_id)
            await self.git_commit_and_push(commit_message)

    async def save_implementation_plan(self, plan_content: str, task_id: str):
        """Salva piano implementazione in docs/development/plan/piano_*.md"""
        filename = f"piano_task_{task_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = f"docs/development/plan/{filename}"
        await self.atomic_write_file(filepath, plan_content)
        await self.store_plan_in_memory(task_id, filepath)
```

### FASE 4: Integration Hooks (1 ora)

#### 4.1 Enhanced UserPromptSubmit Hook
```python
# In user_query_context_enhancer.py
async def enhanced_protocol_enforcement(prompt: str) -> Dict[str, Any]:
    """Integrazione completa enforcement protocollo"""
    # 1. Controlla se sessione protocol attiva
    protocol_state = await ProtocolStateManager().get_current_state()

    if not protocol_state:
        # 2. Analisi complessità per determinare se protocollo richiesto
        complexity = await analyze_request_complexity(prompt)
        if complexity >= 0.7:
            # 3. Force task creation come step 1
            task_id = await TaskFirstHandler().enforce_task_creation(prompt)
            protocol_state = await ProtocolStateManager().create_session(task_id)

    # 4. Valida step corrente e blocca se necessario
    current_step = protocol_state["current_step"]
    validation = await StepValidator().validate_step_completion(current_step)

    if not validation.valid:
        return await InteractiveValidator().handle_step_blocking(validation)

    return {"prompt": prompt, "protocol_state": protocol_state}
```

#### 4.2 Enhanced PostToolUse Hook
```python
# In post_tool_use.py
async def enhanced_task_sync(tool_result: Dict[str, Any]):
    """Sincronizzazione automatica task state"""
    protocol_state = await ProtocolStateManager().get_current_state()
    if protocol_state:
        await TaskStateSync().sync_task_progress(tool_result)

        # Controlla se step completato
        step_completion = await StepValidator().check_step_completion(tool_result)
        if step_completion.completed:
            await ProtocolStateManager().advance_step(step_completion.next_step)
            await CommitAutomation().auto_commit_step_completion(
                step_completion.completed_step,
                protocol_state["task_id"]
            )
```

---

## Deployment Strategy

### Phase 1: Core Infrastructure (Day 1)
- Implementare `ProtocolStateManager` con atomic state persistence
- Creare `TaskFirstHandler` con task creation obbligatoria
- Integrare con existing `UserPromptSubmit` hook

### Phase 2: Validation System (Day 1-2)
- Implementare `StepValidator` con regole specifiche
- Creare `InteractiveValidator` con UI conferme obbligatorie
- Test con casi reali di enforcement

### Phase 3: Integration & Automation (Day 2)
- Integrate `TaskStateSync` con existing hooks
- Implementare `CommitAutomation` per salvataggio automatico
- Test crash recovery scenarios

### Phase 4: Testing & Validation (Day 2-3)
- Test complete workflow enforcement
- Test crash recovery scenarios
- Test with both Sonnet and GLM4.6 models
- Performance validation

---

## Success Metrics

### Technical Metrics
- **99.9%** Task creation compliance (step 1 obbligatorio)
- **95%+** Step completion validation accuracy
- **<5s** Recovery time from crash scenarios
- **100%** Automatic commit/push at milestones

### Quality Metrics
- **Zero** protocol violations without explicit override
- **100%** User confirmation capture for step transitions
- **Complete** audit trail for all protocol activities
- **Persistent** state recovery across session crashes

---

## Risk Mitigation

### Technical Risks
1. **Hook Performance**: Implement caching e async operations
2. **State Corruption**: Atomic writes e backup redundancy
3. **Model Compliance**: Universal enforcement across all Claude models
4. **User Experience**: Clear messaging e smooth interaction flows

### Operational Risks
1. **Migration Path**: Gradual rollout con fallback options
2. **Training**: Documentation chiara e esempi pratici
3. **Support**: Troubleshooting guide e debug tools

---

## Next Steps

1. **Approve this plan** - Conferma implementazione come descritto
2. **Begin Phase 1** - Core infrastructure development
3. **Daily check-ins** - Progress validation e adjustment
4. **Final validation** - Complete system testing

---

**Prepared by**: Claude Code Assistant
**Reviewed by**: [User Approval Required]
**Implementation Timeline**: 2-3 giorni
**Priority**: Critical (9/10)

---

*Questo piano sarà salvato in DevStream memory e recuperabile per riferimento futuro*