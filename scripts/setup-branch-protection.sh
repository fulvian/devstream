#!/bin/bash

# DevStream Branch Protection Setup Script
# Configura automaticamente la protezione del branch main

set -e

echo "🛡️ Configurazione automatica protezione branch main per DevStream..."

# Verifica autenticazione GitHub
if ! gh auth status > /dev/null 2>&1; then
    echo "❌ Errore: GitHub CLI non autenticato. Esegui 'gh auth login'"
    exit 1
fi

# Ottieni nome repository
REPO_FULL_NAME=$(gh repo view --json nameWithOwner | jq -r '.nameWithOwner')
echo "📍 Repository: $REPO_FULL_NAME"

# Configurazione protezione branch main
echo "🔧 Configurazione regole di protezione..."

# Metodo 1: Usando l'API REST di GitHub tramite gh
cat > /tmp/branch-protection.json << 'EOF'
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false,
    "dismissal_restrictions": {}
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false,
  "lock_branch": false,
  "allow_fork_syncing": true
}
EOF

# Applica le regole di protezione
echo "🚀 Applicando regole di protezione al branch main..."

RESPONSE=$(gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "/repos/$REPO_FULL_NAME/branches/main/protection" \
  --input /tmp/branch-protection.json 2>&1)

if [[ $? -eq 0 ]]; then
    echo "✅ Protezione branch main configurata con successo!"
    echo "📋 Regole applicate:"
    echo "   • ❌ Force push disabilitati"
    echo "   • ❌ Cancellazioni disabilitate"
    echo "   • ✅ Pull request obbligatori (1 approvazione)"
    echo "   • ✅ Admin enforcement attivo"
    echo "   • ✅ Fork sync abilitato"
else
    echo "❌ Errore durante la configurazione:"
    echo "$RESPONSE"
    exit 1
fi

# Pulizia
rm -f /tmp/branch-protection.json

echo "🎉 Configurazione completata!"
echo "🔍 Puoi verificare le impostazioni su:"
echo "   https://github.com/$REPO_FULL_NAME/settings/branches"