#!/usr/bin/env python3
"""Monitorear deployment en tiempo real"""

import subprocess
import json
import time
from datetime import datetime

print("╔════════════════════════════════════════════════════════════════╗")
print("║   🔄 MONITOREANDO DEPLOYMENT #222                              ║")
print("╚════════════════════════════════════════════════════════════════╝")
print()

while True:
    try:
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] Verificando estado...")
        
        # Obtener estado del run
        result = subprocess.run(
            ['gh', 'run', 'list', '--limit', '1', '--json', 'status,conclusion,displayTitle'],
            capture_output=True,
            text=True
        )
        
        data = json.loads(result.stdout)
        if not data:
            print("  ⚠️  No se encontró ningún run")
            break
        
        run = data[0]
        status = run.get('status', 'unknown')
        conclusion = run.get('conclusion', '')
        title = run.get('displayTitle', 'N/A')
        
        print(f"  Status: {status}")
        print(f"  Title: {title[:60]}...")
        
        if status == 'completed':
            print()
            print("═══════════════════════════════════════════════════════════════")
            if conclusion == 'success':
                print("✅ ¡DEPLOYMENT EXITOSO!")
            else:
                print(f"❌ Deployment falló: {conclusion}")
            print("═══════════════════════════════════════════════════════════════")
            break
        
        print("  Esperando 15 segundos...")
        print()
        time.sleep(15)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoreo cancelado por el usuario")
        break
    except Exception as e:
        print(f"  ❌ Error: {e}")
        time.sleep(15)
