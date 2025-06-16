# Archivo para el servicio 'googleads' generado automáticamente
from fastapi import APIRouter, Depends, Body, Path, Query, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import googleads_actions
from app.api.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/googleads", tags=["Googleads"])

# Endpoint para: googleads_search_stream
@router.post("/search_stream")
def googleads_search_stream(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para googleads_search_stream"""
    final_params = params or {}
    result = googleads_actions.googleads_search_stream(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: googleads_mutate_campaigns
@router.post("/mutate_campaigns")
def googleads_mutate_campaigns(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para googleads_mutate_campaigns"""
    final_params = params or {}
    result = googleads_actions.googleads_mutate_campaigns(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: googleads_mutate_adgroups
@router.post("/mutate_adgroups")
def googleads_mutate_adgroups(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para googleads_mutate_adgroups"""
    final_params = params or {}
    result = googleads_actions.googleads_mutate_adgroups(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: googleads_mutate_ads
@router.post("/mutate_ads")
def googleads_mutate_ads(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para googleads_mutate_ads"""
    final_params = params or {}
    result = googleads_actions.googleads_mutate_ads(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: googleads_mutate_keywords
@router.post("/mutate_keywords")
def googleads_mutate_keywords(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para googleads_mutate_keywords"""
    final_params = params or {}
    result = googleads_actions.googleads_mutate_keywords(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

