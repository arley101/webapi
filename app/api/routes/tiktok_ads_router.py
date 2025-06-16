# Archivo generado automáticamente
from fastapi import APIRouter, Depends, Body, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import tiktok_ads_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/tiktok_ads", tags=["Tiktok_ads"])

# Endpoint para: tiktok_get_ad_accounts
@router.post("/tiktok_get_ad_accounts")
def tiktok_get_ad_accounts(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = tiktok_ads_actions.tiktok_get_ad_accounts(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: tiktok_list_campaigns
@router.post("/tiktok_list_campaigns")
def tiktok_list_campaigns(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = tiktok_ads_actions.tiktok_list_campaigns(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: tiktok_create_campaign
@router.post("/tiktok_create_campaign")
def tiktok_create_campaign(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = tiktok_ads_actions.tiktok_create_campaign(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: tiktok_update_campaign
@router.post("/tiktok_update_campaign")
def tiktok_update_campaign(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = tiktok_ads_actions.tiktok_update_campaign(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: tiktok_get_basic_report
@router.post("/tiktok_get_basic_report")
def tiktok_get_basic_report(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = tiktok_ads_actions.tiktok_get_basic_report(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

