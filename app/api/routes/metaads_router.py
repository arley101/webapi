# Archivo para el servicio 'metaads' generado automáticamente
from fastapi import APIRouter, Depends, Body, Path, Query, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import metaads_actions
from app.api.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/metaads", tags=["Metaads"])

# Endpoint para: metaads_list_campaigns
@router.post("/list_campaigns")
def metaads_list_campaigns(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para metaads_list_campaigns"""
    final_params = params or {}
    result = metaads_actions.metaads_list_campaigns(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: metaads_create_campaign
@router.post("/create_campaign")
def metaads_create_campaign(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para metaads_create_campaign"""
    final_params = params or {}
    result = metaads_actions.metaads_create_campaign(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: metaads_update_campaign
@router.post("/update_campaign")
def metaads_update_campaign(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para metaads_update_campaign"""
    final_params = params or {}
    result = metaads_actions.metaads_update_campaign(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: metaads_delete_campaign
@router.post("/delete_campaign")
def metaads_delete_campaign(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para metaads_delete_campaign"""
    final_params = params or {}
    result = metaads_actions.metaads_delete_campaign(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: metaads_get_insights
@router.post("/get_insights")
def metaads_get_insights(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para metaads_get_insights"""
    final_params = params or {}
    result = metaads_actions.metaads_get_insights(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

