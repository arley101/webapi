# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import tiktok_ads_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/tiktok_ads", tags=["Tiktok_ads"])

# Endpoint para: tiktok_get_ad_accounts
@router.get("/tiktok_get_ad_accounts", status_code=200)
async def tiktok_get_ad_accounts(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para tiktok_get_ad_accounts."""
    try:
        result = await tiktok_ads_actions.tiktok_get_ad_accounts(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: tiktok_list_campaigns
@router.get("/tiktok_list_campaigns", status_code=200)
async def tiktok_list_campaigns(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para tiktok_list_campaigns."""
    try:
        result = await tiktok_ads_actions.tiktok_list_campaigns(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: tiktok_create_campaign
@router.post("/tiktok_create_campaign", status_code=200)
async def tiktok_create_campaign(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para tiktok_create_campaign."""
    try:
        result = await tiktok_ads_actions.tiktok_create_campaign(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: tiktok_update_campaign
@router.patch("/tiktok_update_campaign", status_code=200)
async def tiktok_update_campaign(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para tiktok_update_campaign."""
    try:
        result = await tiktok_ads_actions.tiktok_update_campaign(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: tiktok_get_basic_report
@router.get("/tiktok_get_basic_report", status_code=200)
async def tiktok_get_basic_report(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para tiktok_get_basic_report."""
    try:
        result = await tiktok_ads_actions.tiktok_get_basic_report(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

