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
        if response_data.get("status") == "error" and "http_status" in response_data:
            return response_data
        return {"status": "success", "data": response_data}
    else:
        raise TypeError(f"Respuesta inesperada para metadatos, se esperaba dict pero se recibió {type(response_data)}.")

def _get_item_id_from_path_if_needed_onedrive(client: AuthenticatedHttpClient, user_id: str, item_path_or_id: str) -> Union[str, Dict[str, Any]]:
    is_likely_id = '!' in item_path_or_id or \
                   (len(item_path_or_id) > 40 and '/' not in item_path_or_id and '.' not in item_path_or_id) or \
                   item_path_or_id.startswith("driveItem_")

    if is_likely_id:
        return item_path_or_id

    logger.debug(f"'{item_path_or_id}' parece un path. Resolviendo a ID para user '{user_id}'.")
    metadata_params = {"item_id_or_path": item_path_or_id, "select": "id,name", "user_id": user_id}
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

    try:
        response_data = {}
        while current_url and len(all_items) < effective_max_items and page_count < max_pages:
            page_count += 1
            current_params_for_call = query_api_params_initial if page_count == 1 else None
            
            response_data = client.get(url=current_url, scope=scope, params=current_params_for_call)
            
            if not isinstance(response_data, dict):
                 return _handle_onedrive_api_error(TypeError(f"Respuesta inesperada: {type(response_data)}"), action_name_for_log, params)
            if response_data.get("status") == "error": return response_data

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            
            for item in page_items:
                if len(all_items) < effective_max_items:
                    all_items.append(item)
                else: break
            
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max_items: break
        
        total_count = response_data.get("@odata.count", len(all_items))
        return {"status": "success", "data": {"value": all_items, "@odata.count": total_count}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name_for_log, params)

