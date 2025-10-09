# 🚀 Deploy GLM-4.6 Configurazione Ottimizzata - Quick Guide

**Modello**: zai-org/GLM-4.6 (200K context)
**Tempo Stimato**: 5 minuti
**Prerequisiti**: Claude Code Router già installato

---

## ✅ Pre-Flight Checklist

```bash
# 1. Verifica Claude Code Router installato
which ccr
# Output atteso: /usr/local/bin/ccr (o simile)

# 2. Verifica endpoint GLM-4.6 raggiungibile
curl -s http://X.X.12.12:30000/v1/models
# Output atteso: {"data": [{"id": "zai-org/GLM-4.6", ...}]}

# 3. Backup config attuale
cp ~/.claude-code-router/config.json ~/.claude-code-router/config.json.backup-$(date +%Y%m%d-%H%M%S)
```

---

## 📝 Step-by-Step Deployment

### Step 1: Copia Configurazione Ottimizzata

```bash
# Copia file ottimizzato
cp claude-code-router-config-optimized.json ~/.claude-code-router/config.json
```

### Step 2: Verifica Sintassi JSON

```bash
# Valida JSON
cat ~/.claude-code-router/config.json | jq '.' > /dev/null && echo "✅ JSON valido" || echo "❌ JSON invalido"
```

### Step 3: Restart Claude Code Router

```bash
# Restart service
ccr restart

# Attendi 3 secondi per startup
sleep 3
```

### Step 4: Verifica Caricamento Config

```bash
# Check transformer configuration
cat ~/.claude-code-router/config.json | jq '.Providers[0].transformer'

# Output atteso:
# {
#   "use": [
#     "OpenAI",
#     ["maxtoken", {"max_tokens": 200000}],
#     "enhancetool"
#   ],
#   "zai-org/GLM-4.6": {
#     "use": ["reasoning"]
#   }
# }
```

---

## 🧪 Quick Validation Tests

### Test 1: Context Window (200K)

```bash
# Test long context capability
ccr code "Analyze entire DevStream codebase structure"

# Validazione:
# - Task completa senza "context length exceeded"
# - Response considera più di 8K tokens di context
```

### Test 2: Reasoning Mode

```bash
# Test reasoning mode activation
ccr code "Design microservices architecture for real-time analytics platform with 1M+ users"

# Validazione:
# - Response mostra step-by-step reasoning
# - Processing time maggiore del normale (thinking mode attivo)
```

### Test 3: Tool Calling Enhanced

```bash
# Test proactive tool usage
ccr code "Find security vulnerabilities in dependencies and suggest fixes"

# Validazione:
# - Tools invocati automaticamente (npm audit, grep, etc.)
# - No necessità di prompt espliciti per tool usage
```

---

## 📊 Configurazione Dettagliata

### Transformer Chain

**Global Transformers** (applicati a TUTTI i task):
```json
"use": [
  "OpenAI",                              // ✅ Base OpenAI API compatibility
  ["maxtoken", {"max_tokens": 200000}],  // ✅ Full 200K context window
  "enhancetool"                          // ✅ Proactive tool calling
]
```

**Model-Specific Transformer** (solo per routing "think"):
```json
"zai-org/GLM-4.6": {
  "use": ["reasoning"]  // ✅ Extended thinking mode
}
```

### Router Strategy

| Task Type | Max Tokens | Reasoning | Tool Enhancement | Use Case |
|-----------|-----------|-----------|------------------|----------|
| `default` | 200K | ❌ | ✅ | General coding |
| `background` | 200K | ❌ | ✅ | Long operations |
| `think` | 200K | ✅ | ✅ | Complex reasoning |
| `longContext` | 200K | ❌ | ✅ | Context > 150K |

**Threshold Logic**:
- Context < 150K → Route: `default`
- Context ≥ 150K → Route: `longContext`
- Reasoning task → Route: `think` (manual override)

---

## 🔍 Troubleshooting

### Issue 1: "Context length exceeded"

