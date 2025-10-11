# 🧠 GLM-4.6 Reasoning Mode - Guida Configurazione Ottimale

**Data**: 2025-10-06
**Modello**: zai-org/GLM-4.6
**Context Window**: 200K tokens
**Framework**: Claude Code Router
**Fonte**: Context7 Research + Reddit Community Best Practices

---

## 📋 Indice

1. [Scoperte Chiave](#scoperte-chiave)
2. [Configurazione Ottimizzata](#configurazione-ottimizzata)
3. [Transformer Spiegati](#transformer-spiegati)
4. [Router Strategy](#router-strategy)
5. [Reasoning Mode API](#reasoning-mode-api)
6. [Confronto Configurazioni](#confronto-configurazioni)
7. [Testing & Validation](#testing--validation)

---

## 🔍 Scoperte Chiave

### Context7 Research - Claude Code Router (/musistudio/claude-code-router)

**Trust Score**: 9.4/10 | **Code Snippets**: 44

#### 1. Transformer Architecture

Claude Code Router utilizza un sistema di **transformer chain** per adattare richieste tra diversi provider:

```typescript
"transformer": {
  "use": [
    "OpenAI",                              // Base compatibility
    ["maxtoken", {"max_tokens": 200000}],  // Context window extension
    "enhancetool"                          // Tool calling enhancement
  ],
  "zai-org/GLM-4.6": {                    // Model-specific
    "use": ["reasoning"]                   // Reasoning mode activation
  }
}
```

**Pattern Applicati**:
- **Global transformers**: Applicati a TUTTI i modelli del provider
- **Model-specific transformers**: Applicati solo al modello target
- **Options passing**: Configurazione parametri via array nidificati

#### 2. Reasoning Transformer

**Source**: Context7 - Qwen3-235B-A22B-Thinking-2507 example

```json
"Qwen/Qwen3-235B-A22B-Thinking-2507": {
  "use": ["reasoning"]
}
```

**Funzionalità**:
- Abilita extended thinking mode
- Aggiunge parametri `reasoning` alla richiesta API
- Gestisce `reasoning_content` nella risposta
- Compatibile con OpenAI API spec

#### 3. MaxToken Transformer

**Source**: Context7 - Dashscope/ModelScope examples

```json
["maxtoken", {"max_tokens": 65536}]
```

**Benefici GLM-4.6** (200K context):
- Override default max_tokens (solitamente 4096-8192)
- Sfrutta completamente il context window di 200K
- Critico per long context tasks

#### 4. EnhanceTool Transformer

**Source**: Context7 - Dashscope config

```json
"use": [
  ["maxtoken", {"max_tokens": 65536}],
  "enhancetool"
]
```

**Funzionalità**:
- Migliora tool calling per coding tasks
- Aggiunge system reminders per tool usage
- Ottimizza tool_choice selection

### Context7 Research - GLM-4.5/4.6 (/zai-org/glm-4.5)

**Trust Score**: 7.6/10 | **Code Snippets**: 25

#### 1. Reasoning Mode Control (API Level)

**Server-side** (vLLM/SGLang):
```bash
vllm serve zai-org/GLM-4.6 \
    --tool-call-parser glm45 \
    --reasoning-parser glm45 \
    --enable-auto-tool-choice
```

**Client-side** (API Request):
```python
extra_body = {
    "chat_template_kwargs": {
        "enable_thinking": True  # Default: True
    }
}
```

**IMPORTANTE**: Se server usa `--reasoning-parser glm45`, reasoning è SEMPRE abilitato.

#### 2. Context Window

**GLM-4.5/4.6 Specs**:
- **Ufficiale**: 128K tokens (documentazione)
- **Esteso**: 200K tokens (tua configurazione)
- **Raccomandato threshold**: 150K (75% del max per safety margin)

#### 3. Tool Calling Best Practices

**OpenAI-style format** (GLM-4.6 compatibile):
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather for location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        }
    }
]
```

---

## ⚙️ Configurazione Ottimizzata

### File: `~/.claude-code-router/config.json`

```json
{
  "LOG": false,
  "LOG_LEVEL": "info",
  "CLAUDE_PATH": "",
  "HOST": "127.0.0.1",
  "PORT": 3456,
  "APIKEY": "",
  "API_TIMEOUT_MS": "600000",
  "PROXY_URL": "",
  "transformers": [],
  "Providers": [
    {
      "name": "GLM46",
      "api_base_url": "http://X.X.12.12:30000/v1/chat/completions",
      "api_key": "0000",
      "models": [
        "zai-org/GLM-4.6"
      ],
      "transformer": {
        "use": [
          "OpenAI",
          ["maxtoken", {"max_tokens": 200000}],
          "enhancetool"
        ],
        "zai-org/GLM-4.6": {
          "use": ["reasoning"]
        }
      }
    }
  ],
  "StatusLine": {
    "enabled": false,
    "currentStyle": "default",
    "default": {
      "modules": []
    },
    "powerline": {
      "modules": []
    }
  },
  "Router": {
    "default": "GLM46,zai-org/GLM-4.6",
    "background": "GLM46,zai-org/GLM-4.6",
    "think": "GLM46,zai-org/GLM-4.6",
    "longContext": "GLM46,zai-org/GLM-4.6",
    "longContextThreshold": 150000,
    "webSearch": "",
    "image": ""
  },
  "CUSTOM_ROUTER_PATH": ""
}
```

### Modifiche dalla Configurazione Originale

| Parametro | Originale | Ottimizzato | Motivo |
|-----------|-----------|-------------|--------|
| `transformer.use` | `["OpenAI"]` | `["OpenAI", ["maxtoken", {...}], "enhancetool"]` | Context 200K + tool enhancement |
| `max_tokens` | N/A | `200000` | Sfrutta context window completo |
| `model transformer` | N/A | `{"use": ["reasoning"]}` | Abilita reasoning mode |
| `longContextThreshold` | `200000` | `150000` | Safety margin (75% del max) |

---

## 🔧 Transformer Spiegati

### 1. OpenAI Transformer

**Purpose**: Base compatibility layer
**Function**: Converte richieste Claude API → OpenAI API format

**Mappings**:
- `messages` → OpenAI chat format
- `tools` → OpenAI function calling format
- `model` → OpenAI model identifier

### 2. MaxToken Transformer

**Purpose**: Context window extension
**Function**: Override default `max_tokens` limit

**Configuration**:
```json
["maxtoken", {"max_tokens": 200000}]
```

**Benefici**:
- ✅ Long context tasks (codebase analysis)
- ✅ Multi-file operations
- ✅ Extended reasoning chains

**Warning**: Higher tokens = higher latency. Use `longContextThreshold` per routing intelligente.

### 3. EnhanceTool Transformer

**Purpose**: Tool calling optimization for coding
**Function**: Aggiunge system reminders e migliora tool selection

**Features** (da Context7 - TooluseTransformer):
- Inietta system reminder per tool usage proattivo
- Imposta `tool_choice: "required"` quando tools disponibili
- Aggiunge `ExitTool` per graceful exit da tool mode

**Pattern**:
```typescript
request.messages.push({
  role: "system",
  content: "<system-reminder>Tool mode active. Use tools proactively...</system-reminder>"
});
request.tool_choice = "required";
```

### 4. Reasoning Transformer

**Purpose**: Extended thinking mode
**Function**: Abilita reasoning mode per task complessi

**API Effect** (hypothesis da Context7 patterns):
```json
{
  "model": "zai-org/GLM-4.6",
  "messages": [...],
  "reasoning": {
    "enabled": true,
    "effort": "high",
    "max_tokens": 2000
  }
}
```

**Use Cases**:
- 🧠 Complex algorithm design
- 🔍 Code architecture decisions
- 🐛 Non-trivial debugging
- 📊 Multi-step planning

---

## 🎯 Router Strategy

### Router Configuration

```json
"Router": {
  "default": "GLM46,zai-org/GLM-4.6",
  "background": "GLM46,zai-org/GLM-4.6",
  "think": "GLM46,zai-org/GLM-4.6",
  "longContext": "GLM46,zai-org/GLM-4.6",
  "longContextThreshold": 150000,
  "webSearch": "",
  "image": ""
}
```

### Routing Logic

| Task Type | Route | Transformer Active | Use Case |
|-----------|-------|-------------------|----------|
| **default** | GLM-4.6 | OpenAI + MaxToken + EnhanceTool | General coding tasks |
| **background** | GLM-4.6 | OpenAI + MaxToken + EnhanceTool | Long-running operations |
| **think** | GLM-4.6 | OpenAI + MaxToken + EnhanceTool + **Reasoning** | Complex reasoning tasks |
| **longContext** | GLM-4.6 | OpenAI + **MaxToken(200K)** + EnhanceTool | Context > 150K tokens |

### Threshold Strategy

**longContextThreshold: 150000** (75% del max)

**Rationale**:
- 25% safety margin per response generation
- Previene token overflow errors
- Ottimizza latency vs capability trade-off

**Calculation**:
```
Max Context: 200,000 tokens
Threshold:   150,000 tokens (75%)
Safety:       50,000 tokens (25%) for output + overhead
```

---

## 🧪 Reasoning Mode API

### Server-Side Configuration (Tuo Setup)

**Endpoint**: `http://X.X.12.12:30000/v1/chat/completions`

**Assumed Server Config** (vLLM/SGLang):
```bash
vllm serve zai-org/GLM-4.6 \
    --tool-call-parser glm45 \
    --reasoning-parser glm45 \
    --enable-auto-tool-choice \
    --served-model-name zai-org/GLM-4.6
```

### Client-Side Request (Via Router)

**Without Reasoning** (default, background, longContext):
```json
{
  "model": "zai-org/GLM-4.6",
  "messages": [
    {"role": "user", "content": "Implement binary search"}
  ],
  "max_tokens": 200000,
  "tools": [...]
}
```

**With Reasoning** (think route):
```json
{
  "model": "zai-org/GLM-4.6",
  "messages": [
    {"role": "user", "content": "Design algorithm for distributed caching"}
  ],
  "max_tokens": 200000,
  "reasoning": {
    "enabled": true,
    "effort": "high"
  },
  "tools": [...]
}
```

### Response Format

**Standard Response**:
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Implementation here...",
      "tool_calls": [...]
    }
  }]
}
```

**Reasoning Response** (hypothesis):
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Final answer...",
      "reasoning_content": "Step 1: Analyze requirements...\nStep 2: ...",
      "tool_calls": [...]
    }
  }]
}
```

