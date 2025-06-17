# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import power_automate_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/power_automate", tags=["Power_automate"])

# Endpoint para: pa_listar_flows
@router.get("/pa_listar_flows", status_code=200)
async def pa_listar_flows(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para pa_listar_flows."""
    try:
        result = await power_automate_actions.listar_flows(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: pa_obtener_flow
@router.get("/pa_obtener_flow", status_code=200)
async def pa_obtener_flow(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para pa_obtener_flow."""
    try:
        result = await power_automate_actions.obtener_flow(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: pa_ejecutar_flow
@router.post("/pa_ejecutar_flow", status_code=200)
async def pa_ejecutar_flow(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para pa_ejecutar_flow."""
    try:
        result = await power_automate_actions.ejecutar_flow(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: pa_obtener_estado_ejecucion_flow
@router.get("/pa_obtener_estado_ejecucion_flow", status_code=200)
async def pa_obtener_estado_ejecucion_flow(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para pa_obtener_estado_ejecucion_flow."""
    try:
        result = await power_automate_actions.obtener_estado_ejecucion_flow(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

