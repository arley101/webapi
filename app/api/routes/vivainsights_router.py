# Archivo para el servicio 'vivainsights' generado automáticamente
from fastapi import APIRouter, Depends, Body, Path, Query, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import vivainsights_actions
from app.api.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/vivainsights", tags=["Vivainsights"])

# Endpoint para: viva_get_my_analytics
@router.post("/viva_get_my_analytics")
def viva_get_my_analytics(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para viva_get_my_analytics"""
    final_params = params or {}
    result = vivainsights_actions.get_my_analytics(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: viva_get_focus_plan
@router.post("/viva_get_focus_plan")
def viva_get_focus_plan(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para viva_get_focus_plan"""
    final_params = params or {}
    result = vivainsights_actions.get_focus_plan(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

