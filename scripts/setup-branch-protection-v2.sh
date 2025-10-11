#!/bin/bash

# DevStream Branch Protection Setup Script v2
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

# Testa prima l'API per vedere se ha successo
echo "🔍 Testando accesso API..."

TEST_RESPONSE=$(gh api \
  --method GET \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "/repos/$REPO_FULL_NAME/branches/main/protection" 2>&1 || echo "API_TEST_FAILED")

if [[ "$TEST_RESPONSE" == *"API_TEST_FAILED"* ]]; then
    echo "📝 Branch main non protetto (come previsto), procedo con la configurazione..."
else
    echo "ℹ️ Branch main ha già protezioni, le aggiorno..."
fi

# Configurazione semplificata (metodo API più affidabile)
echo "🚀 Applicando regole di protezione al branch main..."

# Creiamo un payload JSON più semplice
cat > /tmp/protection.json << 'EOF'
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false
  },
  "enforce_admins": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

# Applica le regole
echo "📡 Invio richiesta API..."

HTTP_STATUS=$(gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "/repos/$REPO_FULL_NAME/branches/main/protection" \
  --input /tmp/protection.json \
  --jq '.message // "Success"' 2>&1)

if [[ $? -eq 0 ]]; then
    echo "✅ Protezione branch main configurata con successo!"
    echo ""
    echo "📋 Regole applicate:"
    echo "   • 🚫 Force push disabilitati"
    echo "   • 🚫 Cancellazioni disabilitate"
    echo "   • ✅ Pull request obbligatori (1 approvazione)"
    echo "   • ✅ Regole applicate anche agli admin"
    echo "   • ✅ Review stale non necessarie (flessibilità)"
else
    echo "❌ Errore durante la configurazione:"
    echo "$HTTP_STATUS"
    echo ""
    echo "🔧 Tentando metodo alternativo..."

    # Metodo alternativo: usiamo curl con token GitHub
    GITHUB_TOKEN=$(gh auth token)

    curl_response=$(curl -s -X PUT \
      -H "Authorization: token $GITHUB_TOKEN" \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      -d @/tmp/protection.json \
      "https://api.github.com/repos/$REPO_FULL_NAME/branches/main/protection" 2>&1)

    if [[ $? -eq 0 ]]; then
        echo "✅ Metodo alternativo riuscito!"
    else
        echo "❌ Anche il metodo alternativo è fallito:"
        echo "$curl_response"
    fi
fi

# Pulizia
rm -f /tmp/protection.json

echo ""
echo "🎉 Configurazione completata!"
echo "🔍 Puoi verificare le impostazioni su:"
echo "   https://github.com/$REPO_FULL_NAME/settings/branches"