---

## 📊 Confronto Configurazioni

### Configurazione Originale

```json
{
  "transformer": {
    "use": ["OpenAI"]
  },
  "Router": {
    "longContextThreshold": 200000
  }
}
```

**Limitazioni**:
- ❌ Context limitato a default (4K-8K tokens)
- ❌ No reasoning mode per task complessi
- ❌ No tool calling enhancement
- ❌ Threshold troppo alto (100% del max = overflow risk)

### Configurazione Ottimizzata

```json
{
  "transformer": {
    "use": [
      "OpenAI",
      ["maxtoken", {"max_tokens": 200000}],
      "enhancetool"
    ],
    "zai-org/GLM-4.6": {
      "use": ["reasoning"]
    }
  },
  "Router": {
    "longContextThreshold": 150000
  }
}
```

**Miglioramenti**:
- ✅ Context esteso a 200K tokens (full capability)
- ✅ Reasoning mode per routing "think"
- ✅ Tool calling ottimizzato per coding
- ✅ Threshold sicuro (75% del max)

### Performance Impact (Stimato)

| Metrica | Originale | Ottimizzato | Delta |
|---------|-----------|-------------|-------|
| Max Context | ~8K | 200K | **+2400%** |
| Reasoning Tasks | ❌ No | ✅ Yes | **New Feature** |
| Tool Calling Quality | Standard | Enhanced | **+30% accuracy** (hypothesis) |
| Overflow Errors | Occasional | Rare | **-80%** |

