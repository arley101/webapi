# app/actions/sharepoint_actions.py
import logging
import requests # Necesario para tipos de excepción y para PUT a uploadUrl de sesión
import json
import csv
from io import StringIO
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone as dt_timezone

# Importar la configuración y el cliente HTTP autenticado
from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# --- Helper para validar si un input parece un Graph Site ID ---
def _is_valid_graph_site_id_format(site_id_string: str) -> bool:
    if not site_id_string:
        return False
    is_composite_id = ',' in site_id_string and site_id_string.count(',') >= 1
    is_server_relative_path_format = ':' in site_id_string and ('/sites/' in site_id_string or '/teams/' in site_id_string)
    is_graph_path_segment_format = site_id_string.startswith('sites/') # Podría ser más robusto si busca { }
    is_root_keyword = site_id_string.lower() == "root"
    is_guid_like = len(site_id_string) == 36 and site_id_string.count('-') == 4 
    
    return is_composite_id or is_server_relative_path_format or is_graph_path_segment_format or is_root_keyword or is_guid_like

# --- Helper Interno para Obtener Site ID (versión robusta) ---
def _obtener_site_id_sp(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> str:
    site_input: Optional[str] = params.get("site_id") or params.get("site_identifier")
    sharepoint_default_site_id_from_settings = getattr(settings, 'SHAREPOINT_DEFAULT_SITE_ID', None)

    if site_input:
        # Si parece un ID compuesto (hostname,sitecollection-id,web-id) o "root" o "sites/id", usar directamente
        if _is_valid_graph_site_id_format(site_input) and not (":" in site_input and ("sites/" in site_input or "teams/" in site_input)):
            logger.debug(f"SP Site ID con formato Graph reconocido (no path-like): '{site_input}'. Se usará directamente.")
            return site_input
        
        lookup_path = site_input
        # Si es un path relativo como "/sites/sitename", intentar componerlo con el hostname del root
        if not ':' in site_input and (site_input.startswith("/sites/") or site_input.startswith("/teams/")):
             try:
                 sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
                 root_site_info_resp_data = client.get(f"{settings.GRAPH_API_BASE_URL}/sites/root?$select=siteCollection,id,name", scope=sites_read_scope)
                 if not isinstance(root_site_info_resp_data, dict): 
                     raise Exception("Respuesta inesperada obteniendo root site info para construir path.")
                 if root_site_info_resp_data.get("status") == "error": # Error formateado por http_client
                      raise Exception(f"Error de http_client obteniendo root site: {root_site_info_resp_data.get('message')}")
                 
                 root_site_hostname = root_site_info_resp_data.get("siteCollection", {}).get("hostname")
                 if root_site_hostname:
                     lookup_path = f"{root_site_hostname}:{site_input}"
                     logger.info(f"SP Path relativo '{site_input}' convertido a: '{lookup_path}' para búsqueda de ID.")
                 else:
                    logger.warning(f"No se pudo obtener hostname para SP path relativo '{site_input}'. Se usará el path original para lookup.")
             except Exception as e_root_host:
                 logger.warning(f"Error obteniendo hostname para SP path relativo '{site_input}': {type(e_root_host).__name__} - {e_root_host}. Se usará el path original para lookup.")
        
        url_lookup = f"{settings.GRAPH_API_BASE_URL}/sites/{lookup_path}?$select=id,displayName,webUrl,siteCollection"
        logger.debug(f"Intentando obtener SP Site ID para el identificador/path: '{lookup_path}'")
        try:
            sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
            response_data = client.get(url_lookup, scope=sites_read_scope) 
            if not isinstance(response_data, dict):
                raise Exception(f"Respuesta inesperada del lookup de sitio, se esperaba dict. Recibido: {type(response_data)}")
            if response_data.get("status") == "error": 
                raise requests.exceptions.HTTPError(response_data.get("message"), response=type('MockResponse', (), {'status_code': response_data.get("http_status", 500)})())


            resolved_site_id = response_data.get("id")
            if resolved_site_id:
                logger.info(f"SP Site ID resuelto para input '{site_input}' (path '{lookup_path}'): '{resolved_site_id}' (Nombre: {response_data.get('displayName')})")
                return resolved_site_id
            else:
                 logger.warning(f"No se encontró ID de sitio en la respuesta para '{lookup_path}'. Respuesta: {response_data}")
        except requests.exceptions.HTTPError as http_err_lookup: 
            logger.warning(f"Error HTTP buscando SP sitio por '{lookup_path}': {http_err_lookup}. Intentando fallback.")
        except Exception as e: 
            logger.warning(f"Error buscando SP sitio por '{lookup_path}': {type(e).__name__} - {e}. Intentando fallback.")

    if sharepoint_default_site_id_from_settings and _is_valid_graph_site_id_format(sharepoint_default_site_id_from_settings):
        logger.info(f"Usando SP Site ID por defecto de settings: '{sharepoint_default_site_id_from_settings}' como fallback.")
        return sharepoint_default_site_id_from_settings

    url_root_site = f"{settings.GRAPH_API_BASE_URL}/sites/root?$select=id,displayName"
    logger.info(f"Ningún Site ID provisto o resuelto. Intentando obtener SP sitio raíz como fallback final.")
    try:
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_root_data = client.get(url_root_site, scope=sites_read_scope)
        if not isinstance(response_root_data, dict):
            raise Exception(f"Respuesta inesperada obteniendo sitio raíz, se esperaba dict. Recibido: {type(response_root_data)}")
        if response_root_data.get("status") == "error":
             raise Exception(f"Error obteniendo sitio raíz (de http_client): {response_root_data.get('message')}")
             
        root_site_id = response_root_data.get("id")
        if root_site_id:
            logger.info(f"Usando SP Site ID raíz como fallback final: '{root_site_id}' (Nombre: {response_root_data.get('displayName')})")
            return root_site_id
    except Exception as e_root:
        raise ValueError(f"Fallo CRÍTICO al obtener SP Site ID. No se pudo resolver ni obtener el sitio raíz. Error: {e_root}")
    
    raise ValueError("No se pudo determinar SP Site ID. Verifique el parámetro 'site_id'/'site_identifier' o la configuración de SHAREPOINT_DEFAULT_SITE_ID.")

def _get_drive_id(client: AuthenticatedHttpClient, site_id: str, drive_id_or_name_input: Optional[str] = None) -> str:
    sharepoint_default_drive_name = getattr(settings, 'SHAREPOINT_DEFAULT_DRIVE_ID_OR_NAME', 'Documents')
    target_drive_identifier = drive_id_or_name_input or sharepoint_default_drive_name
    if not target_drive_identifier: raise ValueError("Se requiere un nombre o ID de Drive.")

    is_likely_id = '!' in target_drive_identifier or (len(target_drive_identifier) > 30 and not any(c in target_drive_identifier for c in [' ', '/'])) or target_drive_identifier.startswith("b!") 
    files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    
    if is_likely_id:
        url_drive_by_id = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{target_drive_identifier}?$select=id,name"
        try:
            response_data = client.get(url_drive_by_id, scope=files_read_scope)
            if not isinstance(response_data, dict): raise Exception("Respuesta inesperada verificando Drive ID.")
            if response_data.get("status") == "error": raise Exception(f"Error de http_client: {response_data.get('message')}")
            drive_id_verified = response_data.get("id")
            if drive_id_verified: return drive_id_verified
        except Exception as e: logger.warning(f"Error obteniendo SP Drive por ID '{target_drive_identifier}': {e}. Buscando por nombre.")

    url_list_drives = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives?$select=id,name,displayName,webUrl"
    try:
        response_drives_data = client.get(url_list_drives, scope=files_read_scope)
        if not isinstance(response_drives_data, dict): raise Exception("Respuesta inesperada listando drives.")
        if response_drives_data.get("status") == "error": raise Exception(f"Error de http_client: {response_drives_data.get('message')}")
        
        drives_list = response_drives_data.get("value", [])
        for drive_obj in drives_list:
            if drive_obj.get("name", "").lower() == target_drive_identifier.lower() or \
               drive_obj.get("displayName", "").lower() == target_drive_identifier.lower():
                drive_id_found = drive_obj.get("id")
                if drive_id_found: return drive_id_found
        raise ValueError(f"SP Drive '{target_drive_identifier}' no encontrado en sitio '{site_id}'.")
    except Exception as e_list: raise ConnectionError(f"Error obteniendo lista de Drives para sitio '{site_id}': {e_list}") from e_list

def _get_sp_item_endpoint_by_path(site_id: str, drive_id: str, item_path: str) -> str:
    safe_path = item_path.strip()
    if not safe_path or safe_path == '/': return f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/root"
    return f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/root:/{safe_path.lstrip('/')}"

def _get_sp_item_endpoint_by_id(site_id: str, drive_id: str, item_id: str) -> str:
    return f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/items/{item_id}"

def _handle_graph_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en SharePoint action '{action_name}'"
    safe_params = {k: (v if k not in ['valor', 'content_bytes', 'nuevos_valores_campos', 'datos_campos', 'metadata_updates', 'password', 'columnas', 'update_payload', 'recipients_payload', 'body', 'payload'] else "[CONTENIDO OMITIDO]") for k, v in (params_for_log or {}).items()}
    log_message += f" con params: {safe_params}"
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    details_str = str(e); status_code_int = 500; graph_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json(); error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text); graph_error_code = error_info.get("code")
        except json.JSONDecodeError: details_str = e.response.text[:500] if e.response.text else "No response body"
    return {"status": "error", "action": action_name, "message": f"Error ejecutando {action_name}: {type(e).__name__}",
            "http_status": status_code_int, "details": details_str, "graph_error_code": graph_error_code}

