#!/usr/bin/env python3
"""
Generador de Refresh Token - Método Manual
Usa redirect_uri estándar: urn:ietf:wg:oauth:2.0:oob
No requiere modificar configuración en Google Cloud Console
"""

import os
import sys
import webbrowser

print("""
╔════════════════════════════════════════════════════════════════╗
║   🔑 GENERADOR DE REFRESH TOKEN - MÉTODO MANUAL                ║
║   (Solución para redirect_uri_mismatch)                        ║
╚════════════════════════════════════════════════════════════════╝
""")

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    print("⚠️  python-dotenv no instalado, leyendo .env manualmente...")

CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ ERROR: Faltan CLIENT_ID o CLIENT_SECRET en el archivo .env")
    sys.exit(1)

print(f"✅ CLIENT_ID: {CLIENT_ID[:30]}...")
print(f"✅ CLIENT_SECRET: {CLIENT_SECRET[:20]}...")
print()

# Construir URL de autorización
auth_url = (
    "https://accounts.google.com/o/oauth2/auth?"
    f"client_id={CLIENT_ID}&"
    "redirect_uri=urn:ietf:wg:oauth:2.0:oob&"
    "scope=https://www.googleapis.com/auth/adwords&"
    "response_type=code&"
    "access_type=offline&"
    "prompt=consent"
)

print("═" * 64)
print("📋 PASOS A SEGUIR:")
print("═" * 64)
print()
print("1️⃣  Se abrirá tu navegador con la página de autorización de Google")
print("2️⃣  Inicia sesión con tu cuenta de Google Ads")
print("3️⃣  Autoriza el acceso")
print("4️⃣  Google te mostrará un CÓDIGO")
print("5️⃣  Copia ese código y pégalo aquí")
print()
print("⏳ Abriendo navegador en 3 segundos...")
print()

import time
time.sleep(3)

# Abrir navegador
webbrowser.open(auth_url)

print("🌐 Navegador abierto.")
print("   Si no se abrió automáticamente, copia esta URL:")
print()
print(f"   {auth_url[:80]}...")
print()
print("-" * 64)

# Solicitar código de autorización
print()
code = input("📝 Pega aquí el código de autorización: ").strip()
print()

if not code:
    print("❌ No ingresaste ningún código")
    sys.exit(1)

print("🔄 Intercambiando código por refresh token...")
print()

# Intercambiar código por tokens
try:
    import requests
    
    response = requests.post(
        'https://oauth2.googleapis.com/token',
        data={
            'code': code,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'grant_type': 'authorization_code'
        }
    )
    
    result = response.json()
    
    if 'error' in result:
        print(f"❌ ERROR: {result.get('error')}")
        print(f"   Descripción: {result.get('error_description', 'Sin descripción')}")
        sys.exit(1)
    
    if 'refresh_token' not in result:
        print("❌ ERROR: No se recibió refresh_token")
        print("   Respuesta completa:", result)
        sys.exit(1)
    
    refresh_token = result['refresh_token']
    access_token = result.get('access_token', 'N/A')
    
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║              ✅ ¡REFRESH TOKEN GENERADO!                       ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    print("🔑 REFRESH TOKEN:")
    print()
    print(f"   {refresh_token}")
    print()
    print("═" * 64)
    print()
    
    # Preguntar si actualizar .env
    update = input("❓ ¿Actualizar archivo .env automáticamente? (s/n): ").strip().lower()
    
    if update == 's':
        try:
            # Leer .env actual
            with open('.env', 'r') as f:
                lines = f.readlines()
            
            # Actualizar línea del refresh token
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('GOOGLE_ADS_REFRESH_TOKEN='):
                    lines[i] = f'GOOGLE_ADS_REFRESH_TOKEN={refresh_token}\n'
                    updated = True
                    break
            
            # Si no existía, agregarlo
            if not updated:
                lines.append(f'\nGOOGLE_ADS_REFRESH_TOKEN={refresh_token}\n')
            
            # Guardar .env
            with open('.env', 'w') as f:
                f.writelines(lines)
            
            print("✅ Archivo .env actualizado correctamente")
            print()
        except Exception as e:
            print(f"⚠️  Error al actualizar .env: {e}")
            print("   Puedes copiarlo manualmente")
    else:
        print()
        print("📋 COPIA MANUAL:")
        print("   Abre el archivo .env y reemplaza la línea:")
        print()
        print(f"   GOOGLE_ADS_REFRESH_TOKEN={refresh_token}")
        print()
    
    print("═" * 64)
    print("🎯 PRÓXIMOS PASOS:")
    print("═" * 64)
    print()
    print("1. Actualizar Azure App Service con el nuevo token:")
    print("   - Ve a: Azure Portal > elitedynamicsapi")
    print("   - Configuración > Variables de aplicación")
    print("   - Actualiza: GOOGLE_ADS_REFRESH_TOKEN")
    print()
    print("2. Reiniciar servidor local para probar:")
    print("   pkill -f uvicorn")
    print("   python3 -m uvicorn app.main:app --reload")
    print()
    print("✅ ¡Listo! El sistema de renovación automática ya está activo")
    print()
    
except ImportError:
    print("❌ ERROR: requests no está instalado")
    print("   Ejecuta: pip install requests")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
