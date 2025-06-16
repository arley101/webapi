# Archivo generado automáticamente
from fastapi import APIRouter, Depends, Body, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import power_automate_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/power_automate", tags=["Power_automate"])

# Endpoint para: pa_listar_flows
@router.post("/pa_listar_flows")
def pa_listar_flows(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = power_automate_actions.listar_flows(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: pa_obtener_flow
@router.post("/pa_obtener_flow")
def pa_obtener_flow(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = power_automate_actions.obtener_flow(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: pa_ejecutar_flow
@router.post("/pa_ejecutar_flow")
def pa_ejecutar_flow(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = power_automate_actions.ejecutar_flow(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: pa_obtener_estado_ejecucion_flow
@router.post("/pa_obtener_estado_ejecucion_flow")
def pa_obtener_estado_ejecucion_flow(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = power_automate_actions.obtener_estado_ejecucion_flow(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

