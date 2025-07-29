# app/main.py
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import logging
from datetime import datetime

# Importar el router de acciones
from app.api.routes.dynamics_actions import router as dynamics_router

# Importar la configuración de la aplicación
from app.core.config import settings

# Configuración básica de logging
logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Lifespan manager (reemplaza @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Iniciando EliteDynamicsAPI-Local v1.1-localdev...")
    logger.info(f"Nivel de Logging configurado: {settings.LOG_LEVEL.upper()}")
    yield
    # Shutdown
    logger.info("Apagando EliteDynamicsAPI-Local...")

# Crear la instancia de la aplicación FastAPI con lifespan
app = FastAPI(
    title="EliteDynamicsAPI-Local",
    description="API Local de Elite Dynamics para acciones empresariales",
    version="1.1-localdev",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan  # Usar lifespan en lugar de on_event
)

# Incluir el router con prefijo
app.include_router(dynamics_router, prefix="/api/v1")

# Log de confirmación después de incluir routers
logger.info("Router de acciones dinámicas incluido bajo el prefijo: /api/v1")
logger.info("Documentación OpenAPI (Swagger UI) disponible en: /api/v1/docs")
logger.info("Documentación ReDoc disponible en: /api/v1/redoc")

# Endpoint de health check
@app.get("/")
async def root():
    return {
        "message": "EliteDynamicsAPI-Local está funcionando",
        "version": "1.1-localdev",
        "docs": "/api/v1/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.1-localdev",
        "environment": settings.ENVIRONMENT
    }

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint para verificar estado del sistema."""
    from app.core.action_mapper import ACTION_MAP
    from app.core.config import settings
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "total_actions": len(ACTION_MAP),
        "backend_features": {
            "google_ads": bool(settings.GOOGLE_ADS_CLIENT_ID),
            "youtube": bool(settings.YOUTUBE_CLIENT_ID or settings.GOOGLE_ADS_CLIENT_ID),
            "gemini": bool(settings.GEMINI_API_KEY),
            "auth_manager": True
        }
    }