# 🚀 Quick Start: Claude Code con z.ai (GLM-4.6)

## ✅ Configurazione Completata

La chiave API z.ai è già configurata in `.env` (single source of truth).

## 🎯 Come Avviare Claude Code con GLM-4.6

### Opzione 1: Launcher Automatico (RACCOMANDATO) ✅

```bash
./start-devstream.sh start z.ai
```

**Cosa fa lo script**:
- ✅ Carica `.env` (root) con tutte le API keys
- ✅ Override `DEVSTREAM_LLM_PROVIDER=z.ai`
- ✅ Source `.env.llm-providers` per configurazione provider
- ✅ Imposta `ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic`
- ✅ Imposta `ANTHROPIC_API_KEY` dalla chiave z.ai in `.env`
- ✅ Avvia DevStream MCP Server
- ✅ Avvia Claude Code con z.ai backend

### Opzione 2: Configurazione Manuale

```bash
# 1. Source root .env
source .env

# 2. Override provider
export DEVSTREAM_LLM_PROVIDER=z.ai

# 3. Source provider config
source .env.llm-providers

# 4. Avvia Claude Code
claude
```

### Opzione 3: One-Liner (per test rapidi)

```bash
source .env && export DEVSTREAM_LLM_PROVIDER=z.ai && source .env.llm-providers && claude
```

## 📊 Mapping Modelli

| Claude Model | z.ai Model | Descrizione |
|--------------|------------|-------------|
| claude-opus-* | glm-4.6 | Flagship reasoning (massime prestazioni) |
| claude-sonnet-4-5* | glm-4.6 | Stesso modello (cost-effective) |
| claude-haiku-* | glm-4.5-air | Ultra-veloce (risposte rapide) |

## 🧪 Test Connessione API

```bash
# Test rapido (già eseguito con successo ✅)
./test_zai_connection.sh 5a51efd5fd5f450886ef55241ded3dc7.0NT4E02LD3NLHftM

# Output atteso:
# ✅ Connessione z.ai RIUSCITA!
# 📝 Risposta API: "Connessione z.ai funzionante!"
# 🎯 Provider z.ai pronto per l'uso con Claude Code
```

## 📝 Architettura Configurazione

```
Root .env (SINGLE SOURCE OF TRUTH)
  ↓
  └─ ZAI_API_KEY=5a51efd5fd5f450886ef55241ded3dc7.0NT4E02LD3NLHftM
     ↓
     ├─ .env.llm-providers (provider config)
     │  └─ ZAI_API_KEY=${ZAI_API_KEY:-} (inherited)
     │
     └─ scripts/providers/z.ai.sh
        └─ source .env → ZAI_API_KEY available
```

## 🔐 Gestione Credenziali

**IMPORTANTE**: Tutte le API keys sono in `.env` (root), MAI hardcoded altrove.

```bash
# .env (root) - UNICA FONTE
ZAI_API_KEY=5a51efd5fd5f450886ef55241ded3dc7.0NT4E02LD3NLHftM
SYNTHETIC_API_KEY=syn_2931060d44941b8444d15620bb6dc23d
OPENROUTER_API_KEY=sk-or-v1-...
```

## ⚙️ Verifica Stato Corrente

```bash
# Check provider attivo
grep "^DEVSTREAM_LLM_PROVIDER=" .env.llm-providers

# Check chiave API z.ai
grep "^ZAI_API_KEY=" .env

# Test completo
bash scripts/providers/z.ai.sh
```

## 🚨 Troubleshooting

### Errore: "ZAI_API_KEY not set"
```bash
# Verifica .env contiene la chiave
cat .env | grep ZAI_API_KEY

# Se mancante, aggiungi:
echo "ZAI_API_KEY=5a51efd5fd5f450886ef55241ded3dc7.0NT4E02LD3NLHftM" >> .env
```

### Errore: "API 401 Unauthorized"
- Verifica credito disponibile su https://z.ai/
- Controlla validità chiave API su https://z.ai/manage-apikey/apikey-list

### Modelli non trovati
- GLM-4.6 disponibile per account Pro
- GLM-4.5-air disponibile per tutti

## 📚 Risorse

- **z.ai Dashboard**: https://z.ai/
- **API Keys**: https://z.ai/manage-apikey/apikey-list
- **Documentazione**: https://z.ai/docs
- **Modelli disponibili**: https://open.bigmodel.cn/

---

**Status**: ✅ Configurazione validata (2025-10-06)
**Test API**: ✅ Connessione riuscita (HTTP 200)
**Credenziali**: ✅ Root .env configurato
**Ready**: ✅ Pronto per produzione
