# app/main.py
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Importación masiva de todos los routers generados
# Asegúrate de que los archivos generados por el script estén en esta carpeta
from app.api.routes import (
    azuremgmt_router, bookings_router, calendario_router, correo_router,
    forms_router, github_router, googleads_router, graph_router,
    hubspot_router, linkedin_ads_router, metaads_router, notion_router,
    office_router, onedrive_router, openai_router, planner_router,
    power_automate_router, powerbi_router, sharepoint_router, stream_router,
    teams_router, tiktok_ads_router, todo_router, userprofile_router,
    users_router, vivainsights_router, youtube_ads_router
)

# Configuración de Logging
logging.basicConfig(level=settings.LOG_LEVEL.upper(), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Creación de la App FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=f"API para Elite Dynamics (Arquitectura Explícita). Entorno: {os.getenv('AZURE_ENV', 'Desconocido')}",
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.elitedynamics.ai", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusión masiva de todos los routers en la aplicación
routers = [
    azuremgmt_router, bookings_router, calendario_router, correo_router,
    forms_router, github_router, googleads_router, graph_router,
    hubspot_router, linkedin_ads_router, metaads_router, notion_router,
    office_router, onedrive_router, openai_router, planner_router,
    power_automate_router, powerbi_router, sharepoint_router, stream_router,
    teams_router, tiktok_ads_router, todo_router, userprofile_router,
    users_router, vivainsights_router, youtube_ads_router
]

for router_module in routers:
    app.include_router(router_module.router, prefix="/api/v1")

logger.info(f"✅ Se han cargado {len(routers)} routers de servicios explícitos.")

@app.get("/health", tags=["General"])
async def health_check():
    return {"status": "ok", "appName": settings.APP_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)