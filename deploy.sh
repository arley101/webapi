#!/usr/bin/env bash
set -euo pipefail

# ===== CONFIGURA AQUÍ =====
RG="Memorycognitiva"
APP="elitedynamicsapi"
BRANCH_LOCAL="prodution"        # <-- tu rama actual
BRANCH_REMOTE="master"          # Azure Local Git SIEMPRE escucha master
# ===========================

echo "🔍 Comprobando AZ CLI..."
az account show >/dev/null 2>&1 || az login

echo "🔍 Obteniendo/creando remoto Local Git de Azure..."
GIT_URL=$(az webapp deployment source config-local-git \
  --name "$APP" \
  --resource-group "$RG" \
  --query url -o tsv)

if git remote | grep -q "^azure$"; then
  echo "✅ Remoto 'azure' ya existe"
else
  echo "➕ Creando remoto 'azure' => $GIT_URL"
  git remote add azure "$GIT_URL"
fi

echo "🧹 Limpiando dependencias conflictivas en requirements (enum34, enum, etc)"
if grep -Ei '^(enum|enum34)' requirements.txt >/dev/null 2>&1; then
  echo "Remueve 'enum/enum34' manualmente de requirements.txt y vuelve a correr."
  exit 1
fi

echo "🚀 Pusheando a Azure ( $BRANCH_LOCAL -> $BRANCH_REMOTE )..."
git push azure "$BRANCH_LOCAL":"$BRANCH_REMOTE" --force

echo "⏳ Esperando a que Azure construya con Oryx..."
echo "   Ve los logs con:  az webapp log tail -g $RG -n $APP"

echo "✅ Despliegue enviado. Verifica /health:"
echo "   https://$APP.azurewebsites.net/health"