# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import vivainsights_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/vivainsights", tags=["Vivainsights"])

# Endpoint para: viva_get_my_analytics
@router.get("/viva_get_my_analytics", status_code=200)
async def viva_get_my_analytics(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para viva_get_my_analytics."""
    try:
        result = await vivainsights_actions.get_my_analytics(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: viva_get_focus_plan
@router.get("/viva_get_focus_plan", status_code=200)
async def viva_get_focus_plan(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para viva_get_focus_plan."""
    try:
        result = await vivainsights_actions.get_focus_plan(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

