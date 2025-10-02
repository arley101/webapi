# app/main_production_complete.py
"""
🚀 ELITE DYNAMICS API - CONFIGURACIÓN COMPLETA PARA PRODUCCIÓN
Sistema robusto con TODOS los routers activos y manejo inteligente de errores
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime
import os
import sys

# ============================================================================
# CONFIGURACIÓN DE LOGGING ROBUSTO
# ============================================================================
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ============================================================================
# IMPORTACIÓN SEGURA DE SETTINGS
# ============================================================================
try:
    from app.core.config import settings
    logger.info("✅ Settings cargado exitosamente")
except Exception as e:
    logger.warning(f"⚠️ Fallo al importar settings, usando valores por defecto: {e}")
    class _FallbackSettings:
        LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
        APP_VERSION = os.getenv("APP_VERSION", "1.1")
        AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
        GOOGLE_ADS_CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
        YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
        META_APP_ID = os.getenv("META_APP_ID", "")
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        WP_SITE_URL = os.getenv("WP_SITE_URL", "")
        NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
        HUBSPOT_PRIVATE_APP_KEY = os.getenv("HUBSPOT_PRIVATE_APP_KEY", "")
    settings = _FallbackSettings()

# ============================================================================
# IMPORTACIÓN SEGURA DE ROUTERS CON LOGGING DETALLADO
# ============================================================================

# Contador de routers exitosos
loaded_routers = {}
failed_routers = {}

def safe_import_router(module_path: str, router_name: str, display_name: str):
    """
    Importa un router de forma segura con logging detallado
    Retorna el router si se carga exitosamente, None si falla
    """
    try:
        module = __import__(module_path, fromlist=[router_name])
        router = getattr(module, router_name)
        loaded_routers[display_name] = module_path
        logger.info(f"✅ {display_name} cargado exitosamente")
        return router
    except ImportError as e:
        failed_routers[display_name] = f"ImportError: {str(e)}"
        logger.warning(f"⚠️ {display_name} NO cargado: {e}")
        return None
    except Exception as e:
        failed_routers[display_name] = f"Error: {str(e)}"
        logger.error(f"❌ {display_name} falló al cargar: {e}")
        return None

# Router principal de acciones dinámicas (CRÍTICO)
dynamics_router = safe_import_router(
    "app.api.routes.dynamics_actions", 
    "router", 
    "Dynamics Actions (Core API)"
)

# Router de ChatGPT Proxy para OpenAI Custom GPT
chatgpt_router = safe_import_router(
    "app.api.routes.chatgpt_proxy",
    "router",
    "ChatGPT Proxy (OpenAI Integration)"
)

# Router de Asistente Unificado Independiente
unified_assistant_router = safe_import_router(
    "app.api.routes.unified_assistant",
    "router",
    "Unified Assistant (Independent AI)"
)

# Router de Selector de Asistentes
assistant_selector_router = safe_import_router(
    "app.api.routes.assistant_selector",
    "router",
    "Assistant Selector (Intelligent Router)"
)

# Router de Gestión de Workflows
workflow_router = safe_import_router(
    "app.api.routes.workflow_manager",
    "router",
    "Workflow Manager (Automation)"
)

# Router de Asistente Simple
simple_assistant_router = safe_import_router(
    "app.api.routes.simple_assistant",
    "router",
    "Simple Assistant (Lightweight)"
)

# Router de WhatsApp Webhook
whatsapp_webhook_router = safe_import_router(
    "app.api.routes.whatsapp_webhook",
    "router",
    "WhatsApp Webhook (Messaging)"
)

# Router de Debug e Información del Sistema
debug_router = safe_import_router(
    "app.api.routes.debug_info",
    "router",
    "Debug Info (System Diagnostics)"
)

# Router de Información del Sistema
system_info_router = safe_import_router(
    "app.api.routes.system_info",
    "router",
    "System Info (Metrics)"
)

# ============================================================================
# COMPATIBILIDAD CON OPENAI CUSTOM GPT
# ============================================================================
try:
    from app.core.openapi_compatibility import optimize_for_custom_gpt
    logger.info("✅ OpenAI compatibility module cargado")
except Exception as e:
    logger.warning(f"⚠️ OpenAI compatibility no disponible: {e}")
    optimize_for_custom_gpt = lambda app: app  # Fallback no-op

# ============================================================================
# LIFESPAN MANAGER
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    # Startup
    logger.info("=" * 80)
    logger.info("🚀 ELITE DYNAMICS API - INICIANDO")
    logger.info("=" * 80)
    logger.info(f"📊 Versión: {getattr(settings, 'APP_VERSION', '1.1')}")
    logger.info(f"🌍 Entorno: {settings.ENVIRONMENT}")
    logger.info(f"📝 Nivel de logging: {settings.LOG_LEVEL}")
    logger.info(f"✅ Routers cargados: {len(loaded_routers)}")
    logger.info(f"⚠️ Routers fallidos: {len(failed_routers)}")
    
    # Mostrar routers cargados
    for name, module in loaded_routers.items():
        logger.info(f"   ✓ {name}")
    
    # Mostrar routers fallidos (si los hay)
    if failed_routers:
        logger.warning("⚠️ ROUTERS QUE NO SE PUDIERON CARGAR:")
        for name, error in failed_routers.items():
            logger.warning(f"   ✗ {name}: {error}")
    
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("👋 ELITE DYNAMICS API - APAGANDO")

# ============================================================================
# CREAR INSTANCIA DE FASTAPI
# ============================================================================
app = FastAPI(
    title="EliteDynamicsAPI",
    description="API Empresarial Avanzada con 418+ Integraciones | Optimizada para Custom GPT | Sistema de Asistentes Inteligentes",
    version="1.1.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# Optimizar para Custom GPT (OpenAPI 3.0.3)
app = optimize_for_custom_gpt(app)

# ============================================================================
# MIDDLEWARE - CORS
# ============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Manejo consistente de errores de validación"""
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Datos de entrada inválidos",
            "http_status": 422,
            "details": exc.errors(),
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Manejo consistente de errores generales"""
    logger.exception(f"Error no manejado: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Error interno del servidor",
            "http_status": 500,
            "details": str(exc),
        },
    )

# ============================================================================
# REGISTRAR ROUTERS
# ============================================================================

# Router principal (CRÍTICO - debe estar disponible)
if dynamics_router is not None:
    app.include_router(dynamics_router, prefix="/api/v1", tags=["Core Actions"])
    logger.info("✅ Dynamics Actions Router registrado: /api/v1/dynamics")
else:
    logger.error("❌ CRÍTICO: Dynamics Router no se pudo cargar - API principal no disponible")

# Router de ChatGPT Proxy
if chatgpt_router is not None:
    app.include_router(chatgpt_router, prefix="/api/v1", tags=["ChatGPT"])
    logger.info("✅ ChatGPT Proxy Router registrado: /api/v1/chatgpt")

# Router de Asistente Unificado
if unified_assistant_router is not None:
    app.include_router(unified_assistant_router, prefix="/api/v1", tags=["Unified Assistant"])
    logger.info("✅ Unified Assistant Router registrado: /api/v1/assistant")

# Router de Selector de Asistentes
if assistant_selector_router is not None:
    app.include_router(assistant_selector_router, prefix="/api/v1", tags=["Assistant Selector"])
    logger.info("✅ Assistant Selector Router registrado: /api/v1/selector")

# Router de Workflows
if workflow_router is not None:
    app.include_router(workflow_router, prefix="/api/v1", tags=["Workflows"])
    logger.info("✅ Workflow Manager Router registrado: /api/v1/workflows")

# Router de Asistente Simple
if simple_assistant_router is not None:
    app.include_router(simple_assistant_router, prefix="/api/v1", tags=["Simple Assistant"])
    logger.info("✅ Simple Assistant Router registrado: /api/v1/simple")

# Router de WhatsApp Webhook
if whatsapp_webhook_router is not None:
    app.include_router(whatsapp_webhook_router, tags=["WhatsApp"])
    logger.info("✅ WhatsApp Webhook Router registrado")

# Router de Debug
if debug_router is not None:
    app.include_router(debug_router, prefix="/api/v1", tags=["Debug"])
    logger.info("✅ Debug Router registrado: /api/v1/debug")

# Router de System Info
if system_info_router is not None:
    app.include_router(system_info_router, prefix="/api/v1", tags=["System"])
    logger.info("✅ System Info Router registrado: /api/v1/system")

# ============================================================================
# ENDPOINTS DE SALUD Y DIAGNÓSTICO
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """Endpoint raíz con información básica"""
    return {
        "message": "EliteDynamicsAPI está funcionando",
        "version": "1.1.0",
        "docs": "/api/v1/docs",
        "environment": settings.ENVIRONMENT,
        "routers_loaded": len(loaded_routers),
        "routers_failed": len(failed_routers),
        "status": "healthy" if dynamics_router is not None else "degraded"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check básico para monitoreo"""
    return {
        "status": "healthy" if dynamics_router is not None else "degraded",
        "version": "1.1.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now().isoformat(),
        "routers": {
            "loaded": list(loaded_routers.keys()),
            "failed": list(failed_routers.keys())
        }
    }

