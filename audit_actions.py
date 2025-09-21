#!/usr/bin/env python3
"""
Script de auditoría para entender qué está cargando el action_mapper
"""

import sys
import os
import importlib
from pathlib import Path

# Agregar el directorio del proyecto al path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def load_action_module(module_name):
    """Cargar un módulo de acciones de forma segura"""
    try:
        module_path = f"app.actions.{module_name}"
        return importlib.import_module(module_path)
    except Exception as e:
        print(f"❌ Error cargando {module_name}: {e}")
        return None

def analyze_module(module_name, module):
    """Analizar qué funciones tiene un módulo"""
    print(f"\n=== {module_name} ===")
    print(f"Archivo: {getattr(module, '__file__', 'N/A')}")
    
    functions_found = []
    all_attrs = dir(module)
    
    for attr_name in all_attrs:
        if not attr_name.startswith('_'):
            try:
                attr = getattr(module, attr_name)
                if callable(attr):
                    # Verificar si es función definida en este módulo
                    if hasattr(attr, '__module__') and module_name in str(attr.__module__):
                        functions_found.append({
                            'name': attr_name,
                            'type': 'async' if str(attr).startswith('<coroutine function') else 'sync',
                            'module': attr.__module__,
                            'callable': True
                        })
                    else:
                        print(f"  🔍 Saltando {attr_name} (de {getattr(attr, '__module__', 'unknown')})")
            except Exception as e:
                print(f"  ⚠️  Error con {attr_name}: {e}")
    
    print(f"✅ Funciones encontradas: {len(functions_found)}")
    for func in functions_found:
        print(f"  - {func['name']} ({func['type']})")
    
    return functions_found

def main():
    print("🔍 AUDITORÍA COMPLETA DEL ACTION_MAPPER")
    print("=" * 50)
    
    # Lista de módulos que debería cargar (EXACTAMENTE igual que action_mapper.py)
    module_names = [
        'azuremgmt_actions', 'bookings_actions', 'calendar_actions', 'calendario_actions',
        'correo_actions', 'email_optimized_actions', 'forms_actions', 'gemini_actions',
        'github_actions', 'google_marketing_enhanced', 'google_services_actions', 
        'googleads_actions', 'graph_actions', 'hubspot_actions', 'intelligent_assistant_actions',
        'linkedin_enhanced_actions', 'metaads_actions', 
        'notion_actions', 'office_actions', 'onedrive_actions', 'openai_actions',
        'planner_actions', 'power_automate_actions', 'powerbi_actions', 'resolver_actions',
        'runway_actions', 'runway_unified', 'sharepoint_actions', 'stream_actions',
        'teams_actions', 'tiktok_enhanced', 'todo_actions',
        'userprofile_actions', 'users_actions', 'vivainsights_actions', 'webresearch_actions',
        'whatsapp_actions', 'wordpress_enhanced', 'x_enhanced',
        'youtube_channel_actions'
    ]
    
    total_functions = 0
    successful_modules = 0
    failed_modules = 0
    
    for module_name in module_names:
        module = load_action_module(module_name)
        if module:
            functions = analyze_module(module_name, module)
            total_functions += len(functions)
            successful_modules += 1
        else:
            failed_modules += 1
    
    print(f"\n" + "=" * 50)
    print(f"📊 RESUMEN:")
    print(f"  Módulos exitosos: {successful_modules}")
    print(f"  Módulos fallidos: {failed_modules}")
    print(f"  Total funciones: {total_functions}")
    print(f"  Esperado: 480+")
    
    if total_functions < 100:
        print(f"🚨 PROBLEMA: Solo se encontraron {total_functions} funciones de las 480+ esperadas")

if __name__ == "__main__":
    main()