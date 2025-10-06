#!/usr/bin/env python3
"""
Script SIMPLIFICADO para generar refresh token de Google Ads
Usa google-auth-oauthlib que es más confiable
"""

import os
import sys

print("""
╔════════════════════════════════════════════════════════════════╗
║     🔑 GENERADOR AUTOMÁTICO DE REFRESH TOKEN - GOOGLE ADS      ║
╚════════════════════════════════════════════════════════════════╝
""")

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv('.env')

CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ ERROR: Faltan CLIENT_ID o CLIENT_SECRET en el archivo .env")
    sys.exit(1)

print(f"✅ CLIENT_ID encontrado: {CLIENT_ID[:20]}...")
print(f"✅ CLIENT_SECRET encontrado: {CLIENT_SECRET[:15]}...")
print()

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    
    print("🔄 Iniciando flujo de autenticación OAuth2...")
    print("   Se abrirá tu navegador automáticamente")
    print("   Autoriza el acceso a Google Ads")
    print()
    
    # Configuración del cliente OAuth2
    client_config = {
        'installed': {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': ['http://localhost']
        }
    }
    
    # Crear flujo de autenticación
    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=['https://www.googleapis.com/auth/adwords']
    )
    
    # Ejecutar servidor local y obtener credenciales
    print("📱 Abriendo navegador...")
    credentials = flow.run_local_server(
        port=8080,
        success_message='✅ ¡Autenticación exitosa! Puedes cerrar esta ventana.',
        open_browser=True
    )
    
    print()
    print("═" * 70)
    print("✅ ¡REFRESH TOKEN GENERADO EXITOSAMENTE!")
    print("═" * 70)
    print()
    print("📝 Tu nuevo REFRESH_TOKEN es:")
    print()
    print(f"   {credentials.refresh_token}")
    print()
    print("═" * 70)
    print()
    print("🔧 PRÓXIMOS PASOS:")
    print()
    print("1️⃣  ACTUALIZAR ARCHIVO .ENV:")
    print()
    print("   Abre el archivo .env y reemplaza la línea:")
    print(f"   GOOGLE_ADS_REFRESH_TOKEN={credentials.refresh_token}")
    print()
    print("2️⃣  ACTUALIZAR AZURE APP SERVICE:")
    print()
    print("   Ve a Azure Portal > Tu App Service > Configuración")
    print("   Variables de aplicación > Edita GOOGLE_ADS_REFRESH_TOKEN")
    print(f"   Nuevo valor: {credentials.refresh_token}")
    print()
    print("3️⃣  REINICIAR SERVIDOR LOCAL:")
    print()
    print("   pkill -f uvicorn")
    print("   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
    print()
    print("═" * 70)
    print()
    
    # Intentar actualizar automáticamente el .env
    print("¿Quieres que actualice automáticamente el archivo .env? (s/n): ", end='')
    response = input().strip().lower()
    
    if response in ['s', 'si', 'yes', 'y']:
        try:
            # Leer .env actual
            with open('.env', 'r') as f:
                lines = f.readlines()
            
            # Actualizar la línea del refresh token
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('GOOGLE_ADS_REFRESH_TOKEN='):
                    lines[i] = f'GOOGLE_ADS_REFRESH_TOKEN={credentials.refresh_token}\n'
                    updated = True
                    break
            
            # Si no existía, agregarlo
            if not updated:
                lines.append(f'GOOGLE_ADS_REFRESH_TOKEN={credentials.refresh_token}\n')
            
            # Guardar .env
            with open('.env', 'w') as f:
                f.writelines(lines)
            
            print()
            print("✅ Archivo .env actualizado correctamente!")
            print()
            print("🔄 Ahora reinicia el servidor para que tome efecto:")
            print("   pkill -f uvicorn && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
            print()
            
        except Exception as e:
            print(f"❌ Error actualizando .env: {e}")
            print("   Por favor, actualízalo manualmente.")
    else:
        print()
        print("👍 OK, actualiza el .env manualmente con el token mostrado arriba.")
    
    print()
    print("═" * 70)
    print("✅ ¡Proceso completado!")
    print("═" * 70)
    print()

except ImportError:
    print()
    print("❌ ERROR: Falta el paquete google-auth-oauthlib")
    print()
    print("Instálalo con:")
    print("   pip3 install google-auth-oauthlib")
    print()
    sys.exit(1)
    
except Exception as e:
    print()
    print(f"❌ ERROR: {e}")
    print()
    import traceback
    traceback.print_exc()
    sys.exit(1)
