#!/bin/bash
echo "🚀 Iniciando validación del ACTION_MAP..."

# Esto le dice a Python que use la raíz del proyecto para buscar los módulos
PYTHONPATH=. python3 app/validate_action_map.py