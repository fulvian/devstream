# DevStream Quickstart

**Setup rapido per iniziare con DevStream in 5 minuti**

---

## 🚀 Quickstart (5 minuti)

### Prerequisites
```bash
# Verifica requisiti
python3 --version  # 3.11+
node --version     # 16+
git --version      # 2.x
```

### 1. Installazione Globale (una sola volta)
```bash
# Clona DevStream
git clone https://github.com/fulvian/devstream.git
cd devstream

# Installa globalmente
bash scripts/install-devstream-global.sh

# Riavvia il terminale o esegui:
source ~/.bashrc  # o source ~/.zshrc
```

### 2. Setup API Keys
```bash
# Per Anthropic (Claude)
npm install -g @anthropic-ai/claude-code
claude login

# Per z.ai (GLM-4.6)
export ZAI_API_KEY='tua-api-key'
echo 'export ZAI_API_KEY='tua-api-key'' >> ~/.bashrc
```

### 3. Crea Nuovo Progetto
```bash
# Crea progetto
mkdir my-project
cd my-project
echo 'def hello(): print("Hello DevStream!")' > main.py

# Installa DevStream per il progetto
bash /Users/fulvioventura/devstream/scripts/install-devstream-automatic.sh
```

### 4. Scegli Provider AI e Avvia
```bash
# Launcher interattivo
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh

# Scegli:
# 1) 🤖 Claude Code + DevStream
# → Seleziona provider: 1) Anthropic o 2) z.ai
# → Inizia a codare!
```

---

## 📋 Comandi Essenziali

```bash
# Per qualsiasi nuovo progetto
cd /path/to/new-project
bash /Users/fulvioventura/devstream/scripts/install-devstream-automatic.sh

# Avvia con scelta provider
/Users/fulvioventura/devstream/scripts/start-project-devstream.sh

# Gestione progetti
devstream list                    # Lista tutti i progetti
devstream status                   # Status progetto corrente
devstream detect                   # Rileva progetto

# Cambia provider
/Users/fulvioventura/devstream/scripts/devstream-provider.sh set anthropic
/Users/fulvioventura/devstream/scripts/devstream-provider.sh set z.ai
```

---

## 🔧 Tipi di Progetto Supportati

### Python
```bash
mkdir my-python-app && cd my-python-app
echo 'flask==2.3.3' > requirements.txt
echo 'def app(): return "Hello"' > main.py
bash /Users/fulvioventura/devstream/scripts/install-devstream-automatic.sh
```

### TypeScript/React
```bash
mkdir my-react-app && cd my-react-app
npm init -y
echo '{"compilerOptions": {"target": "es2020"}}' > tsconfig.json
mkdir src
echo 'export default () => <div>Hello</div>;' > src/App.tsx
bash /Users/fulvioventura/devstream/scripts/install-devstream-automatic.sh
```

### Go
```bash
mkdir my-go-service && cd my-go-service
go mod init my-service
echo 'package main; func main() { println("Hello") }' > main.go
bash /Users/fulvioventura/devstream/scripts/install-devstream-automatic.sh
```

---

## ⚡ Provider AI Choice

| Provider | Best For | Cost | Setup |
|----------|-----------|------|-------|
| 🤖 **Anthropic** | Complex reasoning, architecture | Higher | `claude login` |
| 🧠 **z.ai** | Fast implementation, testing | Lower | `ZAI_API_KEY` |

---

## 🆘 Troubleshooting Rapido

**DevStream non trovato?**
```bash
export PATH="$HOME/.devstream/bin:$PATH"
```

**Provider non funziona?**
```bash
# Anthropic
claude login

# z.ai
export ZAI_API_KEY='tua-api-key'
```

**Reinizializza progetto:**
```bash
devstream-init.py . --force
```

---

**🎉 Fatto! Ora usa DevStream per tutti i tuoi progetti!**

Per guida completa: `docs/guides/complete-installation-and-startup-guide.md`