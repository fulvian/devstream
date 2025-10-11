# DevStream Session Startup Guide

Guida completa per avviare sessioni DevStream con Sonnet 4.5 e GLM-4.6, includendo accesso mobile sicuro tramite Muxile.

## 📋 Prerequisiti

- **DevStream installato** nella directory `/Users/fulvioventura/devstream`
- **Wrapper scripts protetti** in `~/bin/` (devstream-sonnet, devstream-glm)
- **tmux** installato e funzionante
- **Muxile plugin** configurato per accesso mobile

## 🚀 Sessioni Disponibili

### 1. DevStream Sonnet 4.5 Session
- **Uso**: Architettura, ragionamento complesso, lavoro lungo-termine
- **Wrapper**: `devstream-sonnet`
- **Nome sessione tmux**: `devstream-sonnet`

### 2. DevStream GLM-4.6 Session
- **Uso**: Esecuzione precisa, cost-optimized, tool calling efficiente
- **Wrapper**: `devstream-glm`
- **Nome sessione tmux**: `devstream-glm`

## 🔧 Metodo 1: Wrapper Scripts (Consigliato)

I wrapper scripts includono validazioni di sicurezza, logging e cleanup automatico.

### Avvio Sessione Sonnet 4.5

```bash
# Avvia sessione Sonnet 4.5
devstream-sonnet
```

**Cosa succede**:
1. ✅ Validazione sicurezza (permessi, ownership script)
2. ✅ Logging automatico in `~/.devstream/logs/wrapper-YYYYMMDD.log`
3. ✅ Creazione sessione tmux `devstream-sonnet`
4. ✅ Avvio DevStream con modello Sonnet 4.5
5. ✅ Collegamento automatico alla sessione

### Avvio Sessione GLM-4.6

```bash
# Avvia sessione GLM-4.6
devstream-glm
```

**Cosa succede**:
1. ✅ Stesse validazioni di sicurezza di Sonnet
2. ✅ Logging automatico
3. ✅ Creazione sessione tmux `devstream-glm`
4. ✅ Avvio DevStream con modello GLM-4.6
5. ✅ Collegamento automatico alla sessione

## 🔧 Metodo 2: Creazione Diretta tmux

Se i wrapper scripts non funzionano, puoi creare le sessioni direttamente:

### Sessione Sonnet 4.5

```bash
# Crea sessione tmux diretta
tmux new-session -d -s "devstream-sonnet" "/Users/fulvioventura/devstream/start-devstream.sh restart anthropic"

# Collegati alla sessione
tmux attach -t devstream-sonnet
```

### Sessione GLM-4.6

```bash
# Crea sessione tmux diretta
tmux new-session -d -s "devstream-glm" "/Users/fulvioventura/devstream/start-devstream.sh restart glm"

# Collegati alla sessione
tmux attach -t devstream-glm
```

## 📱 Accesso Mobile con Muxile

Dopo aver avviato una sessione (con qualsiasi metodo), puoi abilitare l'accesso mobile:

### Passo 1: Genera QR Code

All'interno della sessione DevStream:

```bash
# Premi Ctrl+B poi T
Ctrl+B, poi T
```

Questo attiverà Muxile e genererà un QR code sullo schermo.

### Passo 2: Scansiona QR Code

1. 📱 Apri la fotocamera del tuo dispositivo mobile
2. 📸 Scansiona il QR code apparso sullo schermo
3. 🔗 Tocca il link che appare sul telefono
4. 🌐 Apri nel browser mobile

### Passo 3: Usa il Terminale Mobile

Ora puoi:
- ✅ Visualizzare il terminale dal telefono
- ✅ Inserire comandi dal telefono
- ✅ Vedere output in tempo reale
- ✅ Utilizzare DevStream da mobile

## 🔒 Sicurezza - ⚠️ AVVERTENZE FONDAMENTALI

### ⚠️ Rischio Privacy

**IMPORTANTE**: Muxile invia TUTTO il traffico del terminale attraverso un worker Cloudflare di terze parti.

- ❌ **NO end-to-end encryption**: Cloudflare può leggere il contenuto
- ⚠️ **Data exposure**: Tutto ciò che scrivi è visibile a terzi
- 🔒 **Transport encryption solo**: Solo HTTPS/TLS tra dispositivi

### 🚫 Cosa NON inserire MAI

- ❌ Password, API keys, token di autenticazione
- ❌ Credenziali di produzione o staging
- ❌ Dati sensibili o personali (GDPR, HIPAA)
- ❌ Chiavi SSH, certificati, segreti
- ❌ Dati finanziari o PCI DSS

### ✅ Cosa puoi usare in sicurezza

- ✅ Lettura di codice sorgente e documentazione
- ✅ Monitoraggio di build, test, deployment
- ✅ Analisi di log e output
- ✅ Tutorial e apprendimento
- ✅ Configurazioni non sensibili

## 🛠️ Gestione Sessioni

### Lista Sessioni Attive

```bash
# Vedi tutte le sessioni tmux
tmux list-sessions
```

