# app/main.py
import logging
import os
from fastapi import FastAPI, Request
import uvicorn

# Importar los routers
from app.api.routes.dynamics_actions import router as dynamics_router
# ¡AÑADIR ESTE NUEVO IMPORT!
from app.api.routes.facade_routes import router as facade_router
from app.core.config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=f"API para Elite Dynamics. Entorno: {os.getenv('AZURE_ENV', 'Desconocido')}",
    # La URL del openapi para la fachada será diferente
    # openapi_url=f"{settings.API_PREFIX}/openapi.json", # Este es el de la API interna
    docs_url=None, # Deshabilitamos docs globales para evitar confusión
    redoc_url=None
)

@app.on_event("startup")
async def startup_event():
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}...")

@app.get("/health", tags=["General"], summary="Verifica el estado de salud de la API.")
async def health_check():
    logger.info("Health check solicitado.")
    return {"status": "ok", "appName": settings.APP_NAME}

# Router para la API interna (la original)
app.include_router(
    dynamics_router, 
    prefix=settings.API_PREFIX,
    tags=["API Interna Dinámica"]
)

# ¡AÑADIR ESTE NUEVO ROUTER!
# Este es el router que expondrás a tu asistente de OpenAI
app.include_router(
    facade_router,
    prefix="/facade", # Usamos un prefijo distinto para no colisionar
    tags=["Fachada para Asistente OpenAI"]
)

logger.info(f"API Interna disponible en: {settings.API_PREFIX}")
logger.info(f"API Fachada para Asistente disponible en: /facade")
logger.info(f"Documentación para la fachada disponible en: /facade/docs")

if __name__ == "__main__":
    host_dev = os.getenv("HOST", "127.0.0.1")
    port_dev = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host=host_dev, port=port_dev, reload=True)