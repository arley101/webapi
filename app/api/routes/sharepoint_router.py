# Archivo generado automáticamente
from fastapi import APIRouter, Depends, Body, HTTPException, status, Response
from typing import Dict, Any, Optional
from app.actions import sharepoint_actions
from app.dependencies import get_authenticated_http_client
from app.shared.helpers.http_client import AuthenticatedHttpClient

router = APIRouter(prefix="/sharepoint", tags=["Sharepoint"])

# Endpoint para: sp_list_lists
@router.post("/sp_list_lists")
def sp_list_lists(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.list_lists(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_get_list
@router.post("/sp_get_list")
def sp_get_list(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.get_list(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_create_list
@router.post("/sp_create_list")
def sp_create_list(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.create_list(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_update_list
@router.post("/sp_update_list")
def sp_update_list(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.update_list(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_delete_list
@router.post("/sp_delete_list")
def sp_delete_list(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.delete_list(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_list_list_items
@router.post("/sp_list_list_items")
def sp_list_list_items(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.list_list_items(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_get_list_item
@router.post("/sp_get_list_item")
def sp_get_list_item(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.get_list_item(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_add_list_item
@router.post("/sp_add_list_item")
def sp_add_list_item(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.add_list_item(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_update_list_item
@router.post("/sp_update_list_item")
def sp_update_list_item(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.update_list_item(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_delete_list_item
@router.post("/sp_delete_list_item")
def sp_delete_list_item(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.delete_list_item(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_search_list_items
@router.post("/sp_search_list_items")
def sp_search_list_items(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.search_list_items(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_list_document_libraries
@router.post("/sp_list_document_libraries")
def sp_list_document_libraries(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.list_document_libraries(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_list_folder_contents
@router.post("/sp_list_folder_contents")
def sp_list_folder_contents(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.list_folder_contents(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_get_file_metadata
@router.post("/sp_get_file_metadata")
def sp_get_file_metadata(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.get_file_metadata(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_upload_document
@router.post("/sp_upload_document")
def sp_upload_document(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.upload_document(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_download_document
@router.post("/sp_download_document")
def sp_download_document(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.download_document(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_delete_document
@router.post("/sp_delete_document")
def sp_delete_document(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.delete_document(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_delete_item
@router.post("/sp_delete_item")
def sp_delete_item(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.delete_item(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_create_folder
@router.post("/sp_create_folder")
def sp_create_folder(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.create_folder(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_move_item
@router.post("/sp_move_item")
def sp_move_item(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.move_item(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_copy_item
@router.post("/sp_copy_item")
def sp_copy_item(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.copy_item(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_update_file_metadata
@router.post("/sp_update_file_metadata")
def sp_update_file_metadata(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.update_file_metadata(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_get_site_info
@router.post("/sp_get_site_info")
def sp_get_site_info(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.get_site_info(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_search_sites
@router.post("/sp_search_sites")
def sp_search_sites(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.search_sites(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_memory_ensure_list
@router.post("/sp_memory_ensure_list")
def sp_memory_ensure_list(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.memory_ensure_list(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_memory_save
@router.post("/sp_memory_save")
def sp_memory_save(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.memory_save(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_memory_get
@router.post("/sp_memory_get")
def sp_memory_get(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.memory_get(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_memory_delete
@router.post("/sp_memory_delete")
def sp_memory_delete(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.memory_delete(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_memory_list_keys
@router.post("/sp_memory_list_keys")
def sp_memory_list_keys(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.memory_list_keys(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_memory_export_session
@router.post("/sp_memory_export_session")
def sp_memory_export_session(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.memory_export_session(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_get_sharing_link
@router.post("/sp_get_sharing_link")
def sp_get_sharing_link(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.get_sharing_link(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_add_item_permissions
@router.post("/sp_add_item_permissions")
def sp_add_item_permissions(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.add_item_permissions(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_remove_item_permissions
@router.post("/sp_remove_item_permissions")
def sp_remove_item_permissions(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.remove_item_permissions(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_list_item_permissions
@router.post("/sp_list_item_permissions")
def sp_list_item_permissions(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.list_item_permissions(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

# Endpoint para: sp_export_list_to_format
@router.post("/sp_export_list_to_format")
def sp_export_list_to_format(client: AuthenticatedHttpClient = Depends(get_authenticated_http_client), params: Optional[Dict[str, Any]] = Body(None)):
    result = sharepoint_actions.sp_export_list_to_format(client=client, params=params or {})
    if isinstance(result, dict) and result.get('status') == 'error':
        raise HTTPException(status_code=result.get('http_status', 500), detail=result)
    return result

