# main.py - Entry point para Azure App Service
"""
Entry point principal para elitedynamicsapi.azurewebsites.net
Importa la aplicación desde app/main.py para compatibilidad con Azure
"""

from app.main import app

# Esta línea es crucial para que Azure encuentre la aplicación
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)