# Codex CLI Event Surface (Draft)

> Status: Draft | Owner: @devops-specialist | Last Updated: 2025-10-06
>
> Purpose: document the Codex CLI lifecycle hooks we need to bridge into DevStream without touching existing Claude Code automation.

## 1. Event Inventory

| Codex Signal | Description | Trigger Conditions | DevStream Counterpart |
|--------------|-------------|--------------------|-----------------------|
| `session_start` | CLI opens a new interactive session for a workspace | User runs `codex` in repo root; new sandbox established | `.claude/hooks/devstream/tasks/session_start.py` → provides repository fingerprint + memory bootstrap |
| `user_prompt_submit` | User sends natural-language instruction to Codex | Every free-form user input | `.claude/hooks/devstream/context/user_query_context_enhancer.py` (protocol gate + context assembly) |
| `tool_pre_execute` | Codex is about to run an editing/testing command (`Edit`, `Write`, `Bash`, etc.) | Before tool invocation | `.claude/hooks/devstream/memory/pre_tool_use.py` (context injection, delegation hints) |
| `tool_post_execute` | Codex finished executing a tool | After tool completes (success/failure) | `.claude/hooks/devstream/memory/post_tool_use.py` (memory capture + embeddings + checkpoints) |
| `session_stop` | CLI session terminates | User exits Codex, process interrupted, or fatal error | `.claude/hooks/devstream/tasks/stop.py` (session summary + memory flush) |
| `heartbeat` *(optional)* | Periodic telemetry/keep-alive while session idle | Timer-based, ~60s cadence | `.claude/hooks/devstream/tasks/progress_tracker.py` polling loop |

### Assumptions
- Codex exposes JSON payloads analogous to Claude cchooks (session id, cwd, tool metadata, stdout/stderr).
- Each event is non-blocking: DevStream adapter must degrade gracefully on errors to avoid stalling the CLI.
- Payload guarantees: `session_id`, `cwd`, `tool_name`, `tool_args`, and `result` fields are present where relevant.

### Open Questions
1. Does Codex surface diff previews before applying edits (needed for richer memory capture)?
2. Are tool executions strictly sequential, or can parallel commands occur (affects lock usage in TaskEngine adapters)?
3. Does Codex provide explicit success/failure flags per tool call, or must we infer from exit codes/stdout?

## 2. Event → Service Mapping

| Event | Adapter Responsibility | DevStream Service/Module |
|-------|-----------------------|--------------------------|
| `session_start` | - Detect DevStream project markers<br>- Load project + memory context<br>- Register lifecycle manager | `TaskLifecycleManager`, `MemoryStorage`, `SessionStartHook` logic |
| `user_prompt_submit` | - Invoke protocol enforcement
- Trigger agent delegation analysis
- Inject Context7 + memory context | `UserPromptSubmitHook`, `Context7Client`, `HybridSearchEngine` |
| `tool_pre_execute` | - Assemble per-tool context (relevant memories, hints)<br>- Enforce rate limits | `PreToolUseHook`, `ContextAssembler`, `rate_limiter` |
| `tool_post_execute` | - Extract artifacts, store memory, generate embeddings<br>- Trigger checkpoints | `PostToolUseHook`, `OllamaEmbeddingClient`, `CheckpointManager` |
| `session_stop` | - Summarise session, persist decisions, flush tasks | `SessionSummaryManager`, `TaskLifecycleManager` |
| `heartbeat` | - Poll active tasks, update progress if idle | `TaskStatusUpdater` |

## 3. Payload Notes

| Field | Expected Type | Notes |
|-------|---------------|-------|
| `session_id` | `str` | Stable per Codex invocation; reuse for DevStream session tracking |
| `cwd` | `str` (absolute path) | Validate against project root before reading/writing |
| `tool_name` | `str` | Map to DevStream critical tool list (`Write`, `Edit`, `MultiEdit`, `Bash`, `TodoWrite`) |
| `tool_args` | `dict` | Must include `file_path`, `new_content`, etc. for memory diffing |
| `result` | `dict` | Capture stdout, stderr, exit_code for failure analysis |
| `timestamp` | `str` ISO 8601 | Needed for ordering events and checkpoints |

## 4. Error Handling & Fallbacks
- All adapters call into `DevStreamHookBase.safe_mcp_call` equivalents; timeouts must default to success to avoid blocking Codex.
- MCP server availability should be checked once per session; subsequent failures downgrade features (e.g., skip embeddings).
- Rate limiting mirrors existing implementation (`memory_rate_limiter`, `ollama_rate_limiter`).

## 5. Next Steps
1. Implement adapter interfaces in `src/devstream/integrations/codex/events.py` (task 3).
2. Define configuration schema for Codex integration (env vars + optional CLI flags).
3. Capture concrete payload examples once Codex CLI telemetry is available; update this document to "Stable" status.


## 6. Raccolta Payload
- Esegui `scripts/codex/relay.sh --event '{"event_type":"session_start","session_id":"demo","cwd":"."}'` per testare manualmente.
- In modalità streaming, inviare eventi JSON line-by-line all'eseguibile; l'output restituisce la risposta DevStream.
- Impostare `DEVSTREAM_CODEX_SAMPLE_OUTPUT_PATH` per salvare i payload campione altrove (default `data/codex_event_samples.jsonl`).
- Per evitare problemi di permessi ai log, impostare `DEVSTREAM_CODEX_HOME` (o creare il folder `~/.claude/logs/devstream` all'interno del workspace). Di default il runner usa la directory corrente se `~/.claude` non esiste.
- Per simulazioni offline (senza MCP server) impostare `DEVSTREAM_MEMORY_ENABLED=false` e `DEVSTREAM_PROTOCOL_ENFORCEMENT_ENABLED=false` per evitare timeout, ricordando però che in produzione sono richiesti.
- `./start-devstream.sh codex` prepara automaticamente MCP, variabili Codex e directory di logging isolate.