def list_items(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "onedrive_list_items"
    logger.info(f"Ejecutando {action_name} con params: %s", params)
    
    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        ruta_param: str = params.get("ruta", "/")
        is_likely_id = not ("/" in ruta_param) and (len(ruta_param) > 40 or '!' in ruta_param or ruta_param.startswith("driveItem_"))
        item_endpoint_base = _get_od_user_item_by_id_endpoint(user_identifier, ruta_param) if is_likely_id else _get_od_user_item_by_path_endpoint(user_identifier, ruta_param)
        
        url_base = f"{item_endpoint_base}/children"

        query_api_params: Dict[str, Any] = {'$top': min(int(params.get("top_per_page", 50)), 200)}
        query_api_params['$select'] = params.get("select") or "id,name,webUrl,size,file,folder,parentReference,createdDateTime"
        if params.get("filter_query"): query_api_params['$filter'] = params.get("filter_query")
        if params.get("order_by"): query_api_params['$orderby'] = params.get("order_by")
        
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        return _onedrive_paged_request(client, url_base, files_read_scope, params, query_api_params, params.get("max_items_total"), action_name)
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def get_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "onedrive_get_item"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        return _internal_onedrive_get_item_metadata(client, user_identifier, params)
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def upload_file(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "onedrive_upload_file"
    log_params = {k:v for k,v in params.items() if k != "contenido_bytes"}
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        nombre_archivo: Optional[str] = params.get("nombre_archivo")
        contenido_bytes: Optional[bytes] = params.get("contenido_bytes")
        if not nombre_archivo or contenido_bytes is None: raise ValueError("'nombre_archivo' y 'contenido_bytes' son requeridos.")
        if not isinstance(contenido_bytes, bytes): raise TypeError("'contenido_bytes' debe ser de tipo bytes.")

        ruta_destino_relativa: str = params.get("ruta_destino_relativa", "/")
        conflict_behavior: str = params.get("conflict_behavior", "rename")
        
        clean_folder_path = ruta_destino_relativa.strip('/')
        target_file_path_for_api = f"{nombre_archivo}" if not clean_folder_path else f"{clean_folder_path}/{nombre_archivo}"
        item_endpoint_for_upload_base = _get_od_user_item_by_path_endpoint(user_identifier, target_file_path_for_api)

        file_size_mb = len(contenido_bytes) / (1024.0 * 1024.0)
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)

        if file_size_mb <= 4.0:
            url_put_simple = f"{item_endpoint_for_upload_base}/content"
            query_api_params_put = {"@microsoft.graph.conflictBehavior": conflict_behavior}
            custom_headers_put = {'Content-Type': 'application/octet-stream'}
            response_obj = client.put(url=url_put_simple, scope=files_rw_scope, params=query_api_params_put, data=contenido_bytes, headers=custom_headers_put)
            return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
        else:
            create_session_url = f"{item_endpoint_for_upload_base}/createUploadSession"
            session_body = {"item": {"@microsoft.graph.conflictBehavior": conflict_behavior}}
            response_session_obj = client.post(create_session_url, scope=files_rw_scope, json_data=session_body)
            upload_url = response_session_obj.json().get("uploadUrl")
            if not upload_url: raise ValueError("No se pudo obtener 'uploadUrl' de la sesión.")

            chunk_size = 5 * 1024 * 1024; start_byte = 0
            while start_byte < len(contenido_bytes):
                end_byte = min(start_byte + chunk_size - 1, len(contenido_bytes) - 1)
                chunk_data = contenido_bytes[start_byte : end_byte + 1]
                headers = {'Content-Length': str(len(chunk_data)), 'Content-Range': f"bytes {start_byte}-{end_byte}/{len(contenido_bytes)}"}
                chunk_response = requests.put(upload_url, headers=headers, data=chunk_data, timeout=DEFAULT_CHUNK_UPLOAD_TIMEOUT_SECONDS)
                chunk_response.raise_for_status()
                start_byte = end_byte + 1
                if chunk_response.content and chunk_response.status_code in [200, 201]:
                    return {"status": "success", "data": chunk_response.json(), "message": "Archivo subido con sesión."}
            return {"status": "success", "message": "Archivo subido con sesión, sin metadata final."}
            
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def download_file(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[bytes, Dict[str, Any]]:
    params = params or {}
    action_name = "onedrive_download_file"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")
        
        item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
        if not item_id_or_path_param: raise ValueError("'item_id_or_path' es requerido.")
        
        is_path_like = "/" in item_id_or_path_param or ("." in item_id_or_path_param and not item_id_or_path_param.startswith("driveItem_"))
        item_endpoint_base = _get_od_user_item_by_path_endpoint(user_identifier, item_id_or_path_param) if is_path_like else _get_od_user_item_by_id_endpoint(user_identifier, item_id_or_path_param)
        
        url = f"{item_endpoint_base}/content"
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        
        response_content = client.get(url, scope=files_read_scope, stream=True)
        if isinstance(response_content, bytes):
            return response_content
        else:
            raise TypeError(f"Se esperaban bytes pero se recibió {type(response_content)}.")
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def delete_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "onedrive_delete_item"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
        if not item_id_or_path_param: raise ValueError("'item_id_or_path' es requerido.")
        
        resolved_item_id = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_param)
        if isinstance(resolved_item_id, dict): return resolved_item_id
        
        item_endpoint = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id))
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.delete(item_endpoint, scope=files_rw_scope)
        return {"status": "success", "message": "Elemento eliminado.", "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def create_folder(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "onedrive_create_folder"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        nombre_carpeta: Optional[str] = params.get("nombre_carpeta")
        if not nombre_carpeta: raise ValueError("'nombre_carpeta' es requerido.")
        
        ruta_padre_relativa: str = params.get("ruta_padre_relativa", "/")
        
        parent_item_endpoint = _get_od_user_item_by_path_endpoint(user_identifier, ruta_padre_relativa)
        url = f"{parent_item_endpoint}/children"
        
        body = {"name": nombre_carpeta, "folder": {}, "@microsoft.graph.conflictBehavior": params.get("conflict_behavior", "fail")}
        
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.post(url, scope=files_rw_scope, json_data=body)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def move_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "onedrive_move_item"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        item_id_or_path_origen: Optional[str] = params.get("item_id_or_path_origen")
        parent_reference_param: Optional[Dict[str, str]] = params.get("parent_reference")
        if not item_id_or_path_origen or not parent_reference_param:
            raise ValueError("'item_id_or_path_origen' y 'parent_reference' son requeridos.")
        
        resolved_item_id = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_origen)
        if isinstance(resolved_item_id, dict): return resolved_item_id
        
        item_origen_endpoint = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id))
        
        body: Dict[str, Any] = {"parentReference": parent_reference_param}
        if params.get("nuevo_nombre"): body["name"] = params["nuevo_nombre"]
        
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.patch(item_origen_endpoint, scope=files_rw_scope, json_data=body)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def copy_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "onedrive_copy_item"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        item_id_or_path_origen: Optional[str] = params.get("item_id_or_path_origen")
        parent_reference_param: Optional[Dict[str, str]] = params.get("parent_reference")
        if not item_id_or_path_origen or not parent_reference_param:
            raise ValueError("'item_id_or_path_origen' y 'parent_reference' son requeridos.")
        
        resolved_item_id = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_origen)
        if isinstance(resolved_item_id, dict): return resolved_item_id
        
        item_origen_endpoint = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id))
        url_copy = f"{item_origen_endpoint}/copy"

        body_copy_payload: Dict[str, Any] = {"parentReference": parent_reference_param}
        if params.get("nuevo_nombre_copia"): body_copy_payload["name"] = params["nuevo_nombre_copia"]
        
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.post(url_copy, scope=files_rw_scope, json_data=body_copy_payload)
        
        monitor_url = response_obj.headers.get('Location')
        if response_obj.status_code == 202 and monitor_url:
            return {"status": "pending", "message": "Solicitud de copia aceptada.", "monitor_url": monitor_url, "http_status": 202}
        else:
            return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
            
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def update_item_metadata(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "onedrive_update_item_metadata"
    logger.info(f"Ejecutando {action_name}")

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
        nuevos_valores_payload: Optional[Dict[str, Any]] = params.get("nuevos_valores")
        if not item_id_or_path_param or not nuevos_valores_payload:
            raise ValueError("'item_id_or_path' y 'nuevos_valores' (dict) son requeridos.")
            
        resolved_item_id = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_param)
        if isinstance(resolved_item_id, dict): return resolved_item_id
        
        item_endpoint_for_update = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id))
        
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.patch(item_endpoint_for_update, scope=files_rw_scope, json_data=nuevos_valores_payload)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def search_items(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "onedrive_search_items"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        query_text: Optional[str] = params.get("query_text")
        if not query_text: raise ValueError("'query_text' es requerido.")

        base_drive_endpoint = _get_od_user_drive_base_endpoint(user_identifier)
        url_search = f"{base_drive_endpoint}/root/search(q='{query_text}')"

        api_query_params: Dict[str, Any] = {}
        if params.get("top"): api_query_params['$top'] = params["top"]
        if params.get("select"): api_query_params['$select'] = params["select"]
        
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_data = client.get(url_search, scope=files_read_scope, params=api_query_params)

        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data.get("value", [])}
        else:
            raise TypeError(f"Respuesta inesperada: {type(response_data)}")
            
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def get_sharing_link(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "onedrive_get_sharing_link"
    logger.info(f"Ejecutando {action_name}")

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")
        
        item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
        if not item_id_or_path_param: raise ValueError("'item_id_or_path' es requerido.")
            
        resolved_item_id = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_param)
        if isinstance(resolved_item_id, dict): return resolved_item_id

        item_endpoint = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id))
        url_create_link = f"{item_endpoint}/createLink"

        body: Dict[str, Any] = {
            "type": params.get("type", "view"),
            "scope": params.get("scope", "organization")
        }
        if params.get("password"): body["password"] = params["password"]
        if params.get("expirationDateTime"): body["expirationDateTime"] = params["expirationDateTime"]
        
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.post(url_create_link, scope=files_rw_scope, json_data=body)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)