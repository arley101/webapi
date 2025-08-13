from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Crear una mini app para servir la interfaz de chat
chat_app = FastAPI(title="Chat Interface", version="1.0.0")

# Servir archivos estáticos
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    chat_app.mount("/static", StaticFiles(directory=static_path), name="static")

@chat_app.get("/")
async def serve_chat_interface():
    """Servir la interfaz de chat"""
    static_file = os.path.join(static_path, "index.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    else:
        return {"message": "Interfaz de chat no encontrada. Asegúrate de que static/index.html existe."}

@chat_app.get("/chat")
async def serve_chat_interface_alt():
    """Ruta alternativa para la interfaz de chat"""
    return await serve_chat_interface()

# Información sobre la interfaz
@chat_app.get("/info")
async def chat_info():
    """Información sobre la interfaz de chat"""
    return {
        "title": "🤖 Interfaz de Chat con Tu Asistente Inteligente",
        "description": "Interfaz web con soporte de voz para interactuar con tu asistente de 405 acciones",
        "features": [
            "💬 Chat en tiempo real",
            "🎤 Reconocimiento de voz",
            "🔊 Síntesis de voz", 
            "📱 Responsive design",
            "🧠 Integración completa con tu API"
        ],
        "endpoints": {
            "chat_interface": "/",
            "alternative_route": "/chat",
            "api_docs": "/docs"
        }
    }
