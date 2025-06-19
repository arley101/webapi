import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.dependencies import initialize_http_client, shutdown_http_client
from app.api.routes import (
    azuremgmt_router, bookings_router, calendario_router, correo_router,
    forms_router, github_router, googleads_router, graph_router,
    hubspot_router, linkedin_ads_router, metaads_router, notion_router,
    office_router, onedrive_router, openai_router, planner_router,
    power_automate_router, powerbi_router, sharepoint_router, stream_router,
    teams_router, tiktok_ads_router, todo_router, userprofile_router,
    users_router, vivainsights_router, youtube_ads_router
)

# Configuración del logging
logging.basicConfig(level=settings.LOG_LEVEL.upper(), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Creación de la aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Eventos de ciclo de vida de la aplicación
@app.on_event("startup")
async def startup_event():
    logger.info("Iniciando la aplicación y el cliente HTTP...")
    await initialize_http_client()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Cerrando el cliente HTTP y la aplicación...")
    await shutdown_http_client()

# Middlewares (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, esto debería ser más restrictivo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lista de todos los routers a incluir
routers = [
    azuremgmt_router, bookings_router, calendario_router, correo_router,
    forms_router, github_router, googleads_router, graph_router,
    hubspot_router, linkedin_ads_router, metaads_router, notion_router,
    office_router, onedrive_router, openai_router, planner_router,
    power_automate_router, powerbi_router, sharepoint_router, stream_router,
    teams_router, tiktok_ads_router, todo_router, userprofile_router,
    users_router, vivainsights_router, youtube_ads_router
]

# Inclusión masiva de todos los routers en la aplicación
for router_module in routers:
    app.include_router(router_module.router, prefix="/api/v1")

logger.info(f"✅ Se han cargado {len(routers)} routers de servicios explícitos.")

# Endpoint de verificación de salud
@app.get("/health", tags=["General"])
async def health_check():
    return {"status": "ok", "appName": settings.APP_NAME, "appVersion": settings.APP_VERSION}