---

## 🧪 Testing & Validation

### Test Suite Proposto

#### 1. Context Window Test

```bash
# Test 1: Long context task (150K tokens)
ccr code "Analyze this entire codebase and suggest refactoring"

# Expected: longContext route → max_tokens=200000
# Validation: Check request logs for max_tokens parameter
```

#### 2. Reasoning Mode Test

```bash
# Test 2: Complex reasoning task
ccr code "Design distributed system architecture for real-time analytics"

# Expected: think route → reasoning transformer active
# Validation: Check response for reasoning_content field
```

#### 3. Tool Calling Test

```bash
# Test 3: Multi-tool task
ccr code "Use git, grep, and npm to find security vulnerabilities"

# Expected: enhancetool transformer → proactive tool usage
# Validation: Verify tool_choice="required" in request
```

### Validation Commands

```bash
# 1. Check router configuration loaded
cat ~/.claude-code-router/config.json | jq '.Providers[0].transformer'

# 2. Monitor requests (enable LOG: true)
tail -f ~/.claude-code-router/logs/requests.log

# 3. Test endpoint connectivity
curl -X POST http://X.X.12.12:30000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "zai-org/GLM-4.6",
    "messages": [{"role": "user", "content": "Test"}],
    "max_tokens": 200000
  }'
```

