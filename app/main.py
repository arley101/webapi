# app/main.py
from fastapi import FastAPI, Request 
from contextlib import asynccontextmanager
import logging
from datetime import datetime
import sys

# Importar el router de acciones
from app.api.routes.dynamics_actions import router as dynamics_router

# Importar la configuración de la aplicación
from app.core.config import settings

# Importar middleware y exception handlers
from app.middleware.security import SecurityMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.cors import CORSMiddleware
from app.core.exceptions import register_exception_handlers
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware

# Enhanced logging configuration
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
log_handlers = [
    logging.StreamHandler(sys.stdout)
]

# Add file logging in production, configurable via environment variable
if settings.ENVIRONMENT == "production":
    log_file_path = os.getenv("LOG_FILE_PATH")
    if log_file_path:
        log_handlers.append(
            logging.FileHandler(log_file_path)
        )

logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format=log_format,
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

# Lifespan manager (reemplaza @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando EliteDynamicsAPI v1.1 (Enterprise Edition)...")
    logger.info(f"📊 Nivel de Logging configurado: {settings.LOG_LEVEL.upper()}")
    logger.info(f"🌍 Entorno: {settings.ENVIRONMENT}")
    logger.info(f"🔒 Middleware de seguridad: {'Activo' if settings.ENVIRONMENT != 'development' else 'Desarrollo'}")
    logger.info(f"📝 Logging estructurado: Activo")
    yield
    # Shutdown
    logger.info("⛔ Apagando EliteDynamicsAPI...")

# Crear la instancia de la aplicación FastAPI con lifespan
app = FastAPI(
    title="EliteDynamicsAPI",
    description="API empresarial de Elite Dynamics para automatización de procesos de negocio",
    version="1.1.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc", 
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# Register exception handlers
register_exception_handlers(app)

# Add CORS middleware (must be added before other middleware)
cors_config = CORSMiddleware.get_middleware_config(settings.ENVIRONMENT)
app.add_middleware(
    FastAPICORSMiddleware,
    **cors_config
)

# Add security middleware
app.add_middleware(
    SecurityMiddleware,
    rate_limit_requests=100 if settings.ENVIRONMENT == "development" else 60,
    rate_limit_window=60,
    enable_rate_limiting=True
)

# Add logging middleware
app.add_middleware(
    LoggingMiddleware,
    log_requests=True,
    log_responses=True,
    log_request_body=settings.ENVIRONMENT == "development",  # Only in dev for security
    max_body_size=1024
)

# Incluir el router con prefijo
app.include_router(dynamics_router, prefix="/api/v1")

# Log de confirmación después de incluir routers
logger.info("🔗 Router de acciones dinámicas incluido bajo el prefijo: /api/v1")
logger.info("📚 Documentación OpenAPI (Swagger UI) disponible en: /api/v1/docs")
logger.info("📖 Documentación ReDoc disponible en: /api/v1/redoc")

# Endpoint de health check
@app.get("/")
async def root():
    return {
        "message": "EliteDynamicsAPI Enterprise está funcionando correctamente",
        "version": "1.1.0",
        "docs": "/api/v1/docs",
        "environment": settings.ENVIRONMENT,
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint básico"""
    return {
        "status": "healthy",
        "version": "1.1.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now().isoformat(),
        "uptime": "operational"
    }

@app.get("/api/v1/health")
async def api_health_check():
    """Health check endpoint detallado para verificar estado del sistema."""
    from app.core.action_mapper import ACTION_MAP
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "total_actions": len(ACTION_MAP),
        "middleware": {
            "security": "active",
            "logging": "active", 
            "cors": "active",
            "exception_handling": "active"
        },
        "backend_features": {
            "microsoft_graph": bool(getattr(settings, 'AZURE_CLIENT_ID', None)),
            "google_ads": bool(getattr(settings, 'GOOGLE_ADS_CLIENT_ID', None)),
            "youtube": bool(getattr(settings, 'YOUTUBE_CLIENT_ID', None) or getattr(settings, 'GOOGLE_ADS_CLIENT_ID', None)),
            "meta_ads": bool(getattr(settings.META_ADS, 'APP_ID', None)),
            "gemini": bool(getattr(settings, 'GEMINI_API_KEY', None)),
            "wordpress": bool(getattr(settings, 'WP_SITE_URL', None)),
            "notion": bool(getattr(settings, 'NOTION_API_TOKEN', None)),
            "hubspot": bool(getattr(settings, 'HUBSPOT_PRIVATE_APP_TOKEN', None)),
            "auth_manager": True
        },
        "security": {
            "rate_limiting": "active",
            "cors_configured": True,
            "security_headers": "active"
        }
    }