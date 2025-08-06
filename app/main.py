# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Importar nuevos componentes V3
from app.middleware.audit_middleware import AuditMiddleware, SecurityHeadersMiddleware
from app.routers.v3 import orchestrate
from app.core.v3.orchestrator import orchestrator
from app.core.v3.event_bus import event_bus, setup_cascade_events
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
    """Maneja el ciclo de vida de la aplicación"""
    # Startup
    logger.info("🚀 Iniciando EliteDynamics V3...")
    
    try:
        # Inicializar orquestador
        await orchestrator.initialize()
        logger.info("✅ Orquestador inicializado")
        
        # Configurar eventos de cascada
        await setup_cascade_events()
        logger.info("✅ Eventos de cascada configurados")
        
        logger.info("✅ EliteDynamics V3 iniciado correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error durante inicio: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("👋 Cerrando EliteDynamics V3...")

# Crear la instancia de la aplicación FastAPI con lifespan
app = FastAPI(
    title="EliteDynamics API V3",
    description="Sistema de Orquestación Cognitiva Empresarial",
    version="3.0.0",
    lifespan=lifespan
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # Cambiar a dominios específicos en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar nuevos middlewares V3
app.add_middleware(AuditMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Incluir el router con prefijo
app.include_router(dynamics_router, prefix="/api/v1")

# Incluir nuevo router de orquestación V3
app.include_router(orchestrate.router)

# Log de confirmación después de incluir routers
logger.info("Router de acciones dinámicas incluido bajo el prefijo: /api/v1")
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
            "auth_manager": True
        }
    }

# Agregar endpoint de health mejorado
@app.get("/health/v3")
async def health_check_v3():
    """Health check con información de V3"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "features": {
            "orchestration": True,
            "state_management": True,
            "event_bus": True,
            "audit": True,
            "cascade_actions": True
        },
        "timestamp": datetime.utcnow().isoformat()
    }