**Causa**: max_tokens non applicato
**Fix**:
```bash
# Verifica transformer maxtoken presente
cat ~/.claude-code-router/config.json | jq '.Providers[0].transformer.use[] | select(.[0] == "maxtoken")'

# Output atteso: ["maxtoken", {"max_tokens": 200000}]
```

### Issue 2: Reasoning mode non attivo

**Causa**: Model-specific transformer mancante
**Fix**:
```bash
# Verifica reasoning transformer
cat ~/.claude-code-router/config.json | jq '.Providers[0].transformer."zai-org/GLM-4.6"'

# Output atteso: {"use": ["reasoning"]}
```

### Issue 3: Tool calling non proattivo

**Causa**: enhancetool transformer non configurato
**Fix**:
```bash
# Verifica enhancetool presente
cat ~/.claude-code-router/config.json | jq '.Providers[0].transformer.use[] | select(. == "enhancetool")'

# Output atteso: "enhancetool"
```

### Issue 4: Server non risponde

**Causa**: Endpoint errato o server offline
**Fix**:
```bash
# Test connectivity
curl -X POST http://X.X.12.12:30000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 0000" \
  -d '{
    "model": "zai-org/GLM-4.6",
    "messages": [{"role": "user", "content": "Test"}],
    "max_tokens": 100
  }'

# Se timeout: Verifica firewall, VPN, server status
```

---

## 📈 Performance Monitoring

### Enable Debug Logging

```bash
# Edit config per debugging
jq '.LOG = true | .LOG_LEVEL = "debug"' ~/.claude-code-router/config.json > /tmp/config.json
mv /tmp/config.json ~/.claude-code-router/config.json
ccr restart
```

### Monitor Logs

```bash
# Real-time log monitoring
tail -f ~/.claude-code-router/logs/requests.log

# Grep reasoning mode requests
grep "reasoning" ~/.claude-code-router/logs/requests.log

# Grep max_tokens applications
grep "max_tokens" ~/.claude-code-router/logs/requests.log
```

---

## 🔄 Rollback Procedure

Se problemi dopo deployment:

```bash
# 1. Stop router
ccr stop

# 2. Restore backup
cp ~/.claude-code-router/config.json.backup-YYYYMMDD-HHMMSS ~/.claude-code-router/config.json

# 3. Restart
ccr restart

# 4. Verify
ccr status
```

---

## ✅ Success Criteria

Configurazione funzionante se:

- [x] Context > 100K tokens elaborato senza errori
- [x] Reasoning tasks mostrano step-by-step thinking
- [x] Tools invocati proattivamente senza prompt espliciti
- [x] Nessun "context length exceeded" error sotto 150K
- [x] Latency accettabile (< 30s per reasoning tasks)

---

## 📚 File di Riferimento

| File | Descrizione | Posizione |
|------|-------------|-----------|
| `claude-code-router-config-optimized.json` | Config ottimizzata | Project root |
| `GLM46_REASONING_MODE_GUIDE.md` | Guida completa | Project root |
| `config.json` | Config attiva | `~/.claude-code-router/` |
| `requests.log` | Request logs | `~/.claude-code-router/logs/` |

---

## 🎯 Next Steps Post-Deployment

1. **Immediate** (0-1 ore):
   - Eseguire 3 validation tests
   - Verificare logs per errori
   - Confermare transformer chain attiva

2. **Short-term** (1-7 giorni):
   - Monitorare performance real-world
   - Raccogliere metriche latency/accuracy
   - Iterare su threshold tuning

3. **Long-term** (1+ mesi):
   - Considerare multi-model fallback
   - Valutare GLM-4.7 quando disponibile
   - Documentare best practices team

---

**Deployment Date**: 2025-10-06
**Config Version**: 2.0 (Optimized for GLM-4.6)
**Status**: ✅ Ready for Production
**Support**: Vedi `GLM46_REASONING_MODE_GUIDE.md` per troubleshooting esteso
