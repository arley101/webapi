# app/main.py
import logging
import os
from fastapi import FastAPI, Request, status as http_status 
# from fastapi.responses import JSONResponse # No se usa directamente aquí
# from azure.identity import DefaultAzureCredential # No se usa directamente aquí
import uvicorn

# Importar el router de acciones
from app.api.routes.dynamics_actions import router as dynamics_router

# Importar la configuración de la aplicación
from app.core.config import settings

# Configuración básica de logging.
logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Crear la instancia de la aplicación FastAPI
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
    logger.info(f"Nivel de Logging configurado: {settings.LOG_LEVEL}")
    # Línea de prueba para verificar carga de rutas (opcional, puedes removerla después)
    try:
        logger.info(f"Rutas de dynamics_router: {[route.path for route in dynamics_router.routes]}") #type: ignore
        logger.info(f"Rutas totales en app: {[route.path for route in app.routes]}") #type: ignore
    except Exception as e:
        logger.error(f"Error al intentar loggear rutas: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Apagando {settings.APP_NAME}...")

@app.get(
    "/health", 
    tags=["General"], 
    summary="Verifica el estado de salud de la API.",
    response_description="Devuelve el estado actual de la aplicación."
)
async def health_check(request: Request): 
    client_host = request.client.host if request.client else "N/A"
    logger.info(f"Health check solicitado por: {client_host} - Respuesta: OK")
    return {
        "status": "ok", 
        "appName": settings.APP_NAME, 
        "appVersion": settings.APP_VERSION,
        "message": "Servicio EliteDynamicsAPI operativo."
    }

app.include_router(
    dynamics_router, 
    prefix=settings.API_PREFIX,
    tags=["Acciones Dinámicas"] 
)

logger.info(f"Router de acciones dinámicas incluido bajo el prefijo: {settings.API_PREFIX}")
logger.info(f"Documentación OpenAPI (Swagger UI) disponible en: {settings.API_PREFIX}/docs")
logger.info(f"Documentación ReDoc disponible en: {settings.API_PREFIX}/redoc")

if __name__ == "__main__":
    host_dev = os.getenv("HOST", "127.0.0.1")
    port_dev = int(os.getenv("PORT", "8000")) 
    log_level_dev = settings.LOG_LEVEL.lower()

    logger.info(f"Iniciando servidor de desarrollo Uvicorn en http://{host_dev}:{port_dev}")
    uvicorn.run(
        "app.main:app", 
        host=host_dev, 
        port=port_dev, 
        log_level=log_level_dev,
        reload=True 
    )