#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   🔄 MONITOREANDO DEPLOYMENT #222                              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

while true; do
    TIMESTAMP=$(date '+%H:%M:%S')
    echo "[$TIMESTAMP] Verificando estado..."
    
    STATUS=$(gh run list --limit 1 --json status --jq -r '.[0].status')
    CONCLUSION=$(gh run list --limit 1 --json conclusion --jq -r '.[0].conclusion')
    
    echo "  Status: $STATUS"
    
    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        if [ "$CONCLUSION" = "success" ]; then
            echo "✅ ¡DEPLOYMENT EXITOSO!"
        else
            echo "❌ Deployment falló: $CONCLUSION"
        fi
        echo "═══════════════════════════════════════════════════════════════"
        break
    fi
    
    echo "  Esperando 15 segundos..."
    echo ""
    sleep 15
done
