# app/actions/sharepoint_actions.py
import logging
import requests
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
    is_graph_path_segment_format = site_id_string.startswith('sites/') and '{' in site_id_string and '}' in site_id_string
    is_root_keyword = site_id_string.lower() == "root"
    is_guid_like = len(site_id_string) == 36 and site_id_string.count('-') == 4
    return is_composite_id or is_server_relative_path_format or is_graph_path_segment_format or is_root_keyword or is_guid_like

# --- Helper Interno para Obtener Site ID (versión robusta) ---
def _obtener_site_id_sp(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> str:
    # Esta función es interna, el logger.info principal debe estar en la función pública que la llama si es necesario.
    # params ya debería ser un dict (params or {} hecho en la pública).
    site_input: Optional[str] = params.get("site_id") or params.get("site_identifier")
    sharepoint_default_site_id_from_settings = getattr(settings, 'SHAREPOINT_DEFAULT_SITE_ID', None)

    if site_input:
        if _is_valid_graph_site_id_format(site_input):
            logger.debug(f"SP Site ID con formato Graph reconocido: '{site_input}'.")
            return site_input
        lookup_path = site_input
        if not ':' in site_input and (site_input.startswith("/sites/") or site_input.startswith("/teams/")):
             try:
                 sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
                 root_site_info_resp = client.get(f"{settings.GRAPH_API_BASE_URL}/sites/root?$select=siteCollection", scope=sites_read_scope)
                 
                 # --- CORRECCIÓN ---
                 # `client.get` ya devuelve un dict. Se elimina `.json()`.
                 root_site_hostname = root_site_info_resp.get("siteCollection", {}).get("hostname")

                 if root_site_hostname:
                     lookup_path = f"{root_site_hostname}:{site_input}"
                     logger.info(f"SP Path relativo '{site_input}' convertido a: '{lookup_path}' para búsqueda de ID.")
             except Exception as e_root_host:
                 logger.warning(f"Error obteniendo hostname para SP path relativo '{site_input}': {e_root_host}. Se usará el path original para lookup.")
        
        url_lookup = f"{settings.GRAPH_API_BASE_URL}/sites/{lookup_path}?$select=id,displayName,webUrl,siteCollection"
        logger.debug(f"Intentando obtener SP Site ID para el identificador/path: '{lookup_path}'")
        try:
            sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
            response = client.get(url_lookup, scope=sites_read_scope)

            # --- CORRECCIÓN ---
            site_data = response; resolved_site_id = site_data.get("id")

            if resolved_site_id:
                logger.info(f"SP Site ID resuelto para input '{site_input}' (usando lookup path '{lookup_path}'): '{resolved_site_id}' (Nombre: {site_data.get('displayName')})")
                return resolved_site_id
        except Exception as e:
            logger.warning(f"Error buscando SP sitio por '{lookup_path}': {e}. Intentando fallback si no se encontró Site ID.")

    if sharepoint_default_site_id_from_settings and _is_valid_graph_site_id_format(sharepoint_default_site_id_from_settings):
        logger.debug(f"Usando SP Site ID por defecto de settings: '{sharepoint_default_site_id_from_settings}' como fallback.")
        return sharepoint_default_site_id_from_settings

    url_root_site = f"{settings.GRAPH_API_BASE_URL}/sites/root?$select=id,displayName"
    logger.debug(f"Ningún Site ID provisto o resuelto. Intentando obtener SP sitio raíz como fallback final.")
    try:
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_root = client.get(url_root_site, scope=sites_read_scope)

        # --- CORRECCIÓN ---
        root_site_data = response_root; root_site_id = root_site_data.get("id")

        if root_site_id:
            logger.info(f"Usando SP Site ID raíz como fallback final: '{root_site_id}' (Nombre: {root_site_data.get('displayName')})")
            return root_site_id
    except Exception as e_root:
        raise ValueError(f"Fallo CRÍTICO al obtener SP Site ID. No se pudo resolver ni obtener el sitio raíz. Error: {e_root}")
    raise ValueError("No se pudo determinar SP Site ID. Verifique el parámetro 'site_id'/'site_identifier' o la configuración de SHAREPOINT_DEFAULT_SITE_ID.")

# --- Helper Interno para Obtener Drive ID ---
def _get_drive_id(client: AuthenticatedHttpClient, site_id: str, drive_id_or_name_input: Optional[str] = None) -> str:
    sharepoint_default_drive_name = getattr(settings, 'SHAREPOINT_DEFAULT_DRIVE_ID_OR_NAME', 'Documents')
    target_drive_identifier = drive_id_or_name_input or sharepoint_default_drive_name
    
    if not target_drive_identifier: 
        raise ValueError("Se requiere un nombre o ID de Drive para operar (parámetro 'drive_id_or_name' o config SHAREPOINT_DEFAULT_DRIVE_ID_OR_NAME).")

    is_likely_id = '!' in target_drive_identifier or \
                   (len(target_drive_identifier) > 30 and not any(c in target_drive_identifier for c in [' ', '/'])) or \
                   target_drive_identifier.startswith("b!") # Formato común de Drive ID
    
    files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    
    if is_likely_id:
        logger.debug(f"Asumiendo que '{target_drive_identifier}' es un Drive ID. Intentando verificar.")
        url_drive_by_id = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{target_drive_identifier}?$select=id,name"
        try:
            response = client.get(url_drive_by_id, scope=files_read_scope)
            
            # --- CORRECCIÓN ---
            drive_data = response; drive_id = drive_data.get("id")

            if drive_id: 
                logger.info(f"Drive ID '{drive_id}' verificado para sitio '{site_id}'.")
                return drive_id
        except Exception as e: 
            logger.warning(f"Error obteniendo SP Drive por ID '{target_drive_identifier}' para sitio '{site_id}': {e}. Procediendo a buscar por nombre.")

    logger.debug(f"Buscando Drive por nombre/displayName '{target_drive_identifier}' en sitio '{site_id}'.")
    url_list_drives = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives?$select=id,name,displayName,webUrl"
    try:
        response_drives = client.get(url_list_drives, scope=files_read_scope)
        
        # --- CORRECCIÓN ---
        drives_list = response_drives.get("value", [])

        for drive_obj in drives_list:
            if drive_obj.get("name", "").lower() == target_drive_identifier.lower() or \
               drive_obj.get("displayName", "").lower() == target_drive_identifier.lower():
                drive_id = drive_obj.get("id")
                if drive_id: 
                    logger.info(f"Drive ID '{drive_id}' (Nombre: {drive_obj.get('name')}, DisplayName: {drive_obj.get('displayName')}) encontrado para sitio '{site_id}'.")
                    return drive_id
        raise ValueError(f"SP Drive con nombre/displayName '{target_drive_identifier}' no encontrado en sitio '{site_id}'. Drives disponibles: {[d.get('name') for d in drives_list]}")
    except Exception as e_list: 
        raise ConnectionError(f"Error obteniendo lista de Drives para sitio '{site_id}' para resolver '{target_drive_identifier}': {e_list}") from e_list

def _get_sp_item_endpoint_by_path(site_id: str, drive_id: str, item_path: str) -> str:
    safe_path = item_path.strip()
    if not safe_path or safe_path == '/': 
        return f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/root"
    if safe_path.startswith('/'): 
        safe_path = safe_path[1:]
    # Asegurar que el path está correctamente encodeado para la URL si tiene caracteres especiales
    # La librería requests usualmente maneja esto para params, pero aquí es parte del path.
    # El http_client.request debería manejar la URL final, así que no se requiere quote aquí.
    return f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/root:/{safe_path}"

def _get_sp_item_endpoint_by_id(site_id: str, drive_id: str, item_id: str) -> str:
    return f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/items/{item_id}"

def _handle_graph_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en SharePoint action '{action_name}'"
    safe_params = {} # Inicializar safe_params
    if params_for_log:
        # Definir claves sensibles a omitir del log
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
    max_pages_to_fetch = getattr(settings, 'MAX_PAGING_PAGES', 20)
    top_value_initial = query_api_params_initial.get('$top', getattr(settings, 'DEFAULT_PAGING_SIZE', 50))
    
    # El logger.info principal ya se hizo en la función llamante
    logger.debug(f"Iniciando solicitud paginada SP para '{action_name_for_log}' desde '{url_base.split('?')[0]}...'. Max total: {max_items_total or 'todos'}, por pág: {top_value_initial}, max_págs: {max_pages_to_fetch}")
    try:
        while current_url and (max_items_total is None or len(all_items) < max_items_total) and page_count < max_pages_to_fetch:
            page_count += 1
            is_first_call = (page_count == 1 and current_url == url_base)
            current_params = query_api_params_initial if is_first_call else None
            
            logger.debug(f"Página SP {page_count} para '{action_name_for_log}': GET {current_url.split('?')[0]} con params: {current_params}")
            response = client.get(url=current_url, scope=scope, params=current_params)

            # --- CORRECCIÓN ---
            response_data = response

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): 
                logger.warning(f"Respuesta paginada SP inesperada, 'value' no es lista: {response_data}")
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

