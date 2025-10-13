#!/bin/bash

# DevStream Minimal Branch Protection Setup
# Opzione B: Protezioni minime per solo developer
# - Force push disabilitati (sicurezza)
# - Cancellazioni disabilitate (sicurezza)
# - NO PR obbligatori (workflow semplice)

set -e

echo "🛡️ Configurazione protezione minima branch main per DevStream..."
echo "📋 Regole da applicare:"
echo "   ✅ Force push disabilitati (sicurezza)"
echo "   ✅ Cancellazioni disabilitate (sicurezza)"
echo "   ❌ PR obbligatori RIMOSSI (workflow semplice)"
echo ""

# Verifica autenticazione GitHub
if ! gh auth status > /dev/null 2>&1; then
    echo "❌ Errore: GitHub CLI non autenticato. Esegui 'gh auth login'"
    exit 1
fi

# Ottieni nome repository
REPO_FULL_NAME=$(gh repo view --json nameWithOwner -q '.nameWithOwner')
echo "📍 Repository: $REPO_FULL_NAME"
echo ""

# Crea payload JSON con protezioni minime
cat > /tmp/minimal-protection.json << 'EOF'
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false,
  "lock_branch": false,
  "allow_fork_syncing": true
}
EOF

echo "🚀 Applicando protezioni minime al branch main..."

# Applica le regole via GitHub API
if gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "/repos/$REPO_FULL_NAME/branches/main/protection" \
  --input /tmp/minimal-protection.json > /dev/null 2>&1; then

    echo "✅ Protezione minima configurata con successo!"
    echo ""
    echo "📋 Configurazione attiva:"
    echo "   🚫 Force push: DISABILITATI (git push --force bloccato)"
    echo "   🚫 Cancellazioni: DISABILITATE (branch main protetto)"
    echo "   ✅ Push diretti: CONSENTITI (no PR richiesti)"
    echo "   ✅ Admin bypass: ABILITATO (massima flessibilità)"
    echo ""
    echo "🎯 Workflow semplificato:"
    echo "   git add ."
    echo "   git commit -m 'messaggio'"
    echo "   git push"
    echo ""
else
    echo "❌ Errore durante la configurazione"
    echo ""
    echo "🔧 Tentativo metodo alternativo con curl..."

    GITHUB_TOKEN=$(gh auth token)

    if curl -s -X PUT \
      -H "Authorization: token $GITHUB_TOKEN" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      -d @/tmp/minimal-protection.json \
      "https://api.github.com/repos/$REPO_FULL_NAME/branches/main/protection" > /dev/null 2>&1; then

        echo "✅ Metodo alternativo riuscito!"
    else
        echo "❌ Anche il metodo alternativo è fallito"
        echo "⚠️  Verifica manualmente su:"
        echo "   https://github.com/$REPO_FULL_NAME/settings/branches"
        exit 1
    fi
fi

# Pulizia
rm -f /tmp/minimal-protection.json

echo "🎉 Configurazione completata!"
echo "🔍 Verifica impostazioni su:"
echo "   https://github.com/$REPO_FULL_NAME/settings/branches"
