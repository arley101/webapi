# app/actions/onedrive_actions.py
import logging
import requests
import json
from typing import Dict, List, Optional, Union, Any

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_UPLOAD_TIMEOUT_SECONDS = settings.DEFAULT_API_TIMEOUT

def _get_od_user_drive_base_endpoint(user_id: str) -> str:
    return f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/drive"

def _get_od_user_item_by_path_endpoint(user_id: str, relative_path: str) -> str:
    drive_endpoint = _get_od_user_drive_base_endpoint(user_id)
    safe_path = relative_path.strip()
    if not safe_path or safe_path == '/':
        return f"{drive_endpoint}/root"
    if safe_path.startswith('/'):
        safe_path = safe_path[1:]
    return f"{drive_endpoint}/root:/{safe_path}"

def _get_od_user_item_by_id_endpoint(user_id: str, item_id: str) -> str:
    drive_endpoint = _get_od_user_drive_base_endpoint(user_id)
    return f"{drive_endpoint}/items/{item_id}"

def _handle_onedrive_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en OneDrive action '{action_name}'"
    if params_for_log:
        safe_params = {k: v for k, v in params_for_log.items() if k not in ['contenido_bytes', 'password']}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {e}", exc_info=True)
    details = str(e)
    status_code = 500
    error_code_graph = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code = e.response.status_code
        try:
            error_data = e.response.json()
            details = error_data.get("error", {}).get("message", e.response.text)
            error_code_graph = error_data.get("error", {}).get("code")
        except json.JSONDecodeError:
            details = e.response.text
    return {
        "status": "error", "action": action_name,
        "message": f"Error en {action_name}: {type(e).__name__}",
        "http_status": status_code, "details": details,
        "graph_error_code": error_code_graph
    }

