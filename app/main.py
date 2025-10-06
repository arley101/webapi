# app/main.py
from fastapi import FastAPI, Request 
from contextlib import asynccontextmanager
import logging
from datetime import datetime

# Importar todos los routers
from app.api.routes.dynamics_actions import router as dynamics_router
from app.api.routes.chatgpt_proxy import router as chatgpt_router
from app.api.routes.unified_assistant import router as unified_router
from app.api.routes.assistant_selector import router as selector_router
from app.api.routes.workflow_manager import router as workflow_router
from app.api.routes.simple_assistant import router as simple_router
from app.api.routes.whatsapp_webhook import router as whatsapp_router
from app.api.routes.debug_info import router as debug_router
from app.api.routes.system_info import router as system_router

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
    logger.info("Iniciando EliteDynamicsAPI v1.2...")
    logger.info(f"Nivel de Logging configurado: {settings.LOG_LEVEL.upper()}")
    logger.info(f"Entorno: {settings.ENVIRONMENT}")
    
    # 🔄 UnifiedOAuthManager se auto-inicia en primera llamada
    logger.info("✅ UnifiedOAuthManager configurado - Auto-refresh activo al primer uso")
    
    yield
    
    # Shutdown
    logger.info("Apagando EliteDynamicsAPI...")

# Crear la instancia de la aplicación FastAPI con lifespan
app = FastAPI(
    title="EliteDynamics Pro API v1.2",
    version="1.2",
    description="Sistema empresarial profesional - FastAPI + Azure + OpenAI + 9 Routers",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Incluir todos los routers con sus prefijos
app.include_router(dynamics_router, prefix="/api/v1")
app.include_router(chatgpt_router, prefix="/api/v1")
app.include_router(unified_router, prefix="/api/v1")
app.include_router(selector_router, prefix="/api/v1")
app.include_router(workflow_router, prefix="/api/v1")
app.include_router(simple_router, prefix="/api/v1")
app.include_router(whatsapp_router, prefix="/api/v1")
app.include_router(debug_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")

# Log de confirmación después de incluir routers
logger.info("✅ Todos los routers activados:")
logger.info("  - Dynamics Actions Router: /api/v1/dynamics")
logger.info("  - ChatGPT Proxy Router: /api/v1/chatgpt")
logger.info("  - Unified Assistant Router: /api/v1/assistant")
logger.info("  - Assistant Selector Router: /api/v1/selector")
logger.info("  - Workflow Manager Router: /api/v1/workflows")
logger.info("  - Simple Assistant Router: /api/v1/simple")
logger.info("  - WhatsApp Webhook Router: /api/v1/whatsapp")
logger.info("  - Debug Info Router: /api/v1/debug")
logger.info("  - System Info Router: /api/v1/system")
logger.info("Documentación OpenAPI (Swagger UI) disponible en: /api/v1/docs")
logger.info("Documentación ReDoc disponible en: /api/v1/redoc")

# Endpoint de health check
@app.get("/")
async def root():
    return {
        "message": "EliteDynamicsAPI está funcionando",
        "version": "1.2",
        "docs": "/api/v1/docs",
        "environment": settings.ENVIRONMENT,
        "active_routers": 9
    }

@app.get("/health")
async def health_check():
    """Health check endpoint básico"""
    return {
        "status": "healthy",
        "version": "1.2",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now().isoformat(),
        "active_routers": 9
    }

@app.get("/api/v1/health")
async def api_health_check():
    """Health check endpoint detallado para verificar estado del sistema."""
    from app.core.action_mapper import ACTION_MAP
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.2.production",
        "environment": settings.ENVIRONMENT,
        "total_actions": len(ACTION_MAP),
        "active_routers": 9,
        "routers": [
            "dynamics_actions",
            "chatgpt_proxy", 
            "unified_assistant",
            "assistant_selector",
            "workflow_manager",
            "simple_assistant",
            "whatsapp_webhook",
            "debug_info",
            "system_info"
        ],
        "backend_features": {
            "microsoft_graph": bool(settings.AZURE_CLIENT_ID),
            "google_ads": bool(settings.GOOGLE_ADS_CLIENT_ID),
            "youtube": bool(settings.YOUTUBE_CLIENT_ID or settings.GOOGLE_ADS_CLIENT_ID),
            "meta_ads": bool(getattr(settings, 'META_ADS', None) and settings.META_ADS.APP_ID),
            "gemini": bool(settings.GEMINI_API_KEY),
            "wordpress": bool(settings.WP_SITE_URL),
            "notion": bool(settings.NOTION_API_KEY),
            "hubspot": bool(settings.HUBSPOT_PRIVATE_APP_KEY),
            "auth_manager": True
        }
    }