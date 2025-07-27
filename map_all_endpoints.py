import re
import os

def extract_endpoints(file_path):
    """Extrae todos los endpoints de un archivo Python."""
    endpoints = []
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Buscar decoradores de FastAPI
        patterns = [
            r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
            r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for method, path in matches:
                endpoints.append({
                    'file': file_path,
                    'method': method.upper(),
                    'path': path
                })
    except Exception as e:
        print(f"Error leyendo {file_path}: {e}")
    
    return endpoints

print("🌐 MAPEANDO TODOS LOS ENDPOINTS DE LA API...")
print("=" * 70)

all_endpoints = []
for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith('.py'):
            file_path = os.path.join(root, file)
            endpoints = extract_endpoints(file_path)
            all_endpoints.extend(endpoints)

if all_endpoints:
    print(f"📊 TOTAL DE ENDPOINTS ENCONTRADOS: {len(all_endpoints)}")
    print()
    
    # Agrupar por método HTTP
    by_method = {}
    for endpoint in all_endpoints:
        method = endpoint['method']
        if method not in by_method:
            by_method[method] = []
        by_method[method].append(endpoint)
    
    for method in sorted(by_method.keys()):
        print(f"🔸 {method} ({len(by_method[method])} endpoints):")
        for endpoint in by_method[method]:
            print(f"   {endpoint['path']} ({endpoint['file']})")
        print()
else:
    print("❌ NO SE ENCONTRARON ENDPOINTS")
