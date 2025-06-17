# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import hubspot_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/hubspot", tags=["Hubspot"])

# Endpoint para: hubspot_get_contacts
@router.get("/get_contacts", status_code=200)
async def hubspot_get_contacts(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para hubspot_get_contacts."""
    try:
        result = await hubspot_actions.hubspot_get_contacts(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: hubspot_create_contact
@router.post("/create_contact", status_code=200)
async def hubspot_create_contact(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para hubspot_create_contact."""
    try:
        result = await hubspot_actions.hubspot_create_contact(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: hubspot_update_contact
@router.patch("/update_contact", status_code=200)
async def hubspot_update_contact(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para hubspot_update_contact."""
    try:
        result = await hubspot_actions.hubspot_update_contact(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: hubspot_delete_contact
@router.delete("/delete_contact", status_code=200)
async def hubspot_delete_contact(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para hubspot_delete_contact."""
    try:
        result = await hubspot_actions.hubspot_delete_contact(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: hubspot_get_deals
@router.get("/get_deals", status_code=200)
async def hubspot_get_deals(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para hubspot_get_deals."""
    try:
        result = await hubspot_actions.hubspot_get_deals(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: hubspot_create_deal
@router.post("/create_deal", status_code=200)
async def hubspot_create_deal(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para hubspot_create_deal."""
    try:
        result = await hubspot_actions.hubspot_create_deal(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: hubspot_update_deal
@router.patch("/update_deal", status_code=200)
async def hubspot_update_deal(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para hubspot_update_deal."""
    try:
        result = await hubspot_actions.hubspot_update_deal(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: hubspot_delete_deal
@router.delete("/delete_deal", status_code=200)
async def hubspot_delete_deal(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para hubspot_delete_deal."""
    try:
        result = await hubspot_actions.hubspot_delete_deal(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

