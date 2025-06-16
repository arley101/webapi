# Archivo para el servicio 'tiktok_ads' generado automáticamente
from fastapi import APIRouter, Depends, Body, Path, Query, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import tiktok_ads_actions
from app.api.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/tiktok_ads", tags=["Tiktok_ads"])

# Endpoint para: tiktok_get_ad_accounts
@router.post("/tiktok_get_ad_accounts")
def tiktok_get_ad_accounts(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para tiktok_get_ad_accounts"""
    final_params = params or {}
    result = tiktok_ads_actions.tiktok_get_ad_accounts(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: tiktok_list_campaigns
@router.post("/tiktok_list_campaigns")
def tiktok_list_campaigns(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para tiktok_list_campaigns"""
    final_params = params or {}
    result = tiktok_ads_actions.tiktok_list_campaigns(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: tiktok_create_campaign
@router.post("/tiktok_create_campaign")
def tiktok_create_campaign(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para tiktok_create_campaign"""
    final_params = params or {}
    result = tiktok_ads_actions.tiktok_create_campaign(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: tiktok_update_campaign
@router.post("/tiktok_update_campaign")
def tiktok_update_campaign(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para tiktok_update_campaign"""
    final_params = params or {}
    result = tiktok_ads_actions.tiktok_update_campaign(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: tiktok_get_basic_report
@router.post("/tiktok_get_basic_report")
def tiktok_get_basic_report(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para tiktok_get_basic_report"""
    final_params = params or {}
    result = tiktok_ads_actions.tiktok_get_basic_report(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

