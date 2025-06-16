# Archivo generado automáticamente
from fastapi import APIRouter, Depends, Body, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import linkedin_ads_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/linkedin_ads", tags=["Linkedin_ads"])

# Endpoint para: linkedin_get_ad_accounts
@router.post("/linkedin_get_ad_accounts")
def linkedin_get_ad_accounts(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = linkedin_ads_actions.linkedin_get_ad_accounts(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: linkedin_list_campaigns
@router.post("/linkedin_list_campaigns")
def linkedin_list_campaigns(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = linkedin_ads_actions.linkedin_list_campaigns(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: linkedin_get_basic_report
@router.post("/linkedin_get_basic_report")
def linkedin_get_basic_report(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = linkedin_ads_actions.linkedin_get_basic_report(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

