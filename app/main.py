# app/main.py (Versión Original Restaurada)
import logging
import os
from fastapi import FastAPI, Request
import uvicorn

from app.api.routes.dynamics_actions import router as dynamics_router
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
    description=f"API para Elite Dynamics, potenciando la automatización y la integración de servicios. Entorno: {os.getenv('AZURE_ENV', 'Desconocido')}",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc"
)

@app.on_event("startup")
async def startup_event():
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Apagando {settings.APP_NAME}...")

@app.get("/health", tags=["General"], summary="Verifica el estado de salud de la API.")
async def health_check():
    logger.info("Health check solicitado.")
    return {"status": "ok", "appName": settings.APP_NAME}

app.include_router(
    dynamics_router, 
    prefix=settings.API_PREFIX,
    tags=["Acciones Dinámicas"]
)

logger.info(f"Router de acciones dinámicas incluido bajo el prefijo: {settings.API_PREFIX}")

if __name__ == "__main__":
    host_dev = os.getenv("HOST", "127.0.0.1")
    port_dev = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host=host_dev, port=port_dev, reload=True)