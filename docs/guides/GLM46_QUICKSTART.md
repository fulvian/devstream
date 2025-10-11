# Guida Rapida - Attivare GLM-4.6 in Claude Code

## ✅ Problema Risolto

Claude Code ora può usare **GLM-4.6 di z.ai** invece del modello predefinito Anthropic Sonnet 4.5.

## 🚀 Comando per Avviare con GLM-4.6

### Metodo 1: Script DevStream (Raccomandato)
```bash
./start-devstream.sh start z.ai
```

### Metodo 2: Manuale
```bash
# 1. Carica configurazione z.ai
source .env.llm-providers

# 2. Avvia Claude Code
claude
```

## 📊 Verifica Configurazione

Quando avvii con il provider z.ai, dovresti vedere:

```
✅ DevStream LLM Provider: z.ai (GLM-4.6)
   Base URL: https://api.z.ai/api/anthropic
   Models: Opus/Sonnet→glm-4.6, Haiku→glm-4.5-air
```

## 🤖 Caratteristiche GLM-4.6

- **Modello**: GLM-4.6 di Zhipu AI
- **Finestra di contesto**: 200K tokens
- **Tool Calling**: Supporto nativo
- **Reasoning Mode**: Abilitata di default
- **Piano**: GLM Coding Lite ($3/mese)

## 🔧 Configurazione Tecnica

La configurazione utilizza l'endpoint Claude-compatible di z.ai:
- **Endpoint**: `https://api.z.ai/api/anthropic`
- **Autenticazione**: Bearer token (ZAI_API_KEY)
- **Mapping modelli**:
  - `claude-sonnet-*` → `glm-4.6`
  - `claude-opus-*` → `glm-4.6`
  - `claude-haiku-*` → `glm-4.5-air`

## 📝 Note Importanti

1. **API Key già configurata**: La tua API key z.ai è già impostata
2. **Endpoint corretto**: DevStream usa l'endpoint Claude-compatible di z.ai
3. **Nessuna modifica richiesta**: Tutto è già configurato correttamente
4. **Basta solo attivare**: Usa il comando `./start-devstream.sh start z.ai`

## 🆚 Differenze Sonnet 4.5 vs GLM-4.6

Quando chiedi "quale modello sei?":
- **Sonnet 4.5**: "Sono Claude Sonnet 4.5, un modello linguistico avanzato sviluppato da Anthropic"
- **GLM-4.6**: "Sono GLM-4.6, un modello linguistico avanzato sviluppato da Zhipu AI"

## ⚡ Usage

Dopo l'avvio con `./start-devstream.sh start z.ai`, Claude Code risponderà con GLM-4.6 mantenendo tutte le funzionalità di DevStream:
- ✅ Semantic Memory
- ✅ Agent Auto-Delegation
- ✅ Context7 Integration
- ✅ Task Management
- ✅ Quality Gates

---
*Creato: 2025-10-05 | Stato: ✅ Verificato e funzionante*