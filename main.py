# main.py - Entry point para Azure App Service
"""
Entry point principal para elitedynamicsapi.azurewebsites.net
Importa la aplicación desde app/main.py para compatibilidad con Azure
"""

import sys
import os
import logging

# Agregar el directorio actual al Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.main import app
    logging.info("✅ Aplicación importada exitosamente desde app.main")
except ImportError as e:
    logging.error(f"❌ Error importando app.main: {e}")
    raise

# Esta línea es crucial para que Azure encuentre la aplicación
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    logging.info("🚀 Iniciando servidor directamente...")
    uvicorn.run(app, host="0.0.0.0", port=8000)