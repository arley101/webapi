# app/main.py
from fastapi import FastAPI, Request 
from contextlib import asynccontextmanager
import logging
from datetime import datetime

# Importar el router de acciones
from app.api.routes.dynamics_actions import router as dynamics_router
from app.api.routes.ai_workflows import router as ai_workflows_router

# Importar la configuración de la aplicación
from app.core.config import settings

# Importar nuevos componentes de Phase 1
from app.core.state_manager import state_manager
from app.core.event_bus import event_bus, setup_default_listeners
from app.middlewares.audit_middleware import AuditMiddleware

# Configuración básica de logging
logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Lifespan manager con inicialización de Phase 1 components
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Iniciando EliteDynamicsAPI v1.1...")
    logger.info(f"Nivel de Logging configurado: {settings.LOG_LEVEL.upper()}")
    logger.info(f"Entorno: {settings.ENVIRONMENT}")
    
    # Phase 1: Initialize state management and event bus
    logger.info("🚀 Phase 1: Initializing state management and event bus...")
    
    try:
        # Initialize state manager
        await state_manager.initialize()
        
        # Initialize event bus
        await event_bus.initialize()
        await event_bus.start_listening()
        
        # Setup default event listeners
        await setup_default_listeners()
        
        logger.info("✅ Phase 1 components initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Phase 1 components: {e}")
        logger.warning("🔄 Continuing with degraded functionality")
    
    yield
    
    # Shutdown
    logger.info("Apagando EliteDynamicsAPI...")
    
    # Cleanup Phase 1 components
    try:
        await event_bus.close()
        await state_manager.close()
        logger.info("✅ Phase 1 components cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

# Crear la instancia de la aplicación FastAPI con lifespan
app = FastAPI(
    title="EliteDynamicsAPI",
    description="API de Elite Dynamics para acciones empresariales con state management y event bus",
    version="1.1",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# Add audit middleware
app.add_middleware(AuditMiddleware)

# Incluir el router con prefijo
app.include_router(dynamics_router, prefix="/api/v1")
app.include_router(ai_workflows_router, prefix="/api/v1", tags=["AI Workflows"])

# Log de confirmación después de incluir routers
logger.info("Router de acciones dinámicas incluido bajo el prefijo: /api/v1")
logger.info("Router de AI Workflows incluido bajo el prefijo: /api/v1")
logger.info("Documentación OpenAPI (Swagger UI) disponible en: /api/v1/docs")
logger.info("Documentación ReDoc disponible en: /api/v1/redoc")

# Endpoint de health check
@app.get("/")
async def root():
    return {
        "message": "EliteDynamicsAPI está funcionando",
        "version": "1.1",
        "docs": "/api/v1/docs",
        "environment": settings.ENVIRONMENT,
        "features": {
            "state_management": "enabled",
            "event_bus": "enabled", 
            "audit_middleware": "enabled"
        }
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
    
    # Check Phase 1 components health
    state_health = await state_manager.health_check()
    event_health = await event_bus.health_check()
    
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
            "auth_manager": True
        },
        "phase1_components": {
            "state_manager": state_health,
            "event_bus": event_health,
            "audit_middleware": {"status": "enabled" if settings.AUDIT_ENABLED else "disabled"}
        }
    }