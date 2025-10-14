# DevStream API Key Management

**Gestione centralizzata delle API key per provider AI**

---

## 🎯 Overview

DevStream gestisce le API key attraverso un sistema centralizzato che garantisce:
- **Persistenza** - Le API key vengono salvate automaticamente
- **Sicurezza** - Non è necessario impostarle manualmente ogni volta
- **Condivisione** - Tutti i progetti DevStream accedono alle stesse credenziali

---

## 🔐 Configurazione API Key

### Provider z.ai (GLM-4.6)

La API key di z.ai viene gestita automaticamente tramite il file `.env` di DevStream:

#### Step 1: Ottenere API Key
1. Visita la piattaforma z.ai
2. Registra un account se necessario
3. Ottieni la tua API key dal dashboard

#### Step 2: Configurare in DevStream
```bash
# Edit il file .env di DevStream
nano /Users/fulvioventura/devstream/.env

# Aggiungi la tua API key
ZAI_API_KEY='tua-api-key-z.ai-qui'

# Salva il file (Ctrl+X, Y, Enter in nano)
```

#### Step 3: Verifica Configurazione
```bash
# Verifica che la API key sia caricata
cd /Users/fulvioventura/devstream
grep ZAI_API_KEY .env

# Test di avvio con provider z.ai
cd /path/to/your/project
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh
# Scegli: 1) Claude Code + DevStream → 2) z.ai GLM-4.6
```

### Provider Anthropic (Claude)

Anthropic usa OAuth tramite Claude Code CLI:

#### Step 1: Installa Claude Code
```bash
npm install -g @anthropic-ai/claude-code
```

#### Step 2: Login OAuth
```bash
claude login
# Segui le istruzioni nel browser
# Visita https://claude.ai/ per completare
```

#### Step 3: Verifica Login
```bash
claude --version
# Dovrebbe mostrare la versione e confermare il login
```

---

## 🗂️ Struttura File

### `.env` di DevStream
```
# /Users/fulvioventura/devstream/.env

# Provider z.ai
ZAI_API_KEY=5a51efd5fd5f450886ef55241ded3dc7.0NT4E02LD3NLHftM

# Altre configurazioni DevStream
DEVSTREAM_DEBUG=false
DEVSTREAM_LOG_LEVEL=INFO
```

### `.devstream/config.json` del Progetto
```json
{
  "project": {
    "name": "nome-progetto",
    "provider": "z.ai",  // o "anthropic"
    "auto_start": true
  },
  "providers": {
    "anthropic": {
      "enabled": true,
      "model": "claude-3-5-sonnet-20241022",
      "auth_method": "oauth"
    },
    "z.ai": {
      "enabled": true,
      "model": "glm-4.6",
      "api_key_env": "ZAI_API_KEY"
    }
  }
}
```

---

## 🔧 Gestione API Key

### Verifica Stato API Key
```bash
# Controlla se l'API key è configurata
grep ZAI_API_KEY /Users/fulvioventura/devstream/.env

# Verifica caricamento automatico
cd /path/to/project
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh
# Scegli opzione 5) Provider configuration → 3) Show API setup instructions
```

### Aggiorna API Key
```bash
# Modifica il file .env
nano /Users/fulvioventura/devstream/.env

# Aggiorna la linea ZAI_API_KEY
ZAI_API_KEY='nuova-api-key-qui'

# Salva e riavvia la sessione
```

### Rimuovi API Key
```bash
# Edit il file .env
nano /Users/fulvioventura/devstream/.env

# Commenta o rimuovi la linea
# ZAI_API_KEY=vecchia-api-key

# Salva il file
```

---

## 🔍 Troubleshooting API Key

### Problema: "ZAI_API_KEY not found"
**Causa**: L'API key non è nel file `.env` di DevStream

**Soluzione**:
```bash
# 1. Verifica il file
cat /Users/fulvioventura/devstream/.env | grep ZAI_API_KEY

# 2. Se manca, aggiungila
echo "ZAI_API_KEY='tua-api-key'" >> /Users/fulvioventura/devstream/.env

# 3. Riavvia il launcher
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh
```

### Problema: "API key non valida"
**Causa**: L'API key è scaduta o errata

**Soluzione**:
```bash
# 1. Ottieni nuova API key dalla piattaforma z.ai
# 2. Aggiorna il file .env
nano /Users/fulvioventura/devstream/.env
# 3. Sostituisci la vecchia API key
# 4. Salva e testa nuovamente
```

### Problema: "Claude Code login non funzionante"
**Causa**: Problema con OAuth o sessione scaduta

**Soluzione**:
```bash
# 1. Logout forzato
claude logout

# 2. Login nuovo
claude login

# 3. Verifica
claude --version
```

### Problema: "Provider non disponibile"
**Causa**: Il provider non è configurato nel progetto

**Soluzione**:
```bash
# 1. Configura il provider
cd /path/to/project
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py set-provider z.ai .

# 2. Verifica configurazione
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py show .

# 3. Riavvia il launcher
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh
```

---

## 🔒 Sicurezza

### Best Practices per API Key

1. **Mai commitare le API key** in Git
   ```bash
   # .gitignore
   .env
   *.key
   ZAI_API_KEY*
   ```

2. **Usare API key dedicate** per ogni progetto/ambiente
3. **Rotazione periodica** delle API key
4. **Limitare permessi** delle API key

### Verifica Sicurezza
```bash
# Controlla che .env sia in .gitignore
grep "\.env" /Users/fulvioventura/devstream/.gitignore

# Verifica che non ci siano API key commitate
git log --all --full-history -- "*.env" | grep -i "key\|secret\|token"
```

---

## 🚀 Quick Reference

### Setup Rapido z.ai
```bash
# 1. Configura API key
echo "ZAI_API_KEY='tua-api-key'" >> /Users/fulvioventura/devstream/.env

# 2. Avvia progetto con provider z.ai
cd /path/to/project
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh
# → Scegli: 1) Claude Code + DevStream → 2) z.ai GLM-4.6
```

### Setup Rapido Anthropic
```bash
# 1. Installa e login Claude Code
npm install -g @anthropic-ai/claude-code
claude login

# 2. Avvia progetto con provider Anthropic
cd /path/to/project
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh
# → Scegli: 1) Claude Code + DevStream → 1) Anthropic Claude
```

### Test Provider
```bash
# Test z.ai
export ZAI_API_KEY='tua-api-key'
curl -H "Authorization: Bearer $ZAI_API_KEY" https://api.z.ai/v1/models

# Test Anthropic
claude --version
```

---

## 📋 Checklist Configurazione

- [ ] API key z.ai in `/Users/fulvioventura/devstream/.env`
- [ ] Claude Code installato e login completato
- [ ] Provider configurato per ogni progetto
- [ ] `.env` in `.gitignore`
- [ ] Test di avvio sessione completato

---

**Ora le tue API key sono gestite automaticamente e in modo sicuro!** 🔐✨