# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import linkedin_ads_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/linkedin_ads", tags=["Linkedin_ads"])

# Endpoint para: linkedin_get_ad_accounts
@router.get("/linkedin_get_ad_accounts", status_code=200)
async def linkedin_get_ad_accounts(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para linkedin_get_ad_accounts."""
    try:
        result = await linkedin_ads_actions.linkedin_get_ad_accounts(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: linkedin_list_campaigns
@router.get("/linkedin_list_campaigns", status_code=200)
async def linkedin_list_campaigns(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para linkedin_list_campaigns."""
    try:
        result = await linkedin_ads_actions.linkedin_list_campaigns(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: linkedin_get_basic_report
@router.get("/linkedin_get_basic_report", status_code=200)
async def linkedin_get_basic_report(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para linkedin_get_basic_report."""
    try:
        result = await linkedin_ads_actions.linkedin_get_basic_report(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