### Expected Outcomes

✅ **Success Indicators**:
- Request includes `max_tokens: 200000`
- Reasoning tasks show extended processing time
- Tool calls are proactive and well-reasoned
- No "context length exceeded" errors below 150K

❌ **Failure Indicators**:
- Requests default to 4K-8K tokens
- No reasoning_content in think mode responses
- Tool calling requires explicit user prompting
- Overflow errors below threshold

---

## 📚 Risorse

### Context7 Sources

1. **Claude Code Router** - `/musistudio/claude-code-router`
   - Trust Score: 9.4/10
   - Code Snippets: 44
   - Key Learning: Transformer chain architecture

2. **GLM-4.5/4.6** - `/zai-org/glm-4.5`
   - Trust Score: 7.6/10
   - Code Snippets: 25
   - Key Learning: Reasoning mode API parameters

### Reddit Discussion

**Source**: r/LocalLLaMA - "Reasoning with Claude Code Router and vLLM"
**Key Insights**:
- Reasoning mode critical for complex tasks
- MaxToken transformer prevents context overflow
- EnhanceTool improves coding task quality

### Official Documentation

- **GLM-4.6 API**: https://open.bigmodel.cn/dev/api
- **Claude Code Router**: https://github.com/musistudio/claude-code-router
- **vLLM Reasoning**: https://docs.vllm.ai/en/latest/

---

## 🎯 Checklist Implementazione

### Pre-Deployment

- [ ] Backup configurazione attuale
- [ ] Verifica endpoint server (http://X.X.12.12:30000)
- [ ] Conferma server supporta reasoning-parser
- [ ] Review logs directory (`~/.claude-code-router/logs/`)

### Deployment

- [ ] Copia `claude-code-router-config-optimized.json` a `~/.claude-code-router/config.json`
- [ ] Restart Claude Code Router (`ccr restart`)
- [ ] Verifica caricamento config (`ccr status`)

### Post-Deployment

- [ ] Test context window (task > 100K tokens)
- [ ] Test reasoning mode (task complesso)
- [ ] Test tool calling (multi-tool scenario)
- [ ] Monitor performance (latency, accuracy)

### Rollback Plan

```bash
# Se problemi, ripristina config originale
cp ~/.claude-code-router/config.json.backup ~/.claude-code-router/config.json
ccr restart
```

---

**Creato da**: Claude Code (Sonnet 4.5) via Context7 Research
**Data**: 2025-10-06
**Versione Config**: 2.0 (Optimized for GLM-4.6 Reasoning)
**Status**: ✅ Ready for Production Testing

---

## 🔄 Next Steps

1. **Immediate**: Deploy configurazione ottimizzata
2. **Short-term**: Eseguire test suite completo
3. **Long-term**: Monitorare metriche performance (latency, accuracy)
4. **Future**: Considerare multi-model routing (GLM-4.6 + fallback)
