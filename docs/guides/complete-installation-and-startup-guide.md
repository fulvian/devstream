# DevStream: Guida Completa all'Installazione e Avvio

**Versione**: 2.2.0 | **Data**: 2025-10-15 | **Stato**: Production Ready

---

## 📋 Indice

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Metodi di Installazione](#metodi-di-installazione)
4. [Configurazione Provider AI](#configurazione-provider-ai)
5. [Avvio di Nuovi Progetti](#avvio-di-nuovi-progetti)
6. [Gestione Progetti Multipli](#gestione-progetti-multipli)
7. [Troubleshooting](#troubleshooting)
8. [Riferimento Comandi](#riferimento-comandi)

---

## 🎯 Overview

DevStream è un sistema multi-progetto che fornisce:
- **Isolamento Progetti**: Ogni progetto ha il proprio database e configurazione
- **Scelta Provider AI**: Anthropic Claude o z.ai GLM-4.6 per ogni progetto
- **Memory System**: Database vettoriale per contesto semantico
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

## 🚀 Metodi di Installazione

### Metodo 1: Installazione Automatica Consigliata ⭐

Usa lo script automatico per qualsiasi progetto:

```bash
# Scarica DevStream (se non già fatto)
git clone https://github.com/fulvian/devstream.git
cd devstream

# Installa globalmente
bash scripts/install-devstream-global.sh

# Per qualsiasi nuovo progetto:
cd /path/to/your/project
bash /Users/fulvioventura/devstream/scripts/install-devstream-automatic.sh
```

**Cosa fa questo script:**
- ✅ Installa DevStream globalmente in `~/.devstream/`
- ✅ Configura PATH nel tuo shell profile
- ✅ Inizializza il progetto specifico
- ✅ Crea database isolato per il progetto
- ✅ Scansiona automaticamente il codebase
- ✅ Registra il progetto nel registry globale

### Metodo 2: Installazione Manuale

Per controllo completo sul processo:

#### Step 1: Installazione Globale
```bash
# Crea directory globale
mkdir -p ~/.devstream/{bin,data,config,hooks,lib,share,templates,logs}

# Copia i tool CLI
cp /path/to/devstream/scripts/devstream ~/.devstream/bin/
cp /path/to/devstream/scripts/devstream-init.py ~/.devstream/bin/
chmod +x ~/.devstream/bin/*

# Aggiungi al PATH
echo 'export PATH="$HOME/.devstream/bin:$PATH"' >> ~/.bashrc  # o ~/.zshrc
source ~/.bashrc
```

#### Step 2: Inizializzazione Progetto
```bash
cd /path/to/your/project
devstream-init.py . --verbose
```

#### Step 3: Registrazione Progetto
```bash
devstream register .
```

---

## 🤖 Configurazione Provider AI

### Scelta Provider per Progetto

Ogni progetto può avere un provider diverso:

#### Metodo Interattivo (Raccomandato)
```bash
cd /path/to/your/project
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh

# Scegli:
# 1) 🤖 Claude Code + DevStream (choose provider)
# → Seleziona 1) Anthropic o 2) z.ai
```

#### Metodo CLI
```bash
# Imposta provider Anthropic
/Users/fulvioventura/devstream/scripts/devstream-provider.sh /path/to/project set anthropic

# Imposta provider z.ai
/Users/fulvioventura/devstream/scripts/devstream-provider.sh /path/to/project set z.ai

# Vedi provider corrente
/Users/fulvioventura/devstream/scripts/devstream-provider.sh /path/to/project get
```

#### Metodo Python
```bash
# Configurazione diretta
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py set-provider anthropic /path/to/project
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py set-provider z.ai /path/to/project
```

### Configurazione Provider

**Anthropic Claude:**
- 🧠 **Best per**: Complex reasoning, architecture, planning
- 🔐 **Auth**: OAuth via Claude Code
- 📊 **Context**: Higher limits
- 💰 **Cost**: Higher

**z.ai GLM-4.6:**
- ⚡ **Best per**: Fast implementation, code generation, testing
- 🔐 **Auth**: API Key (ZAI_API_KEY)
- 📊 **Context**: Good limits
- 💰 **Cost**: Lower

---

## 🎬 Avvio di Nuovi Progetti

### Workflow Completo per Nuovo Progetto

#### Step 1: Setup Repository Git
```bash
mkdir my-awesome-project
cd my-awesome-project
git init
echo "# My Awesome Project" > README.md
git add .
git commit -m "Initial commit"
```

#### Step 2: Installazione DevStream
```bash
# Metodo automatico (raccomandato)
bash /Users/fulvioventura/devstream/scripts/install-devstream-automatic.sh

# Oppure manuale
devstream-init.py . --verbose
```

#### Step 3: Scelta Provider AI
```bash
# Launcher interattivo
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh

# Scegli provider dal menu
```

#### Step 4: Avvio Sessione
```bash
# Dal menu scegli:
# 1) Claude Code + DevStream

# Oppure diretto con provider specifico
claude --project .
```

### Esempi per Tipi di Progetto

#### Progetto Python
```bash
mkdir my-python-app
cd my-python-app

# Crea struttura base
echo 'flask==2.3.3' > requirements.txt
echo 'def hello(): return "Hello World"' > app.py
mkdir tests

# Installa DevStream
bash /Users/fulvioventura/devstream/scripts/install-devstream-automatic.sh

# Avvia con provider scelta
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh
```

#### Progetto TypeScript/React
```bash
mkdir my-react-app
cd my-react-app

# Crea struttura base
npm init -y
npm install react typescript @types/react
echo '{"compilerOptions": {"target": "es2020", "module": "commonjs"}}' > tsconfig.json
mkdir src
echo 'export default function App() { return <div>Hello</div>; }' > src/App.tsx

# Installa DevStream
bash /Users/fulvioventura/devstream/scripts/install-devstream-automatic.sh

# Avvia
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh
```

#### Progetto Go
```bash
mkdir my-go-service
cd my-go-service

# Inizializza modulo Go
go mod init my-go-service
echo 'package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}' > main.go

# Installa DevStream
bash /Users/fulvioventura/devstream/scripts/install-devstream-automatic.sh

# Avvia
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh
```

---

## 🗂️ Gestione Progetti Multipli

### Lista Tutti i Progetti
```bash
# Vedi tutti i progetti registrati
devstream list

# Output esempio:
# Registered Projects (3):
# ✅ accountabilly
#    Path: /Users/fulvioventura/accountabilly
#    Type: python
# ✅ my-react-app
#    Path: /Users/fulvioventura/projects/my-react-app
#    Type: typescript
# ✅ go-service
#    Path: /Users/fulvioventura/projects/go-service
#    Type: go
```

### Status Progetto
```bash
# Da qualsiasi directory
devstream status

# Da directory specifica
cd /path/to/project
devstream status
```

### Rileva Progetto Corrente
```bash
# Rileva se la directory corrente è un progetto DevStream
devstream detect

# Output esempio:
# DevStream project detected:
#   Name: my-react-app
#   Path: /Users/fulvioventura/projects/my-react-app
#   Database: /Users/fulvioventura/projects/my-react-app/.devstream/db/devstream.db
#   Type: typescript
```

### Cambia Provider per Progetto Esistente
```bash
# Vedi provider corrente
/Users/fulvioventura/devstream/scripts/devstream-provider.sh /path/to/project get

# Cambia provider
/Users/fulvioventura/devstream/scripts/devstream-provider.sh /path/to/project set anthropic
# o
/Users/fulvioventura/devstream/scripts/devstream-provider.sh /path/to/project set z.ai

# Vedi configurazione completa
/Users/fulvioventura/devstream/scripts/devstream-provider.sh /path/to/project show
```

---

## 🔧 Troubleshooting

### Comuni Problemi e Soluzioni

#### Problema: "DevStream non trovato"
```bash
# Soluzione: Controlla PATH
echo $PATH | grep devstream

# Se non presente, aggiungi manualmente
export PATH="$HOME/.devstream/bin:$PATH"
echo 'export PATH="$HOME/.devstream/bin:$PATH"' >> ~/.bashrc
```

#### Problema: "Python 3.11+ non trovato"
```bash
# Su macOS con Homebrew
brew install python@3.11

# Su Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv

# Verifica
python3.11 --version
```

#### Problema: "Claude Code non funziona"
```bash
# Reinstalla Claude Code
npm uninstall -g @anthropic-ai/claude-code
npm install -g @anthropic-ai/claude-code

# Login di nuovo
claude login
```

#### Problema: "z.ai API key non funzionante"
```bash
# Verifica API key
echo $ZAI_API_KEY

# Imposta di nuovo
export ZAI_API_KEY='tua-api-key-corretta'

# Aggiungi al profile permanente
echo 'export ZAI_API_KEY='tua-api-key-corretta'' >> ~/.zshrc
source ~/.zshrc
```

#### Problema: "Database non trovato"
```bash
# Reinizializza progetto
cd /path/to/project
devstream-init.py . --force

# Verifica directory
ls -la .devstream/db/
```

#### Problema: "Hook non funzionanti"
```bash
# Reinstalla dipendenze hook
cd /path/to/devstream
.devstream/bin/python -m pip install cchooks aiohttp structlog
```

### Debug Mode

Abilita output dettagliato:
```bash
# Per initialization
devstream-init.py . --verbose

# Per startup script
export DEVSTREAM_DEBUG=true
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh
```

### Log Files

Controlla i log per errori:
```bash
# Log di progetto
tail -f /path/to/project/.devstream/logs/devstream.log

# Log globali
tail -f ~/.devstream/logs/devstream.log
```

---

## 📚 Riferimento Comandi

### DevStream CLI (Global)
```bash
# Installazione e gestione
devstream --help                    # Mostra aiuto
devstream --version                 # Versione
devstream status                    # Status globale e progetto corrente
devstream list                      # Lista tutti i progetti
devstream detect                    # Rileva progetto corrente
devstream register /path/to/project # Registra progetto
```

### Project Initialization
```bash
# Inizializzazione
devstream-init.py --help            # Aiuto initialization
devstream-init.py /path/to/project  # Inizializza progetto specifico
devstream-init.py . --verbose       # Inizializzazione dettagliata
devstream-init.py . --force         # Forza reinizializzazione
devstream-init.py . --no-scan       # Senza scansionare codebase
```

### Universal Project Launcher
```bash
# Launcher universale
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh --help
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh /path/to/project
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh .  # Corrente directory
```

### Provider Management
```bash
# CLI provider
/Users/fulvioventura/devstream/scripts/devstream-provider.sh --help
/Users/fulvioventura/devstream/scripts/devstream-provider.sh /path/to/project get
/Users/fulvioventura/devstream/scripts/devstream-provider.sh /path/to/project set anthropic
/Users/fulvioventura/devstream/scripts/devstream-provider.sh /path/to/project set z.ai
/Users/fulvioventura/devstream/scripts/devstream-provider.sh /path/to/project show
/Users/fulvioventura/devstream/scripts/devstream-provider.sh /path/to/project list
```

### Python Configuration
```bash
# Config management
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py --help
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py get-provider /path/to/project
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py set-provider z.ai /path/to/project
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py show /path/to/project
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py init /path/to/project
```

### Automatic Installation
```bash
# Installazione automatica
bash /Users/fulvioventura/devstream/scripts/install-devstream-automatic.sh --help
bash /Users/fulvioventura/devstream/scripts/install-devstream-automatic.sh /path/to/project
bash /Users/fulvioventura/devstream/scripts/install-devstream-automatic.sh /path/to/project ~/.devstream --force
```

### Global Installation
```bash
# Installazione globale
bash /Users/fulvioventura/devstream/scripts/install-devstream-global.sh
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

### 5. Backup Configuration
```bash
# Backup configurazioni progetti
cp -r ~/.devstream/data/ ~/backup/devstream-$(date +%Y%m%d)

# Backup singolo progetto
cp /path/to/project/.devstream/config.json ~/backup/project-config-$(date +%Y%m%d).json
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
devstream status

# Project diagnostics
cd /path/to/project
devstream detect
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py show .

# Global installation check
ls -la ~/.devstream/
```

---

**🎉 Ora sei pronto per usare DevStream con tutti i tuoi progetti!**

Per iniziare, scegli il metodo di installazione che preferisci e segui i passaggi per il tuo primo progetto.