def _get_item_id_from_path_if_needed_sp(
    client: AuthenticatedHttpClient, item_path_or_id: str,
    site_id: str, drive_id: str,
    # params_for_metadata es el dict de params ORIGINAL de la acción que llama a este helper.
    # Esto es para _handle_graph_api_error si get_file_metadata falla.
    params_for_metadata: Optional[Dict[str, Any]] = None
) -> Union[str, Dict[str, Any]]: # Devuelve ID de item o un dict de error
    
    is_likely_id = '!' in item_path_or_id or \
                   (len(item_path_or_id) > 30 and '/' not in item_path_or_id and '.' not in item_path_or_id) or \
                   item_path_or_id.startswith("driveItem_") or \
                   (len(item_path_or_id) > 60 and item_path_or_id.count('-') > 3) # IDs de listItem

    if is_likely_id:
        logger.debug(f"Asumiendo que '{item_path_or_id}' ya es un ID de item SP (DriveItem o ListItem).")
        return item_path_or_id

    logger.debug(f"'{item_path_or_id}' parece un path SP. Intentando obtener su ID para sitio '{site_id}', drive '{drive_id}'.")
    # Usar los params originales de la acción que llama a este helper para el get_file_metadata
    metadata_call_params = {
        "site_id": site_id, # Asegurar que pasamos site_id ya resuelto
        "drive_id_or_name": drive_id, # Asegurar que pasamos drive_id ya resuelto
        "item_id_or_path": item_path_or_id,
        "select": "id,name" # Solo necesitamos id y name para confirmación
    }
    # Añadir el "site_identifier" original si estaba en params_for_metadata, por si _obtener_site_id_sp lo necesita dentro de get_file_metadata
    if params_for_metadata and params_for_metadata.get("site_identifier"):
        metadata_call_params["site_identifier"] = params_for_metadata.get("site_identifier")

    try:
        item_metadata_response = get_file_metadata(client, metadata_call_params)
        if item_metadata_response.get("status") == "success":
            item_data = item_metadata_response.get("data", {})
            item_id = item_data.get("id")
            if item_id:
                logger.info(f"ID '{item_id}' (Nombre: {item_data.get('name')}) obtenido para SP path '{item_path_or_id}' en drive '{drive_id}', sitio '{site_id}'.")
                return item_id
            else:
                # Si status es success pero no hay ID (improbable pero posible)
                msg = f"ID no encontrado en metadatos para SP path '{item_path_or_id}' (Sitio: {site_id}, Drive: {drive_id})."
                logger.error(msg + f" Metadata obtenida: {item_data}")
                return {"status": "error", "message": msg, "details": item_data, "http_status": 404}
        else:
            # Propagar el error ya formateado por get_file_metadata
            msg = f"Fallo al obtener metadatos para resolver ID de SP path '{item_path_or_id}' (Sitio: {site_id}, Drive: {drive_id})."
            logger.error(msg + f" Respuesta de get_file_metadata: {item_metadata_response}")
            # Devolver la respuesta de error original de get_file_metadata
            return item_metadata_response
    except Exception as e_meta:
        # Capturar cualquier otra excepción y formatearla
        msg = f"Excepción al intentar obtener ID para SP path '{item_path_or_id}' (Sitio: {site_id}, Drive: {drive_id}): {type(e_meta).__name__} - {e_meta}"
        logger.error(msg, exc_info=True)
        # Usar el helper estándar de error de este módulo.
        # Usar params_for_metadata si está disponible para el log de error.
        return _handle_graph_api_error(e_meta, "_get_item_id_from_path_if_needed_sp", params_for_metadata or metadata_call_params)


