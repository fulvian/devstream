# Simplified GitHub Workflow - DevStream

**Status**: ✅ Active | **Last Updated**: 2025-10-11 | **Branch Protection**: Minimal (Opzione B)

---

## 📋 Overview

DevStream utilizza un **workflow semplificato per solo developer** con protezioni minime che bilanciano sicurezza e flessibilità.

### Previous Workflow (Removed)
```bash
# ❌ VECCHIO: Complicato con PR obbligatori
git checkout -b feature-branch
git commit -m "fix"
git push -u origin feature-branch
gh pr create
gh pr review --approve  # Auto-approval necessaria!
gh pr merge
git checkout main
git pull
```

### Current Workflow (Active)
```bash
# ✅ NUOVO: Semplice e diretto
git add .
git commit -m "messaggio"
git push  # Push diretto a main, NO PR richiesti!
```

---

## 🛡️ Branch Protection Configuration

### Minimal Protections (Opzione B)

**File**: `.github/settings.yml`

```yaml
branches:
  - name: main
    protection:
      # ✅ Protezioni essenziali
      allow_force_pushes: false      # Blocca git push --force
      allow_deletions: false          # Protegge da eliminazione branch

      # ❌ NO requisiti PR
      required_pull_request_reviews: null

      # ❌ NO enforce admins (massima flessibilità)
      enforce_admins: false
```

### Security Guarantees

| Protection | Status | Rationale |
|------------|--------|-----------|
| **Force Push** | 🚫 BLOCKED | Previene sovrascrittura accidentale della history |
| **Branch Deletion** | 🚫 BLOCKED | Protegge il branch main da eliminazioni accidentali |
| **PR Reviews** | ✅ OPTIONAL | Non richiesti per solo developer (semplificazione) |
| **Admin Enforcement** | ❌ DISABLED | Admin può bypassare se necessario (flessibilità) |

---

## 🚀 Daily Workflow

### 1. Make Changes
```bash
# Edit files locally
vim src/api/users.py
```

### 2. Commit Changes
```bash
git add .
git commit -m "feat: Add user authentication endpoint"
```

### 3. Push to Remote
```bash
# Direct push to main (NO PR required)
git push
```

### 4. Verify on GitHub
```bash
# Optional: Open browser to verify
gh repo view --web
```

---

## 🔄 Special Scenarios

### Force Push (Blocked)
```bash
# ❌ Questo FALLIRÀ (protezione attiva)
git push --force

# ✅ Alternativa sicura: revert + nuovo commit
git revert <commit-hash>
git push
```

### Emergency Override (Admin)
```bash
# Solo in caso di emergenza (admin bypass disponibile)
# 1. Disabilita temporaneamente protezione via GitHub UI
# 2. Esegui operazione necessaria
# 3. Riabilita protezione con script

./scripts/setup-minimal-protection.sh
```

### Optional PR Workflow
```bash
# Se vuoi usare PR per review complesse (opzionale)
git checkout -b feature/complex-change
git commit -m "..."
git push -u origin feature/complex-change
gh pr create
gh pr merge  # Merge quando pronto (NO approval richiesta)
```

---

## 🛠️ Management Scripts

### Apply Minimal Protection
```bash
# Script automatico per configurare protezioni minime
./scripts/setup-minimal-protection.sh
```

**Output**:
```
🛡️ Configurazione protezione minima branch main per DevStream...
📋 Regole da applicare:
   ✅ Force push disabilitati (sicurezza)
   ✅ Cancellazioni disabilitate (sicurezza)
   ❌ PR obbligatori RIMOSSI (workflow semplice)

📍 Repository: fulvian/devstream

✅ Protezione minima configurata con successo!
```

### Verify Current Protection
```bash
# Verifica protezioni via GitHub CLI
gh api repos/fulvian/devstream/branches/main/protection | jq '
{
  allow_force_pushes: .allow_force_pushes.enabled,
  allow_deletions: .allow_deletions.enabled,
  required_reviews: .required_pull_request_reviews,
  enforce_admins: .enforce_admins.enabled
}'
```

---

## 📦 Local ↔️ Remote Sync

### Sync Strategy

**Golden Rule**: **Local codebase comanda, remote è mirror**

```bash
# 1. Local changes → Remote (standard workflow)
git add .
git commit -m "..."
git push

# 2. Remote changes → Local (fetch + merge)
git pull

# 3. Divergenze (remote has changes)
git fetch origin
git rebase origin/main  # O git merge origin/main
git push
```

### .gitignore Best Practices

**File**: `.gitignore`

```bash
# Test files in root (temporary development)
test_*.py
test_*.js
test_*.ts
test_*.md
test_*.json
test_*.txt

# Embedding test files
embedding_*.json

# Strange version files (pip install artifacts)
=*.*.*
```

**Rationale**: Mantieni repository pulito, escludi file temporanei/test dalla codebase remota.

---

## ✅ Success Criteria

Workflow è considerato **funzionante** se:

- ✅ Push diretto a `main` senza PR
- ✅ Force push bloccati (sicurezza)
- ✅ Cancellazioni branch bloccate (sicurezza)
- ✅ Local codebase sincronizzato con remote
- ✅ Nessun file temporaneo/test nel repo remoto
- ✅ Workflow richiede <30 secondi (da commit a push)

**Validazione** (2025-10-11):
```bash
# Test eseguito con successo
git commit -m "feat: Simplify GitHub workflow..."
git push  # ✅ Riuscito senza PR!

# Output: To https://github.com/fulvian/devstream.git
#         8c8177e..f22f0df  main -> main
```

---

## 🔍 Troubleshooting

### Push Fails with "Protected Branch"
```bash
# Problema: Protezioni ancora attive
# Soluzione: Ri-applica configurazione minima
./scripts/setup-minimal-protection.sh

# Verifica su GitHub UI:
https://github.com/fulvian/devstream/settings/branches
```

### Force Push Needed (Edge Case)
```bash
# ❌ NON FARE: git push --force (bloccato)

# ✅ ALTERNATIVA 1: Revert locale
git reset --soft HEAD~1
git commit --amend
git push

# ✅ ALTERNATIVA 2: Nuovo commit
git revert <problematic-commit>
git push
```

### Divergent Branches
```bash
# Local e remote divergono
git fetch origin
git log --oneline --graph --all  # Visualizza divergenze

# Opzione A: Rebase (history lineare)
git rebase origin/main
git push

# Opzione B: Merge (mantiene history)
git merge origin/main
git push
```

---

## 📚 Related Documentation

- **Branch Protection Setup**: `scripts/setup-minimal-protection.sh`
- **GitHub Settings**: `.github/settings.yml`
- **Release Process**: `docs/developer-guide/release-process.md`
- **Git Ignore Rules**: `.gitignore`

---

## 🎯 Next Steps

1. ✅ **Workflow attivo** - usa `git add → commit → push` direttamente
2. 🔄 **Monitor protezioni** - verifica periodicamente su GitHub UI
3. 📝 **Document changes** - aggiorna questa guida per nuove best practices
4. 🧪 **Test edge cases** - valida workflow con scenari complessi

---

**Maintained by**: DevStream Team
**Last Validation**: 2025-10-11 23:50 UTC
**Status**: ✅ Production Ready
