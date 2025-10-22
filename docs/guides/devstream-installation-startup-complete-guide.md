# DevStream: Guida Completa Installazione e Avvio

**Versione**: 2.2.0 | **Data**: 2025-10-17 | **Stato**: Production Ready

---

## 📋 Indice

1. [Overview del Sistema](#overview-del-sistema)
2. [Prerequisites](#prerequisites)
3. [Modalità di Installazione](#modalità-di-installazione)
   - [Scenario A: Nuovo Progetto ex-novo](#scenario-a-nuovo-progetto-ex-novo)
   - [Scenario B: Progetto Esistente con Codebase](#scenario-b-progetto-esistente-con-codebase)
   - [Scenario C: Setup Progetto DevStream Principale](#scenario-c-setup-progetto-devstream-principale)
4. [Modalità di Avvio Sessione Claude+DevStream](#modalità-di-avvio-sessione-claude+devstream)
5. [Enhanced Hook Copying System (Nuovo)](#enhanced-hook-copying-system-nuovo)
6. [Troubleshooting](#troubleshooting)
7. [Riferimento Comandi Rapido](#riferimento-comandi-rapido)

---

## 🎯 Overview del Sistema

DevStream è un sistema multi-progetto che fornisce:
- **Isolamento Progetti**: Ogni progetto ha il proprio database e configurazione
- **Scelta Provider AI**: Anthropic Claude o z.ai GLM-4.6 per ogni progetto
- **Memory System**: Database vettoriale per contesto semantico con popolamento automatico
- **Enhanced Hook Copying**: Sistema avanzato di copia hook con Copier v9.10.2
- **Codebase Scanning**: Analisi automatica della struttura del progetto

---

## ✅ Prerequisites

### Sistema Operativo
- **macOS** (testato su macOS 15+)
- **Linux** (Ubuntu 20.04+, Debian 11+)
- **Windows** (WSL2 raccomandato)

### Software Richiesto
```bash
# Verifica Python 3.11+
python3 --version  # Dovrebbe mostrare 3.11.x o superiore

# Verifica Node.js 16+
node --version     # Dovrebbe mostrare v16.x o superiore

# Verifica Git
git --version      # Dovrebbe mostrare 2.x.x
```

### Claude Code (per provider Anthropic)
```bash
# Installa Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Login ad Anthropic
claude login
# Visita https://claude.ai/ per completare l'autenticazione
```

### API Key z.ai (per provider z.ai)
```bash
# Imposta la variabile d'ambiente
export ZAI_API_KEY='tua-api-key-z.ai'

# Aggiungi al tuo shell profile per persistenza
echo 'export ZAI_API_KEY='tua-api-key-z.ai'' >> ~/.bashrc  # o ~/.zshrc
source ~/.bashrc  # o source ~/.zshrc
```

---

## 🚀 Modalità di Installazione

### Scenario A: Nuovo Progetto ex-novo

#### Step 1: Setup Repository Git
```bash
mkdir my-awesome-project
cd my-awesome-project
git init
echo "# My Awesome Project" > README.md
git add .
git commit -m "Initial commit"
```

#### Step 2: Installazione DevStream con Enhanced Hook Copying
```bash
# Metodo automatico CON enhanced hook copying (raccomandato)
/Users/fulvioventura/devstream/scripts/install-devstream.sh --enhanced-hook-copying

# Senza enhanced hook copying (fallback standard)
/Users/fulvioventura/devstream/scripts/install-devstream.sh

# Per progetto esistente (preserva codice esistente)
/Users/fulvioventura/devstream/scripts/install-devstream.sh --existing-project --enhanced-hook-copying
```

**Cosa fa l'installazione con enhanced hook copying:**
- ✅ **Setup Python Environment**: Crea venv .devstream con Python 3.11+
- ✅ **Enhanced Hook Copying**: Usa Copier v9.10.2 per template-based copying
- ✅ **6-Level Integrity Validation**: Verifica completa degli hook copiati
- ✅ **Project Structure**: Crea directory DevStream complete
- ✅ **Dependencies Installation**: Installa cchooks, aiohttp, structlog, Copier
- ✅ **Database Initialization**: Crea database con Direct DB Architecture
- ✅ **Claude Code Configuration**: Configura settings.json automaticamente
- ✅ **Memory Bootstrap**: Scansiona e indicizza automaticamente il codebase

#### Step 3: Scelta Provider AI e Avvio
```bash
# Metodo interattivo (raccomandato)
/Users/fulvioventura/devstream/scripts/start-devstream.sh

# Scegli dal menu:
# 1) 🤖 Claude Code + DevStream
# 2) 📋 Multi-Project Setup (per progetti multipli)
# 3) ⚙️  Configure DevStream
# 4) 📊 Project Status
# 5) 🚀 Quick Start with Provider

# Oppure avvio diretto
export DEVSTREAM_PROJECT_ROOT="/path/to/my-awesome-project"
/Users/fulvioventura/devstream/start-devstream.sh start anthropic
# oppure
/Users/fulvioventura/devstream/start-devstream.sh start z.ai
```

---

### Scenario B: Progetto Esistente con Codebase

Questo scenario è per progetti che hanno già un codebase sviluppato e需要 DevStream integration.

#### Step 1: Naviga nel Progetto Esistente
```bash
cd /path/to/your/existing-project

# Verifica che sia un progetto Git
git status
```

#### Step 2: Installazione DevStream con Popolamento Database Automatico
```bash
# Installazione INTEGRATA per progetto esistente
/Users/fulvioventura/devstream/scripts/install-devstream.sh \
  --existing-project \
  --enhanced-hook-copying \
  --merge-requirements
```

**Cosa succede automaticamente:**
- ✅ **Preserve Existing Code**: Mantiene tutto il codice esistente intatto
- ✅ **Merge Requirements**: Unisce requirements.txt esistenti con dipendenze DevStream (con backup automatico)
- ✅ **Enhanced Hook Copying**: Installa hook DevStream con validazione integrità
- ✅ **Project Type Detection**: Rileva automaticamente Python/TS/Go/Rust/Java
- ✅ **Codebase Scanning Smart**: Seleziona automaticamente le directory principali (src/, app/, frontend/, …) e salva la configurazione in `.env.devstream`
- ✅ **Protocol Copying**: Copia in progetto i protocolli `sessions/protocols/*.md` per mantenere la documentazione locale
- ✅ **Memory Database Population**: Indicizza il codebase nel database vettoriale (solo se non già popolato)
- ✅ **Project Migrations (Alembic)**: Se `alembic.ini` e `migrations/` sono presenti, lo script esegue `alembic upgrade head`
- ✅ **CLAUDE.md Generation**: Crea protocollo DevStream specifico per il progetto
- ✅ **Virtual Environment**: Crea `.devstream/` venv se non esiste

#### Step 3: Gestione database esistente
Quando nel progetto è già presente `data/devstream.db`:
- Lo script segnala la presenza del DB e chiede se mantenerlo o ricrearlo.
- In caso di **mantenimento**, viene applicato lo schema aggiornato (senza distruggere i dati).
- In caso di **ricreazione**, il DB viene rigenerato e il bootstrap di memoria riparte da zero.
- È sempre possibile cambiare idea più tardi con `make db-reset` o `python scripts/init-project-db.py`.

#### Step 4: Verifica Popolamento Database
```bash
# Il bootstrap full parte in automatico a fine installazione
ls -la data/devstream.db
.devstream/bin/python -c "
from .claude.hooks.devstream.utils.direct_client import get_direct_client
client = get_direct_client()
result = client.search_memory('main function', limit=5)
print(f'Found {len(result[\"results\"])} indexed items')
"

# Output atteso (bootstrap e migrazioni già eseguiti):
# Found 15 indexed items (o di più)
# Log bootstrap: ~/.claude/logs/devstream/memory_bootstrap.log
# Log migrazioni (se fallite): controlla in installazione Step 6.2
 
# Verifica che la variabile d'ambiente punti al DB di progetto
env | grep DEVSTREAM_DB_PATH
# -> DEVSTREAM_DB_PATH=/path/to/project/data/devstream.db
```

#### Step 5: Avvio Sessione
```bash
# Imposta il progetto corrente
export DEVSTREAM_PROJECT_ROOT="$(pwd)"

# Avvia con provider scelto
/Users/fulvioventura/devstream/start-devstream.sh start anthropic
# oppure
/Users/fulvioventura/devstream/start-devstream.sh start z.ai
```

**Vantaggi del progetto esistente con DevStream:**
- 🧠 **Context Immediately Available**: Il codebase è già indicizzato e disponibile appena avvii Claude Code
- 🎯 **Project-Aware Protocol**: CLAUDE.md contiene comandi specifici per il tuo progetto
- 📊 **Smart Memory**: Ricerca semantica funziona subito sul tuo codice (o riparte da zero se hai scelto il reset)
- 📚 **Protocolli Locali**: I file `sessions/protocols/*.md` sono copiati nel progetto e sempre aggiornati
- 🔧 **Enhanced Features**: Hook system con validazione e Copier integration

---

### Scenario C: Setup Progetto DevStream Principale

Per lavorare sul codice DevStream stesso o per sessioni di sistema.

#### Step 1: Naviga nel Repository DevStream
```bash
cd /Users/fulvioventura/devstream
```

#### Step 2: Setup Ambiente DevStream
```bash
# Verifica/installa dipendenze
if [ ! -d ".devstream" ]; then
    python3.11 -m venv .devstream
fi

.devstream/bin/python -m pip install -r requirements.txt
.devstream/bin/python -m pip install cchooks aiohttp structlog
```

#### Step 3: Avvio Sessione DevStream System
```bash
# Metodo 1: Start DevStream System (raccomandato)
./start-devstream.sh start anthropic
# oppure
./start-devstream.sh start z.ai

# Metodo 2: Restart (se già in esecuzione)
./start-devstream.sh restart anthropic

# Metodo 3: Quick launcher
./scripts/simple-launcher.sh start anthropic
```

**Cosa succede durante l'avvio di DevStream system:**
- 🔄 **Enhanced Hook Copying**: Verifica e aggiorna hook DevStream system
- 🗄️ **System Database**: Inizializza database per gestione multi-progetto
- 🧠 **Memory System**: Prepara memory system per progetti multipli
- 🔧 **System Services**: Avvia servizi interni DevStream
- 📊 **Project Registry**: Prepara registry per tracking progetti

---

## 🚀 Modalità di Avvio Sessione Claude+DevStream

### 1. Avvio in Progetto DevStream (System Mode)

```bash
# Directory: /Users/fulvioventura/devstream
./start-devstream.sh start anthropic
./start-devstream.sh start z.ai
./start-devstream.sh restart anthropic  # per restart
```

**Use case:** Lavorare sul codice DevStream, sviluppo di sistema, testing interno

### 2. Avvio in Progetti Esterni (Project Mode)

```bash
# Method 1: Export + Start (raccomandato)
cd /path/to/your-project
export DEVSTREAM_PROJECT_ROOT="$(pwd)"
/Users/fulvioventura/devstream/start-devstream.sh start anthropic

# Method 2: Direct from DevStream (funziona ma meno comune)
cd /Users/fulvioventura/devstream
export DEVSTREAM_PROJECT_ROOT="/path/to/your-project"
./start-devstream.sh start anthropic

# Method 3: Simple Launcher (per progetti già configurati)
cd /path/to/your-project
/Users/fulvioventura/devstream/scripts/simple-launcher.sh start anthropic
```

**Use case:** Sviluppo su progetti esterni con DevStream integration

> ℹ️ `start-devstream.sh` copia automaticamente i protocolli in `sessions/protocols`, esporta `DEVSTREAM_DB_PATH` e aggiorna `PYTHONPATH` con gli hook condivisi. Non è più necessario eseguire passaggi manuali dopo l’avvio.

### 3. Avvio Multi-Project Mode

```bash
# Dal progetto principale
export DEVSTREAM_PROJECT_ROOT="/path/to/main-project"
/Users/fulvioventura/devstream/start-devstream.sh start anthropic

# Il sistema rileverà automaticamente i sotto-progetti
# e creerà database isolati per ciascuno
```

**Use case:** Progetti complessi con sub-progetti o monorepo

### 4. Provider Switching Runtime

```bash
# Cambia provider al volo
cd /path/to/your-project
./start-devstream.sh restart z.ai  # da anthropic a z.ai
./start-devstream.sh restart anthropic  # da z.ai a anthropic
```

---

## 🔧 Enhanced Hook Copying System (Nuovo)

Il nuovo sistema di enhanced hook copying è ora integrato e disponibile.

### Caratteristiche Principali

**🚀 Copier v9.10.2 Integration**
- Template-based project copying
- Incremental deployment support
- Intelligent file handling

**🛡️ 6-Level Integrity Validation**
- File existence validation
- Permissions validation
- Syntax validation
- Dependency validation
- Functionality validation
- Integration validation

**🔍 SHA256 Checksum Verification**
- Cryptographic integrity checking
- Automatic corruption detection
- Backup and recovery support

### Utilizzo

#### Installazione con Enhanced Hook Copying
```bash
# Nuovo progetto
/Users/fulvioventura/devstream/scripts/install-devstream.sh --enhanced-hook-copying

# Progetto esistente
/Users/fulvioventura/devstream/scripts/install-devstream.sh \
  --existing-project \
  --enhanced-hook-copying \
  --merge-requirements
```

#### Verifica Enhanced Hook Copying
```bash
# Verifica che gli hook siano stati installati correttamente
ls -la .claude/hooks/devstream/
ls -la .claude/hooks/devstream/utils/multi_project_hook_copier.py
ls -la .claude/hooks/devstream/utils/hook_integrity_validator.py

# Test validazione integrità
.devstream/bin/python -c "
from .claude.hooks.devstream.utils.hook_integrity_validator import HookIntegrityValidator
validator = HookIntegrityValidator('/Users/fulvioventura/devstream')
import asyncio
result = asyncio.run(validator.validate_comprehensive('.claude/hooks/devstream'))
print(f'Validation passed: {result.get(\"success\", False)}')
"
```

#### Manual Enhanced Hook Copying (se necessario)
```bash
# Copia manuale con enhanced system
.devstream/bin/python -c "
import asyncio
import sys
sys.path.insert(0, '.claude/hooks/devstream/utils')

from multi_project_bootstrap import bootstrap_devstream_project

result = asyncio.run(bootstrap_devstream_project(
    target_root='.',
    source_root='/Users/fulvioventura/devstream',
    project_name='my-project',
    integrity_validation=True,
    claude_code_config=True,
    verbose=True
))

print(result)
"
```

---

## 🔧 Troubleshooting

### Problemi Comuni e Soluzioni

#### 1. "Enhanced hook copying failed"
```bash
# Soluzione: Usa fallback standard
/Users/fulvioventura/devstream/scripts/install-devstream.sh --existing-project

# Verifica dipendenze Copier
.devstream/bin/python -c "import copier; print(f'Copier v{copier.__version__} available')"
```

#### 2. "Database not populated" in progetti esistenti
```bash
# Soluzione: Forza memory bootstrap
.devstream/bin/python .claude/hooks/devstream/memory/memory_bootstrap.py . --mode incremental

# Verifica popolamento
.devstream/bin/python -c "
from .claude.hooks.devstream.utils.direct_client import get_direct_client
client = get_direct_client()
result = client.search_memory('test', limit=1)
print(f'Database populated: {len(result[\"results\"]) > 0}')
"
```

#### 3. "Python 3.11+ non trovato"
```bash
# Su macOS con Homebrew
brew install python@3.11

# Su Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv

# Verifica
python3.11 --version
```

#### 4. "Claude Code non funziona"
```bash
# Reinstalla Claude Code
npm uninstall -g @anthropic-ai/claude-code
npm install -g @anthropic-ai/claude-code

# Login di nuovo
claude login
```

#### 5. "Multi-project mode non rileva progetto"
```bash
# Verifica impostazione
echo $DEVSTREAM_PROJECT_ROOT

# Imposta manualmente
export DEVSTREAM_PROJECT_ROOT="/path/to/your/project"
./start-devstream.sh start anthropic
```

### Debug Mode

Abilita output dettagliato:
```bash
# Per installation
export DEVSTREAM_DEBUG=true
/Users/fulvioventura/devstream/scripts/install-devstream.sh --enhanced-hook-copying

# Per startup
export DEVSTREAM_DEBUG=true
./start-devstream.sh start anthropic
```

### Log Files

Controlla i log per errori:
```bash
# Log di progetto
tail -f .devstream/logs/devstream.log

# Log system DevStream
tail -f /Users/fulvioventura/devstream/.claude/logs/devstream.log
```

---

## 📚 Riferimento Comandi Rapido

### Installazione
```bash
# Nuovo progetto con enhanced hook copying
/Users/fulvioventura/devstream/scripts/install-devstream.sh --enhanced-hook-copying

# Progetto esistente con popolamento database automatico
/Users/fulvioventura/devstream/scripts/install-devstream.sh --existing-project --enhanced-hook-copying --merge-requirements
```

### Avvio Sessioni
```bash
# Progetto DevStream (system mode)
./start-devstream.sh start anthropic
./start-devstream.sh start z.ai

# Progetti esterni (project mode)
export DEVSTREAM_PROJECT_ROOT="/path/to/project"
/Users/fulvioventura/devstream/start-devstream.sh start anthropic

# Quick launcher (progetti configurati)
/Users/fulvioventura/devstream/scripts/simple-launcher.sh start anthropic
```

### Gestione Progetti
```bash
# Lista tutti i progetti
~/.devstream/bin/devstream list

# Status progetto corrente
~/.devstream/bin/devstream status

# Rileva progetto corrente
~/.devstream/bin/devstream detect
```

### Provider Management
```bash
# Cambia provider
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py set-provider anthropic .

# Verifica provider
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py get-provider .
```

### Enhanced Hook Copying
```bash
# Test validazione hook
.devstream/bin/python -c "
from .claude.hooks.devstream.utils.hook_integrity_validator import HookIntegrityValidator
validator = HookIntegrityValidator('/Users/fulvioventura/devstream')
import asyncio
result = asyncio.run(validator.validate_comprehensive('.claude/hooks/devstream'))
print(result)
"
```

---

## 🎯 Best Practices

### 1. Organizzazione Progetti
```
~/projects/
├── work/
│   ├── project-alpha/     # Provider: Anthropic (architecture)
│   ├── project-beta/      # Provider: z.ai (implementation)
│   └── project-gamma/     # Provider: Anthropic (research)
├── personal/
│   ├── my-blog/          # Provider: z.ai (simple)
│   └── home-automation/  # Provider: z.ai (iot)
└── learning/
    ├── rust-demo/        # Provider: Anthropic (learning)
    └── ml-experiment/    # Provider: Anthropic (complex)
```

### 2. Provider Choice Guidelines
- **Anthropic**: Progetti complessi, architettura, ricerca, planning
- **z.ai**: Implementazione rapida, testing, progetti semplici, MVP

### 3. Environment Setup
```bash
# .bashrc o .zshrc
export PATH="$HOME/.devstream/bin:$PATH"
export ZAI_API_KEY='tua-api-key'
export DEVSTREAM_DEBUG=false  # Imposta a true per debug
```

### 4. Git Integration
Ignora file DevStream in Git:
```bash
# .gitignore
.devstream/db/
.devstream/cache/
.devstream/logs/
*.log
__pycache__/
node_modules/
.env
```

---

## 🆘 Supporto e Community

### Risorse
- **Repository**: https://github.com/fulvian/devstream
- **Documentation**: `/docs` directory nel repository
- **Issues**: https://github.com/fulvian/devstream/issues

### Comandi di Diagnostica
```bash
# System check
~/.devstream/bin/devstream status

# Project diagnostics
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py show .

# Enhanced hook copying check
.devstream/bin/python -c "
import sys
sys.path.insert(0, '.claude/hooks/devstream/utils')
from multi_project_hook_copier import copy_devstream_hooks_enhanced
print('Enhanced hook copying: AVAILABLE')
"
```

---

**🎉 Ora sei pronto per usare DevStream in tutti gli scenari!**

Questa guida copre tutte le modalità di installazione e avvio, dal nuovo progetto ex-novo al progetto esistente con codebase, fino al sistema DevStream principale. Il nuovo enhanced hook copying system garantisce deployments robusti e validati.
