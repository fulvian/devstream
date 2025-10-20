# DevStream: Quick Reference Commands

**Versione**: 2.2.0 | **Data**: 2025-10-17

---

## 🚀 Comandi Essenziali

### Installazione Nuovo Progetto (Ex-Novo)
```bash
mkdir my-project && cd my-project
git init && echo "# My Project" > README.md
git add . && git commit -m "Initial commit"

# Installazione con Enhanced Hook Copying (raccomandato)
/Users/fulvioventura/devstream/scripts/install-devstream.sh --enhanced-hook-copying

# Avvio sessione
./start-devstream.sh start anthropic
# oppure
./start-devstream.sh start z.ai
```

### Installazione Progetto Esistente con Codebase
```bash
cd /path/to/existing-project

# Installazione con popolamento database automatico
/Users/fulvioventura/devstream/scripts/install-devstream.sh \
  --existing-project \
  --enhanced-hook-copying \
  --merge-requirements

# Avvio sessione
export DEVSTREAM_PROJECT_ROOT="$(pwd)"
/Users/fulvioventura/devstream/start-devstream.sh start anthropic

# Verifica DB puntando al progetto
env | grep DEVSTREAM_DB_PATH

# I protocolli DevStream copiati in locale sono disponibili in sessions/protocols/
ls sessions/protocols

# Conteggio rapido delle memorie indicizzate automaticamente
sqlite3 data/devstream.db "SELECT COUNT(*) FROM semantic_memory;"

# Se il progetto usa Alembic, le migrazioni vengono eseguite automaticamente.
# Per rilanciarle manualmente:
# .venv/bin/python -m alembic upgrade head
# Controlla quante memorie sono state indicizzate automaticamente
.devstream/bin/python -c "from .claude.hooks.devstream.utils.direct_client import get_direct_client; print(len(get_direct_client().semantic_memory_entries()))"
```

### Avvio Sessione DevStream System
```bash
# Nel repository DevStream
cd /Users/fulvioventura/devstream

# Avvio system mode
./start-devstream.sh start anthropic
./start-devstream.sh start z.ai
./start-devstream.sh restart anthropic
```

---

## 📋 Gestione Progetti

### Lista Progetti
```bash
~/.devstream/bin/devstream list
```

### Status Progetto Corrente
```bash
~/.devstream/bin/devstream status
```

### Rileva Progetto
```bash
~/.devstream/bin/devstream detect
```

### Cambia Provider
```bash
# Imposta Anthropic
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py set-provider anthropic .

# Imposta z.ai
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py set-provider z.ai .

# Verifica provider corrente
python3 /Users/fulvioventura/devstream/scripts/devstream-config.py get-provider .
```

---

## 🔧 Enhanced Hook Copying System

### Installazione con Enhanced Hook Copying
```bash
# Nuovo progetto
/Users/fulvioventura/devstream/scripts/install-devstream.sh --enhanced-hook-copying

# Progetto esistente
/Users/fulvioventura/devstream/scripts/install-devstream.sh \
  --existing-project \
  --enhanced-hook-copying \
  --merge-requirements
```

### Verifica Enhanced Hook Copying
```bash
# Verifica file hook
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

### Test Copier Integration
```bash
# Verifica Copier availability
.devstream/bin/python -c "import copier; print(f'Copier v{copier.__version__} available')"

# Test enhanced copying module
.devstream/bin/python -c "
import sys
sys.path.insert(0, '.claude/hooks/devstream/utils')
from multi_project_hook_copier import copy_devstream_hooks_enhanced
print('Enhanced hook copying: AVAILABLE')
"
```

---

## 🧠 Memory System Verification

### Verifica Popolamento Database
```bash
# Verifica database esiste
ls -la data/devstream.db

# Test ricerca nel database
.devstream/bin/python -c "
from .claude.hooks.devstream.utils.direct_client import get_direct_client
client = get_direct_client()
result = client.search_memory('main function', limit=5)
print(f'Found {len(result[\"results\"])} indexed items')
for item in result['results'][:3]:
    print(f'- {item[\"content_type\"]}: {item[\"content\"][:80]}...')
"
```

### Memory Bootstrap Manuale
```bash
# Forza popolamento database
.devstream/bin/python .claude/hooks/devstream/memory/memory_bootstrap.py . --mode incremental

# Popolamento completo (se vuoto)
.devstream/bin/python .claude/hooks/devstream/memory/memory_bootstrap.py . --mode full
```

---

## 🔍 Diagnostica e Debug

### Debug Mode
```bash
# Abilita debug per installation
export DEVSTREAM_DEBUG=true
/Users/fulvioventura/devstream/scripts/install-devstream.sh --enhanced-hook-copying

# Abilita debug per startup
export DEVSTREAM_DEBUG=true
./start-devstream.sh start anthropic
```

### Verifica Installazione
```bash
# Verifica venv Python
ls -la .devstream/bin/python
.devstream/bin/python --version

# Verifica dipendenze hook
.devstream/bin/python -m pip list | grep -E "(cchooks|aiohttp|structlog|copier)"

