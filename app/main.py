# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime
import os

# Importar el router de acciones
from app.api.routes.dynamics_actions import router as dynamics_router
from app.api.routes.chatgpt_proxy import router as chatgpt_router

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
    logger.info("Iniciando EliteDynamicsAPI v1.1...")
    logger.info(f"Nivel de Logging configurado: {settings.LOG_LEVEL.upper()}")
    logger.info(f"Entorno: {settings.ENVIRONMENT}")
    yield
    # Shutdown
    logger.info("Apagando EliteDynamicsAPI...")

# Crear la instancia de la aplicación FastAPI con lifespan
app = FastAPI(
    title="EliteDynamicsAPI",
    description="API de Elite Dynamics para acciones empresariales",
    version="1.1",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan  # Usar lifespan en lugar de on_event
)

# CORS (ajústelo para producción: dominios específicos)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Normalización de errores 422 (validación) y 500 (genéricos) a JSON consistente
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Datos de entrada inválidos.",
            "http_status": 422,
            "details": exc.errors(),
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Evita respuestas HTML y mantiene formato JSON homogéneo
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Error interno del servidor.",
            "http_status": 500,
            "details": str(exc),
        },
    )

# Incluir el router con prefijo
app.include_router(dynamics_router, prefix="/api/v1")
app.include_router(chatgpt_router, prefix="/api/v1")

# Log de confirmación después de incluir routers
logger.info("Router de acciones dinámicas incluido bajo el prefijo: /api/v1")
logger.info("Router ChatGPT Proxy incluido bajo el prefijo: /api/v1")
logger.info("Documentación OpenAPI (Swagger UI) disponible en: /api/v1/docs")
logger.info("Documentación ReDoc disponible en: /api/v1/redoc")

# Endpoint de health check
@app.get("/")
async def root():
    return {
        "message": "EliteDynamicsAPI está funcionando",
        "version": "1.1",
        "docs": "/api/v1/docs",
        "environment": settings.ENVIRONMENT
    }

@app.get("/health")
async def health_check():
    """Health check endpoint básico"""
    return {
        "status": "healthy",
        "version": "1.1",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/health")
async def api_health_check():
    """Health check endpoint detallado para verificar estado del sistema."""
    from app.core.action_mapper import ACTION_MAP
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": getattr(settings, 'APP_VERSION', '1.1'),
        "environment": settings.ENVIRONMENT,
        "total_actions": len(ACTION_MAP),
        "backend_features": {
            "microsoft_graph": bool(settings.AZURE_CLIENT_ID),
            "google_ads": bool(settings.GOOGLE_ADS_CLIENT_ID),
            "youtube": bool(settings.YOUTUBE_CLIENT_ID or settings.GOOGLE_ADS_CLIENT_ID),
            "meta_ads": bool(settings.META_APP_ID),
            "gemini": bool(settings.GEMINI_API_KEY),
            "wordpress": bool(settings.WP_SITE_URL),
            "notion": bool(settings.NOTION_API_KEY),
            "hubspot": bool(settings.HUBSPOT_PRIVATE_APP_KEY),
            "runway": bool(os.getenv("RUNWAY_API_KEY")),
            "auth_manager": True
        }
    }