#!/usr/bin/env python3
"""
Script para corregir errores críticos encontrados en las pruebas
"""

# 1. Crear alias para calendar_actions
import os

# Crear enlace simbólico o copia para calendar_actions
calendar_content = '''# app/actions/calendar_actions.py
"""
Alias para calendario_actions.py para compatibilidad
"""

from .calendario_actions import *
'''

with open('app/actions/calendar_actions.py', 'w') as f:
    f.write(calendar_content)

print("✅ Creado calendar_actions.py como alias")

# 2. Agregar SimpleMemory a simple_memory.py
simple_memory_addition = '''

# Alias para compatibilidad
SimpleMemory = SimpleMemoryManager
'''

with open('app/memory/simple_memory.py', 'a') as f:
    f.write(simple_memory_addition)

print("✅ Agregado alias SimpleMemory")

# 3. Verificar acciones en ACTION_MAP
import sys
sys.path.insert(0, 'app')

try:
    from app.core.action_mapper import ACTION_MAP
    
    # Verificar acciones faltantes
    missing_actions = []
    
    if 'teams_send_message' not in ACTION_MAP:
        missing_actions.append('teams_send_message')
    
    if 'workflow_execute' not in ACTION_MAP:
        missing_actions.append('workflow_execute')
    
    if missing_actions:
        print(f"⚠️  Acciones faltantes en ACTION_MAP: {missing_actions}")
        
        # Buscar acciones similares
        for action in missing_actions:
            similar = [k for k in ACTION_MAP.keys() if action.split('_')[0] in k or action.split('_')[1] in k]
            if similar:
                print(f"   Acciones similares para {action}: {similar[:3]}")
    else:
        print("✅ Todas las acciones críticas están disponibles")
        
except Exception as e:
    print(f"❌ Error verificando ACTION_MAP: {e}")

print("\n🚀 Correcciones aplicadas. Ejecutar pruebas nuevamente.")