@app.get("/api/v1/health", tags=["Health"])
async def api_health_check():
    """Health check detallado con información de integraciones"""
    # Importación lazy para evitar circular imports
    try:
        from app.core.action_mapper import ACTION_MAP
        total_actions = len(ACTION_MAP)
    except:
        total_actions = 0
    
    return {
        "status": "healthy" if dynamics_router is not None else "degraded",
        "timestamp": datetime.now().isoformat(),
        "version": "1.1.0",
        "environment": settings.ENVIRONMENT,
        "total_actions": total_actions,
        "routers": {
            "total_loaded": len(loaded_routers),
            "total_failed": len(failed_routers),
            "loaded": list(loaded_routers.keys()),
            "failed": list(failed_routers.keys()) if failed_routers else []
        },
        "backend_features": {
            "microsoft_graph": bool(settings.AZURE_CLIENT_ID),
            "google_ads": bool(settings.GOOGLE_ADS_CLIENT_ID),
            "youtube": bool(settings.YOUTUBE_CLIENT_ID or settings.GOOGLE_ADS_CLIENT_ID),
            "meta_ads": bool(settings.META_APP_ID),
            "gemini": bool(settings.GEMINI_API_KEY),
            "wordpress": bool(settings.WP_SITE_URL),
            "notion": bool(settings.NOTION_API_KEY),
            "hubspot": bool(settings.HUBSPOT_PRIVATE_APP_KEY),
        }
    }

