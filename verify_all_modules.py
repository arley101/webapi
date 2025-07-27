import os
import importlib.util
import sys
from pathlib import Path

def test_module_import(module_path):
    """Prueba si un módulo se puede importar correctamente."""
    try:
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True, None
    except Exception as e:
        return False, str(e)

def find_python_modules():
    """Encuentra todos los módulos Python en el proyecto."""
    modules = []
    for root, dirs, files in os.walk("."):
        # Ignorar directorios de cache y virtuales
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.env', 'venv']]
        
        for file in files:
            if file.endswith('.py') and file != 'verify_all_modules.py':
                modules.append(os.path.join(root, file))
    return modules

def categorize_modules(modules):
    """Categoriza los módulos por tipo."""
    categories = {
        'actions': [],
        'services': [],
        'models': [],
        'utils': [],
        'routers': [],
        'main': [],
        'other': []
    }
    
    for module in modules:
        if 'action' in module.lower():
            categories['actions'].append(module)
        elif 'service' in module.lower():
            categories['services'].append(module)
        elif 'model' in module.lower():
            categories['models'].append(module)
        elif 'util' in module.lower():
            categories['utils'].append(module)
        elif 'router' in module.lower() or 'route' in module.lower():
            categories['routers'].append(module)
        elif 'main.py' in module:
            categories['main'].append(module)
        else:
            categories['other'].append(module)
    
    return categories

print("🔍 ANALIZANDO TODOS LOS MÓDULOS DEL PROYECTO...")
print("=" * 60)

modules = find_python_modules()
categorized = categorize_modules(modules)

total_modules = len(modules)
working_modules = 0
broken_modules = 0

print(f"📊 TOTAL DE MÓDULOS ENCONTRADOS: {total_modules}")
print()

for category, module_list in categorized.items():
    if module_list:
        print(f"📁 {category.upper()} ({len(module_list)} módulos):")
        for module in module_list:
            success, error = test_module_import(module)
            status = "✅" if success else "❌"
            print(f"  {status} {module}")
            if not success:
                print(f"     Error: {error}")
                broken_modules += 1
            else:
                working_modules += 1
        print()

print("=" * 60)
print(f"📈 RESUMEN:")
print(f"✅ Módulos funcionando: {working_modules}")
print(f"❌ Módulos con errores: {broken_modules}")
print(f"📊 Porcentaje de éxito: {(working_modules/total_modules)*100:.1f}%")

if broken_modules == 0:
    print("\n🎉 ¡TODOS LOS MÓDULOS ESTÁN FUNCIONANDO CORRECTAMENTE!")
else:
    print(f"\n⚠️  NECESITAS CORREGIR {broken_modules} MÓDULOS")