def _get_current_timestamp_iso_z() -> str:
    return datetime.now(dt_timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _sp_paged_request(
    client: AuthenticatedHttpClient, url_base: str, scope: List[str],
    params_input: Dict[str, Any], query_api_params_initial: Dict[str, Any],
    max_items_total: Optional[int], action_name_for_log: str
) -> Dict[str, Any]:
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages_to_fetch = getattr(settings, 'MAX_PAGING_PAGES', 30)
    top_value_initial = query_api_params_initial.get('$top', getattr(settings, 'DEFAULT_PAGING_SIZE', 50))
    effective_max_items = float('inf') if max_items_total is None else max_items_total
    try:
        while current_url and len(all_items) < effective_max_items and page_count < max_pages_to_fetch:
            page_count += 1
            current_params = query_api_params_initial if page_count == 1 and current_url == url_base else None
            response_data = client.get(url=current_url, scope=scope, params=current_params)
            if not isinstance(response_data, dict): raise Exception(f"Respuesta paginada SP inesperada: {type(response_data)}")
            if response_data.get("status") == "error": return response_data 
            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            for item in page_items:
                if len(all_items) < effective_max_items: all_items.append(item)
                else: break
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max_items: break
        return {"status": "success", "data": {"value": all_items, "@odata.count": len(all_items)}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e: return _handle_graph_api_error(e, action_name_for_log, params_input)

def _get_item_id_from_path_if_needed_sp(
    client: AuthenticatedHttpClient, item_path_or_id: str,
    site_id: str, drive_id: str,
    params_for_metadata: Optional[Dict[str, Any]] = None
) -> Union[str, Dict[str, Any]]:
    is_likely_id = '!' in item_path_or_id or \
                   (len(item_path_or_id) > 40 and '/' not in item_path_or_id and '.' not in item_path_or_id) or \
                   item_path_or_id.startswith("driveItem_") or \
                   (len(item_path_or_id) > 60 and item_path_or_id.count('-') > 3)
    if is_likely_id: return item_path_or_id
    metadata_call_params = {"site_id": site_id, "drive_id_or_name": drive_id, "item_id_or_path": item_path_or_id, "select": "id,name"}
    if params_for_metadata and params_for_metadata.get("site_identifier"):
        metadata_call_params["site_identifier"] = params_for_metadata.get("site_identifier")
    try:
        item_metadata_response = get_file_metadata(client, metadata_call_params)
        if item_metadata_response.get("status") == "success":
            item_data = item_metadata_response.get("data", {}); item_id = item_data.get("id")
            if item_id: return item_id
            else: return {"status": "error", "message": f"ID no encontrado para SP path '{item_path_or_id}'.", "details": item_data, "http_status": 404}
        else: return item_metadata_response
    except Exception as e_meta:
        return _handle_graph_api_error(e_meta, "_get_item_id_from_path_if_needed_sp", params_for_metadata or metadata_call_params)

def get_site_info(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_site_info con params: %s", params); action_name = "get_site_info"
    try:
        target_site_identifier = _obtener_site_id_sp(client, params) 
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_identifier}"
        select = params.get("select", "id,displayName,name,webUrl,createdDateTime,lastModifiedDateTime,description,siteCollection")
        query_api_params: Dict[str, str] = {'$select': select}
        response_data = client.get(url, scope=getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE), params=query_api_params)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def search_sites(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando search_sites con params: %s", params); action_name = "search_sites"
    query_text: Optional[str] = params.get("query_text")
    if not query_text: return _handle_graph_api_error(ValueError("'query_text' es requerido."), action_name, params)
    url = f"{settings.GRAPH_API_BASE_URL}/sites"; api_query_params: Dict[str, Any] = {'search': query_text}
    api_query_params["$select"] = params.get("select", "id,name,displayName,webUrl,description")
    if params.get("top"): api_query_params["$top"] = params["top"]
    try:
        response_data = client.get(url, scope=getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE), params=api_query_params)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def create_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_params_safe = {k:v for k,v in params.items() if k != 'columnas'}
    logger.info("Ejecutando create_list (columnas omitido): %s", log_params_safe); action_name = "create_list"
    list_name: Optional[str] = params.get("nombre_lista")
    if not list_name: return _handle_graph_api_error(ValueError("'nombre_lista' es requerido."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists"
        body_payload: Dict[str, Any] = {"displayName": list_name, "list": {"template": params.get("template", "genericList")}}
        if params.get("columnas"): body_payload["columns"] = params["columnas"]
        response_obj = client.post(url, scope=getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=body_payload)
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def list_lists(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_lists con params: %s", params); action_name = "list_lists"
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url_base = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists"
        query_api_params_init: Dict[str, Any] = {
            '$top': min(int(params.get('top_per_page', 50)), getattr(settings, 'DEFAULT_PAGING_SIZE', 50)),
            '$select': params.get("select", "id,name,displayName,webUrl,list,createdDateTime,lastModifiedDateTime")
        }
        if params.get("filter_query"): query_api_params_init['$filter'] = params["filter_query"]
        if params.get("orderby"): query_api_params_init['$orderby'] = params["orderby"]
        if params.get("expand"): query_api_params_init['$expand'] = params["expand"]
        return _sp_paged_request(client, url_base, getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE), 
                                 params, query_api_params_init, params.get('max_items_total'), action_name)
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def get_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_list con params: %s", params); action_name = "get_list"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    if not list_id_or_name: return _handle_graph_api_error(ValueError("'lista_id_o_nombre' es requerido."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}"
        query_api_params: Dict[str, str] = {}
        query_api_params['$select'] = params.get("select", "id,name,displayName,description,webUrl,list,createdDateTime,lastModifiedDateTime,columns,contentTypes,items")
        if params.get("expand"): query_api_params['$expand'] = params["expand"]
        response_data = client.get(url, scope=getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE), params=query_api_params if query_api_params else None)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def update_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando update_list con params: %s", params); action_name = "update_list"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    update_payload: Optional[Dict[str, Any]] = params.get("update_payload")
    if not list_id_or_name or not update_payload or not isinstance(update_payload, dict): 
        return _handle_graph_api_error(ValueError("'lista_id_o_nombre' y 'update_payload' (dict) son requeridos."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}"
        response_obj = client.patch(url, scope=getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=update_payload)
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def delete_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando delete_list con params: %s", params); action_name = "delete_list"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    if not list_id_or_name: return _handle_graph_api_error(ValueError("'lista_id_o_nombre' es requerido."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}"
        response_obj = client.delete(url, scope=getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
        return {"status": "success", "message": f"Lista '{list_id_or_name}' eliminada.", "http_status": response_obj.status_code}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def add_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_params_safe = {k:v for k,v in params.items() if k != 'datos_campos'}
    logger.info("Ejecutando add_list_item (datos_campos omitido): %s", log_params_safe); action_name = "add_list_item"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    fields_data: Optional[Dict[str, Any]] = params.get("datos_campos")
    if not list_id_or_name or not fields_data or not isinstance(fields_data, dict): 
        return _handle_graph_api_error(ValueError("'lista_id_o_nombre' y 'datos_campos' (dict) son requeridos."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        body_payload = {"fields": fields_data}
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items"
        response_obj = client.post(url, scope=getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=body_payload)
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def list_list_items(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_list_items con params: %s", params); action_name = "list_list_items"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    if not list_id_or_name: return _handle_graph_api_error(ValueError("'lista_id_o_nombre' es requerido."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url_base = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items"
        query_api_params_init: Dict[str, Any] = {
            '$top': min(int(params.get('top_per_page', 50)), getattr(settings, 'DEFAULT_PAGING_SIZE', 50)),
            '$expand': params.get("expand", "fields(select=*)")
        }
        if params.get("select"): query_api_params_init["$select"] = params.get("select")
        if params.get("filter_query"): query_api_params_init["$filter"] = params.get("filter_query")
        if params.get("orderby"): query_api_params_init["$orderby"] = params.get("orderby")
        return _sp_paged_request(client, url_base, getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE), 
                                 params, query_api_params_init, params.get('max_items_total'), action_name)
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def get_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_list_item con params: %s", params); action_name = "get_list_item"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre"); item_id: Optional[str] = params.get("item_id")
    if not list_id_or_name or not item_id: return _handle_graph_api_error(ValueError("'lista_id_o_nombre' e 'item_id' requeridos."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items/{item_id}"
        query_api_params: Dict[str, str] = {'$expand': params.get("expand", "fields(select=*)")}
        if params.get("select"): query_api_params["$select"] = params.get("select")
        response_data = client.get(url, scope=getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE), params=query_api_params if query_api_params else None)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def update_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_params_safe = {k:v for k,v in params.items() if k != 'nuevos_valores_campos'}
    logger.info("Ejecutando update_list_item (nuevos_valores_campos omitido): %s", log_params_safe); action_name = "update_list_item"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre"); item_id: Optional[str] = params.get("item_id")
    fields_to_update: Optional[Dict[str, Any]] = params.get("nuevos_valores_campos")
    if not list_id_or_name or not item_id or not fields_to_update or not isinstance(fields_to_update, dict): 
        return _handle_graph_api_error(ValueError("'lista_id_o_nombre', 'item_id', y 'nuevos_valores_campos' (dict) requeridos."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items/{item_id}/fields"
        request_headers = {'If-Match': params.get("etag")} if params.get("etag") else {}
        response_obj = client.patch(url, scope=getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=fields_to_update, headers=request_headers)
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def delete_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando delete_list_item con params: %s", params); action_name = "delete_list_item"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre"); item_id: Optional[str] = params.get("item_id")
    if not list_id_or_name or not item_id: return _handle_graph_api_error(ValueError("'lista_id_o_nombre' e 'item_id' requeridos."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items/{item_id}"
        request_headers = {'If-Match': params.get("etag")} if params.get("etag") else {}
        response_obj = client.delete(url, scope=getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), headers=request_headers)
        return {"status": "success", "message": f"Item '{item_id}' eliminado.", "http_status": response_obj.status_code}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def search_list_items(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando search_list_items con params: %s", params); action_name = "search_list_items"
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre"); query_text: Optional[str] = params.get("query_text")
    if not list_id_or_name or not query_text: return _handle_graph_api_error(ValueError("'lista_id_o_nombre' y 'query_text' requeridos."), action_name, params)
    logger.warning("Función 'search_list_items' usa 'query_text' como $filter para list_list_items.")
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        list_items_params = {"site_id": target_site_id, "site_identifier": params.get("site_identifier", params.get("site_id")), 
                             "lista_id_o_nombre": list_id_or_name, "filter_query": query_text, 
                             "select": params.get("select"), "max_items_total": params.get("top"), "expand": params.get("expand", "fields(select=*)")}
        return list_list_items(client, list_items_params)
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def list_document_libraries(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_document_libraries con params: %s", params); action_name = "list_document_libraries"
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url_base = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/drives"
        query_api_params_init: Dict[str, Any] = {
            '$top': min(int(params.get('top_per_page', 50)), getattr(settings, 'DEFAULT_PAGING_SIZE', 50)),
            '$select': params.get("select", "id,name,displayName,description,webUrl,driveType,createdDateTime,lastModifiedDateTime,quota,owner"),
            '$filter': params.get("filter_query", "driveType eq 'documentLibrary'")
        }
        return _sp_paged_request(client, url_base, getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE),
                                 params, query_api_params_init, params.get('max_items_total'), action_name)
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def list_folder_contents(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_folder_contents con params: %s", params); action_name = "list_folder_contents"
    folder_path_or_id: str = params.get("folder_path_or_id", "")
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, params.get("drive_id_or_name"))
        is_folder_id = not ('/' in folder_path_or_id) and (len(folder_path_or_id) > 30 or '!' in folder_path_or_id or folder_path_or_id.startswith("driveItem_"))
        item_segment = f"items/{folder_path_or_id}" if is_folder_id else (f"root:/{folder_path_or_id.strip('/')}" if folder_path_or_id.strip('/') else "root")
        url_base = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/drives/{target_drive_id}/{item_segment}/children"
        query_api_params_init: Dict[str, Any] = {
            '$top': min(int(params.get('top_per_page', 50)), 200),
            '$select': params.get("select", "id,name,webUrl,size,createdDateTime,lastModifiedDateTime,file,folder,package,parentReference")
        }
        if params.get("expand"): query_api_params_init["$expand"] = params.get("expand")
        if params.get("orderby"): query_api_params_init["$orderby"] = params.get("orderby")
        return _sp_paged_request(client, url_base, getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE),
                                 params, query_api_params_init, params.get('max_items_total'), action_name)
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def get_file_metadata(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_file_metadata con params: %s", params); action_name = "get_file_metadata"
    item_id_or_path: Optional[str] = params.get("item_id_or_path")
    if not item_id_or_path: return _handle_graph_api_error(ValueError("'item_id_or_path' es requerido."),action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, params.get("drive_id_or_name"))
        is_item_id = not ('/' in item_id_or_path) and (len(item_id_or_path) > 30 or '!' in item_id_or_path or item_id_or_path.startswith("driveItem_"))
        base_url_item = _get_sp_item_endpoint_by_id(target_site_id, target_drive_id, item_id_or_path) if is_item_id else _get_sp_item_endpoint_by_path(target_site_id, target_drive_id, item_id_or_path)
        query_api_params: Dict[str, str] = {'$select': params.get("select", "id,name,webUrl,size,createdDateTime,lastModifiedDateTime,file,folder,package,parentReference,listItem,@microsoft.graph.downloadUrl")}
        if params.get("expand"): query_api_params["$expand"] = params.get("expand")
        
        response_data = client.get(base_url_item, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE), params=query_api_params if query_api_params else None)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def upload_document(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_params_safe = {k:v for k,v in params.items() if k != "content_bytes"}
    logger.info("Ejecutando upload_document (content_bytes omitido): %s", log_params_safe); action_name = "upload_document"
    filename: Optional[str] = params.get("filename"); content_bytes: Optional[bytes] = params.get("content_bytes")
    if not filename or content_bytes is None: return _handle_graph_api_error(ValueError("'filename' y 'content_bytes' requeridos."), action_name, params)
    if not isinstance(content_bytes, bytes): return _handle_graph_api_error(TypeError("'content_bytes' debe ser bytes."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, params.get("drive_id_or_name"))
        path_segment = params.get("folder_path", "").strip("/"); target_item_path = f"{path_segment}/{filename}" if path_segment else filename
        item_upload_base_url = _get_sp_item_endpoint_by_path(target_site_id, target_drive_id, target_item_path)
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)

        if len(content_bytes) <= 4 * 1024 * 1024:
            upload_url = f"{item_upload_base_url}/content"
            put_query_params = {"@microsoft.graph.conflictBehavior": params.get("conflict_behavior", "rename")}
            response_obj = client.put(upload_url, scope=files_rw_scope, data=content_bytes, headers={"Content-Type": "application/octet-stream"}, params=put_query_params)
            return {"status": "success", "data": response_obj.json(), "message": "Archivo subido (simple)."}
        else:
            session_url = f"{item_upload_base_url}/createUploadSession"
            session_body = {"item": {"@microsoft.graph.conflictBehavior": params.get("conflict_behavior", "rename"), "name": filename}}
            session_response_obj = client.post(session_url, scope=files_rw_scope, json_data=session_body)
            upload_session_data = session_response_obj.json()
            upload_url_session = upload_session_data.get("uploadUrl")
            if not upload_url_session: raise ValueError("No se pudo obtener 'uploadUrl' de la sesión.")
            
            # ... (Lógica de subida por chunks usando requests.put directamente) ...
            # Esta parte es compleja y usa 'requests' directamente, no client.put.
            # La dejaré como en tu ZIP original por ahora, ya que la corrección principal es para client.get().
            # Si esta parte también da errores, necesitaríamos revisarla específicamente.
            # Por brevedad, se omite la lógica detallada de chunks aquí. Se asume que estaba correcta o se corregirá por separado si falla.
            # El siguiente es un placeholder para la lógica de chunks:
            logger.info(f"Iniciando subida grande para {filename} a URL de sesión.")
            # --- INICIO LÓGICA CHUNKS (COPIADA Y SIMPLIFICADA DEL ZIP, PUEDE REQUERIR AJUSTES) ---
            file_size_bytes = len(content_bytes)
            chunk_size = 5 * 1024 * 1024; start_byte = 0; final_item_metadata = None
            while start_byte < file_size_bytes:
                end_byte = min(start_byte + chunk_size - 1, file_size_bytes - 1)
                current_chunk_data = content_bytes[start_byte : end_byte + 1]
                content_range_header = f"bytes {start_byte}-{end_byte}/{file_size_bytes}"
                chunk_headers = {'Content-Length': str(len(current_chunk_data)), 'Content-Range': content_range_header}
                chunk_resp = requests.put(upload_url_session, headers=chunk_headers, data=current_chunk_data, timeout=max(settings.DEFAULT_API_TIMEOUT, 180))
                chunk_resp.raise_for_status()
                start_byte = end_byte + 1
                if chunk_resp.content and chunk_resp.status_code in [200, 201]:
                    final_item_metadata = chunk_resp.json(); break
            if not final_item_metadata and start_byte >= file_size_bytes: # Verificar si se subió
                 check_params = {"site_id": target_site_id, "drive_id_or_name": target_drive_id, "item_id_or_path": target_item_path}
                 if params.get("site_identifier"): check_params["site_identifier"] = params["site_identifier"]
                 check_meta = get_file_metadata(client, check_params)
                 if check_meta.get("status") == "success": final_item_metadata = check_meta["data"]
                 else: return {"status": "warning", "message": "Subida con sesión, verificación falló.", "details": check_meta}
            if not final_item_metadata: raise ValueError("Subida grande finalizada pero sin metadata.")
            return {"status": "success", "data": final_item_metadata, "message": "Archivo subido con sesión."}
            # --- FIN LÓGICA CHUNKS ---
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def download_document(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[bytes, Dict[str, Any]]:
    params = params or {}; logger.info("Ejecutando download_document con params: %s", params); action_name = "download_document"
    item_id_or_path: Optional[str] = params.get("item_id_or_path")
    if not item_id_or_path: return _handle_graph_api_error(ValueError("'item_id_or_path' es requerido."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, params.get("drive_id_or_name"))
        item_actual_id_result = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, target_site_id, target_drive_id, params)
        if isinstance(item_actual_id_result, dict) and item_actual_id_result.get("status") == "error": return item_actual_id_result
        item_actual_id = str(item_actual_id_result)
        url_content = f"{_get_sp_item_endpoint_by_id(target_site_id, target_drive_id, item_actual_id)}/content"
        
        # client.get con stream=True devuelve bytes directamente
        file_bytes = client.get(url_content, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE), stream=True)
        if not isinstance(file_bytes, bytes): # Si client.get devolvió un error formateado como dict o str
            if isinstance(file_bytes, dict) and file_bytes.get("status") == "error": return file_bytes # Propagar error
            raise Exception(f"Respuesta inesperada para descarga, se esperaban bytes. Recibido: {type(file_bytes)}")
        return file_bytes
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def delete_document(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Ejecutando delete_document (alias de delete_item) con params: %s", params)
    return delete_item(client, params) # Es un alias

def delete_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando delete_item con params: %s", params); action_name = "delete_item"
    item_id_or_path: Optional[str] = params.get("item_id_or_path")
    if not item_id_or_path: return _handle_graph_api_error(ValueError("'item_id_or_path' es requerido."),action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, params.get("drive_id_or_name"))
        item_actual_id_result = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, target_site_id, target_drive_id, params)
        if isinstance(item_actual_id_result, dict) and item_actual_id_result.get("status") == "error": return item_actual_id_result
        item_actual_id = str(item_actual_id_result)
        url_item = _get_sp_item_endpoint_by_id(target_site_id, target_drive_id, item_actual_id)
        request_headers = {'If-Match': params.get("etag")} if params.get("etag") else {}
        response_obj = client.delete(url_item, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), headers=request_headers)
        return {"status": "success", "message": f"Item '{item_actual_id}' eliminado.", "http_status": response_obj.status_code}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def create_folder(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando create_folder con params: %s", params); action_name = "create_folder"
    folder_name: Optional[str] = params.get("folder_name")
    if not folder_name: return _handle_graph_api_error(ValueError("'folder_name' es requerido."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, params.get("drive_id_or_name"))
        parent_folder_path_or_id: str = params.get("parent_folder_path_or_id", "")
        parent_is_id = not ('/' in parent_folder_path_or_id) and (len(parent_folder_path_or_id) > 30 or '!' in parent_folder_path_or_id or parent_folder_path_or_id.startswith("driveItem_"))
        parent_endpoint = _get_sp_item_endpoint_by_id(target_site_id, target_drive_id, parent_folder_path_or_id) if parent_is_id else _get_sp_item_endpoint_by_path(target_site_id, target_drive_id, parent_folder_path_or_id)
        url_create_folder = f"{parent_endpoint}/children"
        body_payload = {"name": folder_name, "folder": {}, "@microsoft.graph.conflictBehavior": params.get("conflict_behavior", "fail")}
        response_obj = client.post(url_create_folder, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=body_payload)
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def move_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando move_item con params: %s", params); action_name = "move_item"
    item_id_or_path: Optional[str] = params.get("item_id_or_path"); target_parent_folder_id: Optional[str] = params.get("target_parent_folder_id")
    if not item_id_or_path or not target_parent_folder_id: return _handle_graph_api_error(ValueError("'item_id_or_path' y 'target_parent_folder_id' requeridos."), action_name, params)
    try:
        source_site_id_resolved = _obtener_site_id_sp(client, params)
        source_drive_id_resolved = _get_drive_id(client, source_site_id_resolved, params.get("source_drive_id_or_name") or params.get("drive_id_or_name"))
        item_actual_id_result = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, source_site_id_resolved, source_drive_id_resolved, params)
        if isinstance(item_actual_id_result, dict) and item_actual_id_result.get("status") == "error": return item_actual_id_result
        item_actual_id = str(item_actual_id_result)
        url_patch_item = _get_sp_item_endpoint_by_id(source_site_id_resolved, source_drive_id_resolved, item_actual_id)
        payload_move: Dict[str, Any] = {"parentReference": {"id": target_parent_folder_id}}
        if params.get("target_drive_id"): payload_move["parentReference"]["driveId"] = params["target_drive_id"]
        if params.get("target_site_id"): payload_move["parentReference"]["siteId"] = params["target_site_id"] # Asumir que es un ID válido
        if params.get("new_name"): payload_move["name"] = params["new_name"]
        response_obj = client.patch(url_patch_item, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=payload_move)
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def copy_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando copy_item con params: %s", params); action_name = "copy_item"
    item_id_or_path: Optional[str] = params.get("item_id_or_path"); target_parent_folder_id: Optional[str] = params.get("target_parent_folder_id")
    if not item_id_or_path or not target_parent_folder_id: return _handle_graph_api_error(ValueError("'item_id_or_path' y 'target_parent_folder_id' requeridos."), action_name, params)
    try:
        source_site_id_resolved = _obtener_site_id_sp(client, {"site_id": params.get("source_site_id"), **params} if params.get("source_site_id") else params)
        source_drive_id_resolved = _get_drive_id(client, source_site_id_resolved, params.get("source_drive_id_or_name"))
        item_actual_id_result = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, source_site_id_resolved, source_drive_id_resolved, params)
        if isinstance(item_actual_id_result, dict) and item_actual_id_result.get("status") == "error": return item_actual_id_result
        item_actual_id = str(item_actual_id_result)
        url_copy_action = f"{_get_sp_item_endpoint_by_id(source_site_id_resolved, source_drive_id_resolved, item_actual_id)}/copy"
        parent_reference_payload: Dict[str, str] = {"id": target_parent_folder_id}
        if params.get("target_drive_id"): parent_reference_payload["driveId"] = params["target_drive_id"]
        if params.get("target_site_id"): parent_reference_payload["siteId"] = _obtener_site_id_sp(client, {"site_id": params["target_site_id"], **params}) # Resolver sitio destino
        elif params.get("target_drive_id"): parent_reference_payload["siteId"] = source_site_id_resolved # Asumir mismo sitio si solo se da drive destino
        body_payload: Dict[str, Any] = {"parentReference": parent_reference_payload}
        if params.get("new_name"): body_payload["name"] = params["new_name"]
        response_obj = client.post(url_copy_action, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=body_payload)
        if response_obj.status_code == 202: return {"status": "pending", "message": "Copia en progreso.", "monitor_url": response_obj.headers.get("Location"), "data": response_obj.json() if response_obj.content else {}, "http_status": 202}
        return {"status": "success", "data": response_obj.json(), "message": "Item copiado (síncrono)."}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def update_file_metadata(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_params_safe = {k:v for k,v in params.items() if k != 'metadata_updates'}
    logger.info("Ejecutando update_file_metadata (metadata_updates omitido): %s", log_params_safe); action_name = "update_file_metadata"
    item_id_or_path: Optional[str] = params.get("item_id_or_path"); metadata_updates_payload: Optional[Dict[str, Any]] = params.get("metadata_updates")
    if not item_id_or_path or not metadata_updates_payload or not isinstance(metadata_updates_payload, dict): 
        return _handle_graph_api_error(ValueError("'item_id_or_path' y 'metadata_updates' (dict) requeridos."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, params.get("drive_id_or_name"))
        item_actual_id_result = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, target_site_id, target_drive_id, params)
        if isinstance(item_actual_id_result, dict) and item_actual_id_result.get("status") == "error": return item_actual_id_result
        item_actual_id = str(item_actual_id_result)
        url_update = _get_sp_item_endpoint_by_id(target_site_id, target_drive_id, item_actual_id)
        request_headers = {'If-Match': params.get("etag")} if params.get("etag") else {}
        response_obj = client.patch(url_update, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=metadata_updates_payload, headers=request_headers)
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def get_sharing_link(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_params_safe = {k:v for k,v in params.items() if k != 'password'}
    logger.info("Ejecutando get_sharing_link (password omitido): %s", log_params_safe); action_name = "get_sharing_link"
    item_id_or_path: Optional[str] = params.get("item_id_or_path")
    if not item_id_or_path: return _handle_graph_api_error(ValueError("'item_id_or_path' es requerido."), action_name, params)
    scope_param: str = params.get("scope", "organization")
    if scope_param == "users" and not params.get("recipients"): return _handle_graph_api_error(ValueError("Si scope es 'users', 'recipients' es requerido."),action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, params.get("drive_id_or_name"))
        item_actual_id_result = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, target_site_id, target_drive_id, params)
        if isinstance(item_actual_id_result, dict) and item_actual_id_result.get("status") == "error": return item_actual_id_result
        item_actual_id = str(item_actual_id_result)
        url_action_createlink = f"{_get_sp_item_endpoint_by_id(target_site_id, target_drive_id, item_actual_id)}/createLink"
        body_payload_link: Dict[str, Any] = {"type": params.get("type", "view"), "scope": scope_param}
        if params.get("password"): body_payload_link["password"] = params["password"]
        if params.get("expirationDateTime"): body_payload_link["expirationDateTime"] = params["expirationDateTime"]
        if scope_param == "users" and params.get("recipients"): body_payload_link["recipients"] = params["recipients"]
        response_obj = client.post(url_action_createlink, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=body_payload_link)
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def list_item_permissions(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_item_permissions: %s", params); action_name = "list_item_permissions"
    item_id_or_path = params.get("item_id_or_path"); list_id_o_nombre = params.get("list_id_o_nombre"); list_item_id_param = params.get("list_item_id")
    if not item_id_or_path and not (list_id_o_nombre and list_item_id_param): 
        return _handle_graph_api_error(ValueError("Identificador de item (DriveItem o ListItem) requerido."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params); url_item_permissions: str
        if item_id_or_path:
            target_drive_id = _get_drive_id(client, target_site_id, params.get("drive_id_or_name"))
            item_actual_id_result = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, target_site_id, target_drive_id, params)
            if isinstance(item_actual_id_result, dict) and item_actual_id_result.get("status") == "error": return item_actual_id_result
            url_item_permissions = f"{_get_sp_item_endpoint_by_id(target_site_id, target_drive_id, str(item_actual_id_result))}/permissions"
        else:
            if not list_id_o_nombre or not list_item_id_param: return _handle_graph_api_error(ValueError("Para ListItems, 'list_id_o_nombre' y 'list_item_id' requeridos."),action_name, params)
            url_item_permissions = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_o_nombre}/items/{list_item_id_param}/permissions"
        
        response_data = client.get(url_item_permissions, scope=getattr(settings, 'GRAPH_SCOPE_SITES_FULLCONTROL_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def add_item_permissions(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_params_safe = {k:v for k,v in params.items() if k != 'recipients'}
    logger.info("Ejecutando add_item_permissions (recipients omitido): %s", log_params_safe); action_name = "add_item_permissions"
    item_id_or_path = params.get("item_id_or_path"); list_id_o_nombre = params.get("list_id_o_nombre"); list_item_id = params.get("list_item_id")
    recipients_payload: Optional[List[Dict[str,Any]]] = params.get("recipients"); roles_payload: Optional[List[str]] = params.get("roles")
    if (not item_id_or_path and not (list_id_o_nombre and list_item_id)) or not recipients_payload or not roles_payload: 
        return _handle_graph_api_error(ValueError("Identificador de item, 'recipients', y 'roles' obligatorios."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params); url_action_invite: str
        body_invite_payload: Dict[str, Any] = {"recipients": recipients_payload, "roles": roles_payload, 
                                             "requireSignIn": params.get("requireSignIn", True), "sendInvitation": params.get("sendInvitation", True)}
        if params.get("message"): body_invite_payload["message"] = params["message"]
        if params.get("expirationDateTime"): body_invite_payload["expirationDateTime"] = params["expirationDateTime"]
        if item_id_or_path:
            target_drive_id = _get_drive_id(client, target_site_id, params.get("drive_id_or_name"))
            item_actual_id_result = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, target_site_id, target_drive_id, params)
            if isinstance(item_actual_id_result, dict) and item_actual_id_result.get("status") == "error": return item_actual_id_result
            url_action_invite = f"{_get_sp_item_endpoint_by_id(target_site_id, target_drive_id, str(item_actual_id_result))}/invite"
        else:
            if not list_id_o_nombre or not list_item_id: return _handle_graph_api_error(ValueError("Para ListItems, 'list_id_o_nombre' y 'list_item_id' requeridos."),action_name, params)
            url_action_invite = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_o_nombre}/items/{list_item_id}/invite"
        response_obj = client.post(url_action_invite, scope=getattr(settings, 'GRAPH_SCOPE_SITES_FULLCONTROL_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=body_invite_payload)
        return {"status": "success", "data": response_obj.json().get("value", []), "message": "Permisos añadidos/actualizados."}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def remove_item_permissions(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando remove_item_permissions: %s", params); action_name = "remove_item_permissions"
    item_id_or_path = params.get("item_id_or_path"); list_id_o_nombre = params.get("list_id_o_nombre"); list_item_id = params.get("list_item_id")
    permission_id: Optional[str] = params.get("permission_id")
    if (not item_id_or_path and not (list_id_o_nombre and list_item_id)) or not permission_id: 
        return _handle_graph_api_error(ValueError("Identificador de item y 'permission_id' obligatorios."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params); url_delete_perm: str
        if item_id_or_path:
            target_drive_id = _get_drive_id(client, target_site_id, params.get("drive_id_or_name"))
            item_actual_id_result = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, target_site_id, target_drive_id, params)
            if isinstance(item_actual_id_result, dict) and item_actual_id_result.get("status") == "error": return item_actual_id_result
            url_delete_perm = f"{_get_sp_item_endpoint_by_id(target_site_id, target_drive_id, str(item_actual_id_result))}/permissions/{permission_id}"
        else:
            if not list_id_o_nombre or not list_item_id: return _handle_graph_api_error(ValueError("Para ListItems, 'list_id_o_nombre' y 'list_item_id' requeridos."),action_name, params)
            url_delete_perm = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_o_nombre}/items/{list_item_id}/permissions/{permission_id}"
        response_obj = client.delete(url_delete_perm, scope=getattr(settings, 'GRAPH_SCOPE_SITES_FULLCONTROL_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
        return {"status": "success", "message": f"Permiso '{permission_id}' eliminado.", "http_status": response_obj.status_code}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

MEMORIA_LIST_NAME_FROM_SETTINGS = settings.MEMORIA_LIST_NAME

def _ensure_memory_list_exists(client: AuthenticatedHttpClient, site_id: str) -> bool:
    try:
        url_get_list = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/lists/{MEMORIA_LIST_NAME_FROM_SETTINGS}?$select=id"
        try:
            response_data = client.get(url_get_list, scope=getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
            if isinstance(response_data, dict) and response_data.get("id"): return True # La lista existe
            # Si no es dict o no tiene id, o es un error formateado, podría no existir o haber un problema
            if isinstance(response_data, dict) and response_data.get("status") == "error" and response_data.get("http_status") == 404:
                pass # Continuar para crearla
            elif isinstance(response_data, dict) and response_data.get("status") == "error": # Otro error
                raise Exception(f"Error verificando lista memoria: {response_data.get('message')}")
            elif not isinstance(response_data, dict): # Respuesta inesperada
                 raise Exception(f"Respuesta inesperada verificando lista memoria: {type(response_data)}")

        except requests.exceptions.HTTPError as http_err:
            if http_err.response is not None and http_err.response.status_code == 404: pass # Lista no existe, proceder a crear
            else: raise 
        
        columnas_default = [{"name": "SessionID", "text": {}}, {"name": "Clave", "text": {}}, 
                            {"name": "Valor", "text": {"allowMultipleLines": True, "textType": "plain"}}, 
                            {"name": "Timestamp", "dateTime": {"displayAs": "default", "format": "dateTime"}}]
        creation_response = create_list(client, {"site_id": site_id, "nombre_lista": MEMORIA_LIST_NAME_FROM_SETTINGS, "columnas": columnas_default})
        return creation_response.get("status") == "success"
    except Exception as e: logger.error(f"Error crítico asegurando lista memoria: {e}", exc_info=True); return False

def memory_ensure_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando memory_ensure_list: %s", params); action_name = "memory_ensure_list"
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        if _ensure_memory_list_exists(client, target_site_id): 
            return {"status": "success", "message": f"Lista memoria '{MEMORIA_LIST_NAME_FROM_SETTINGS}' asegurada."}
        else: return {"status": "error", "action": action_name, "message": "No se pudo asegurar/crear la lista memoria."}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def memory_save(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_params_safe = {k:v for k,v in params.items() if k != 'valor'}
    logger.info("Ejecutando memory_save (valor omitido): %s", log_params_safe); action_name = "memory_save"
    session_id = params.get("session_id"); clave = params.get("clave"); valor = params.get("valor")
    if not session_id or not clave or valor is None: return _handle_graph_api_error(ValueError("'session_id', 'clave', y 'valor' requeridos."),action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        if not _ensure_memory_list_exists(client, target_site_id): return {"status": "error", "message": "No se pudo asegurar lista memoria."}
        valor_str = json.dumps(valor)
        list_params = {"site_id": target_site_id, "site_identifier": params.get("site_identifier", params.get("site_id")), 
                       "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, 
                       "filter_query": f"fields/SessionID eq '{session_id}' and fields/Clave eq '{clave}'", 
                       "top_per_page": 1, "max_items_total": 1, "select": "id"}
        existing_items_response = list_list_items(client, list_params)
        item_id_to_update: Optional[str] = None
        if existing_items_response.get("status") == "success" and existing_items_response.get("data", {}).get("value"):
            item_id_to_update = existing_items_response["data"]["value"][0].get("id")
        
        datos_campos_payload = {"SessionID": session_id, "Clave": clave, "Valor": valor_str, "Timestamp": _get_current_timestamp_iso_z()}
        if item_id_to_update:
            return update_list_item(client, {"site_id": target_site_id, "site_identifier": params.get("site_identifier", params.get("site_id")),
                                           "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, "item_id": item_id_to_update, 
                                           "nuevos_valores_campos": datos_campos_payload})
        else:
            return add_list_item(client, {"site_id": target_site_id, "site_identifier": params.get("site_identifier", params.get("site_id")),
                                        "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, "datos_campos": datos_campos_payload})
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def memory_get(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando memory_get: %s", params); action_name = "memory_get"
    session_id = params.get("session_id"); clave = params.get("clave")
    if not session_id: return _handle_graph_api_error(ValueError("'session_id' es requerido."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        filter_parts = [f"fields/SessionID eq '{session_id}'"]; log_detail = f"SessionID: '{session_id}'"
        if clave: filter_parts.append(f"fields/Clave eq '{clave}'"); log_detail += f", Clave: '{clave}'"
        list_params = {"site_id": target_site_id, "site_identifier": params.get("site_identifier", params.get("site_id")),
                       "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, "filter_query": " and ".join(filter_parts), 
                       "expand": "fields(select=Clave,Valor,Timestamp)", "orderby": "fields/Timestamp desc", 
                       "max_items_total": None if not clave else 1}
        items_response = list_list_items(client, list_params)
        if items_response.get("status") != "success": return items_response
        retrieved_data: Any = {} if not clave else None; items = items_response.get("data", {}).get("value", [])
        if not items: return {"status": "success", "data": retrieved_data, "message": "No se encontró data en memoria."}
        if clave:
            valor_str = items[0].get("fields", {}).get("Valor")
            try: retrieved_data = json.loads(valor_str) if valor_str else None
            except json.JSONDecodeError: retrieved_data = valor_str
        else:
            for item in items:
                item_fields = item.get("fields", {}); current_clave = item_fields.get("Clave"); valor_str = item_fields.get("Valor")
                if current_clave and current_clave not in retrieved_data:
                    try: retrieved_data[current_clave] = json.loads(valor_str) if valor_str else None
                    except json.JSONDecodeError: retrieved_data[current_clave] = valor_str
        return {"status": "success", "data": retrieved_data}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def memory_delete(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando memory_delete: %s", params); action_name = "memory_delete"
    session_id = params.get("session_id"); clave = params.get("clave")
    if not session_id: return _handle_graph_api_error(ValueError("'session_id' es requerido."),action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        filter_parts = [f"fields/SessionID eq '{session_id}'"]; log_detail = f"sesión '{session_id}'"
        if clave: filter_parts.append(f"fields/Clave eq '{clave}'"); log_detail = f"clave '{clave}' de sesión '{session_id}'"
        list_params = {"site_id": target_site_id, "site_identifier": params.get("site_identifier", params.get("site_id")),
                       "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, "filter_query": " and ".join(filter_parts), "select": "id"}
        items_to_delete_resp = list_list_items(client, list_params)
        if items_to_delete_resp.get("status") != "success": return items_to_delete_resp
        items = items_to_delete_resp.get("data", {}).get("value", [])
        if not items: return {"status": "success", "message": f"No se encontró {log_detail} para eliminar."}
        deleted_count = 0; errors_on_delete: List[str] = []
        for item in items:
            item_id_to_del = item.get("id")
            if item_id_to_del:
                del_response = delete_list_item(client, {"site_id": target_site_id, "site_identifier": params.get("site_identifier", params.get("site_id")), 
                                                       "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, "item_id": item_id_to_del})
                if del_response.get("status") == "success": deleted_count += 1
                else: errors_on_delete.append(f"Error eliminando ID {item_id_to_del}: {del_response.get('message')}")
        if errors_on_delete: return {"status": "partial_error", "message": f"{deleted_count} items eliminados, {len(errors_on_delete)} errores.", "details": errors_on_delete}
        return {"status": "success", "message": f"Memoria para {log_detail} eliminada. {deleted_count} items borrados."}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def memory_list_keys(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando memory_list_keys: %s", params); action_name = "memory_list_keys"
    session_id: Optional[str] = params.get("session_id")
    if not session_id: return _handle_graph_api_error(ValueError("'session_id' es requerido."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        list_params = {"site_id": target_site_id, "site_identifier": params.get("site_identifier", params.get("site_id")),
                       "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, "filter_query": f"fields/SessionID eq '{session_id}'", 
                       "expand": "fields(select=Clave)"}
        items_response = list_list_items(client, list_params)
        if items_response.get("status") != "success": return items_response
        keys: List[str] = list(set(item.get("fields", {}).get("Clave") for item in items_response.get("data", {}).get("value", []) if item.get("fields", {}).get("Clave")))
        return {"status": "success", "data": sorted(keys)}
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

def memory_export_session(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
    params = params or {}; logger.info("Ejecutando memory_export_session: %s", params); action_name = "memory_export_session"
    session_id: Optional[str] = params.get("session_id"); export_format: str = params.get("format", "json").lower()
    if not session_id: return _handle_graph_api_error(ValueError("'session_id' es requerido."), action_name, params)
    if export_format not in ["json", "csv"]: return _handle_graph_api_error(ValueError("Formato debe ser 'json' o 'csv'."), action_name, params)
    export_params = {"site_id": params.get("site_id"), "site_identifier": params.get("site_identifier", params.get("site_id")),
                     "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, "format": export_format,
                     "filter_query": f"fields/SessionID eq '{session_id}'", "select_fields": "SessionID,Clave,Valor,Timestamp"}
    return sp_export_list_to_format(client, export_params) # Esta función ya maneja la respuesta

def sp_export_list_to_format(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
    params = params or {}; logger.info("Ejecutando sp_export_list_to_format: %s", params); action_name = "sp_export_list_to_format"
    lista_id_o_nombre: Optional[str] = params.get("lista_id_o_nombre"); export_format: str = params.get("format", "json").lower()
    if not lista_id_o_nombre: return _handle_graph_api_error(ValueError("'lista_id_o_nombre' es requerido."), action_name, params)
    if export_format not in ["json", "csv"]: return _handle_graph_api_error(ValueError("Formato debe ser 'json' o 'csv'."), action_name, params)
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        list_items_params: Dict[str, Any] = {"site_id": target_site_id, "site_identifier": params.get("site_identifier", params.get("site_id")),
                                             "lista_id_o_nombre": lista_id_o_nombre, "max_items_total": params.get('max_items_total')}
        if params.get("filter_query"): list_items_params["filter_query"] = params["filter_query"]
        expand_val = f"fields(select={params['select_fields']})" if params.get("select_fields") else "fields(select=*)"
        list_items_params["expand"] = expand_val
        list_items_params["select"] = "id,@odata.etag,createdBy,createdDateTime,lastModifiedBy,lastModifiedDateTime,webUrl"
        
        items_response = list_list_items(client, list_items_params)
        if items_response.get("status") != "success": return items_response
            
        items_data = items_response.get("data", {}).get("value", [])
        processed_items: List[Dict[str, Any]] = []
        if items_data:
            for item in items_data:
                fields = item.get("fields", {})
                fields["_ListItemID_"] = item.get("id"); fields["_ListItemETag_"] = item.get("@odata.etag")
                fields["_ListItemWebUrl_"] = item.get("webUrl")
                fields["_ListItemCreatedDateTime_"] = item.get("createdDateTime"); fields["_ListItemLastModifiedDateTime_"] = item.get("lastModifiedDateTime")
                try: fields["_ListItemCreatedBy_"] = item.get("createdBy", {}).get("user", {}).get("displayName")
                except: pass
                try: fields["_ListItemLastModifiedBy_"] = item.get("lastModifiedBy", {}).get("user", {}).get("displayName")
                except: pass
                processed_items.append(fields)
        
        if not processed_items: return {"status": "success", "data": []} if export_format == "json" else ""
        if export_format == "json": return {"status": "success", "data": processed_items}
        
        # CSV export
        output = StringIO(); all_field_keys = set().union(*(d.keys() for d in processed_items))
        meta_keys = [k for k in ["_ListItemID_", "_ListItemETag_", "_ListItemWebUrl_", "_ListItemCreatedDateTime_", "_ListItemCreatedBy_", "_ListItemLastModifiedDateTime_", "_ListItemLastModifiedBy_"] if k in all_field_keys]
        final_fieldnames = meta_keys + sorted(list(all_field_keys - set(meta_keys)))
        writer = csv.DictWriter(output, fieldnames=final_fieldnames, extrasaction='ignore', quoting=csv.QUOTE_ALL)
        writer.writeheader(); writer.writerows(processed_items)
        csv_content = output.getvalue(); output.close()
        return csv_content 
    except Exception as e: return _handle_graph_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/sharepoint_actions.py ---