@app.get("/api/v1/router-status", tags=["System"])
async def router_status():
    """Estado detallado de todos los routers"""
    return {
        "timestamp": datetime.now().isoformat(),
        "routers_loaded": {name: {"module": module, "status": "active"} for name, module in loaded_routers.items()},
        "routers_failed": {name: {"error": error, "status": "inactive"} for name, error in failed_routers.items()},
        "summary": {
            "total": len(loaded_routers) + len(failed_routers),
            "active": len(loaded_routers),
            "inactive": len(failed_routers),
            "health": "optimal" if len(failed_routers) == 0 else "degraded"
        }
    }

# ============================================================================
# INTERFAZ WEB ESTÁTICA (SI EXISTE)
# ============================================================================
try:
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    if os.path.exists(static_path):
        app.mount("/static", StaticFiles(directory=static_path), name="static")
        logger.info(f"✅ Archivos estáticos servidos desde: {static_path}")
        
        @app.get("/chat", tags=["Interface"])
        async def serve_chat_interface():
            """Interfaz web de chat con audio"""
            static_file = os.path.join(static_path, "index.html")
            if os.path.exists(static_file):
                return FileResponse(static_file)
            else:
                return {
                    "message": "Interfaz de chat no encontrada",
                    "instructions": "La interfaz está disponible en static/index.html",
                    "api_docs": "/api/v1/docs"
                }
        
        logger.info("✅ Interfaz de chat disponible en: /chat")
except Exception as e:
    logger.warning(f"⚠️ No se pudo configurar interfaz de chat: {e}")

# ============================================================================
# INFORMACIÓN FINAL
# ============================================================================
logger.info("=" * 80)
logger.info("📚 DOCUMENTACIÓN DISPONIBLE:")
logger.info("   • Swagger UI: /api/v1/docs")
logger.info("   • ReDoc: /api/v1/redoc")
logger.info("   • OpenAPI JSON: /api/v1/openapi.json")
logger.info("=" * 80)
logger.info("🎯 ENDPOINTS PRINCIPALES:")
logger.info("   • Health Check: /health")
logger.info("   • API Health: /api/v1/health")
logger.info("   • Router Status: /api/v1/router-status")
if dynamics_router:
    logger.info("   • Core Actions: /api/v1/dynamics")
if chatgpt_router:
    logger.info("   • ChatGPT Proxy: /api/v1/chatgpt")
if unified_assistant_router:
    logger.info("   • Unified Assistant: /api/v1/assistant/chat")
if workflow_router:
    logger.info("   • Workflows: /api/v1/workflows")
logger.info("=" * 80)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
