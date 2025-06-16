# Archivo para el servicio 'power_automate' generado automáticamente
from fastapi import APIRouter, Depends, Body, Path, Query, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import power_automate_actions
from app.api.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/power_automate", tags=["Power_automate"])

# Endpoint para: pa_listar_flows
@router.post("/pa_listar_flows")
def pa_listar_flows(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para pa_listar_flows"""
    final_params = params or {}
    result = power_automate_actions.listar_flows(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: pa_obtener_flow
@router.post("/pa_obtener_flow")
def pa_obtener_flow(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para pa_obtener_flow"""
    final_params = params or {}
    result = power_automate_actions.obtener_flow(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: pa_ejecutar_flow
@router.post("/pa_ejecutar_flow")
def pa_ejecutar_flow(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para pa_ejecutar_flow"""
    final_params = params or {}
    result = power_automate_actions.ejecutar_flow(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: pa_obtener_estado_ejecucion_flow
@router.post("/pa_obtener_estado_ejecucion_flow")
def pa_obtener_estado_ejecucion_flow(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para pa_obtener_estado_ejecucion_flow"""
    final_params = params or {}
    result = power_automate_actions.obtener_estado_ejecucion_flow(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

