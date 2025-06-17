# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import googleads_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/googleads", tags=["Googleads"])

# Endpoint para: googleads_search_stream
@router.get("/search_stream", status_code=200)
async def googleads_search_stream(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para googleads_search_stream."""
    try:
        result = await googleads_actions.googleads_search_stream(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: googleads_mutate_campaigns
@router.post("/mutate_campaigns", status_code=200)
async def googleads_mutate_campaigns(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para googleads_mutate_campaigns."""
    try:
        result = await googleads_actions.googleads_mutate_campaigns(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: googleads_mutate_adgroups
@router.post("/mutate_adgroups", status_code=200)
async def googleads_mutate_adgroups(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para googleads_mutate_adgroups."""
    try:
        result = await googleads_actions.googleads_mutate_adgroups(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: googleads_mutate_ads
@router.post("/mutate_ads", status_code=200)
async def googleads_mutate_ads(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para googleads_mutate_ads."""
    try:
        result = await googleads_actions.googleads_mutate_ads(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: googleads_mutate_keywords
@router.post("/mutate_keywords", status_code=200)
async def googleads_mutate_keywords(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para googleads_mutate_keywords."""
    try:
        result = await googleads_actions.googleads_mutate_keywords(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