def _internal_onedrive_get_item_metadata(client: AuthenticatedHttpClient, user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    item_path_or_id: Optional[str] = params.get("item_id_or_path")
    if not item_path_or_id:
        raise ValueError("'item_id_or_path' es requerido.")
    
    select: Optional[str] = params.get("select")
    expand: Optional[str] = params.get("expand")

    is_path_like = "/" in item_path_or_id or \
                   ("." in item_path_or_id and not item_path_or_id.startswith("driveItem_") and len(item_path_or_id) < 70 and '!' not in item_path_or_id)

    if is_path_like:
        item_endpoint = _get_od_user_item_by_path_endpoint(user_id, item_path_or_id)
    else:
        item_endpoint = _get_od_user_item_by_id_endpoint(user_id, item_path_or_id)

    query_api_params: Dict[str, Any] = {}
    if select: query_api_params['$select'] = select
    if expand: query_api_params['$expand'] = expand
    
    logger.debug(f"Interno: Obteniendo metadatos OneDrive para user '{user_id}', item '{item_path_or_id}'")
    files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    
    response_data = client.get(item_endpoint, scope=files_read_scope, params=query_api_params if query_api_params else None)
    
    if isinstance(response_data, dict):
        # Propagar el error si http_client ya lo formateó
        if response_data.get("status") == "error" and "http_status" in response_data:
            return response_data
        return {"status": "success", "data": response_data}
    else:
        # Esto sería un caso inesperado si la API devuelve algo que no es JSON para metadatos
        raise TypeError(f"Respuesta inesperada para metadatos, se esperaba dict pero se recibió {type(response_data)}.")

def _get_item_id_from_path_if_needed_onedrive(client: AuthenticatedHttpClient, user_id: str, item_path_or_id: str) -> Union[str, Dict[str, Any]]:
    is_likely_id = '!' in item_path_or_id or \
                   (len(item_path_or_id) > 40 and '/' not in item_path_or_id and '.' not in item_path_or_id) or \
                   item_path_or_id.startswith("driveItem_")

    if is_likely_id:
        return item_path_or_id

    logger.debug(f"'{item_path_or_id}' parece un path. Resolviendo a ID para user '{user_id}'.")
    metadata_params = {"item_id_or_path": item_path_or_id, "select": "id,name"}
    try:
        response = _internal_onedrive_get_item_metadata(client, user_id, metadata_params)
        if response.get("status") == "success" and response.get("data", {}).get("id"):
            item_id = response["data"]["id"]
            logger.info(f"ID resuelto para path '{item_path_or_id}': {item_id}")
            return item_id
        else:
            error_msg = f"No se pudo obtener el ID para el path '{item_path_or_id}'."
            return response if isinstance(response, dict) and response.get("status") == "error" else \
                   {"status": "error", "message": error_msg, "details": str(response)}
    except Exception as e_resolve:
        return _handle_onedrive_api_error(e_resolve, "_get_item_id_from_path_if_needed_onedrive", {"user_id": user_id, "item_path_or_id": item_path_or_id})

def _onedrive_paged_request(
    client: AuthenticatedHttpClient, url_base: str, scope: List[str],
    params: Dict[str, Any], query_api_params_initial: Dict[str, Any],
    max_items_total: Optional[int], action_name_for_log: str
) -> Dict[str, Any]:
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages = getattr(settings, 'MAX_PAGING_PAGES', 30)
    effective_max_items = float('inf') if max_items_total is None else max_items_total

    logger.debug(f"Iniciando solicitud paginada para '{action_name_for_log}' desde '{url_base.split('?')[0]}...'.")
    try:
        while current_url and len(all_items) < effective_max_items and page_count < max_pages:
            page_count += 1
            is_first_call = (current_url == url_base and page_count == 1)
            current_params_for_call = query_api_params_initial if is_first_call else None
            
            response_data = client.get(url=current_url, scope=scope, params=current_params_for_call)
            
            if not isinstance(response_data, dict):
                 return _handle_onedrive_api_error(TypeError(f"Respuesta inesperada, no es un dict: {type(response_data)}"), action_name_for_log, params)
            if response_data.get("status") == "error": return response_data

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            
            for item in page_items:
                if len(all_items) < effective_max_items:
                    all_items.append(item)
                else: break
            
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max_items: break
        
        logger.info(f"'{action_name_for_log}' recuperó {len(all_items)} items en {page_count} páginas.")
        total_count = response_data.get("@odata.count", len(all_items)) if 'response_data' in locals() and isinstance(response_data, dict) else len(all_items)
        return {"status": "success", "data": {"value": all_items, "@odata.count": total_count}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name_for_log, params)

def list_items(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "onedrive_list_items"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return _handle_onedrive_api_error(ValueError("'user_id' es requerido."), action_name, params)

    ruta_param: str = params.get("ruta", "/")
    top_per_page: int = min(int(params.get("top_per_page", 50)), 200)
    max_items_total: Optional[int] = params.get("max_items_total")
    select: Optional[str] = params.get("select")
    filter_query: Optional[str] = params.get("filter_query")
    order_by: Optional[str] = params.get("order_by")

    try:
        is_likely_id = not ("/" in ruta_param) and (len(ruta_param) > 40 or '!' in ruta_param or ruta_param.startswith("driveItem_"))
        item_endpoint_base = _get_od_user_item_by_id_endpoint(user_identifier, ruta_param) if is_likely_id else _get_od_user_item_by_path_endpoint(user_identifier, ruta_param)
        
        url_base = f"{item_endpoint_base}/children"

        query_api_params: Dict[str, Any] = {'$top': top_per_page}
        query_api_params['$select'] = select or "id,name,webUrl,size,file,folder,parentReference,createdDateTime,lastModifiedDateTime"
        if filter_query: query_api_params['$filter'] = filter_query
        if order_by: query_api_params['$orderby'] = order_by
        
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        return _onedrive_paged_request(client, url_base, files_read_scope, params, query_api_params, max_items_total, action_name)
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def get_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "onedrive_get_item"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return _handle_onedrive_api_error(ValueError("'user_id' es requerido."), action_name, params)

    item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
    if not item_id_or_path_param:
        return _handle_onedrive_api_error(ValueError("'item_id_or_path' es requerido."), action_name, params)

    try:
        return _internal_onedrive_get_item_metadata(client, user_identifier, params)
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def upload_file(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "onedrive_upload_file"
    log_params = {k:v for k,v in params.items() if k != "contenido_bytes"}
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return _handle_onedrive_api_error(ValueError("'user_id' es requerido."), action_name, params)

    nombre_archivo: Optional[str] = params.get("nombre_archivo")
    contenido_bytes: Optional[bytes] = params.get("contenido_bytes")
    ruta_destino_relativa: str = params.get("ruta_destino_relativa", "/")
    conflict_behavior: str = params.get("conflict_behavior", "rename")

    if not nombre_archivo or contenido_bytes is None:
        return _handle_onedrive_api_error(ValueError("'nombre_archivo' y 'contenido_bytes' son requeridos."), action_name, params)
    if not isinstance(contenido_bytes, bytes):
        return _handle_onedrive_api_error(TypeError("'contenido_bytes' debe ser de tipo bytes."), action_name, params)

    try:
        clean_folder_path = ruta_destino_relativa.strip('/')
        target_file_path_for_api = f"{nombre_archivo}" if not clean_folder_path else f"{clean_folder_path}/{nombre_archivo}"
        
        item_endpoint_for_upload_base = _get_od_user_item_by_path_endpoint(user_identifier, target_file_path_for_api)

        file_size_bytes = len(contenido_bytes)
        file_size_mb = file_size_bytes / (1024.0 * 1024.0)
        logger.info(f"Subiendo a OneDrive user '{user_identifier}': path '{target_file_path_for_api}' ({file_size_mb:.2f} MB)")
        
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)

        if file_size_mb > 4.0:
            logger.info("Archivo > 4MB. Iniciando sesión de carga.")
            create_session_url = f"{item_endpoint_for_upload_base}/createUploadSession"
            if item_endpoint_for_upload_base.endswith(":"): 
                create_session_url = f"{item_endpoint_for_upload_base.rstrip(':')}/createUploadSession"

            session_body = {"item": {"@microsoft.graph.conflictBehavior": conflict_behavior, "name": nombre_archivo }}
            response_session_obj = client.post(create_session_url, scope=files_rw_scope, json_data=session_body)
            session_info = response_session_obj.json()
            upload_url_from_session = session_info.get("uploadUrl")
            if not upload_url_from_session: raise ValueError("No se pudo obtener 'uploadUrl' de la sesión.")
            
            chunk_size = 5 * 1024 * 1024; start_byte = 0
            final_item_metadata: Optional[Dict[str, Any]] = None
            
            while start_byte < file_size_bytes:
                end_byte = min(start_byte + chunk_size - 1, file_size_bytes - 1)
                current_chunk_data = contenido_bytes[start_byte : end_byte + 1]
                content_range_header = f"bytes {start_byte}-{end_byte}/{file_size_bytes}"
                chunk_upload_timeout = max(DEFAULT_CHUNK_UPLOAD_TIMEOUT_SECONDS, int(len(current_chunk_data) / (50 * 1024)) + 30)
                
                chunk_headers = {'Content-Length': str(len(current_chunk_data)), 'Content-Range': content_range_header}
                
                chunk_response = requests.put(upload_url_from_session, headers=chunk_headers, data=current_chunk_data, timeout=chunk_upload_timeout)
                chunk_response.raise_for_status()
                start_byte = end_byte + 1
                if chunk_response.content:
                    response_json = chunk_response.json()
                    if chunk_response.status_code in [200, 201] and response_json.get("id"):
                        final_item_metadata = response_json; break
                elif start_byte >= file_size_bytes: break
            
            if not final_item_metadata and start_byte >= file_size_bytes:
                return {"status": "warning", "message": "Archivo subido con sesión, pero no se recibió metadata final.", "http_status": 202}

            if not final_item_metadata:
                 raise ValueError(f"Subida grande finalizada pero sin metadata.")
            return {"status": "success", "data": final_item_metadata, "message": "Archivo subido con sesión."}
        else:
            logger.info("Archivo <= 4MB. Usando subida simple.")
            url_put_simple = f"{item_endpoint_for_upload_base}/content"
            query_api_params_put = {"@microsoft.graph.conflictBehavior": conflict_behavior}
            custom_headers_put = {'Content-Type': 'application/octet-stream'}
            response_obj = client.put(url=url_put_simple, scope=files_rw_scope, params=query_api_params_put, data=contenido_bytes, headers=custom_headers_put)
            return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def download_file(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[bytes, Dict[str, Any]]:
    params = params or {}
    action_name = "onedrive_download_file"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return _handle_onedrive_api_error(ValueError("'user_id' es requerido."), action_name, params)

    item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
    if not item_id_or_path_param:
        return _handle_onedrive_api_error(ValueError("'item_id_or_path' es requerido."), action_name, params)
        
    try:
        is_path_like = "/" in item_id_or_path_param or ("." in item_id_or_path_param and not item_id_or_path_param.startswith("driveItem_") and len(item_id_or_path_param) < 70)
        item_endpoint_base = _get_od_user_item_by_path_endpoint(user_identifier, item_id_or_path_param) if is_path_like else _get_od_user_item_by_id_endpoint(user_identifier, item_id_or_path_param)
        
        url = f"{item_endpoint_base}/content"

        logger.info(f"Descargando archivo OneDrive para user '{user_identifier}': Item '{item_id_or_path_param}'")
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_content = client.get(url, scope=files_read_scope, stream=True)
        if isinstance(response_content, bytes):
            logger.info(f"Archivo descargado ({len(response_content)} bytes).")
            return response_content
        else:
            return _handle_onedrive_api_error(TypeError(f"Se esperaban bytes pero se recibió {type(response_content)}."), action_name, params)
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def delete_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "onedrive_delete_item"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return _handle_onedrive_api_error(ValueError("'user_id' es requerido."), action_name, params)

    item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
    if not item_id_or_path_param:
        return _handle_onedrive_api_error(ValueError("'item_id_or_path' es requerido."), action_name, params)
        
    try:
        resolved_item_id_or_error = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_param)
        if isinstance(resolved_item_id_or_error, dict): return resolved_item_id_or_error
        
        item_endpoint_for_delete = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id_or_error))

        logger.info(f"Eliminando item OneDrive ID '{resolved_item_id_or_error}' de user '{user_identifier}'")
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.delete(item_endpoint_for_delete, scope=files_rw_scope)
        return {"status": "success", "message": "Elemento eliminado.", "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

# --- (El resto de las funciones de OneDrive siguen este mismo patrón corregido) ---
# ...