# ============================================
# ==== ACCIONES PÚBLICAS (Mapeadas) ====
# ============================================
def get_site_info(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_site_info con params: %s", params)
    action_name = "get_site_info"
    
    select_fields: Optional[str] = params.get("select")
    try:
        # _obtener_site_id_sp toma 'params' y busca 'site_id' o 'site_identifier' dentro.
        target_site_identifier = _obtener_site_id_sp(client, params) 
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_identifier}"
        
        query_api_params: Dict[str, str] = {}
        if select_fields: 
            query_api_params['$select'] = select_fields
        else: 
            query_api_params['$select'] = "id,displayName,name,webUrl,createdDateTime,lastModifiedDateTime,description,siteCollection"
        
        logger.info(f"Obteniendo información del sitio SP: '{target_site_identifier}' (Select: {query_api_params['$select']})")
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.get(url, scope=sites_read_scope, params=query_api_params if query_api_params else None)
        
        # --- CORRECCIÓN ---
        return {"status": "success", "data": response}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def search_sites(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando search_sites con params: %s", params)
    action_name = "search_sites"

    query_text: Optional[str] = params.get("query_text")
    if not query_text: 
        return _handle_graph_api_error(ValueError("'query_text' es requerido para search_sites."), action_name, params)
    
    url = f"{settings.GRAPH_API_BASE_URL}/sites" # El endpoint es /sites?search=
    api_query_params: Dict[str, Any] = {'search': query_text}
    if params.get("select"): 
        api_query_params["$select"] = params["select"]
    else:
        api_query_params["$select"] = "id,name,displayName,webUrl,description" # Un select por defecto
    if params.get("top"): 
        api_query_params["$top"] = params["top"] # Para limitar el número de resultados

    logger.info(f"Buscando sitios SP con query: '{query_text}'. (Select: {api_query_params.get('$select')}, Top: {api_query_params.get('$top')})")
    sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.get(url, scope=sites_read_scope, params=api_query_params)
        
        # --- CORRECCIÓN ---
        return {"status": "success", "data": response.get("value", [])}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def create_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando create_list con params (columnas omitidas del log si presentes): %s", {k:v for k,v in params.items() if k != 'columnas'})
    action_name = "create_list"

    list_name: Optional[str] = params.get("nombre_lista")
    columns_definition: Optional[List[Dict[str, Any]]] = params.get("columnas")
    list_template: str = params.get("template", "genericList") # default a lista genérica

    if not list_name: 
        return _handle_graph_api_error(ValueError("'nombre_lista' es requerido."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists"
        
        body_payload: Dict[str, Any] = {"displayName": list_name, "list": {"template": list_template}}
        if columns_definition and isinstance(columns_definition, list): 
            body_payload["columns"] = columns_definition
        
        logger.info(f"Creando lista SP '{list_name}' en sitio '{target_site_id}' (Template: {list_template}). Columnas provistas: {bool(columns_definition)}")
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.post(url, scope=sites_manage_scope, json_data=body_payload)
        return {"status": "success", "data": response.json()}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def list_lists(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_lists con params: %s", params)
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
        
        logger.info(f"Listando listas SP en sitio '{target_site_id}'. (Top: {top_per_page}, Max total: {max_items_total or 'todos'}, Filter: {bool(filter_query)})")
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        return _sp_paged_request(client, url_base, sites_read_scope, params, query_api_params_init, max_items_total, action_name)
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def get_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_list con params: %s", params)
    action_name = "get_list"

    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    select_fields: Optional[str] = params.get("select")
    expand_fields: Optional[str] = params.get("expand")

    if not list_id_or_name: 
        return _handle_graph_api_error(ValueError("'lista_id_o_nombre' es requerido."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}"
        
        query_api_params: Dict[str, str] = {}
        if select_fields: 
            query_api_params['$select'] = select_fields
        else: # Un select por defecto más completo
            query_api_params['$select'] = "id,name,displayName,description,webUrl,list,createdDateTime,lastModifiedDateTime,columns,contentTypes,items"
        if expand_fields: 
            query_api_params['$expand'] = expand_fields
        
        logger.info(f"Obteniendo lista SP '{list_id_or_name}' de sitio '{target_site_id}'. (Select: {query_api_params.get('$select')}, Expand: {query_api_params.get('$expand')})")
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.get(url, scope=sites_read_scope, params=query_api_params if query_api_params else None)

        # --- CORRECCIÓN ---
        return {"status": "success", "data": response}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def update_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando update_list con params: %s", params)
    action_name = "update_list"

    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    update_payload: Optional[Dict[str, Any]] = params.get("update_payload")

    if not list_id_or_name or not update_payload or not isinstance(update_payload, dict): 
        return _handle_graph_api_error(ValueError("'lista_id_o_nombre' y 'update_payload' (dict) son requeridos."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}"
        
        logger.info(f"Actualizando lista SP '{list_id_or_name}' en sitio '{target_site_id}' con payload: {update_payload}")
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.patch(url, scope=sites_manage_scope, json_data=update_payload)
        return {"status": "success", "data": response.json()}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def delete_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando delete_list con params: %s", params)
    action_name = "delete_list"

    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    if not list_id_or_name: 
        return _handle_graph_api_error(ValueError("'lista_id_o_nombre' es requerido."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}"
        
        logger.info(f"Eliminando lista SP '{list_id_or_name}' de sitio '{target_site_id}'.")
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.delete(url, scope=sites_manage_scope)
        # Delete devuelve 204 No Content
        return {"status": "success", "message": f"Lista '{list_id_or_name}' eliminada exitosamente de sitio '{target_site_id}'.", "http_status": response.status_code}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def add_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando add_list_item con params (datos_campos omitido del log si presente): %s", {k:v for k,v in params.items() if k != 'datos_campos'})
    action_name = "add_list_item"

    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    fields_data: Optional[Dict[str, Any]] = params.get("datos_campos")

    if not list_id_or_name or not fields_data or not isinstance(fields_data, dict): 
        return _handle_graph_api_error(ValueError("'lista_id_o_nombre' y 'datos_campos' (dict) son requeridos."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        # El payload para crear un item es {"fields": { ... }}
        body_payload = {"fields": fields_data}
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items"
        
        logger.info(f"Añadiendo item a lista SP '{list_id_or_name}' en sitio '{target_site_id}'. Campos: {list(fields_data.keys())}")
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # Sites.ReadWrite.All o equivalente
        response = client.post(url, scope=sites_manage_scope, json_data=body_payload)
        return {"status": "success", "data": response.json()}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def list_list_items(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_list_items con params: %s", params)
    action_name = "list_list_items"

    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    if not list_id_or_name: 
        return _handle_graph_api_error(ValueError("'lista_id_o_nombre' es requerido."), action_name, params)

    select_fields: Optional[str] = params.get("select") # Para seleccionar campos del ListItem (id, webUrl, etc.)
    filter_query: Optional[str] = params.get("filter_query") # Para filtrar items
    expand_fields: str = params.get("expand", "fields(select=*)") # Por defecto expandir todos los campos de usuario
    top_per_page: int = min(int(params.get('top_per_page', 50)), getattr(settings, 'DEFAULT_PAGING_SIZE', 50))
    max_items_total: Optional[int] = params.get('max_items_total')
    order_by: Optional[str] = params.get("orderby")

    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url_base = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items"
        
        query_api_params_init: Dict[str, Any] = {'$top': top_per_page}
        if select_fields: 
            query_api_params_init["$select"] = select_fields
        if filter_query: 
            query_api_params_init["$filter"] = filter_query
        if expand_fields: 
            query_api_params_init["$expand"] = expand_fields
        if order_by: 
            query_api_params_init["$orderby"] = order_by
        
        logger.info(f"Listando items de lista SP '{list_id_or_name}' en sitio '{target_site_id}'. (Expand: {expand_fields}, Top: {top_per_page})")
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        return _sp_paged_request(client, url_base, sites_read_scope, params, query_api_params_init, max_items_total, action_name)
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def get_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_list_item con params: %s", params)
    action_name = "get_list_item"

    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    item_id: Optional[str] = params.get("item_id") # ID del ListItem
    select_fields: Optional[str] = params.get("select")
    expand_fields: Optional[str] = params.get("expand", "fields(select=*)")

    if not list_id_or_name or not item_id: 
        return _handle_graph_api_error(ValueError("'lista_id_o_nombre' e 'item_id' son requeridos."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items/{item_id}"
        
        query_api_params: Dict[str, str] = {}
        if select_fields: 
            query_api_params["$select"] = select_fields
        if expand_fields: 
            query_api_params["$expand"] = expand_fields
        
        logger.info(f"Obteniendo item SP ID '{item_id}' de lista '{list_id_or_name}', sitio '{target_site_id}'. (Expand: {expand_fields})")
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.get(url, scope=sites_read_scope, params=query_api_params if query_api_params else None)
        
        # --- CORRECCIÓN ---
        return {"status": "success", "data": response}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def update_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando update_list_item con params (nuevos_valores_campos omitido del log): %s", {k:v for k,v in params.items() if k != 'nuevos_valores_campos'})
    action_name = "update_list_item"

    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    item_id: Optional[str] = params.get("item_id")
    fields_to_update: Optional[Dict[str, Any]] = params.get("nuevos_valores_campos")
    etag: Optional[str] = params.get("etag") # Opcional, para control de concurrencia

    if not list_id_or_name or not item_id or not fields_to_update or not isinstance(fields_to_update, dict): 
        return _handle_graph_api_error(ValueError("'lista_id_o_nombre', 'item_id', y 'nuevos_valores_campos' (dict) son requeridos."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        # El endpoint para actualizar los campos de un listItem es /items/{item-id}/fields
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items/{item_id}/fields"
        
        request_headers = {'If-Match': etag} if etag else {}
        
        logger.info(f"Actualizando item SP ID '{item_id}' en lista '{list_id_or_name}', sitio '{target_site_id}'. ETag: {etag or 'N/A'}")
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.patch(url, scope=sites_manage_scope, json_data=fields_to_update, headers=request_headers)
        return {"status": "success", "data": response.json()}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def delete_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando delete_list_item con params: %s", params)
    action_name = "delete_list_item"

    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    item_id: Optional[str] = params.get("item_id")
    etag: Optional[str] = params.get("etag")

    if not list_id_or_name or not item_id: 
        return _handle_graph_api_error(ValueError("'lista_id_o_nombre' e 'item_id' son requeridos."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_or_name}/items/{item_id}"
        
        request_headers = {'If-Match': etag} if etag else {}
        if not etag:
            logger.warning(f"Eliminando item SP ID '{item_id}' de lista '{list_id_or_name}' SIN ETag. Podría haber conflictos de concurrencia.")
        
        logger.info(f"Eliminando item SP ID '{item_id}' de lista '{list_id_or_name}', sitio '{target_site_id}'. ETag: {etag or 'N/A'}")
        sites_manage_scope = getattr(settings, 'GRAPH_SCOPE_SITES_MANAGE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.delete(url, scope=sites_manage_scope, headers=request_headers)
        # Delete devuelve 204 No Content
        return {"status": "success", "message": f"Item '{item_id}' eliminado de lista '{list_id_or_name}'.", "http_status": response.status_code}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def search_list_items(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando search_list_items con params: %s", params)
    action_name = "search_list_items"
    
    list_id_or_name: Optional[str] = params.get("lista_id_o_nombre")
    query_text_as_filter: Optional[str] = params.get("query_text") # Este se usará como $filter
    select_fields: Optional[str] = params.get("select")
    max_results: Optional[int] = params.get("top")

    if not list_id_or_name or not query_text_as_filter: 
        return _handle_graph_api_error(ValueError("'lista_id_o_nombre' y 'query_text' (usado como $filter) son requeridos."), action_name, params)
    
    logger.warning("Función 'search_list_items' está usando el 'query_text' como un $filter OData para la acción 'list_list_items'. No es un endpoint de búsqueda dedicado de Graph.")
    
    try:
        target_site_id = _obtener_site_id_sp(client, params) # _obtener_site_id_sp usa params
        
        # Reutilizar list_list_items pasándole el query_text como filter_query
        list_items_params = {
            "site_id": target_site_id, # Pasar el site_id resuelto
            "site_identifier": params.get("site_identifier", params.get("site_id")), # Pasar el original por si _obtener_site_id_sp lo necesita
            "lista_id_o_nombre": list_id_or_name,
            "filter_query": query_text_as_filter,
            "select": select_fields,
            "max_items_total": max_results,
            "expand": params.get("expand", "fields(select=*)") # Mantener el expand por defecto
        }
        logger.info(f"Redirigiendo search_list_items a list_list_items con $filter: '{query_text_as_filter}'")
        return list_list_items(client, list_items_params)
    except Exception as e: # Captura errores de _obtener_site_id_sp o de la llamada a list_list_items
        return _handle_graph_api_error(e, action_name, params)

def list_document_libraries(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Lista todas las bibliotecas de documentos del sitio."""
    action_name = "sp_list_document_libraries"
    try:
        site_id = _obtener_site_id_sp(client, params)
        logger.info(f"Iniciando lista de bibliotecas de documentos para site_id: {site_id}")
        
        url = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives"
        scope = ["https://graph.microsoft.com/.default"]
        
        # Corregir el campo displayName por name
        select_fields = "id,name,description,driveType,createdDateTime,lastModifiedDateTime,webUrl,owner"
        
        query_params = {
            "$select": select_fields,
            "$orderby": "name",
            "$top": params.get("top", 50)
        }
        
        response = client.get(url, scope=scope, params=query_params)
        
        return {
            "status": "success",
            "action": action_name,
            "data": response.get("value", []),
            "@odata.count": response.get("@odata.count"),
            "@odata.nextLink": response.get("@odata.nextLink"),
            "site_id": site_id,
            "timestamp": _get_current_timestamp_iso_z()
        }
        
    except Exception as e:
        return _handle_graph_api_error(e, action_name, params)

def list_folder_contents(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_folder_contents con params: %s", params)
    action_name = "list_folder_contents"

    folder_path_or_id: str = params.get("folder_path_or_id", "") # Path relativo al root del drive, o ID del folder
    drive_id_or_name_input: Optional[str] = params.get("drive_id_or_name")
    select_fields: Optional[str] = params.get("select")
    expand_fields: Optional[str] = params.get("expand")
    top_per_page: int = min(int(params.get('top_per_page', 50)), 200) # Max para DriveItems es 200
    max_items_total: Optional[int] = params.get('max_items_total')
    order_by: Optional[str] = params.get("orderby")

    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, drive_id_or_name_input)
        
        # Determinar si folder_path_or_id es un ID o un path
        is_folder_id = not ('/' in folder_path_or_id) and \
                       (len(folder_path_or_id) > 30 or '!' in folder_path_or_id or folder_path_or_id.startswith("driveItem_"))
        
        item_segment: str
        if is_folder_id:
            item_segment = f"items/{folder_path_or_id}"
            logger.info(f"Listando contenido de carpeta SP por ID '{folder_path_or_id}' en drive '{target_drive_id}', sitio '{target_site_id}'.")
        else: # Es un path
            clean_path = folder_path_or_id.strip('/')
            if not clean_path: # Si es raíz
                item_segment = "root"
            else:
                item_segment = f"root:/{clean_path}"
            logger.info(f"Listando contenido de carpeta SP por path '{folder_path_or_id}' en drive '{target_drive_id}', sitio '{target_site_id}'.")

        url_base = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/drives/{target_drive_id}/{item_segment}/children"
        
        query_api_params_init: Dict[str, Any] = {'$top': top_per_page}
        query_api_params_init["$select"] = select_fields or "id,name,webUrl,size,createdDateTime,lastModifiedDateTime,file,folder,package,parentReference"
        if expand_fields: query_api_params_init["$expand"] = expand_fields
        if order_by: query_api_params_init["$orderby"] = order_by
        
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        return _sp_paged_request(client, url_base, files_read_scope, params, query_api_params_init, max_items_total, action_name)
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def get_file_metadata(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_file_metadata con params: %s", params)
    action_name = "get_file_metadata"

    item_id_or_path: Optional[str] = params.get("item_id_or_path")
    drive_id_or_name_input: Optional[str] = params.get("drive_id_or_name")
    select_fields: Optional[str] = params.get("select")
    expand_fields: Optional[str] = params.get("expand")

    if not item_id_or_path: 
        return _handle_graph_api_error(ValueError("'item_id_or_path' es requerido."),action_name, params)
    
    try:
        # params ya incluye site_id o site_identifier para _obtener_site_id_sp
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, drive_id_or_name_input)
        
        is_item_id = not ('/' in item_id_or_path) and \
                     (len(item_id_or_path) > 30 or '!' in item_id_or_path or item_id_or_path.startswith("driveItem_"))
        
        base_url_item: str
        if is_item_id:
            base_url_item = _get_sp_item_endpoint_by_id(target_site_id, target_drive_id, item_id_or_path)
            logger.info(f"Obteniendo metadatos de item SP por ID '{item_id_or_path}' en drive '{target_drive_id}', sitio '{target_site_id}'.")
        else:
            base_url_item = _get_sp_item_endpoint_by_path(target_site_id, target_drive_id, item_id_or_path)
            logger.info(f"Obteniendo metadatos de item SP por path '{item_id_or_path}' en drive '{target_drive_id}', sitio '{target_site_id}'.")
            
        query_api_params: Dict[str, str] = {}
        query_api_params["$select"] = select_fields or "id,name,webUrl,size,createdDateTime,lastModifiedDateTime,file,folder,package,parentReference,listItem,@microsoft.graph.downloadUrl"
        if expand_fields: 
            query_api_params["$expand"] = expand_fields
        
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.get(base_url_item, scope=files_read_scope, params=query_api_params if query_api_params else None)

        # --- CORRECCIÓN ---
        return {"status": "success", "data": response}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def upload_document(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando upload_document con params (omitiendo content_bytes del log): %s", {k:v for k,v in params.items() if k != "content_bytes"})
    action_name = "upload_document"

    filename: Optional[str] = params.get("filename")
    content_bytes: Optional[bytes] = params.get("content_bytes")
    folder_path: str = params.get("folder_path", "") # Path relativo al root del drive, o ID de carpeta padre.
    drive_id_or_name_input: Optional[str] = params.get("drive_id_or_name")
    conflict_behavior: str = params.get("conflict_behavior", "rename") # rename, replace, fail

    if not filename or content_bytes is None: 
        return _handle_graph_api_error(ValueError("'filename' y 'content_bytes' son requeridos."), action_name, params)
    if not isinstance(content_bytes, bytes): 
        return _handle_graph_api_error(TypeError("'content_bytes' debe ser de tipo bytes."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, drive_id_or_name_input)
        
        path_segment = folder_path.strip("/")
        target_item_path = f"{path_segment}/{filename}" if path_segment else filename
        
        # Endpoint para PUT simple o crear sesión de carga: /sites/{site-id}/drives/{drive-id}/root:/path/to/folder/filename.ext:
        item_upload_base_url = _get_sp_item_endpoint_by_path(target_site_id, target_drive_id, target_item_path)
        
        file_size_bytes = len(content_bytes)
        file_size_mb = file_size_bytes / (1024 * 1024)
        logger.info(f"Iniciando subida a SP Drive '{target_drive_id}' (Sitio '{target_site_id}'). Path API: 'root:/{target_item_path}'. Tamaño: {file_size_mb:.2f} MB. Conflicto: '{conflict_behavior}'.")
        
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)

        if file_size_bytes <= 4 * 1024 * 1024: # Límite para PUT simple
            logger.info("Archivo <= 4MB. Usando subida simple (PUT).")
            upload_url = f"{item_upload_base_url}/content"
            put_query_params = {"@microsoft.graph.conflictBehavior": conflict_behavior}
            
            response = client.put(upload_url, scope=files_rw_scope, data=content_bytes, headers={"Content-Type": "application/octet-stream"}, params=put_query_params)
            return {"status": "success", "data": response.json(), "message": "Archivo subido (simple)."}
        else: # Subida grande con sesión
            logger.info("Archivo > 4MB. Iniciando sesión de carga.")
            session_url = f"{item_upload_base_url}/createUploadSession"
            session_body = {"item": {"@microsoft.graph.conflictBehavior": conflict_behavior, "name": filename}} # Name es opcional si está en el path
            
            session_response = client.post(session_url, scope=files_rw_scope, json_data=session_body)
            upload_session_data = session_response.json()
            upload_url_session = upload_session_data.get("uploadUrl")
            
            if not upload_url_session: 
                raise ValueError("No se pudo obtener 'uploadUrl' de la sesión de carga.")
            
            logger.info(f"Sesión de carga creada. URL (preview): {upload_url_session.split('?')[0]}...")
            
            chunk_size = 5 * 1024 * 1024 # Ajustable, ej: 5MB
            start_byte = 0
            final_response_json = None
            
            while start_byte < file_size_bytes:
                end_byte = min(start_byte + chunk_size - 1, file_size_bytes - 1)
                current_chunk = content_bytes[start_byte : end_byte + 1]
                chunk_len_str = str(len(current_chunk))
                content_range_header = f"bytes {start_byte}-{end_byte}/{file_size_bytes}"
                
                # Calcular un timeout dinámico para el chunk, o usar uno generoso.
                # El http_client.request tomará el timeout por defecto si no se pasa.
                chunk_upload_timeout = max(settings.DEFAULT_API_TIMEOUT, int(len(current_chunk) / (50 * 1024)) + 60) # 50KB/s + 60s buffer
                
                logger.debug(f"Subiendo chunk SP: {content_range_header}, Timeout: {chunk_upload_timeout}s")
                # Para la subida de chunks, se usa requests directamente porque AuthenticatedHttpClient no está diseñado para esto.
                # No se requiere token de Auth en el header para esta URL de sesión.
                chunk_resp = requests.put(
                    upload_url_session,
                    data=current_chunk,
                    headers={"Content-Length": chunk_len_str, "Content-Range": content_range_header},
                    timeout=chunk_upload_timeout
                )
                chunk_resp.raise_for_status() # Lanza error para 4xx/5xx
                
                if chunk_resp.status_code in (200, 201): # Subida completada
                    final_response_json = chunk_resp.json()
                    logger.info(f"Subida de sesión SP completada. Respuesta final del chunk: {final_response_json.get('id', 'ID no disponible')}")
                    break
                elif chunk_resp.status_code == 202: # Chunk aceptado, esperando más
                    next_expected_ranges = chunk_resp.json().get("nextExpectedRanges")
                    logger.debug(f"Chunk SP aceptado (202). Próximo rango esperado: {next_expected_ranges}")
                    # Podríamos usar next_expected_ranges[0].split('-')[0] para el próximo start_byte si es más robusto.
                else: # Código inesperado
                    logger.warning(f"Respuesta inesperada subiendo chunk SP (Status {chunk_resp.status_code}): {chunk_resp.text[:200]}")

                start_byte = end_byte + 1
            
            if final_response_json:
                return {"status": "success", "data": final_response_json, "message": "Archivo subido con sesión."}
            elif start_byte >= file_size_bytes : # Si todos los bytes se enviaron pero no hubo respuesta 200/201
                logger.warning("Todos los chunks SP enviados, pero no se recibió metadata del item final en la última respuesta. Intentando verificación manual.")
                # Verificar si el archivo existe ahora. params para get_file_metadata:
                check_params = {
                    "site_id": target_site_id, # site_id resuelto
                    "drive_id_or_name": target_drive_id, # drive_id resuelto
                    "item_id_or_path": target_item_path, # path original usado para la subida
                    "site_identifier": params.get("site_identifier") # original, por si _obtener_site_id_sp lo necesita
                }
                check_meta = get_file_metadata(client, check_params)
                if check_meta.get("status") == "success":
                    return {"status": "success", "data": check_meta["data"], "message": "Archivo subido con sesión (verificado post-subida)."}
                else:
                    logger.error(f"Subida de sesión SP parece completa, pero la verificación final del archivo falló. Respuesta de verificación: {check_meta}")
                    return {"status": "warning", "message": "Archivo subido con sesión, pero la verificación final del estado del archivo falló.", "details": check_meta, "http_status": 500}
            else: # No se completó la subida
                raise Exception("Subida de sesión de archivo grande SP no completada. No se recibieron todos los chunks o no hubo respuesta final.")

    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def download_document(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[bytes, Dict[str, Any]]:
    params = params or {}
    logger.info("Ejecutando download_document con params: %s", params)
    action_name = "download_document"

    item_id_or_path: Optional[str] = params.get("item_id_or_path")
    drive_id_or_name_input: Optional[str] = params.get("drive_id_or_name")

    if not item_id_or_path: 
        return _handle_graph_api_error(ValueError("'item_id_or_path' es requerido."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, drive_id_or_name_input)
        
        # Resolver path a ID para obtener el endpoint /content
        item_actual_id = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, target_site_id, target_drive_id, params)
        if isinstance(item_actual_id, dict) and item_actual_id.get("status") == "error": # Si _get_item_id... devolvió un error
            return item_actual_id 
        
        # Usar el ID resuelto para el endpoint /content
        url_content = f"{_get_sp_item_endpoint_by_id(target_site_id, target_drive_id, str(item_actual_id))}/content"
        
        logger.info(f"Descargando documento SP ID '{item_actual_id}' (Original: '{item_id_or_path}') de drive '{target_drive_id}', sitio '{target_site_id}'.")
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        # El http_client.get ya maneja stream=True si es necesario, o devuelve response.content
        response = client.get(url_content, scope=files_read_scope, stream=True) # stream=True es importante para archivos
        
        # --- CORRECCIÓN ---
        # `client.get(stream=True)` devuelve directamente los bytes.
        file_bytes = response
        
        logger.info(f"Documento SP '{item_actual_id}' descargado ({len(file_bytes)} bytes).")
        return file_bytes # FastAPI manejará esto como una respuesta binaria
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def delete_document(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    # Esta función es un alias para delete_item, ya que la lógica es la misma.
    params = params or {}
    logger.info("Ejecutando delete_document (alias de delete_item) con params: %s", params)
    return delete_item(client, params)

def delete_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando delete_item con params: %s", params)
    action_name = "delete_item" # El original era sp_delete_item

    item_id_or_path: Optional[str] = params.get("item_id_or_path")
    drive_id_or_name_input: Optional[str] = params.get("drive_id_or_name")
    etag: Optional[str] = params.get("etag") # Para control de concurrencia

    if not item_id_or_path: 
        return _handle_graph_api_error(ValueError("'item_id_or_path' es requerido."),action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, drive_id_or_name_input)
        
        item_actual_id = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, target_site_id, target_drive_id, params)
        if isinstance(item_actual_id, dict) and item_actual_id.get("status") == "error": # Si _get_item_id... devolvió un error
            return item_actual_id
        
        url_item = _get_sp_item_endpoint_by_id(target_site_id, target_drive_id, str(item_actual_id))
        request_headers = {'If-Match': etag} if etag else {}
        if not etag:
            logger.warning(f"Eliminando item SP ID '{item_actual_id}' SIN ETag. Podría haber conflictos de concurrencia.")

        logger.info(f"Eliminando item SP ID '{item_actual_id}' (Original: '{item_id_or_path}') de drive '{target_drive_id}', sitio '{target_site_id}'. ETag: {etag or 'N/A'}")
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.delete(url_item, scope=files_rw_scope, headers=request_headers)
        # Delete devuelve 204 No Content
        return {"status": "success", "message": f"Item '{item_actual_id}' (Original: {item_id_or_path}) eliminado.", "http_status": response.status_code}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def create_folder(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando create_folder con params: %s", params)
    action_name = "create_folder"

    folder_name: Optional[str] = params.get("folder_name")
    parent_folder_path_or_id: str = params.get("parent_folder_path_or_id", "") # Path relativo al root del drive, o ID de carpeta padre
    drive_id_or_name_input: Optional[str] = params.get("drive_id_or_name")
    conflict_behavior: str = params.get("conflict_behavior", "fail") # fail, rename, replace

    if not folder_name: 
        return _handle_graph_api_error(ValueError("'folder_name' es requerido."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, drive_id_or_name_input)
        
        parent_is_id = not ('/' in parent_folder_path_or_id) and \
                       (len(parent_folder_path_or_id) > 30 or '!' in parent_folder_path_or_id or parent_folder_path_or_id.startswith("driveItem_"))
        
        parent_endpoint: str
        if parent_is_id:
            parent_endpoint = _get_sp_item_endpoint_by_id(target_site_id, target_drive_id, parent_folder_path_or_id)
            logger.info(f"Creando carpeta '{folder_name}' bajo carpeta padre SP por ID '{parent_folder_path_or_id}' en drive '{target_drive_id}', sitio '{target_site_id}'.")
        else: # Es un path
            parent_endpoint = _get_sp_item_endpoint_by_path(target_site_id, target_drive_id, parent_folder_path_or_id)
            logger.info(f"Creando carpeta '{folder_name}' bajo carpeta padre SP por path '{parent_folder_path_or_id or 'root'}' en drive '{target_drive_id}', sitio '{target_site_id}'.")

        url_create_folder = f"{parent_endpoint}/children"
        body_payload = {"name": folder_name, "folder": {}, "@microsoft.graph.conflictBehavior": conflict_behavior}
        
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.post(url_create_folder, scope=files_rw_scope, json_data=body_payload)
        return {"status": "success", "data": response.json()}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def move_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando move_item con params: %s", params)
    action_name = "move_item"

    item_id_or_path: Optional[str] = params.get("item_id_or_path") # Item a mover
    target_parent_folder_id: Optional[str] = params.get("target_parent_folder_id") # ID de la carpeta destino
    new_name_after_move: Optional[str] = params.get("new_name") # Opcional: renombrar al mover
    
    # IDs de drive y sitio para el item de ORIGEN
    source_drive_id_or_name: Optional[str] = params.get("drive_id_or_name") or params.get("source_drive_id_or_name")
    # Nota: _obtener_site_id_sp se basa en 'site_id' o 'site_identifier' en params para el sitio de ORIGEN.
    
    # IDs de drive y sitio para el item de DESTINO (si es diferente al de origen)
    target_drive_id_param: Optional[str] = params.get("target_drive_id") 
    target_site_id_param: Optional[str] = params.get("target_site_id") # Para mover entre sitios

    if not item_id_or_path or not target_parent_folder_id: 
        return _handle_graph_api_error(ValueError("'item_id_or_path' y 'target_parent_folder_id' son requeridos."), action_name, params)
    
    try:
        source_site_id_resolved = _obtener_site_id_sp(client, params) # Resuelve el sitio de origen
        source_drive_id_resolved = _get_drive_id(client, source_site_id_resolved, source_drive_id_or_name)
        
        item_actual_id = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, source_site_id_resolved, source_drive_id_resolved, params)
        if isinstance(item_actual_id, dict) and item_actual_id.get("status") == "error": 
            return item_actual_id 
        
        url_patch_item = _get_sp_item_endpoint_by_id(source_site_id_resolved, source_drive_id_resolved, str(item_actual_id))
        
        payload_move: Dict[str, Any] = {"parentReference": {"id": target_parent_folder_id}}
        
        # Si se especifica un drive de destino (puede ser el mismo o diferente)
        if target_drive_id_param:
            payload_move["parentReference"]["driveId"] = target_drive_id_param
            # Si se especifica un sitio de destino, y es diferente al de origen, también se añade.
            if target_site_id_param and target_site_id_param != source_site_id_resolved:
                # Aquí asumimos que target_site_id_param ya es un ID válido o un identificador que _obtener_site_id_sp puede resolver.
                # Para ser más robusto, se podría resolver explícitamente:
                # dest_site_id_for_move = _obtener_site_id_sp(client, {"site_id": target_site_id_param, **params})
                # payload_move["parentReference"]["siteId"] = dest_site_id_for_move
                # Por ahora, se asume que si se pasa target_site_id_param, es un ID válido.
                payload_move["parentReference"]["siteId"] = target_site_id_param
            elif target_site_id_param and target_site_id_param == source_site_id_resolved:
                 # Si es el mismo sitio, no es estrictamente necesario, pero Graph lo maneja.
                 payload_move["parentReference"]["siteId"] = target_site_id_param

        if new_name_after_move: 
            payload_move["name"] = new_name_after_move
        
        logger.info(f"Moviendo item SP ID '{item_actual_id}' (Original: '{item_id_or_path}') de drive '{source_drive_id_resolved}', sitio '{source_site_id_resolved}'. Destino: {payload_move['parentReference']}. Nuevo nombre: {new_name_after_move or '(sin cambio)'}")
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.patch(url_patch_item, scope=files_rw_scope, json_data=payload_move)
        return {"status": "success", "data": response.json()}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def copy_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando copy_item con params: %s", params)
    action_name = "copy_item"

    item_id_or_path: Optional[str] = params.get("item_id_or_path")
    target_parent_folder_id: Optional[str] = params.get("target_parent_folder_id") # ID de la carpeta destino
    new_name_for_copy: Optional[str] = params.get("new_name") # Opcional: nombre para la copia
    
    source_site_id_param: Optional[str] = params.get("source_site_id") # Si el origen no es el default
    source_drive_id_or_name: Optional[str] = params.get("source_drive_id_or_name")
    
    target_site_id_param: Optional[str] = params.get("target_site_id") # Si el destino es otro sitio
    target_drive_id_param: Optional[str] = params.get("target_drive_id") # Si el destino es otro drive (o el mismo)

    if not item_id_or_path or not target_parent_folder_id: 
        return _handle_graph_api_error(ValueError("'item_id_or_path' y 'target_parent_folder_id' son requeridos."), action_name, params)
    
    try:
        # Resolver sitio y drive de ORIGEN
        # Pasar source_site_id_param explícitamente a _obtener_site_id_sp
        source_site_id_resolved = _obtener_site_id_sp(client, {"site_id": source_site_id_param, **params} if source_site_id_param else params)
        source_drive_id_resolved = _get_drive_id(client, source_site_id_resolved, source_drive_id_or_name)
        
        item_actual_id = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, source_site_id_resolved, source_drive_id_resolved, params)
        if isinstance(item_actual_id, dict) and item_actual_id.get("status") == "error": 
            return item_actual_id 
        
        # URL para la acción de copia del item de ORIGEN
        url_copy_action = f"{_get_sp_item_endpoint_by_id(source_site_id_resolved, source_drive_id_resolved, str(item_actual_id))}/copy"
        
        # Construir el parentReference para el DESTINO
        parent_reference_payload: Dict[str, str] = {"id": target_parent_folder_id}
        if target_drive_id_param:
            parent_reference_payload["driveId"] = target_drive_id_param
            # Si se especifica un drive de destino, se necesita el siteId de ese drive si es diferente al de origen
            if target_site_id_param:
                # Resolver el ID del sitio de destino si se proporcionó un identificador
                dest_site_id_resolved = _obtener_site_id_sp(client, {"site_id": target_site_id_param, **params})
                parent_reference_payload["siteId"] = dest_site_id_resolved
            # Si no se da target_site_id_param pero sí target_drive_id_param, y es un drive en el mismo sitio de origen,
            # Graph podría inferirlo, pero es mejor ser explícito si se conoce.
            # Si target_drive_id_param es de OTRO sitio y no se da target_site_id_param, la API podría fallar.
            # Por seguridad, si target_drive_id_param está y target_site_id_param no, asumir mismo sitio de origen.
            elif not target_site_id_param :
                 parent_reference_payload["siteId"] = source_site_id_resolved

        body_payload: Dict[str, Any] = {"parentReference": parent_reference_payload}
        if new_name_for_copy: 
            body_payload["name"] = new_name_for_copy
        
        logger.info(f"Iniciando copia de item SP ID '{item_actual_id}' (Original: '{item_id_or_path}') de drive '{source_drive_id_resolved}', sitio '{source_site_id_resolved}'. Destino: {parent_reference_payload}. Nuevo nombre: {new_name_for_copy or '(original)'}")
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.post(url_copy_action, scope=files_rw_scope, json_data=body_payload)
        
        # La operación de copia es asíncrona y devuelve 202 Accepted con un Location header para monitorear.
        if response.status_code == 202:
            monitor_url = response.headers.get("Location")
            response_data_dict = response.json() if response.content else {} # Puede no haber cuerpo
            logger.info(f"Solicitud de copia SP aceptada (202). Monitor URL: {monitor_url}")
            return {"status": "pending", "message": "Solicitud de copia aceptada y en progreso. Monitorear con la URL proporcionada.", "monitor_url": monitor_url, "data": response_data_dict, "http_status": 202}
        # A veces, para archivos pequeños, puede ser síncrono.
        elif response.status_code in [200, 201]:
             logger.info(f"Copia SP completada sincrónicamente (Status {response.status_code}).")
             return {"status": "success", "data": response.json(), "message": "Elemento copiado exitosamente (síncrono)."}
        else: # Respuesta inesperada
            logger.warning(f"Respuesta inesperada de copia SP. Status: {response.status_code}, Headers: {response.headers}, Body: {response.text[:200]}")
            # Re-lanzar para que _handle_graph_api_error lo capture
            response.raise_for_status()
            return {} # No debería llegar aquí
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def update_file_metadata(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando update_file_metadata con params (metadata_updates omitido del log): %s", {k:v for k,v in params.items() if k != 'metadata_updates'})
    action_name = "update_file_metadata"

    item_id_or_path: Optional[str] = params.get("item_id_or_path")
    drive_id_or_name_input: Optional[str] = params.get("drive_id_or_name")
    metadata_updates_payload: Optional[Dict[str, Any]] = params.get("metadata_updates") # DriveItem properties a actualizar
    etag: Optional[str] = params.get("etag")

    if not item_id_or_path or not metadata_updates_payload or not isinstance(metadata_updates_payload, dict): 
        return _handle_graph_api_error(ValueError("'item_id_or_path' y 'metadata_updates' (dict) son requeridos."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, drive_id_or_name_input)
        
        item_actual_id = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, target_site_id, target_drive_id, params)
        if isinstance(item_actual_id, dict) and item_actual_id.get("status") == "error": 
            return item_actual_id 
        
        url_update = _get_sp_item_endpoint_by_id(target_site_id, target_drive_id, str(item_actual_id))
        request_headers = {'If-Match': etag} if etag else {}
        if not etag:
            logger.warning(f"Actualizando metadatos de item SP ID '{item_actual_id}' SIN ETag.")
        
        logger.info(f"Actualizando metadatos de item SP ID '{item_actual_id}' (Original: '{item_id_or_path}') en drive '{target_drive_id}', sitio '{target_site_id}'. Payload: {metadata_updates_payload}")
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.patch(url_update, scope=files_rw_scope, json_data=metadata_updates_payload, headers=request_headers)
        return {"status": "success", "data": response.json()}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def get_sharing_link(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_sharing_link con params (password omitido del log): %s", {k:v for k,v in params.items() if k != 'password'})
    action_name = "get_sharing_link"

    item_id_or_path: Optional[str] = params.get("item_id_or_path")
    drive_id_or_name_input: Optional[str] = params.get("drive_id_or_name")
    link_type: str = params.get("type", "view") # 'view', 'edit', 'embed'
    scope_param: str = params.get("scope", "organization") # 'anonymous', 'organization', 'users'
    password_link: Optional[str] = params.get("password") # Opcional
    expiration_datetime_str: Optional[str] = params.get("expirationDateTime") # Opcional, ISO 8601
    recipients_payload: Optional[List[Dict[str,str]]] = params.get("recipients") # Para scope='users'

    if not item_id_or_path: 
        return _handle_graph_api_error(ValueError("'item_id_or_path' es requerido."), action_name, params)
    if scope_param == "users" and not recipients_payload:
        return _handle_graph_api_error(ValueError("Si el scope del enlace es 'users', se requiere el parámetro 'recipients' (lista de objetos con email)."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        target_drive_id = _get_drive_id(client, target_site_id, drive_id_or_name_input)
        
        item_actual_id = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, target_site_id, target_drive_id, params)
        if isinstance(item_actual_id, dict) and item_actual_id.get("status") == "error": 
            return item_actual_id 
        
        url_action_createlink = f"{_get_sp_item_endpoint_by_id(target_site_id, target_drive_id, str(item_actual_id))}/createLink"
        
        body_payload_link: Dict[str, Any] = {"type": link_type, "scope": scope_param}
        if password_link: 
            body_payload_link["password"] = password_link
        if expiration_datetime_str: 
            body_payload_link["expirationDateTime"] = expiration_datetime_str
        if scope_param == "users" and recipients_payload: 
            body_payload_link["recipients"] = recipients_payload
        
        logger.info(f"Creando/obteniendo enlace de compartición para item SP ID '{item_actual_id}' (Original: '{item_id_or_path}'). Tipo: {link_type}, Scope: {scope_param}")
        # Files.ReadWrite.All o Sites.ReadWrite.All podrían ser necesarios si el enlace permite edición o es para un scope amplio.
        # Files.Read.All si solo es 'view' y 'organization'.
        # Por seguridad, usar un scope que permita la creación/modificación de enlaces si es necesario.
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.post(url_action_createlink, scope=files_rw_scope, json_data=body_payload_link)
        return {"status": "success", "data": response.json()} # Devuelve el objeto Permission con el link
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def list_item_permissions(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_item_permissions con params: %s", params)
    action_name = "list_item_permissions"

    item_id_or_path: Optional[str] = params.get("item_id_or_path")
    drive_id_or_name_input: Optional[str] = params.get("drive_id_or_name") # Para DriveItems
    list_id_o_nombre: Optional[str] = params.get("list_id_o_nombre") # Para ListItems
    list_item_id_param: Optional[str] = params.get("list_item_id") # Para ListItems

    if not item_id_or_path and not (list_id_o_nombre and list_item_id_param): 
        return _handle_graph_api_error(ValueError("Se requiere 'item_id_or_path' (para DriveItems) O ('list_id_o_nombre' Y 'list_item_id') (para ListItems)."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url_item_permissions: str
        log_item_description: str

        if item_id_or_path: # Es un DriveItem
            target_drive_id = _get_drive_id(client, target_site_id, drive_id_or_name_input)
            item_actual_id = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, target_site_id, target_drive_id, params)
            if isinstance(item_actual_id, dict) and item_actual_id.get("status") == "error": 
                return item_actual_id
            url_item_permissions = f"{_get_sp_item_endpoint_by_id(target_site_id, target_drive_id, str(item_actual_id))}/permissions"
            log_item_description = f"DriveItem ID '{item_actual_id}' (Original: '{item_id_or_path}') en drive '{target_drive_id}'"
        else: # Es un ListItem
            if not list_id_o_nombre or not list_item_id_param: # Doble chequeo por si acaso
                 return _handle_graph_api_error(ValueError("Para ListItems, 'list_id_o_nombre' y 'list_item_id' son requeridos."),action_name, params)
            url_item_permissions = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_o_nombre}/items/{list_item_id_param}/permissions"
            log_item_description = f"ListItem ID '{list_item_id_param}' en lista '{list_id_o_nombre}'"
        
        logger.info(f"Listando permisos para {log_item_description}, sitio '{target_site_id}'.")
        # Listar permisos generalmente requiere un scope de lectura amplio sobre el sitio o el item.
        # Sites.FullControl.All es seguro, pero Sites.ReadWrite.All o Files.ReadWrite.All podrían ser suficientes.
        perm_scope = getattr(settings, 'GRAPH_SCOPE_SITES_FULLCONTROL_ALL', # O un scope más granular si se conoce
                             getattr(settings, 'GRAPH_SCOPE_SITES_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
        response = client.get(url_item_permissions, scope=perm_scope)

        # --- CORRECCIÓN ---
        return {"status": "success", "data": response.get("value", [])} # Devuelve una colección de objetos Permission
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def add_item_permissions(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando add_item_permissions con params (recipients omitido del log): %s", {k:v for k,v in params.items() if k != 'recipients'})
    action_name = "add_item_permissions"

    item_id_or_path: Optional[str] = params.get("item_id_or_path")
    drive_id_or_name: Optional[str] = params.get("drive_id_or_name")
    list_id_o_nombre: Optional[str] = params.get("list_id_o_nombre")
    list_item_id: Optional[str] = params.get("list_item_id")
    
    recipients_payload: Optional[List[Dict[str,Any]]] = params.get("recipients") # Lista de DriveRecipient
    roles_payload: Optional[List[str]] = params.get("roles") # Ej: ["read"], ["write"]
    require_signin: bool = params.get("requireSignIn", True)
    send_invitation: bool = params.get("sendInvitation", True)
    message_invitation: Optional[str] = params.get("message")
    expiration_datetime_str: Optional[str] = params.get("expirationDateTime")

    if (not item_id_or_path and not (list_id_o_nombre and list_item_id)) or \
       not recipients_payload or not roles_payload: 
        return _handle_graph_api_error(ValueError("Faltan parámetros requeridos: identificador de item (DriveItem o ListItem), 'recipients' (lista), y 'roles' (lista) son obligatorios."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url_action_invite: str
        log_item_desc: str
        
        body_invite_payload: Dict[str, Any] = {
            "recipients": recipients_payload, 
            "roles": roles_payload, 
            "requireSignIn": require_signin, 
            "sendInvitation": send_invitation
        }
        if message_invitation: 
            body_invite_payload["message"] = message_invitation
        if expiration_datetime_str: 
            body_invite_payload["expirationDateTime"] = expiration_datetime_str
        # 'password' es para createLink, no para /invite.

        if item_id_or_path: # DriveItem
            target_drive_id = _get_drive_id(client, target_site_id, drive_id_or_name)
            item_actual_id = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, target_site_id, target_drive_id, params)
            if isinstance(item_actual_id, dict) and item_actual_id.get("status") == "error": 
                return item_actual_id
            item_actual_id_str = str(item_actual_id)
            url_action_invite = f"{_get_sp_item_endpoint_by_id(target_site_id, target_drive_id, item_actual_id_str)}/invite"
            log_item_desc = f"DriveItem ID '{item_actual_id_str}' (Original: '{item_id_or_path}')"
        else: # ListItem
            if not list_id_o_nombre or not list_item_id:
                 return _handle_graph_api_error(ValueError("Para ListItems, 'list_id_o_nombre' y 'list_item_id' son requeridos."),action_name, params)
            url_action_invite = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_o_nombre}/items/{list_item_id}/invite"
            log_item_desc = f"ListItem ID '{list_item_id}' en lista '{list_id_o_nombre}'"
        
        logger.info(f"Añadiendo/invitando permisos para {log_item_desc}, sitio '{target_site_id}'. Roles: {roles_payload}, Recipients: {len(recipients_payload)}.")
        perm_scope = getattr(settings, 'GRAPH_SCOPE_SITES_FULLCONTROL_ALL', # O un scope más granular como Files.ReadWrite.All si es suficiente
                             getattr(settings, 'GRAPH_SCOPE_FILES_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
        response = client.post(url_action_invite, scope=perm_scope, json_data=body_invite_payload)
        # La acción /invite devuelve una colección de objetos Permission creados o actualizados.
        return {"status": "success", "data": response.json().get("value", []), "message": "Permisos añadidos/actualizados."}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def remove_item_permissions(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando remove_item_permissions con params: %s", params)
    action_name = "remove_item_permissions"

    item_id_or_path: Optional[str] = params.get("item_id_or_path")
    drive_id_or_name: Optional[str] = params.get("drive_id_or_name")
    list_id_o_nombre: Optional[str] = params.get("list_id_o_nombre")
    list_item_id: Optional[str] = params.get("list_item_id")
    permission_id: Optional[str] = params.get("permission_id") # ID del objeto Permission a eliminar

    if (not item_id_or_path and not (list_id_o_nombre and list_item_id)) or not permission_id: 
        return _handle_graph_api_error(ValueError("Faltan parámetros requeridos: identificador de item (DriveItem o ListItem) y 'permission_id' son obligatorios."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        url_delete_perm: str
        log_item_desc: str

        if item_id_or_path: # DriveItem
            target_drive_id = _get_drive_id(client, target_site_id, drive_id_or_name)
            item_actual_id = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, target_site_id, target_drive_id, params)
            if isinstance(item_actual_id, dict) and item_actual_id.get("status") == "error": 
                return item_actual_id
            item_actual_id_str = str(item_actual_id)
            url_delete_perm = f"{_get_sp_item_endpoint_by_id(target_site_id, target_drive_id, item_actual_id_str)}/permissions/{permission_id}"
            log_item_desc = f"DriveItem ID '{item_actual_id_str}' (Original: '{item_id_or_path}')"
        else: # ListItem
            if not list_id_o_nombre or not list_item_id:
                 return _handle_graph_api_error(ValueError("Para ListItems, 'list_id_o_nombre' y 'list_item_id' son requeridos."),action_name, params)
            url_delete_perm = f"{settings.GRAPH_API_BASE_URL}/sites/{target_site_id}/lists/{list_id_o_nombre}/items/{list_item_id}/permissions/{permission_id}"
            log_item_desc = f"ListItem ID '{list_item_id}' en lista '{list_id_o_nombre}'"
        
        logger.info(f"Eliminando permiso ID '{permission_id}' de {log_item_desc}, sitio '{target_site_id}'.")
        perm_scope = getattr(settings, 'GRAPH_SCOPE_SITES_FULLCONTROL_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # Requiere permisos elevados
        response = client.delete(url_delete_perm, scope=perm_scope)
        # Devuelve 204 No Content si es exitoso
        return {"status": "success", "message": f"Permiso '{permission_id}' eliminado de {log_item_desc}.", "http_status": response.status_code}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)


# --- Funciones de Memoria (Usando una lista de SharePoint) ---
MEMORIA_LIST_NAME_FROM_SETTINGS = settings.MEMORIA_LIST_NAME

def _ensure_memory_list_exists(client: AuthenticatedHttpClient, site_id: str) -> bool:
    # Esta es una función interna, el logging principal debe hacerse en la función pública que la llama.
    try:
        url_get_list = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/lists/{MEMORIA_LIST_NAME_FROM_SETTINGS}?$select=id"
        sites_read_scope = getattr(settings, 'GRAPH_SCOPE_SITES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        try:
            logger.debug(f"Verificando existencia de lista memoria '{MEMORIA_LIST_NAME_FROM_SETTINGS}' en sitio '{site_id}'.")
            client.get(url_get_list, scope=sites_read_scope)
            logger.info(f"Lista memoria '{MEMORIA_LIST_NAME_FROM_SETTINGS}' ya existe en sitio '{site_id}'.")
            return True
        except requests.exceptions.HTTPError as http_err:
            if (http_err.response is not None and http_err.response.status_code == 404):
                logger.info(f"Lista memoria '{MEMORIA_LIST_NAME_FROM_SETTINGS}' no encontrada. Intentando crearla en sitio '{site_id}'.")
                columnas_default = [
                    {"name": "SessionID", "text": {}}, 
                    {"name": "Clave", "text": {}}, 
                    {"name": "Valor", "text": {"allowMultipleLines": True, "textType": "plain"}}, 
                    {"name": "Timestamp", "dateTime": {"displayAs": "default", "format": "dateTime"}}
                ]
                create_params = {
                    "site_id": site_id, 
                    "nombre_lista": MEMORIA_LIST_NAME_FROM_SETTINGS, 
                    "columnas": columnas_default, 
                    "template": "genericList"
                }
                # Llamar a la acción pública create_list para crearla
                creation_response = create_list(client, create_params)
                if creation_response.get("status") == "success":
                    logger.info(f"Lista memoria '{MEMORIA_LIST_NAME_FROM_SETTINGS}' creada exitosamente en sitio '{site_id}'.")
                    return True
                else:
                    logger.error(f"Fallo al crear lista memoria '{MEMORIA_LIST_NAME_FROM_SETTINGS}'. Respuesta: {creation_response}")
                    return False
            else: 
                raise # Re-lanzar otros errores HTTP
    except Exception as e: 
        logger.error(f"Error crítico asegurando la existencia de la lista memoria '{MEMORIA_LIST_NAME_FROM_SETTINGS}' en sitio '{site_id}': {e}", exc_info=True)
        return False

def memory_ensure_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando memory_ensure_list con params: %s", params)
    action_name = "memory_ensure_list"
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        success = _ensure_memory_list_exists(client, target_site_id)
        if success: 
            return {"status": "success", "message": f"Lista memoria '{MEMORIA_LIST_NAME_FROM_SETTINGS}' asegurada (existente o creada) en sitio '{target_site_id}'."}
        else:
            return {"status": "error", "action": action_name, "message": f"No se pudo asegurar/crear la lista memoria '{MEMORIA_LIST_NAME_FROM_SETTINGS}' en sitio '{target_site_id}'. Revise los logs para detalles."}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def memory_save(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando memory_save con params (valor omitido del log): %s", {k:v for k,v in params.items() if k != 'valor'})
    action_name = "memory_save"

    session_id: Optional[str] = params.get("session_id")
    clave: Optional[str] = params.get("clave")
    valor: Any = params.get("valor") # Puede ser cualquier tipo serializable a JSON

    if not session_id or not clave or valor is None: 
        return _handle_graph_api_error(ValueError("'session_id', 'clave', y 'valor' son requeridos para memory_save."),action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        # Asegurar que la lista exista
        if _ensure_memory_list_exists(client, target_site_id) is not True:
            return {"status": "error", "action": action_name, "message": f"No se pudo asegurar/crear la lista memoria '{MEMORIA_LIST_NAME_FROM_SETTINGS}' en sitio '{target_site_id}'."}

        valor_str = json.dumps(valor) # Serializar el valor a string JSON para almacenarlo
        
        # Buscar si ya existe un item con esa SessionID y Clave
        filter_q = f"fields/SessionID eq '{session_id}' and fields/Clave eq '{clave}'"
        list_params = {
            "site_id": target_site_id,
            "site_identifier": params.get("site_identifier", params.get("site_id")), # Para _obtener_site_id_sp dentro de list_list_items
            "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, 
            "filter_query": filter_q, 
            "top_per_page": 1, 
            "max_items_total": 1, 
            "select": "id", # Solo necesitamos el ID para saber si existe
            "expand": "fields(select=Id)" # O $select=id,@odata.etag
        }
        existing_items_response = list_list_items(client, list_params)
        
        item_id_to_update: Optional[str] = None
        # item_etag_for_update: Optional[str] = None # ETag no se obtiene fácilmente así, y puede causar fallos si es viejo.
                                                # Actualizar sin ETag es más simple para este caso de uso.
        
        if existing_items_response.get("status") == "success":
            items_value = existing_items_response.get("data", {}).get("value", [])
            if items_value and isinstance(items_value, list) and len(items_value) > 0:
                item_info = items_value[0]
                item_id_to_update = item_info.get("id")
                # item_etag_for_update = item_info.get("@odata.etag")
                logger.info(f"Item existente encontrado para memoria (SessionID: {session_id}, Clave: {clave}). ID: {item_id_to_update}. Se actualizará.")
        else:
            logger.warning(f"No se pudo verificar si existe item para memoria (SessionID: {session_id}, Clave: {clave}) debido a error listando: {existing_items_response}. Se intentará crear uno nuevo.")

        datos_campos_payload = {
            "SessionID": session_id, 
            "Clave": clave, 
            "Valor": valor_str, 
            "Timestamp": _get_current_timestamp_iso_z() # Guardar timestamp de la operación
        }

        if item_id_to_update:
            # Actualizar item existente
            update_params = {
                "site_id": target_site_id,
                "site_identifier": params.get("site_identifier", params.get("site_id")),
                "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, 
                "item_id": item_id_to_update, 
                "nuevos_valores_campos": datos_campos_payload
                # "etag": item_etag_for_update # Omitir ETag para simplicidad aquí
            }
            logger.debug(f"Actualizando item de memoria ID: {item_id_to_update} con payload: {datos_campos_payload}")
            return update_list_item(client, update_params)
        else:
            # Crear nuevo item
            add_params = {
                "site_id": target_site_id,
                "site_identifier": params.get("site_identifier", params.get("site_id")),
                "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, 
                "datos_campos": datos_campos_payload
            }
            logger.debug(f"Creando nuevo item de memoria con payload: {datos_campos_payload}")
            return add_list_item(client, add_params)
            
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def memory_get(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando memory_get con params: %s", params)
    action_name = "memory_get"

    session_id: Optional[str] = params.get("session_id")
    clave: Optional[str] = params.get("clave") # Clave específica a obtener, o None para todas las de la sesión

    if not session_id: 
        return _handle_graph_api_error(ValueError("'session_id' es requerido para memory_get."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        # No es necesario asegurar la lista aquí, si no existe, la búsqueda no devolverá nada.

        filter_parts = [f"fields/SessionID eq '{session_id}'"]
        if clave:
            filter_parts.append(f"fields/Clave eq '{clave}'")
        
        list_params = {
            "site_id": target_site_id,
            "site_identifier": params.get("site_identifier", params.get("site_id")),
            "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, 
            "filter_query": " and ".join(filter_parts), 
            "select": "id", # Para ListItem
            "expand": "fields(select=Clave,Valor,Timestamp)", # Campos de usuario
            "orderby": "fields/Timestamp desc", # Más reciente primero si hay múltiples para una clave (no debería si save es upsert)
            "max_items_total": None if not clave else 1 # Si se busca clave específica, solo 1 resultado. Si todas, paginar.
        }
        
        logger.info(f"Obteniendo memoria para SessionID: '{session_id}'" + (f", Clave: '{clave}'" if clave else ", Todas las claves"))
        items_response = list_list_items(client, list_params)
        
        if items_response.get("status") != "success":
            return items_response # Propagar error
            
        retrieved_data: Any = {} if not clave else None # Si no hay clave, devolver dict. Si hay clave, el valor o None.
        items = items_response.get("data", {}).get("value", [])
        
        if not items:
            logger.info(f"No se encontró data en memoria para SessionID: '{session_id}'" + (f", Clave: '{clave}'" if clave else "."))
            return {"status": "success", "data": retrieved_data, "message": "No se encontró data en memoria para los criterios dados."}

        if clave: # Se buscó una clave específica
            valor_str = items[0].get("fields", {}).get("Valor")
            try:
                retrieved_data = json.loads(valor_str) if valor_str else None
            except json.JSONDecodeError:
                logger.warning(f"Valor para memoria (SessionID: {session_id}, Clave: {clave}) no es JSON válido: '{valor_str}'. Devolviendo como string.")
                retrieved_data = valor_str
            logger.info(f"Memoria obtenida para SessionID: {session_id}, Clave: {clave}. Tipo de valor: {type(retrieved_data).__name__}")
        else: # Se buscan todas las claves de la sesión
            for item in items:
                item_fields = item.get("fields", {})
                current_clave = item_fields.get("Clave")
                valor_str = item_fields.get("Valor")
                if current_clave and current_clave not in retrieved_data: # Tomar el más reciente (primero por orderby)
                    try:
                        retrieved_data[current_clave] = json.loads(valor_str) if valor_str else None
                    except json.JSONDecodeError:
                        retrieved_data[current_clave] = valor_str
            logger.info(f"Memoria obtenida para SessionID: {session_id}. {len(retrieved_data)} claves recuperadas.")
            
        return {"status": "success", "data": retrieved_data}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def memory_delete(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando memory_delete con params: %s", params)
    action_name = "memory_delete"

    session_id: Optional[str] = params.get("session_id")
    clave: Optional[str] = params.get("clave") # Clave específica a eliminar, o None para toda la sesión

    if not session_id: 
        return _handle_graph_api_error(ValueError("'session_id' es requerido para memory_delete."),action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        
        filter_parts = [f"fields/SessionID eq '{session_id}'"]
        log_action_detail = f"toda la memoria para sesión '{session_id}'"
        if clave:
            filter_parts.append(f"fields/Clave eq '{clave}'")
            log_action_detail = f"memoria para clave '{clave}' de sesión '{session_id}'"
        
        list_params = {
            "site_id": target_site_id,
            "site_identifier": params.get("site_identifier", params.get("site_id")),
            "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, 
            "filter_query": " and ".join(filter_parts), 
            "select": "id", # Solo necesitamos ID para eliminar
            "max_items_total": None # Eliminar todos los que coincidan
        }
        
        logger.info(f"Buscando items de memoria para eliminar: {log_action_detail}")
        items_to_delete_resp = list_list_items(client, list_params)
        
        if items_to_delete_resp.get("status") != "success":
            return items_to_delete_resp # Propagar error
            
        items = items_to_delete_resp.get("data", {}).get("value", [])
        if not items:
            return {"status": "success", "message": f"No se encontró {log_action_detail} para eliminar."}
            
        deleted_count = 0
        errors_on_delete: List[str] = []
        logger.info(f"Se encontraron {len(items)} items de memoria para eliminar ({log_action_detail}). Procediendo con la eliminación.")
        
        for item in items:
            item_id_to_del = item.get("id")
            if item_id_to_del:
                del_params = {
                    "site_id": target_site_id,
                    "site_identifier": params.get("site_identifier", params.get("site_id")),
                    "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, 
                    "item_id": item_id_to_del
                }
                # delete_list_item ya hace logging interno.
                del_response = delete_list_item(client, del_params)
                if del_response.get("status") == "success":
                    deleted_count += 1
                else:
                    error_msg = f"Error eliminando item de memoria ID {item_id_to_del}: {del_response.get('message', 'Error desconocido')}. Detalles: {del_response.get('details')}"
                    logger.error(error_msg)
                    errors_on_delete.append(error_msg)
            else:
                logger.warning("Item encontrado sin ID durante eliminación de memoria, omitiendo.")
                
        if errors_on_delete:
            return {"status": "partial_error", "action":action_name, "message": f"{deleted_count} items de {log_action_detail} eliminados, pero ocurrieron {len(errors_on_delete)} errores.", "details": errors_on_delete, "deleted_count": deleted_count}
        
        return {"status": "success", "message": f"Memoria para {log_action_detail} eliminada exitosamente. {deleted_count} items borrados."}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def memory_list_keys(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando memory_list_keys con params: %s", params)
    action_name = "memory_list_keys"

    session_id: Optional[str] = params.get("session_id")
    if not session_id: 
        return _handle_graph_api_error(ValueError("'session_id' es requerido para memory_list_keys."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        list_params = {
            "site_id": target_site_id,
            "site_identifier": params.get("site_identifier", params.get("site_id")),
            "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, 
            "filter_query": f"fields/SessionID eq '{session_id}'", 
            "select": "id", # Para ListItem
            "expand": "fields(select=Clave)", # Solo necesitamos Clave de los campos
            "max_items_total": None # Obtener todas las claves para la sesión
        }
        
        logger.info(f"Listando claves de memoria para SessionID: '{session_id}'")
        items_response = list_list_items(client, list_params)
        
        if items_response.get("status") != "success":
            return items_response # Propagar error
            
        keys: List[str] = []
        items_value = items_response.get("data", {}).get("value", [])
        if items_value and isinstance(items_value, list):
            keys = list(set(
                item.get("fields", {}).get("Clave") 
                for item in items_value 
                if item.get("fields", {}).get("Clave") is not None
            ))
        
        logger.info(f"Se encontraron {len(keys)} claves de memoria para SessionID '{session_id}'.")
        return {"status": "success", "data": sorted(keys)} # Devolver lista ordenada de claves únicas
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def memory_export_session(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
    params = params or {}
    logger.info("Ejecutando memory_export_session con params: %s", params)
    action_name = "memory_export_session"

    session_id: Optional[str] = params.get("session_id")
    export_format: str = params.get("format", "json").lower()

    if not session_id: 
        return _handle_graph_api_error(ValueError("'session_id' es requerido para memory_export_session."), action_name, params)
    if export_format not in ["json", "csv"]: 
        return _handle_graph_api_error(ValueError("Formato de exportación no válido. Use 'json' o 'csv'."), action_name, params)
    
    # Reutilizar sp_export_list_to_format
    export_params = {
        "site_id": params.get("site_id"), # Para _obtener_site_id_sp
        "site_identifier": params.get("site_identifier", params.get("site_id")), # Para _obtener_site_id_sp
        "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS,
        "format": export_format,
        "filter_query": f"fields/SessionID eq '{session_id}'",
        "select_fields": "SessionID,Clave,Valor,Timestamp", # Campos a exportar
        "max_items_total": None # Exportar todos los items de la sesión
    }
    logger.info(f"Exportando sesión de memoria '{session_id}' a formato '{export_format}'.")
    return sp_export_list_to_format(client, export_params)

def sp_export_list_to_format(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
    # Esta función ahora devuelve Union[str, Dict[str,Any]] porque el formato CSV es un string,
    # pero los errores y el formato JSON son diccionarios.
    params = params or {}
    logger.info("Ejecutando sp_export_list_to_format con params: %s", params)
    action_name = "sp_export_list_to_format"

    lista_id_o_nombre: Optional[str] = params.get("lista_id_o_nombre")
    export_format: str = params.get("format", "json").lower()
    filter_query: Optional[str] = params.get("filter_query")
    select_fields: Optional[str] = params.get("select_fields") # Campos de 'fields' a seleccionar. Ej: "Title,Author,Created"
    max_items_total: Optional[int] = params.get('max_items_total') # Opcional

    if not lista_id_o_nombre: 
        return _handle_graph_api_error(ValueError("'lista_id_o_nombre' es requerido."), action_name, params)
    if export_format not in ["json", "csv"]: 
        return _handle_graph_api_error(ValueError("Formato de exportación no válido. Use 'json' o 'csv'."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        
        # Configurar parámetros para list_list_items
        list_items_params: Dict[str, Any] = {
            "site_id": target_site_id,
            "site_identifier": params.get("site_identifier", params.get("site_id")),
            "lista_id_o_nombre": lista_id_o_nombre,
            "max_items_total": max_items_total # Pasar el límite si existe
        }
        if filter_query: 
            list_items_params["filter_query"] = filter_query
        
        # Configurar expand y select para obtener los campos deseados
        expand_val = "fields" # Por defecto, expandir 'fields'
        select_val_listitem = "id,@odata.etag" # Campos base del ListItem
        
        if select_fields:
            expand_val = f"fields(select={select_fields})"
        else: # Si no se especifica select_fields, obtener todos los campos de usuario
            expand_val = "fields(select=*)"
            
        list_items_params["expand"] = expand_val
        list_items_params["select"] = select_val_listitem # Seleccionar campos base del ListItem además de los expandidos
        
        logger.info(f"Exportando items de lista SP '{lista_id_o_nombre}' (Sitio: '{target_site_id}') a formato '{export_format}'. Expand: '{expand_val}'")
        items_response = list_list_items(client, list_items_params)
        
        if items_response.get("status") != "success":
            return items_response # Propagar el error
            
        items_data = items_response.get("data", {}).get("value", [])
        
        # Procesar los items para extraer los 'fields' y añadir ID/ETag del ListItem
        processed_items: List[Dict[str, Any]] = []
        if items_data and isinstance(items_data, list):
            for item in items_data:
                fields = item.get("fields", {})
                # Añadir metadatos del ListItem al diccionario de campos para el export
                fields["_ListItemID_"] = item.get("id")
                fields["_ListItemETag_"] = item.get("@odata.etag")
                fields["_ListItemCreatedBy_"] = item.get("createdBy", {}).get("user", {}).get("displayName")
                fields["_ListItemCreatedDateTime_"] = item.get("createdDateTime")
                fields["_ListItemLastModifiedBy_"] = item.get("lastModifiedBy", {}).get("user", {}).get("displayName")
                fields["_ListItemLastModifiedDateTime_"] = item.get("lastModifiedDateTime")
                fields["_ListItemWebUrl_"] = item.get("webUrl")
                processed_items.append(fields)
        
        if not processed_items:
            logger.info("No se encontraron items para exportar.")
            return {"status": "success", "data": []} if export_format == "json" else ""

        if export_format == "json":
            logger.info(f"{len(processed_items)} items procesados para exportación JSON.")
            # El router FastAPI manejará la serialización a JSON si devolvemos un dict.
            # Devolver el dict directamente con status y data.
            return {"status": "success", "data": processed_items}
        
        # Para CSV
        logger.info(f"{len(processed_items)} items procesados para exportación CSV.")
        output = StringIO()
        
        # Determinar todos los posibles nombres de campo para el encabezado CSV
        all_field_keys = set()
        for item_fields_dict in processed_items:
            all_field_keys.update(item_fields_dict.keys())
        
        # Ordenar las claves, poniendo las de metadatos del ListItem primero si existen
        fieldnames_ordered = sorted(list(all_field_keys))
        meta_keys_ordered = ["_ListItemID_", "_ListItemETag_", "_ListItemWebUrl_", "_ListItemCreatedDateTime_", "_ListItemCreatedBy_", "_ListItemLastModifiedDateTime_", "_ListItemLastModifiedBy_"]
        final_fieldnames = [mk for mk in meta_keys_ordered if mk in fieldnames_ordered]
        final_fieldnames.extend([fk for fk in fieldnames_ordered if fk not in meta_keys_ordered])

        writer = csv.DictWriter(output, fieldnames=final_fieldnames, extrasaction='ignore', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(processed_items)
        
        csv_content = output.getvalue()
        output.close()
        logger.info(f"Exportación a CSV completada. Tamaño: {len(csv_content)} bytes.")
        # Para CSV, devolvemos el string directamente. El router FastAPI debe manejar esto.
        return csv_content 
        
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/sharepoint_actions.py ---