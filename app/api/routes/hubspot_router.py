# Archivo para el servicio 'hubspot' generado automáticamente
from fastapi import APIRouter, Depends, Body, Path, Query, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import hubspot_actions
from app.api.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/hubspot", tags=["Hubspot"])

# Endpoint para: hubspot_get_contacts
@router.post("/get_contacts")
def hubspot_get_contacts(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para hubspot_get_contacts"""
    final_params = params or {}
    result = hubspot_actions.hubspot_get_contacts(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: hubspot_create_contact
@router.post("/create_contact")
def hubspot_create_contact(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para hubspot_create_contact"""
    final_params = params or {}
    result = hubspot_actions.hubspot_create_contact(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: hubspot_update_contact
@router.post("/update_contact")
def hubspot_update_contact(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para hubspot_update_contact"""
    final_params = params or {}
    result = hubspot_actions.hubspot_update_contact(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: hubspot_delete_contact
@router.post("/delete_contact")
def hubspot_delete_contact(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para hubspot_delete_contact"""
    final_params = params or {}
    result = hubspot_actions.hubspot_delete_contact(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: hubspot_get_deals
@router.post("/get_deals")
def hubspot_get_deals(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para hubspot_get_deals"""
    final_params = params or {}
    result = hubspot_actions.hubspot_get_deals(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: hubspot_create_deal
@router.post("/create_deal")
def hubspot_create_deal(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para hubspot_create_deal"""
    final_params = params or {}
    result = hubspot_actions.hubspot_create_deal(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: hubspot_update_deal
@router.post("/update_deal")
def hubspot_update_deal(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para hubspot_update_deal"""
    final_params = params or {}
    result = hubspot_actions.hubspot_update_deal(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: hubspot_delete_deal
@router.post("/delete_deal")
def hubspot_delete_deal(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para hubspot_delete_deal"""
    final_params = params or {}
    result = hubspot_actions.hubspot_delete_deal(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

