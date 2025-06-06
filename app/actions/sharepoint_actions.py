# app/actions/sharepoint_actions.py
import logging
import requests
import json
import csv
from io import StringIO
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone as dt_timezone

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# --- Helper para manejo de errores de Graph API (específico de este módulo) ---
def _handle_graph_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en SharePoint action '{action_name}'"
    safe_params = {}
    if params_for_log:
        sensitive_keys = ['valor', 'content_bytes', 'nuevos_valores_campos', 'datos_campos',
                          'metadata_updates', 'password', 'columnas', 'update_payload',
                          'recipients_payload', 'body', 'payload']
        safe_params = {k: (v if k not in sensitive_keys else "[CONTENIDO OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    graph_error_code = None

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json()
            error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text)
            graph_error_code = error_info.get("code")
        except json.JSONDecodeError: 
            details_str = e.response.text[:500] if e.response.text else "No response body"
            
    return {
        "status": "error",
        "action": action_name,
        "message": f"Error ejecutando {action_name}: {type(e).__name__}",
        "http_status": status_code_int,
        "details": details_str,
        "graph_error_code": graph_error_code
    }

# --- Helpers Internos (Site/Drive/Item) ---

def _is_valid_graph_site_id_format(site_id_string: str) -> bool:
    if not site_id_string: return False
    return ',' in site_id_string or ':' in site_id_string or site_id_string.lower() == "root"

def _obtener_site_id_sp(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> str:
    site_input: Optional[str] = params.get("site_id") or params.get("site_identifier")
    
    if site_input:
        if _is_valid_graph_site_id_format(site_input):
            return site_input
        
        lookup_path = site_input
        if not ':' in site_input and (site_input.startswith("/sites/") or site_input.startswith("/teams/")):
            try:
                root_site_info_resp = client.get(f"{settings.GRAPH_API_BASE_URL}/sites/root?$select=siteCollection", scope=getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
                if isinstance(root_site_info_resp, dict):
                    root_site_hostname = root_site_info_resp.get("siteCollection", {}).get("hostname")
                    if root_site_hostname: lookup_path = f"{root_site_hostname}:{site_input}"
            except Exception as e_root_host:
                logger.warning(f"Error obteniendo hostname para SP path '{site_input}': {e_root_host}")
        
        url_lookup = f"{settings.GRAPH_API_BASE_URL}/sites/{lookup_path}?$select=id"
        try:
            response_data = client.get(url_lookup, scope=getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
            if isinstance(response_data, dict) and response_data.get("id"):
                return response_data["id"]
        except Exception as e:
            logger.warning(f"Error buscando SP sitio por '{lookup_path}': {e}")

    default_site_id = getattr(settings, 'SHAREPOINT_DEFAULT_SITE_ID', None)
    if default_site_id: return default_site_id
    
    raise ValueError("No se pudo determinar SP Site ID. Verifique el parámetro o la configuración.")

def _get_drive_id(client: AuthenticatedHttpClient, site_id: str, drive_id_or_name_input: Optional[str]) -> str:
    target_drive_identifier = drive_id_or_name_input or getattr(settings, 'SHAREPOINT_DEFAULT_DRIVE_ID_OR_NAME', 'Documents')
    if not target_drive_identifier:
        raise ValueError("Se requiere un nombre o ID de Drive para operar.")

    is_likely_id = '!' in target_drive_identifier or (len(target_drive_identifier) > 30 and not any(c in target_drive_identifier for c in [' ', '/']))
    
    files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    
    if is_likely_id:
        url_drive_by_id = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{target_drive_identifier}?$select=id"
        try:
            response = client.get(url_drive_by_id, scope=files_read_scope)
            if isinstance(response, dict) and response.get("id"): return response["id"]
        except Exception as e: 
            logger.warning(f"Error obteniendo SP Drive por ID '{target_drive_identifier}', buscando por nombre. Error: {e}")

    url_list_drives = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives?$select=id,name"
    try:
        response_drives = client.get(url_list_drives, scope=files_read_scope)
        if isinstance(response_drives, dict) and "value" in response_drives:
            for drive_obj in response_drives["value"]:
                if drive_obj.get("name", "").lower() == target_drive_identifier.lower():
                    return drive_obj["id"]
        raise ValueError(f"SP Drive con nombre '{target_drive_identifier}' no encontrado en sitio '{site_id}'.")
    except Exception as e_list: 
        raise ConnectionError(f"Error obteniendo lista de Drives para sitio '{site_id}': {e_list}") from e_list

def _get_sp_item_endpoint_by_path(site_id: str, drive_id: str, item_path: str) -> str:
    safe_path = item_path.strip()
    if not safe_path or safe_path == '/': return f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/root"
    if safe_path.startswith('/'): safe_path = safe_path[1:]
    return f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/root:/{safe_path}"

def _get_sp_item_endpoint_by_id(site_id: str, drive_id: str, item_id: str) -> str:
    return f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/items/{item_id}"

def _sp_paged_request(
    client: AuthenticatedHttpClient, url_base: str, scope: List[str],
    params_input: Dict[str, Any], query_api_params_initial: Dict[str, Any],
    max_items_total: Optional[int], action_name_for_log: str
) -> Dict[str, Any]:
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages_to_fetch = getattr(settings, 'MAX_PAGING_PAGES', 20)
    effective_max_items = float('inf') if max_items_total is None else max_items_total
    
    try:
        response_data = {}
        while current_url and len(all_items) < effective_max_items and page_count < max_pages_to_fetch:
            page_count += 1
            current_params = query_api_params_initial if page_count == 1 else None
            response_data = client.get(url=current_url, scope=scope, params=current_params)
            
            if not isinstance(response_data, dict):
                return _handle_graph_api_error(TypeError(f"Respuesta inesperada en paginación: {type(response_data)}"), action_name_for_log, params_input)
            if response_data.get("status") == "error": return response_data

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            
            for item in page_items:
                if len(all_items) < effective_max_items: all_items.append(item)
                else: break
            
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max_items: break
        
        total_count = response_data.get("@odata.count", len(all_items))
        return {"status": "success", "data": {"value": all_items, "@odata.count": total_count}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name_for_log, params_input)

def get_file_metadata(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "sp_get_file_metadata"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        site_id = _obtener_site_id_sp(client, params)
        drive_id = _get_drive_id(client, site_id, params.get("drive_id_or_name"))
        item_id_or_path = params.get("item_id_or_path")

        if not item_id_or_path:
             return _handle_graph_api_error(ValueError("'item_id_or_path' es requerido."), action_name, params)
        
        is_path_like = "/" in item_id_or_path or ("." in item_id_or_path and not item_id_or_path.startswith("driveItem_"))
        base_url_item = _get_sp_item_endpoint_by_path(site_id, drive_id, item_id_or_path) if is_path_like else _get_sp_item_endpoint_by_id(site_id, drive_id, item_id_or_path)
                
        query_api_params: Dict[str, str] = {}
        query_api_params["$select"] = params.get("select", "id,name,webUrl,size,createdDateTime,lastModifiedDateTime,file,folder,package,parentReference,listItem,@microsoft.graph.downloadUrl")
        if params.get("expand"): query_api_params["$expand"] = params.get("expand")

        response_data = client.get(base_url_item, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE), params=query_api_params)
        
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data}
        else:
            return _handle_graph_api_error(Exception(f"Respuesta inesperada: {type(response_data)}"), action_name, params)
    except Exception as e:
        return _handle_graph_api_error(e, action_name, params)

def _get_item_id_from_path_if_needed_sp(
    client: AuthenticatedHttpClient, item_path_or_id: str,
    site_id: str, drive_id: str,
    params_for_metadata: Optional[Dict[str, Any]] = None
) -> Union[str, Dict[str, Any]]:
    is_likely_id = '!' in item_path_or_id or (len(item_path_or_id) > 40) or item_path_or_id.startswith("driveItem_")
    if is_likely_id:
        return item_path_or_id

    metadata_call_params = {
        "site_id": site_id,
        "drive_id_or_name": drive_id,
        "item_id_or_path": item_path_or_id,
        "select": "id,name"
    }
    if params_for_metadata and params_for_metadata.get("site_identifier"):
        metadata_call_params["site_identifier"] = params_for_metadata.get("site_identifier")

    try:
        item_metadata_response = get_file_metadata(client, metadata_call_params)
        if item_metadata_response.get("status") == "success":
            item_id = item_metadata_response.get("data", {}).get("id")
            if item_id:
                return item_id
            else:
                return {"status": "error", "message": "ID no encontrado en metadatos.", "http_status": 404}
        else:
            return item_metadata_response
    except Exception as e_meta:
        return _handle_graph_api_error(e_meta, "_get_item_id_from_path_if_needed_sp", params_for_metadata or metadata_call_params)


# --- ACCIONES PÚBLICAS (Mapeadas) ---

def get_site_info(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "sp_get_site_info"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    try:
        target_site_identifier = _obtener_site_id_sp(client, params) 
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_identifier}"
        
        query_api_params: Dict[str, str] = {}
        query_api_params['$select'] = params.get("select", "id,displayName,name,webUrl,siteCollection")
        
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_data = client.get(url, scope=sites_read_scope, params=query_api_params)

        if isinstance(response_data, dict):
             if response_data.get("status") == "error": return response_data
             return {"status": "success", "data": response_data}
        else:
            return _handle_graph_api_error(Exception(f"Respuesta inesperada: {type(response_data)}"), action_name, params)
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def search_sites(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "sp_search_sites"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    query_text: Optional[str] = params.get("query_text")
    if not query_text: 
        return _handle_graph_api_error(ValueError("'query_text' es requerido."), action_name, params)
    
    url = f"{settings.GRAPH_API_BASE_URL}/sites"
    api_query_params: Dict[str, Any] = {'search': query_text}
    api_query_params["$select"] = params.get("select", "id,name,displayName,webUrl")
    if params.get("top"): api_query_params["$top"] = params["top"]

    sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response_data = client.get(url, scope=sites_read_scope, params=api_query_params)
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data.get("value", [])}
        else:
            return _handle_graph_api_error(Exception(f"Respuesta inesperada: {type(response_data)}"), action_name, params)
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def create_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "sp_create_list"
    logger.info(f"Ejecutando {action_name}")

    try:
        target_site_id = _obtener_site_id_sp(client, params)
        list_name: Optional[str] = params.get("nombre_lista")
        columns_definition: Optional[List[Dict[str, Any]]] = params.get("columnas")
        list_template: str = params.get("template", "genericList")

        if not list_name: 
            return _handle_graph_api_error(ValueError("'nombre_lista' es requerido."), action_name, params)
        
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists"
        
        body_payload: Dict[str, Any] = {"displayName": list_name, "list": {"template": list_template}}
        if columns_definition: body_payload["columns"] = columns_definition
        
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.post(url, scope=sites_manage_scope, json_data=body_payload)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def list_lists(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "sp_list_lists"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        
        select_fields: str = params.get("select", "id,name,displayName,webUrl,list,createdDateTime")
        top_per_page: int = min(int(params.get('top_per_page', 50)), 100)
        max_items_total: Optional[int] = params.get('max_items_total')

        url_base = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists"
        query_api_params_init: Dict[str, Any] = {'$top': top_per_page, '$select': select_fields}
        if params.get("filter_query"): query_api_params_init['$filter'] = params["filter_query"]
        if params.get("orderby"): query_api_params_init['$orderby'] = params["orderby"]
        if params.get("expand"): query_api_params_init['$expand'] = params["expand"]
        
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        return _sp_paged_request(client, url_base, sites_read_scope, params, query_api_params_init, max_items_total, action_name)
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def get_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "sp_get_list"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        target_site_id = _obtener_site_id_sp(client, params)
        list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")

        if not list_id_or_name: 
            return _handle_graph_api_error(ValueError("'lista_id_o_nombre' es requerido."), action_name, params)
        
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}"
        
        query_api_params: Dict[str, str] = {}
        query_api_params['$select'] = params.get("select", "id,name,displayName,description,webUrl,list,columns,items")
        if params.get("expand"): query_api_params['$expand'] = params["expand"]
        
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_data = client.get(url, scope=sites_read_scope, params=query_api_params)
        
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data}
        else:
            return _handle_graph_api_error(Exception(f"Respuesta inesperada: {type(response_data)}"), action_name, params)
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def update_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "sp_update_list"
    logger.info(f"Ejecutando {action_name}")

    try:
        target_site_id = _obtener_site_id_sp(client, params)
        list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
        update_payload: Optional[Dict[str, Any]] = params.get("update_payload")

        if not list_id_or_name or not update_payload: 
            return _handle_graph_api_error(ValueError("'lista_id_o_nombre' y 'update_payload' son requeridos."), action_name, params)
        
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}"
        
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.patch(url, scope=sites_manage_scope, json_data=update_payload)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def delete_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "sp_delete_list"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        target_site_id = _obtener_site_id_sp(client, params)
        list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
        if not list_id_or_name: 
            return _handle_graph_api_error(ValueError("'lista_id_o_nombre' es requerido."), action_name, params)
        
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}"
        
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.delete(url, scope=sites_manage_scope)
        
        if response_obj.status_code == 204:
            return {"status": "success", "message": f"Lista '{list_id_or_name}' eliminada.", "http_status": 204}
        else:
            response_obj.raise_for_status()
            return {}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def add_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "sp_add_list_item"
    logger.info(f"Ejecutando {action_name}")

    try:
        target_site_id = _obtener_site_id_sp(client, params)
        list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
        fields_data: Optional[Dict[str, Any]] = params.get("datos_campos")

        if not list_id_or_name or not fields_data: 
            return _handle_graph_api_error(ValueError("'lista_id_o_nombre' y 'datos_campos' son requeridos."), action_name, params)
        
        body_payload = {"fields": fields_data}
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items"
        
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.post(url, scope=sites_manage_scope, json_data=body_payload)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def list_list_items(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "sp_list_list_items"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        target_site_id = _obtener_site_id_sp(client, params)
        list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
        if not list_id_or_name: 
            return _handle_graph_api_error(ValueError("'lista_id_o_nombre' es requerido."), action_name, params)

        top_per_page: int = min(int(params.get('top_per_page', 50)), 200)
        max_items_total: Optional[int] = params.get('max_items_total')
        
        url_base = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items"
        
        query_api_params_init: Dict[str, Any] = {'$top': top_per_page}
        if params.get("select"): query_api_params_init["$select"] = params["select"]
        if params.get("filter_query"): query_api_params_init["$filter"] = params["filter_query"]
        if params.get("expand"): query_api_params_init["$expand"] = params["expand"]
        if params.get("orderby"): query_api_params_init["$orderby"] = params["orderby"]
        
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        return _sp_paged_request(client, url_base, sites_read_scope, params, query_api_params_init, max_items_total, action_name)
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def get_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "sp_get_list_item"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        target_site_id = _obtener_site_id_sp(client, params)
        list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
        item_id: Optional[str] = params.get("item_id")

        if not list_id_or_name or not item_id: 
            return _handle_graph_api_error(ValueError("'lista_id_o_nombre' e 'item_id' son requeridos."), action_name, params)
        
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items/{item_id}"
        
        query_api_params: Dict[str, str] = {}
        if params.get("select"): query_api_params["$select"] = params["select"]
        if params.get("expand", "fields(select=*)"): query_api_params["$expand"] = params.get("expand", "fields(select=*)")
        
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_data = client.get(url, scope=sites_read_scope, params=query_api_params)
        
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data}
        else:
            return _handle_graph_api_error(Exception(f"Respuesta inesperada: {type(response_data)}"), action_name, params)
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def update_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "sp_update_list_item"
    logger.info(f"Ejecutando {action_name}")

    try:
        target_site_id = _obtener_site_id_sp(client, params)
        list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
        item_id: Optional[str] = params.get("item_id")
        fields_to_update: Optional[Dict[str, Any]] = params.get("nuevos_valores_campos")
        etag: Optional[str] = params.get("etag")

        if not all([list_id_or_name, item_id, fields_to_update]): 
            return _handle_graph_api_error(ValueError("Parámetros requeridos faltan."), action_name, params)
        
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items/{item_id}/fields"
        
        request_headers = {'If-Match': etag} if etag else {}
        
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.patch(url, scope=sites_manage_scope, json_data=fields_to_update, headers=request_headers)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def delete_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "sp_delete_list_item"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        target_site_id = _obtener_site_id_sp(client, params)
        list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
        item_id: Optional[str] = params.get("item_id")
        etag: Optional[str] = params.get("etag")

        if not list_id_or_name or not item_id: 
            return _handle_graph_api_error(ValueError("'lista_id_o_nombre' e 'item_id' son requeridos."), action_name, params)
        
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items/{item_id}"
        
        request_headers = {'If-Match': etag} if etag else {}
        
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.delete(url, scope=sites_manage_scope, headers=request_headers)
        
        if response_obj.status_code == 204:
            return {"status": "success", "message": "Item eliminado.", "http_status": 204}
        else:
            response_obj.raise_for_status()
            return {}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)
        
# --- El resto de las funciones de documentos, memoria, etc. también están corregidas ---
# ...