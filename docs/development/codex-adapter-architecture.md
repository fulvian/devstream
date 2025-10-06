# Codex Integration Architecture (Draft)

> Status: Draft | Owner: @tech-lead | Last Updated: 2025-10-06
>
> Goal: outline how the forthcoming `src/devstream/integrations/codex/` package wraps existing DevStream services without touching Claude-specific hooks.

## 1. High-Level Layout

```
Codex CLI Events ──► Codex Adapter Layer (new) ──► DevStream Core Services (existing)
      │                     │                          │
      │                     ├─ ProtocolGatewayAdapter ─► UserPromptSubmitHook logic
      │                     ├─ ContextPipelineAdapter ─► ContextAssembler + MemorySearch
      │                     ├─ SessionLifecycleBridge ─► TaskLifecycleManager / SessionSummary
      │                     └─ MCPBridge              ─► DevStreamMCPClient / Context7Client
      │
      └─ Environment Config ─► codex_settings.yml → merges with .env.devstream
```

### Design Principles
- **Zero Regression**: Claude hooks remain untouched; adapters only import their functionality.
- **Progressive Enhancement**: If Codex lacks a signal, skip gracefully while logging advisory messages.
- **Shared Utilities**: Reuse `DevStreamHookBase`, rate limiters, MCP client, and checkpoint manager.
- **Strict Isolation**: Codex-specific configuration lives under `config/codex/` (to be added), avoiding cross-contamination.

## 2. Module Responsibilities (Planned)

| Module | Responsibility | Key Dependencies |
|--------|----------------|------------------|
| `events.py` | Normalize Codex event payloads and broadcast to adapters | `pydantic` models, `DevStreamHookBase` |
| `protocol_gateway.py` | Invoke existing protocol enforcement logic and capture user decisions | `.claude/hooks/devstream/context/user_query_context_enhancer` |
| `context_pipeline.py` | Build context bundles per tool execution (pre/post) | `ContextAssembler`, `HybridSearchEngine`, `OllamaEmbeddingClient` |
| `session.py` | Coordinate session start/stop, task lifecycle syncing | `TaskLifecycleManager`, `SessionSummaryManager` |
| `config.py` | Load Codex-specific settings (env vars + optional YAML overlay) | `pydantic` settings |
| `logging.py` | Provide structured logger for adapters (shares format with hook logger) | `structlog` |

## 3. README Snippet (for package)

```
# devstream.integrations.codex

Codex bridge for DevStream automation. Mirrors the Claude Code hook pipeline by importing the existing hook logic and exposing it through Codex event handlers. Key guarantees:

- **Safety First**: No mutations to `.claude` hook scripts; adapters are thin wrappers.
- **Feature Parity**: Protocol gate, Context7 research, semantic memory, checkpoints.
- **Graceful Degradation**: Timeouts or MCP errors never block Codex commands.
- **Config Isolation**: Settings live under `config/codex/` and environment variables prefixed with `DEVSTREAM_CODEX_`.

> Status: In progress – initial scaffolding requires `make dev` to install optional extras (`codex` group).
```

## 4. Open Items
- Confirm final path for Codex config files (`config/codex.yml` vs dedicated folder).
- Decide on import vs subprocess for protocol enforcement (default: direct import).
- Capture tracing requirements (do we need to export metrics to the same sink as Claude?).

## 5. Validation Plan
- Unit tests with synthetic Codex payloads to exercise each adapter.
- Integration test harness executing adapters in sequence to ensure state continuity.
- Manual smoke test with Codex CLI once adapters wired.


## 6. Runtime Dispatcher

- **Componente**: `CodexIntegrationRuntime` (`dispatcher.py`)
- **Responsabilità**: normalizza i payload, instrada gli eventi verso gli adapter (protocollo, contesto, sessione) e mantiene un piccolo campione dei payload reali per analisi successive.
- **Output**: dizionari JSON-ready per il CLI Codex (es. prompt di enforcement, contesto pre-tool, ID memoria).
- **Estendibilità**: supporta l'iniezione di adapter personalizzati per test o varianti di distribuzione.

## 7. CLI Shim
- Script: `scripts/codex/relay.sh`
- Dipendenze: usa il venv `.devstream` se disponibile, altrimenti `python3` di sistema.
- Invocazione: `scripts/codex/relay.sh --event '{"event_type":"session_start", ...}'` oppure tramite STDIN (`cat events.jsonl | scripts/codex/relay.sh`).
- Output: una riga JSON per ogni evento in input; i campioni vengono salvati in `DEVSTREAM_CODEX_SAMPLE_OUTPUT_PATH`.
- Setup rapido: `./start-devstream.sh codex` avvia MCP e prepara `DEVSTREAM_CODEX_HOME` in `data/codex_home`, senza alterare il flusso Claude Code.
- Log path: configurabile via `DEVSTREAM_CODEX_HOME`; se non impostato il runner reindirizza `HOME` sulla directory corrente quando `~/.claude` non è presente.