# Verifica database
ls -la .devstream/db/
ls -la data/devstream.db
```

### Log Files
```bash
# Log progetto
tail -f .devstream/logs/devstream.log

# Log system DevStream
tail -f /Users/fulvioventura/devstream/.claude/logs/devstream.log
```

### Health Check Completo
```bash
# Diagnostica completa
.devstream/bin/python -c "
import sys
sys.path.insert(0, '.claude/hooks/devstream/utils')

print('🔍 DevStream Health Check')
print('=' * 40)

# Test 1: Enhanced Hook Copying
try:
    from multi_project_hook_copier import copy_devstream_hooks_enhanced
    print('✅ Enhanced hook copying: AVAILABLE')
except ImportError as e:
    print(f'❌ Enhanced hook copying: {e}')

# Test 2: Integrity Validator
try:
    from hook_integrity_validator import HookIntegrityValidator
    print('✅ Integrity validator: AVAILABLE')
except ImportError as e:
    print(f'❌ Integrity validator: {e}')

# Test 3: Direct Client
try:
    from direct_client import get_direct_client
    client = get_direct_client()
    is_healthy = client.health_check()
    print(f'✅ Direct DB client: {\"HEALTHY\" if is_healthy else \"ERROR\"}')
except Exception as e:
    print(f'❌ Direct DB client: {e}')

# Test 4: Copier
try:
    import copier
    print(f'✅ Copier: v{copier.__version__}')
except ImportError:
    print('❌ Copier: NOT AVAILABLE')

# Test 5: Database
import sqlite3
import os
db_path = 'data/devstream.db'
if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute('SELECT COUNT(*) FROM memory')
        count = cursor.fetchone()[0]
        conn.close()
        print(f'✅ Database: {count} memory records')
    except Exception as e:
        print(f'❌ Database: {e}')
else:
    print('❌ Database: NOT FOUND')

print('=' * 40)
print('Health check completed!')
"
```

---

## ⚙️ Configurazione Rapida

### Environment Variables
```bash
# Aggiungi al .bashrc o .zshrc
export PATH="$HOME/.devstream/bin:$PATH"
export ZAI_API_KEY='tua-api-key'
export DEVSTREAM_DEBUG=false
```

### Git Ignore
```bash
# Aggiungi al .gitignore
.devstream/db/
.devstream/cache/
.devstream/logs/
*.log
__pycache__/
node_modules/
.env
```

### Provider Setup
```bash
# Claude Code (Anthropic)
npm install -g @anthropic-ai/claude-code
claude login

# z.ai API Key
export ZAI_API_KEY='tua-api-key-z.ai'
echo 'export ZAI_API_KEY='tua-api-key-z.ai'' >> ~/.zshrc
source ~/.zshrc
```

---

## 🆘 Troubleshooting Rapido

### Problemi Comuni
```bash
# "Enhanced hook copying failed" → Usa fallback
/Users/fulvioventura/devstream/scripts/install-devstream.sh --existing-project

# "Database not populated" → Forza bootstrap
.devstream/bin/python .claude/hooks/devstream/memory/memory_bootstrap.py . --mode incremental

# "Python 3.11+ not found" → Installa Python 3.11
brew install python@3.11  # macOS
sudo apt install python3.11  # Ubuntu

# "Claude Code not working" → Reinstalla
npm uninstall -g @anthropic-ai/claude-code
npm install -g @anthropic-ai/claude-code
claude login

# "Multi-project mode not detecting" → Imposta manualmente
export DEVSTREAM_PROJECT_ROOT="/path/to/your/project"
./start-devstream.sh start anthropic
```

### Reset Completo Progetto
```bash
# Backup configurazione importante
cp .devstream/config.json ~/backup/project-config-$(date +%Y%m%d).json

# Reset completo (ATTENZIONE: perde tutti i dati)
rm -rf .devstream/ data/ CLAUDE.md

# Reinstallazione
/Users/fulvioventura/devstream/scripts/install-devstream.sh --enhanced-hook-copying
```

---

## 📁 File Paths Riferimento

### DevStream System
```
/Users/fulvioventura/devstream/
├── start-devstream.sh                    # Main startup script
├── scripts/install-devstream.sh          # Installation script
├── scripts/simple-launcher.sh            # Quick launcher
├── .claude/hooks/devstream/              # Enhanced hooks system
├── .env                                  # Environment variables
└── docs/guides/                          # Documentation
```

### Project Structure
```
your-project/
├── .devstream/
│   ├── bin/python                        # Python 3.11+ venv
│   ├── db/devstream.db                   # Project database
│   ├── config/config.json                # Project configuration
│   ├── workspace.json                   # Project metadata
│   ├── logs/                             # Project logs
│   └── hooks/devstream/                  # Copied DevStream hooks
├── data/devstream.db                     # Main database (Direct DB)
├── CLAUDE.md                             # Project-specific protocol
└── .claude/settings.json                 # Claude Code configuration
```

---

**🎯 Questo quick reference contiene i comandi più usati per tutti gli scenari DevStream!**
