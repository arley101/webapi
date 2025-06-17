# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import metaads_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/metaads", tags=["Metaads"])

# Endpoint para: metaads_list_campaigns
@router.get("/list_campaigns", status_code=200)
async def metaads_list_campaigns(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para metaads_list_campaigns."""
    try:
        result = await metaads_actions.metaads_list_campaigns(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: metaads_create_campaign
@router.post("/create_campaign", status_code=200)
async def metaads_create_campaign(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para metaads_create_campaign."""
    try:
        result = await metaads_actions.metaads_create_campaign(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: metaads_update_campaign
@router.patch("/update_campaign", status_code=200)
async def metaads_update_campaign(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para metaads_update_campaign."""
    try:
        result = await metaads_actions.metaads_update_campaign(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: metaads_delete_campaign
@router.delete("/delete_campaign", status_code=200)
async def metaads_delete_campaign(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para metaads_delete_campaign."""
    try:
        result = await metaads_actions.metaads_delete_campaign(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: metaads_get_insights
@router.get("/get_insights", status_code=200)
async def metaads_get_insights(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para metaads_get_insights."""
    try:
        result = await metaads_actions.metaads_get_insights(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

