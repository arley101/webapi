# Archivo para el servicio 'sharepoint' generado automáticamente
from fastapi import APIRouter, Depends, Body, Path, Query, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import sharepoint_actions
from app.api.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/sharepoint", tags=["Sharepoint"])

# Endpoint para: sp_list_lists
@router.post("/sp_list_lists")
def sp_list_lists(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_list_lists"""
    final_params = params or {}
    result = sharepoint_actions.list_lists(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_get_list
@router.post("/sp_get_list")
def sp_get_list(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_get_list"""
    final_params = params or {}
    result = sharepoint_actions.get_list(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_create_list
@router.post("/sp_create_list")
def sp_create_list(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_create_list"""
    final_params = params or {}
    result = sharepoint_actions.create_list(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_update_list
@router.post("/sp_update_list")
def sp_update_list(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_update_list"""
    final_params = params or {}
    result = sharepoint_actions.update_list(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_delete_list
@router.post("/sp_delete_list")
def sp_delete_list(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_delete_list"""
    final_params = params or {}
    result = sharepoint_actions.delete_list(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_list_list_items
@router.post("/sp_list_list_items")
def sp_list_list_items(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_list_list_items"""
    final_params = params or {}
    result = sharepoint_actions.list_list_items(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_get_list_item
@router.post("/sp_get_list_item")
def sp_get_list_item(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_get_list_item"""
    final_params = params or {}
    result = sharepoint_actions.get_list_item(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_add_list_item
@router.post("/sp_add_list_item")
def sp_add_list_item(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_add_list_item"""
    final_params = params or {}
    result = sharepoint_actions.add_list_item(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_update_list_item
@router.post("/sp_update_list_item")
def sp_update_list_item(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_update_list_item"""
    final_params = params or {}
    result = sharepoint_actions.update_list_item(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_delete_list_item
@router.post("/sp_delete_list_item")
def sp_delete_list_item(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_delete_list_item"""
    final_params = params or {}
    result = sharepoint_actions.delete_list_item(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_search_list_items
@router.post("/sp_search_list_items")
def sp_search_list_items(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_search_list_items"""
    final_params = params or {}
    result = sharepoint_actions.search_list_items(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_list_document_libraries
@router.post("/sp_list_document_libraries")
def sp_list_document_libraries(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_list_document_libraries"""
    final_params = params or {}
    result = sharepoint_actions.list_document_libraries(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_list_folder_contents
@router.post("/sp_list_folder_contents")
def sp_list_folder_contents(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_list_folder_contents"""
    final_params = params or {}
    result = sharepoint_actions.list_folder_contents(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_get_file_metadata
@router.post("/sp_get_file_metadata")
def sp_get_file_metadata(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_get_file_metadata"""
    final_params = params or {}
    result = sharepoint_actions.get_file_metadata(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_upload_document
@router.post("/sp_upload_document")
def sp_upload_document(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_upload_document"""
    final_params = params or {}
    result = sharepoint_actions.upload_document(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_download_document
@router.post("/sp_download_document")
def sp_download_document(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_download_document"""
    final_params = params or {}
    result = sharepoint_actions.download_document(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_delete_document
@router.post("/sp_delete_document")
def sp_delete_document(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_delete_document"""
    final_params = params or {}
    result = sharepoint_actions.delete_document(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_delete_item
@router.post("/sp_delete_item")
def sp_delete_item(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_delete_item"""
    final_params = params or {}
    result = sharepoint_actions.delete_item(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_create_folder
@router.post("/sp_create_folder")
def sp_create_folder(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_create_folder"""
    final_params = params or {}
    result = sharepoint_actions.create_folder(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_move_item
@router.post("/sp_move_item")
def sp_move_item(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_move_item"""
    final_params = params or {}
    result = sharepoint_actions.move_item(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_copy_item
@router.post("/sp_copy_item")
def sp_copy_item(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_copy_item"""
    final_params = params or {}
    result = sharepoint_actions.copy_item(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_update_file_metadata
@router.post("/sp_update_file_metadata")
def sp_update_file_metadata(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_update_file_metadata"""
    final_params = params or {}
    result = sharepoint_actions.update_file_metadata(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_get_site_info
@router.post("/sp_get_site_info")
def sp_get_site_info(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_get_site_info"""
    final_params = params or {}
    result = sharepoint_actions.get_site_info(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_search_sites
@router.post("/sp_search_sites")
def sp_search_sites(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_search_sites"""
    final_params = params or {}
    result = sharepoint_actions.search_sites(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_memory_ensure_list
@router.post("/sp_memory_ensure_list")
def sp_memory_ensure_list(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_memory_ensure_list"""
    final_params = params or {}
    result = sharepoint_actions.memory_ensure_list(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_memory_save
@router.post("/sp_memory_save")
def sp_memory_save(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_memory_save"""
    final_params = params or {}
    result = sharepoint_actions.memory_save(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_memory_get
@router.post("/sp_memory_get")
def sp_memory_get(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_memory_get"""
    final_params = params or {}
    result = sharepoint_actions.memory_get(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_memory_delete
@router.post("/sp_memory_delete")
def sp_memory_delete(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_memory_delete"""
    final_params = params or {}
    result = sharepoint_actions.memory_delete(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_memory_list_keys
@router.post("/sp_memory_list_keys")
def sp_memory_list_keys(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_memory_list_keys"""
    final_params = params or {}
    result = sharepoint_actions.memory_list_keys(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_memory_export_session
@router.post("/sp_memory_export_session")
def sp_memory_export_session(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_memory_export_session"""
    final_params = params or {}
    result = sharepoint_actions.memory_export_session(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_get_sharing_link
@router.post("/sp_get_sharing_link")
def sp_get_sharing_link(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_get_sharing_link"""
    final_params = params or {}
    result = sharepoint_actions.get_sharing_link(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_add_item_permissions
@router.post("/sp_add_item_permissions")
def sp_add_item_permissions(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_add_item_permissions"""
    final_params = params or {}
    result = sharepoint_actions.add_item_permissions(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_remove_item_permissions
@router.post("/sp_remove_item_permissions")
def sp_remove_item_permissions(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_remove_item_permissions"""
    final_params = params or {}
    result = sharepoint_actions.remove_item_permissions(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_list_item_permissions
@router.post("/sp_list_item_permissions")
def sp_list_item_permissions(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_list_item_permissions"""
    final_params = params or {}
    result = sharepoint_actions.list_item_permissions(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

# Endpoint para: sp_export_list_to_format
@router.post("/sp_export_list_to_format")
def sp_export_list_to_format(
    params: Optional[Dict[str, Any]] = Body(None),
    client: AuthenticatedHttpClient = Depends(get_authenticated_http_client)
):
    """Ruta autogenerada para sp_export_list_to_format"""
    final_params = params or {}
    result = sharepoint_actions.sp_export_list_to_format(client=client, params=final_params)
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    if isinstance(result, Response):
        return result
    return result

