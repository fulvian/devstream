# 🚀 Quick Start: Claude Code con z.ai (GLM-4.6)

## 🎯 Modello di Sottoscrizione Duale

**IMPORTANTE**: Anthropic Max Plan e z.ai sono sistemi **separati e indipendenti**.

| Provider | Autenticazione | Sottoscrizione | Modello |
|----------|---------------|----------------|---------|
| **Anthropic** | OAuth (claude login) | Max Plan | Claude Sonnet 4.5 |
| **z.ai** | API Key | Coding Plan | GLM-4.6 |

> ⚠️ **Non puoi mescolare le sottoscrizioni**: z.ai richiede la propria API key e sottoscrizione separata.

## ✅ Prerequisiti

### 1. Anthropic Max Plan (Default)
```bash
# Verifica login
claude auth status

# Se non loggato:
claude login
```

### 2. z.ai Coding Plan (Opzionale)
1. Registrati su https://z.ai/
2. Ottieni API key da https://z.ai/manage-apikey/apikey-list
3. Aggiungi a `.env`:
```bash
ZAI_API_KEY=your-api-key-here
```

## 🚀 Avvio Rapido

### Opzione 1: Anthropic Max Plan (Default) ✅

```bash
./start-devstream.sh start
```

**Cosa fa lo script**:
- ✅ Verifica `claude auth status` (OAuth login)
- ✅ Unset TUTTE le variabili API (preserva Max Plan)
- ✅ Avvia DevStream MCP Server
- ✅ Avvia Claude Code con Sonnet 4.5

### Opzione 2: z.ai Provider

```bash
./start-devstream.sh start z.ai
```

**Cosa fa lo script**:
- ✅ Valida `ZAI_API_KEY` in `.env`
- ✅ Imposta `ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic`
- ✅ Imposta `ANTHROPIC_AUTH_TOKEN=$ZAI_API_KEY`
- ✅ Avvia Claude Code con GLM-4.6

## 📊 Mapping Modelli

| Claude Model | Anthropic | z.ai | Descrizione |
|--------------|-----------|------|-------------|
| claude-opus-* | Opus 3.5 | glm-4.6 | Flagship reasoning |
| claude-sonnet-4-5* | Sonnet 4.5 | glm-4.6 | Production |
| claude-haiku-* | Haiku 3.5 | glm-4.5-air | Ultra-veloce |

## 🔄 Switching tra Providers

### Da Anthropic a z.ai
```bash
./start-devstream.sh restart z.ai
```

### Da z.ai ad Anthropic
```bash
./start-devstream.sh restart anthropic
```

> ✅ **Preservazione Settings**: hooks e mcpServers sono preservati automaticamente

## 🔐 Gestione Credenziali

**IMPORTANTE**: Tutte le API keys sono in `.env` (root), MAI hardcoded altrove.

```bash
# .env (root) - UNICA FONTE
ZAI_API_KEY=your-zai-api-key-here
CONTEXT7_API_KEY=your-context7-api-key-here
GITHUB_PERSONAL_ACCESS_TOKEN=your-github-token-here
```

## ⚙️ Verifica Stato Corrente

```bash
# Check provider attivo
echo $ANTHROPIC_BASE_URL

# Output:
# - (vuoto) = Anthropic Max Plan
# - https://api.z.ai/api/anthropic = z.ai

# Verifica autenticazione Anthropic
claude auth status

# Verifica chiave z.ai
grep "^ZAI_API_KEY=" .env
```

## 🚨 Troubleshooting

### Errore: "Not logged into Claude.ai"
```bash
# Login OAuth per Anthropic Max Plan
claude login

# Verifica
claude auth status
```

### Errore: "ZAI_API_KEY not configured"
```bash
# Verifica .env contiene la chiave
cat .env | grep ZAI_API_KEY

# Se mancante, aggiungi:
echo "ZAI_API_KEY=your-api-key-here" >> .env
```

### Errore: "API 401 Unauthorized" (z.ai)
- Verifica credito disponibile su https://z.ai/
- Controlla validità chiave API su https://z.ai/manage-apikey/apikey-list
- Verifica sottoscrizione Coding Plan attiva

### Max Plan non funziona dopo switch z.ai
```bash
# Reset completo ad Anthropic
./start-devstream.sh restart anthropic

# Verifica tutte le variabili API sono unset
env | grep ANTHROPIC
# Output atteso: (nessun output, tutte unset)
```

## 📚 Architettura Semplificata

```
start-devstream.sh
  ↓
  ├─ Provider: anthropic (default)
  │  ├─ Verifica: claude auth status
  │  ├─ Unset: ANTHROPIC_BASE_URL
  │  ├─ Unset: ANTHROPIC_API_KEY
  │  └─ Unset: ANTHROPIC_AUTH_TOKEN
  │
  └─ Provider: z.ai
     ├─ Valida: ZAI_API_KEY in .env
     ├─ Export: ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
     └─ Export: ANTHROPIC_AUTH_TOKEN=$ZAI_API_KEY
```

## 📚 Risorse

### Anthropic
- **Max Plan Dashboard**: https://claude.ai/
- **CLI Login**: `claude login`
- **Documentazione**: https://docs.anthropic.com/

### z.ai
- **Dashboard**: https://z.ai/
- **API Keys**: https://z.ai/manage-apikey/apikey-list
- **Documentazione**: https://docs.z.ai/
- **Modelli disponibili**: https://open.bigmodel.cn/

---

**Status**: ✅ Dual subscription model (2025-10-06)
**Providers**: Anthropic Max Plan (OAuth) + z.ai Coding Plan (API)
**Architettura**: Semplificata (rimosso .env.llm-providers)
**Ready**: ✅ Pronto per produzione
