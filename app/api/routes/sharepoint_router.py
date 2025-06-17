# Archivo generado automáticamente por refactor_maestro.py
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Dict, Any, Optional
from app.actions import sharepoint_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/sharepoint", tags=["Sharepoint"])

# Endpoint para: sp_list_lists
@router.get("/sp_list_lists", status_code=200)
async def sp_list_lists(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_list_lists."""
    try:
        result = await sharepoint_actions.list_lists(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_get_list
@router.get("/sp_get_list", status_code=200)
async def sp_get_list(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_get_list."""
    try:
        result = await sharepoint_actions.get_list(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_create_list
@router.get("/sp_create_list", status_code=200)
async def sp_create_list(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_create_list."""
    try:
        result = await sharepoint_actions.create_list(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_update_list
@router.get("/sp_update_list", status_code=200)
async def sp_update_list(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_update_list."""
    try:
        result = await sharepoint_actions.update_list(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_delete_list
@router.get("/sp_delete_list", status_code=200)
async def sp_delete_list(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_delete_list."""
    try:
        result = await sharepoint_actions.delete_list(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_list_list_items
@router.get("/sp_list_list_items", status_code=200)
async def sp_list_list_items(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_list_list_items."""
    try:
        result = await sharepoint_actions.list_list_items(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_get_list_item
@router.get("/sp_get_list_item", status_code=200)
async def sp_get_list_item(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_get_list_item."""
    try:
        result = await sharepoint_actions.get_list_item(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_add_list_item
@router.get("/sp_add_list_item", status_code=200)
async def sp_add_list_item(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_add_list_item."""
    try:
        result = await sharepoint_actions.add_list_item(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_update_list_item
@router.get("/sp_update_list_item", status_code=200)
async def sp_update_list_item(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_update_list_item."""
    try:
        result = await sharepoint_actions.update_list_item(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_delete_list_item
@router.get("/sp_delete_list_item", status_code=200)
async def sp_delete_list_item(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_delete_list_item."""
    try:
        result = await sharepoint_actions.delete_list_item(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_search_list_items
@router.get("/sp_search_list_items", status_code=200)
async def sp_search_list_items(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_search_list_items."""
    try:
        result = await sharepoint_actions.search_list_items(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_list_document_libraries
@router.get("/sp_list_document_libraries", status_code=200)
async def sp_list_document_libraries(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_list_document_libraries."""
    try:
        result = await sharepoint_actions.list_document_libraries(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_list_folder_contents
@router.get("/sp_list_folder_contents", status_code=200)
async def sp_list_folder_contents(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_list_folder_contents."""
    try:
        result = await sharepoint_actions.list_folder_contents(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_get_file_metadata
@router.get("/sp_get_file_metadata", status_code=200)
async def sp_get_file_metadata(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_get_file_metadata."""
    try:
        result = await sharepoint_actions.get_file_metadata(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_upload_document
@router.put("/sp_upload_document", status_code=200)
async def sp_upload_document(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_upload_document."""
    try:
        result = await sharepoint_actions.upload_document(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_download_document
@router.get("/sp_download_document", status_code=200)
async def sp_download_document(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_download_document."""
    try:
        result = await sharepoint_actions.download_document(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_delete_document
@router.delete("/sp_delete_document", status_code=200)
async def sp_delete_document(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_delete_document."""
    try:
        result = await sharepoint_actions.delete_document(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_delete_item
@router.delete("/sp_delete_item", status_code=200)
async def sp_delete_item(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_delete_item."""
    try:
        result = await sharepoint_actions.delete_item(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_create_folder
@router.post("/sp_create_folder", status_code=200)
async def sp_create_folder(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_create_folder."""
    try:
        result = await sharepoint_actions.create_folder(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_move_item
@router.patch("/sp_move_item", status_code=200)
async def sp_move_item(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_move_item."""
    try:
        result = await sharepoint_actions.move_item(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_copy_item
@router.patch("/sp_copy_item", status_code=200)
async def sp_copy_item(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_copy_item."""
    try:
        result = await sharepoint_actions.copy_item(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_update_file_metadata
@router.patch("/sp_update_file_metadata", status_code=200)
async def sp_update_file_metadata(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_update_file_metadata."""
    try:
        result = await sharepoint_actions.update_file_metadata(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_get_site_info
@router.get("/sp_get_site_info", status_code=200)
async def sp_get_site_info(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_get_site_info."""
    try:
        result = await sharepoint_actions.get_site_info(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_search_sites
@router.get("/sp_search_sites", status_code=200)
async def sp_search_sites(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_search_sites."""
    try:
        result = await sharepoint_actions.search_sites(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_memory_ensure_list
@router.get("/sp_memory_ensure_list", status_code=200)
async def sp_memory_ensure_list(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_memory_ensure_list."""
    try:
        result = await sharepoint_actions.memory_ensure_list(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_memory_save
@router.post("/sp_memory_save", status_code=200)
async def sp_memory_save(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_memory_save."""
    try:
        result = await sharepoint_actions.memory_save(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_memory_get
@router.get("/sp_memory_get", status_code=200)
async def sp_memory_get(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_memory_get."""
    try:
        result = await sharepoint_actions.memory_get(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_memory_delete
@router.delete("/sp_memory_delete", status_code=200)
async def sp_memory_delete(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_memory_delete."""
    try:
        result = await sharepoint_actions.memory_delete(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_memory_list_keys
@router.get("/sp_memory_list_keys", status_code=200)
async def sp_memory_list_keys(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_memory_list_keys."""
    try:
        result = await sharepoint_actions.memory_list_keys(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_memory_export_session
@router.get("/sp_memory_export_session", status_code=200)
async def sp_memory_export_session(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_memory_export_session."""
    try:
        result = await sharepoint_actions.memory_export_session(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_get_sharing_link
@router.get("/sp_get_sharing_link", status_code=200)
async def sp_get_sharing_link(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_get_sharing_link."""
    try:
        result = await sharepoint_actions.get_sharing_link(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_add_item_permissions
@router.post("/sp_add_item_permissions", status_code=200)
async def sp_add_item_permissions(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_add_item_permissions."""
    try:
        result = await sharepoint_actions.add_item_permissions(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_remove_item_permissions
@router.patch("/sp_remove_item_permissions", status_code=200)
async def sp_remove_item_permissions(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_remove_item_permissions."""
    try:
        result = await sharepoint_actions.remove_item_permissions(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_list_item_permissions
@router.get("/sp_list_item_permissions", status_code=200)
async def sp_list_item_permissions(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_list_item_permissions."""
    try:
        result = await sharepoint_actions.list_item_permissions(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para: sp_export_list_to_format
@router.get("/sp_export_list_to_format", status_code=200)
async def sp_export_list_to_format(
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client),
    params: Dict[str, Any] = Body(None)
):
    """Ruta autogenerada para sp_export_list_to_format."""
    try:
        result = await sharepoint_actions.sp_export_list_to_format(client=client, params=params or {})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

