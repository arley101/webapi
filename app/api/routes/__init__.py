# app/api/routes/__init__.py
# Inicializa el paquete 'routes'.
# Este paquete contiene los módulos que definen los routers de FastAPI
# para los diferentes endpoints de la aplicación.

from .whatsapp_webhook import router as whatsapp_webhook_router
from .simple_assistant import router as simple_assistant_router

__all__ = ["whatsapp_webhook_router", "simple_assistant_router"]
