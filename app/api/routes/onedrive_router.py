# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import onedrive_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/onedrive", tags=["Onedrive"])

# Endpoint para: onedrive_list_items
@router.get("/list_items", status_code=200)
async def onedrive_list_items(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para onedrive_list_items."""
    try:
        result = await onedrive_actions.list_items(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: onedrive_get_item
@router.get("/get_item", status_code=200)
async def onedrive_get_item(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para onedrive_get_item."""
    try:
        result = await onedrive_actions.get_item(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: onedrive_upload_file
@router.put("/upload_file", status_code=200)
async def onedrive_upload_file(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para onedrive_upload_file."""
    try:
        result = await onedrive_actions.upload_file(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: onedrive_download_file
@router.get("/download_file", status_code=200)
async def onedrive_download_file(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para onedrive_download_file."""
    try:
        result = await onedrive_actions.download_file(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: onedrive_delete_item
@router.delete("/delete_item", status_code=200)
async def onedrive_delete_item(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para onedrive_delete_item."""
    try:
        result = await onedrive_actions.delete_item(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: onedrive_create_folder
@router.post("/create_folder", status_code=200)
async def onedrive_create_folder(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para onedrive_create_folder."""
    try:
        result = await onedrive_actions.create_folder(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: onedrive_move_item
@router.patch("/move_item", status_code=200)
async def onedrive_move_item(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para onedrive_move_item."""
    try:
        result = await onedrive_actions.move_item(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: onedrive_copy_item
@router.patch("/copy_item", status_code=200)
async def onedrive_copy_item(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para onedrive_copy_item."""
    try:
        result = await onedrive_actions.copy_item(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: onedrive_search_items
@router.get("/search_items", status_code=200)
async def onedrive_search_items(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para onedrive_search_items."""
    try:
        result = await onedrive_actions.search_items(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: onedrive_get_sharing_link
@router.get("/get_sharing_link", status_code=200)
async def onedrive_get_sharing_link(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para onedrive_get_sharing_link."""
    try:
        result = await onedrive_actions.get_sharing_link(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: onedrive_update_item_metadata
@router.patch("/update_item_metadata", status_code=200)
async def onedrive_update_item_metadata(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para onedrive_update_item_metadata."""
    try:
        result = await onedrive_actions.update_item_metadata(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

