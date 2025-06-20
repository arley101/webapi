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

def _is_valid_graph_site_id_format(site_id_string: str) -> bool:
    if not site_id_string:
        return False
    is_composite_id = ',' in site_id_string and site_id_string.count(',') >= 1
    is_server_relative_path_format = ':' in site_id_string and ('/sites/' in site_id_string or '/teams/' in site_id_string)
    is_graph_path_segment_format = site_id_string.startswith('sites/') and '{' in site_id_string and '}' in site_id_string
    is_root_keyword = site_id_string.lower() == "root"
    is_guid_like = len(site_id_string) == 36 and site_id_string.count('-') == 4
    return is_composite_id or is_server_relative_path_format or is_graph_path_segment_format or is_root_keyword or is_guid_like

def _obtener_site_id_sp(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> str:
    site_input: Optional[str] = params.get("site_id") or params.get("site_identifier")
    sharepoint_default_site_id_from_settings = getattr(settings, 'SHAREPOINT_DEFAULT_SITE_ID', None)

    if site_input:
        if _is_valid_graph_site_id_format(site_input):
            return site_input
        lookup_path = site_input
        if not ':' in site_input and (site_input.startswith("/sites/") or site_input.startswith("/teams/")):
             try:
                 sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
                 root_site_info_resp = client.get(f"{settings.GRAPH_API_BASE_URL}/sites/root?$select=siteCollection", scope=sites_read_scope)
                 root_site_hostname = root_site_info_resp.get("siteCollection", {}).get("hostname")
                 if root_site_hostname:
                     lookup_path = f"{root_site_hostname}:{site_input}"
             except Exception as e_root_host:
                 logger.warning(f"Error obteniendo hostname para SP path relativo '{site_input}': {e_root_host}. Se usará el path original.")
        
        url_lookup = f"{settings.GRAPH_API_BASE_URL}/sites/{lookup_path}?$select=id,displayName,webUrl,siteCollection"
        try:
            sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
            site_data = client.get(url_lookup, scope=sites_read_scope)
            resolved_site_id = site_data.get("id")
            if resolved_site_id:
                return resolved_site_id
        except Exception as e:
            logger.warning(f"Error buscando SP sitio por '{lookup_path}': {e}. Intentando fallback.")

    if sharepoint_default_site_id_from_settings and _is_valid_graph_site_id_format(sharepoint_default_site_id_from_settings):
        return sharepoint_default_site_id_from_settings

    url_root_site = f"{settings.GRAPH_API_BASE_URL}/sites/root?$select=id,displayName"
    try:
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        root_site_data = client.get(url_root_site, scope=sites_read_scope)
        root_site_id = root_site_data.get("id")
        if root_site_id:
            return root_site_id
    except Exception as e_root:
        raise ValueError(f"Fallo CRÍTICO al obtener SP Site ID: {e_root}")
    raise ValueError("No se pudo determinar SP Site ID.")

def _get_drive_id(client: AuthenticatedHttpClient, site_id: str, drive_id_or_name_input: Optional[str] = None) -> str:
    sharepoint_default_drive_name = getattr(settings, 'SHAREPOINT_DEFAULT_DRIVE_ID_OR_NAME', 'Documents')
    target_drive_identifier = drive_id_or_name_input or sharepoint_default_drive_name
    
    if not target_drive_identifier: 
        raise ValueError("Se requiere un nombre o ID de Drive para operar.")

    is_likely_id = '!' in target_drive_identifier or (len(target_drive_identifier) > 30 and not any(c in target_drive_identifier for c in [' ', '/'])) or target_drive_identifier.startswith("b!")
    
    files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    
    if is_likely_id:
        url_drive_by_id = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{target_drive_identifier}?$select=id,name"
        try:
            drive_data = client.get(url_drive_by_id, scope=files_read_scope)
            drive_id = drive_data.get("id")
            if drive_id: 
                return drive_id
        except Exception as e: 
            logger.warning(f"Error obteniendo SP Drive por ID '{target_drive_identifier}': {e}. Buscando por nombre.")

    url_list_drives = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives?$select=id,name,displayName,webUrl"
    try:
        response_drives = client.get(url_list_drives, scope=files_read_scope)
        drives_list = response_drives.get("value", [])
        for drive_obj in drives_list:
            if drive_obj.get("name", "").lower() == target_drive_identifier.lower() or drive_obj.get("displayName", "").lower() == target_drive_identifier.lower():
                drive_id = drive_obj.get("id")
                if drive_id: 
                    return drive_id
        raise ValueError(f"SP Drive con nombre '{target_drive_identifier}' no encontrado en sitio '{site_id}'.")
    except Exception as e_list: 
        raise ConnectionError(f"Error obteniendo lista de Drives para sitio '{site_id}': {e_list}") from e_list

def _get_sp_item_endpoint_by_path(site_id: str, drive_id: str, item_path: str) -> str:
    safe_path = item_path.strip()
    if not safe_path or safe_path == '/': 
        return f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/root"
    if safe_path.startswith('/'): 
        safe_path = safe_path[1:]
    return f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/root:/{safe_path}"

def _get_sp_item_endpoint_by_id(site_id: str, drive_id: str, item_id: str) -> str:
    return f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/items/{item_id}"

def _handle_graph_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en SharePoint action '{action_name}'"
    safe_params = {}
    if params_for_log:
        sensitive_keys = ['valor', 'content_bytes', 'nuevos_valores_campos', 'datos_campos', 'metadata_updates', 'password', 'columnas', 'update_payload', 'recipients_payload', 'body', 'payload']
        safe_params = {k: (v if k not in sensitive_keys else "[CONTENIDO OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    details_str = str(e); status_code_int = 500; graph_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json()
            error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text)
            graph_error_code = error_info.get("code")
        except json.JSONDecodeError: 
            details_str = e.response.text[:500] if e.response.text else "No response body"
    return {"status": "error", "action": action_name, "message": f"Error ejecutando {action_name}: {type(e).__name__}", "http_status": status_code_int, "details": details_str, "graph_error_code": graph_error_code}

def _get_current_timestamp_iso_z() -> str:
    return datetime.now(dt_timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _sp_paged_request(client: AuthenticatedHttpClient, url_base: str, scope: List[str], params_input: Dict[str, Any], query_api_params_initial: Dict[str, Any], max_items_total: Optional[int], action_name_for_log: str) -> Dict[str, Any]:
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages_to_fetch = getattr(settings, 'MAX_PAGING_PAGES', 20)
    top_value_initial = query_api_params_initial.get('$top', getattr(settings, 'DEFAULT_PAGING_SIZE', 50))
    
    logger.debug(f"Iniciando solicitud paginada SP para '{action_name_for_log}' desde '{url_base.split('?')[0]}...'. Max total: {max_items_total or 'todos'}, por pág: {top_value_initial}, max_págs: {max_pages_to_fetch}")
    try:
        while current_url and (max_items_total is None or len(all_items) < max_items_total) and page_count < max_pages_to_fetch:
            page_count += 1
            is_first_call = (page_count == 1 and current_url == url_base)
            current_params = query_api_params_initial if is_first_call else None
            
            logger.debug(f"Página SP {page_count} para '{action_name_for_log}': GET {current_url.split('?')[0]} con params: {current_params}")
            response_data = client.get(url=current_url, scope=scope, params=current_params)
            # CORRECCIÓN: 'response_data' ya es un dict
            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): 
                break
            for item in page_items:
                if max_items_total is None or len(all_items) < max_items_total: 
                    all_items.append(item)
                else: break
            current_url = response_data.get('@odata.nextLink')
            if not current_url or (max_items_total is not None and len(all_items) >= max_items_total): 
                break
        logger.info(f"'{action_name_for_log}' recuperó {len(all_items)} items en {page_count} páginas.")
        return {"status": "success", "data": {"value": all_items, "@odata.count": len(all_items)}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name_for_log, params_input)

def _get_item_id_from_path_if_needed_sp(client: AuthenticatedHttpClient, item_path_or_id: str, site_id: str, drive_id: str, params_for_metadata: Optional[Dict[str, Any]] = None) -> Union[str, Dict[str, Any]]:
    is_likely_id = '!' in item_path_or_id or (len(item_path_or_id) > 30 and '/' not in item_path_or_id and '.' not in item_path_or_id) or item_path_or_id.startswith("driveItem_") or (len(item_path_or_id) > 60 and item_path_or_id.count('-') > 3)

    if is_likely_id:
        return item_path_or_id

    metadata_call_params = {"site_id": site_id, "drive_id_or_name": drive_id, "item_id_or_path": item_path_or_id, "select": "id,name"}
    if params_for_metadata and params_for_metadata.get("site_identifier"):
        metadata_call_params["site_identifier"] = params_for_metadata.get("site_identifier")

    try:
        item_metadata_response = get_file_metadata(client, metadata_call_params)
        if item_metadata_response.get("status") == "success":
            item_data = item_metadata_response.get("data", {})
            item_id = item_data.get("id")
            if item_id:
                return item_id
            else:
                return {"status": "error", "message": f"ID no encontrado para path '{item_path_or_id}'.", "details": item_data, "http_status": 404}
        else:
            return item_metadata_response
    except Exception as e_meta:
        return _handle_graph_api_error(e_meta, "_get_item_id_from_path_if_needed_sp", params_for_metadata or metadata_call_params)

def get_site_info(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "get_site_info"
    select_fields: Optional[str] = params.get("select")
    try:
        target_site_identifier = _obtener_site_id_sp(client, params) 
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_identifier}"
        query_api_params: Dict[str, str] = {}
        if select_fields: query_api_params['$select'] = select_fields
        else: query_api_params['$select'] = "id,displayName,name,webUrl,createdDateTime,lastModifiedDateTime,description,siteCollection"
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_data = client.get(url, scope=sites_read_scope, params=query_api_params)
        # CORRECCIÓN: 'response_data' ya es un dict
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def search_sites(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "search_sites"
    query_text: Optional[str] = params.get("query_text")
    if not query_text: return _handle_graph_api_error(ValueError("'query_text' es requerido."), action_name, params)
    url = f"{settings.GRAPH_API_BASE_URL}/sites"
    api_query_params: Dict[str, Any] = {'search': query_text}
    if params.get("select"): api_query_params["$select"] = params["select"]
    else: api_query_params["$select"] = "id,name,displayName,webUrl,description"
    if params.get("top"): api_query_params["$top"] = params["top"]
    sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response_data = client.get(url, scope=sites_read_scope, params=api_query_params)
        # CORRECCIÓN: 'response_data' ya es un dict
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def create_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "create_list"
    list_name: Optional[str] = params.get("nombre_lista")
    columns_definition: Optional[List[Dict[str, Any]]] = params.get("columnas")
    list_template: str = params.get("template", "genericList")
    if not list_name: return _handle_graph_api_error(ValueError("'nombre_lista' es requerido."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists"
        body_payload: Dict[str, Any] = {"displayName": list_name, "list": {"template": list_template}}
        if columns_definition and isinstance(columns_definition, list): body_payload["columns"] = columns_definition
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.post(url, scope=sites_manage_scope, json_data=body_payload)
        return {"status": "success", "data": response.json()}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def list_lists(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "list_lists"
    select_fields: str = params.get("select", "id,name,displayName,webUrl,list,createdDateTime,lastModifiedDateTime")
    top_per_page: int = min(int(params.get('top_per_page', 50)), getattr(settings, 'DEFAULT_PAGING_SIZE', 50))
    max_items_total: Optional[int] = params.get('max_items_total')
    filter_query: Optional[str] = params.get("filter_query")
    order_by: Optional[str] = params.get("order_by")
    expand_fields: Optional[str] = params.get("expand")
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url_base = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists"
        query_api_params_init: Dict[str, Any] = {'$top': top_per_page, '$select': select_fields}
        if filter_query: query_api_params_init['$filter'] = filter_query
        if order_by: query_api_params_init['$orderby'] = order_by
        if expand_fields: query_api_params_init['$expand'] = expand_fields
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        return _sp_paged_request(client, url_base, sites_read_scope, params, query_api_params_init, max_items_total, action_name)
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def get_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "get_list"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    select_fields: Optional[str] = params.get("select")
    expand_fields: Optional[str] = params.get("expand")
    if not list_id_or_name: return _handle_graph_api_error(ValueError("'lista_id_o_nombre' es requerido."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}"
        query_api_params: Dict[str, str] = {}
        if select_fields: query_api_params['$select'] = select_fields
        else: query_api_params['$select'] = "id,name,displayName,description,webUrl,list,createdDateTime,lastModifiedDateTime,columns,contentTypes,items"
        if expand_fields: query_api_params['$expand'] = expand_fields
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_data = client.get(url, scope=sites_read_scope, params=query_api_params if query_api_params else None)
        # CORRECCIÓN: 'response_data' ya es un dict
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def update_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "update_list"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    update_payload: Optional[Dict[str, Any]] = params.get("update_payload")
    if not list_id_or_name or not update_payload or not isinstance(update_payload, dict): return _handle_graph_api_error(ValueError("'lista_id_o_nombre' y 'update_payload' (dict) son requeridos."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}"
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.patch(url, scope=sites_manage_scope, json_data=update_payload)
        return {"status": "success", "data": response.json()}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def delete_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "delete_list"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    if not list_id_or_name: return _handle_graph_api_error(ValueError("'lista_id_o_nombre' es requerido."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}"
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.delete(url, scope=sites_manage_scope)
        return {"status": "success", "message": f"Lista '{list_id_or_name}' eliminada.", "http_status": response.status_code}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def add_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "add_list_item"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    fields_data: Optional[Dict[str, Any]] = params.get("datos_campos")
    if not list_id_or_name or not fields_data or not isinstance(fields_data, dict): return _handle_graph_api_error(ValueError("'lista_id_o_nombre' y 'datos_campos' (dict) son requeridos."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        body_payload = {"fields": fields_data}
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items"
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.post(url, scope=sites_manage_scope, json_data=body_payload)
        return {"status": "success", "data": response.json()}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def list_list_items(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "list_list_items"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    if not list_id_or_name: return _handle_graph_api_error(ValueError("'lista_id_o_nombre' es requerido."), action_name, params)
    select_fields: Optional[str] = params.get("select")
    filter_query: Optional[str] = params.get("filter_query")
    expand_fields: str = params.get("expand", "fields(select=*)")
    top_per_page: int = min(int(params.get('top_per_page', 50)), getattr(settings, 'DEFAULT_PAGING_SIZE', 50))
    max_items_total: Optional[int] = params.get('max_items_total')
    order_by: Optional[str] = params.get("orderby")
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url_base = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items"
        query_api_params_init: Dict[str, Any] = {'$top': top_per_page}
        if select_fields: query_api_params_init["$select"] = select_fields
        if filter_query: query_api_params_init["$filter"] = filter_query
        if expand_fields: query_api_params_init["$expand"] = expand_fields
        if order_by: query_api_params_init["$orderby"] = order_by
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        return _sp_paged_request(client, url_base, sites_read_scope, params, query_api_params_init, max_items_total, action_name)
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def get_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "get_list_item"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    item_id: Optional[str] = params.get("item_id")
    select_fields: Optional[str] = params.get("select")
    expand_fields: Optional[str] = params.get("expand", "fields(select=*)")
    if not list_id_or_name or not item_id: return _handle_graph_api_error(ValueError("'lista_id_o_nombre' e 'item_id' son requeridos."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items/{item_id}"
        query_api_params: Dict[str, str] = {}
        if select_fields: query_api_params["$select"] = select_fields
        if expand_fields: query_api_params["$expand"] = expand_fields
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_data = client.get(url, scope=sites_read_scope, params=query_api_params if query_api_params else None)
        # CORRECCIÓN: 'response_data' ya es un dict
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def update_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "update_list_item"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    item_id: Optional[str] = params.get("item_id")
    fields_to_update: Optional[Dict[str, Any]] = params.get("nuevos_valores_campos")
    etag: Optional[str] = params.get("etag")
    if not list_id_or_name or not item_id or not fields_to_update or not isinstance(fields_to_update, dict): return _handle_graph_api_error(ValueError("'lista_id_o_nombre', 'item_id', y 'nuevos_valores_campos' (dict) son requeridos."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items/{item_id}/fields"
        request_headers = {'If-Match': etag} if etag else {}
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.patch(url, scope=sites_manage_scope, json_data=fields_to_update, headers=request_headers)
        return {"status": "success", "data": response.json()}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def delete_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "delete_list_item"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    item_id: Optional[str] = params.get("item_id")
    etag: Optional[str] = params.get("etag")
    if not list_id_or_name or not item_id: return _handle_graph_api_error(ValueError("'lista_id_o_nombre' e 'item_id' son requeridos."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items/{item_id}"
        request_headers = {'If-Match': etag} if etag else {}
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.delete(url, scope=sites_manage_scope, headers=request_headers)
        return {"status": "success", "message": f"Item '{item_id}' eliminado.", "http_status": response.status_code}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def search_list_items(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "search_list_items"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    query_text_as_filter: Optional[str] = params.get("query_text")
    if not list_id_or_name or not query_text_as_filter: return _handle_graph_api_error(ValueError("'lista_id_o_nombre' y 'query_text' son requeridos."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        list_items_params = {
            "site_id": target_site_id,
            "site_identifier": params.get("site_identifier", params.get("site_id")),
            "lista_id_o_nombre": list_id_or_name,
            "filter_query": query_text_as_filter,
            "select": params.get("select"),
            "max_items_total": params.get("top"),
            "expand": params.get("expand", "fields(select=*)")
        }
        return list_list_items(client, list_items_params)
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def list_document_libraries(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "list_document_libraries"
    select_fields: str = params.get("select", "id,name,displayName,description,webUrl,driveType,createdDateTime,lastModifiedDateTime,quota,owner")
    top_per_page: int = min(int(params.get('top_per_page', 50)), getattr(settings, 'DEFAULT_PAGING_SIZE', 50))
    max_items_total: Optional[int] = params.get('max_items_total')
    filter_query: Optional[str] = params.get("filter_query")
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url_base = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/drives"
        query_api_params_init: Dict[str, Any] = {'$top': top_per_page, '$select': select_fields}
        if filter_query: query_api_params_init['$filter'] = filter_query
        else: query_api_params_init['$filter'] = "driveType eq 'documentLibrary'"
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        return _sp_paged_request(client, url_base, files_read_scope, params, query_api_params_init, max_items_total, action_name)
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def list_folder_contents(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "list_folder_contents"
    folder_path_or_id: str = params.get("folder_path_or_id", "")
    drive_id_or_name_input: Optional[str] = params.get("drive_id_or_name")
    select_fields: Optional[str] = params.get("select")
    expand_fields: Optional[str] = params.get("expand")
    top_per_page: int = min(int(params.get('top_per_page', 50)), 200)
    max_items_total: Optional[int] = params.get('max_items_total')
    order_by: Optional[str] = params.get("orderby")
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, drive_id_or_name_input)
        is_folder_id = not ('/' in folder_path_or_id) and (len(folder_path_or_id) > 30 or '!' in folder_path_or_id or folder_path_or_id.startswith("driveItem_"))
        item_segment = f"items/{folder_path_or_id}" if is_folder_id else (f"root:/{folder_path_or_id.strip('/')}" if folder_path_or_id.strip('/') else "root")
        url_base = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/drives/{target_drive_id}/{item_segment}/children"
        query_api_params_init: Dict[str, Any] = {'$top': top_per_page}
        query_api_params_init["$select"] = select_fields or "id,name,webUrl,size,createdDateTime,lastModifiedDateTime,file,folder,package,parentReference"
        if expand_fields: query_api_params_init["$expand"] = expand_fields
        if order_by: query_api_params_init["$orderby"] = order_by
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        return _sp_paged_request(client, url_base, files_read_scope, params, query_api_params_init, max_items_total, action_name)
    except Exception as e: return _handle_graph_api_error(e, action_name, params)