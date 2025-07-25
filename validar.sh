#!/bin/bash
echo "🚀 Iniciando validación del ACTION_MAP..."

PYTHONPATH=. python3 -c "
from app.core.action_mapper import ACTION_MAP
print('✅ Acción map cargado')
print(f'Total de acciones: {len(ACTION_MAP)}')
"