Output esempio:
```
devstream-sonnet: 1 windows (created Fri Oct 10 20:46:50 2025)
devstream-glm: 1 windows (created Fri Oct 10 20:47:15 2025)
```

### Collegarsi a Sessione Esistente

```bash
# Collegati a Sonnet
tmux attach -t devstream-sonnet

# Collegati a GLM
tmux attach -t devstream-glm
```

### Scollegarsi (Mantenere Sessione Attiva)

```bash
# Premi Ctrl+B poi D
Ctrl+B, poi D
```

### Terminare Sessione

```bash
# Chiudi sessione Sonnet
tmux kill-session -t devstream-sonnet

# Chiudi sessione GLM
tmux kill-session -t devstream-glm

# Chiudi tutte le sessioni
tmux kill-server
```

## 🔧 Troubleshooting

### Problema: "Session already exists"

```bash
# Soluzione 1: Collegati alla sessione esistente
tmux attach -t devstream-sonnet

# Soluzione 2: Chiudi e ricrea
tmux kill-session -t devstream-sonnet
devstream-sonnet
```

### Problema: "Security Error: world-writable"

```bash
# Correggi permessi dello script
chmod 755 /Users/fulvioventura/devstream/start-devstream.sh

# Riprova
devstream-sonnet
```

### Problema: QR code non viene generato

```bash
# Controlla se Muxile è caricato
tmux list-keys | grep muxile

# Ricarica configurazione tmux
tmux source ~/.tmux.conf

# Riavvia Muxile manualmente
tmux run-shell "~/.tmux/plugins/muxile/scripts/main.sh"
```

### Problema: Connessione mobile non funziona

```bash
# Controlla websocat
which websocat

# Controlla socket
ls -la /tmp/muxile.socket

# Riavvia Muxile
# Ctrl+B T (spento), poi Ctrl+B T (acceso)
```

## 📊 Logging e Monitoraggio

### Log di Sistema DevStream

```bash
# Log dei wrapper scripts
tail -f ~/.devstream/logs/wrapper-$(date +%Y%m%d).log

# Log degli hook DevStream
tail -f ~/.claude/logs/devstream/post_tool_use.log

# Log di Muxile
tail -f ~/.tmux/logs/muxile.log
```

### Esempio Log Output

```
[2025-10-10 20:46:50] 🚀 Starting DevStream Sonnet 4.5 session in tmux...
[2025-10-10 20:46:50] 📱 Mobile access: Press Ctrl+B then T to generate QR code
[2025-10-10 20:46:50] 🔧 Creating new tmux session: devstream-sonnet
[2025-10-10 20:46:51] ✅ DevStream Sonnet 4.5 session started successfully!
[2025-10-10 20:46:51] 📱 Generate QR code with: Ctrl+B then T
[2025-10-10 20:46:51] 📂 Attaching to session...
```

## 🚨 Procedure di Emergenza

### Se sospetti compromissione sessione

```bash
# 1. Chiudi immediatamente la sessione
tmux kill-session -t devstream-sonnet

# 2. Verifica che sia terminata
tmux list-sessions

# 3. Controlla activity recente
history | grep -i "password\|api\|key\|token\|secret"

# 4. Documenta l'incidente
echo "Session compromised at $(date): [details]" >> ~/.devstream/security-incidents.log

# 5. Se necessario, ruota credenziali esposte
```

## 🎯 Best Practices

### Prima di avviare una sessione

1. ✅ Verifica di essere su rete WiFi trusted
2. ✅ Assicurati che nessuno possa vedere il tuo schermo
3. ✅ Conferma che la sessione non conterrà dati sensibili
4. ✅ Chiudi altre sessioni DevStream non necessarie

### Durante l'uso

1. ✅ Tieni il dispositivo mobile bloccato quando non in uso
2. ✅ Monitora per comandi inaspettati
3. ✅ Chiudi il browser mobile quando hai finito
4. ✅ Usa il desktop per operazioni sensibili

### Dopo l'uso

1. ✅ Disattiva Muxile (Ctrl+B T)
2. ✅ Chiudi la sessione tmux se hai finito
3. ✅ Cancella cronologia browser mobile (opzionale)
4. ✅ Verifica i log per activity sospetta

## 📚 Riferimenti

- **Documentazione Muxile**: `/Users/fulvioventura/devstream/docs/guides/devstream-mobile-access-muxile.md`
- **Security Guidelines**: Sezione "CRITICAL SECURITY WARNINGS" nella guida Muxile
- **DevStream Configuration**: `/Users/fulvioventura/devstream/.env.devstream`
- **tmux Documentation**: `man tmux` o https://github.com/tmux/tmux/wiki

---

## 🎉 Riepilogo Rapido

```bash
# Avvio rapido Sonnet 4.5
devstream-sonnet

# Avvio rapido GLM-4.6
devstream-glm

# Accesso mobile (dentro sessione)
Ctrl+B, poi T

# Chiudi sessione
tmux kill-session -t devstream-sonnet  # o devstream-glm
```

**⚠️ Ricorda**: Mai inserire credenziali o dati sensibili quando usi Muxile! Usa solo per lettura e operazioni non sensibili.