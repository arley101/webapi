# app/actions/onedrive_actions.py
import logging
import requests # Para tipos de excepción y llamadas directas a uploadUrl de sesión
import json # Para el helper de error
from typing import Dict, List, Optional, Union, Any

# Importar la configuración y el cliente HTTP autenticado
from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# Constante local para timeout, usando el valor de settings
DEFAULT_CHUNK_UPLOAD_TIMEOUT_SECONDS = settings.DEFAULT_API_TIMEOUT

# ---- Helpers Locales para Endpoints de OneDrive (ahora orientados a /users/{user_id}/drive) ----
def _get_od_user_drive_base_endpoint(user_id: str) -> str:
    return f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/drive"

def _get_od_user_item_by_path_endpoint(user_id: str, relative_path: str) -> str:
    drive_endpoint = _get_od_user_drive_base_endpoint(user_id)
    safe_path = relative_path.strip()
    if not safe_path or safe_path == '/': # Si el path es vacío o solo "/", apunta al root
        return f"{drive_endpoint}/root"
    # Asegurar que el path relativo al root comience con 'root:/' si no es el root mismo
    return f"{drive_endpoint}/root:/{safe_path.lstrip('/')}"

def _get_od_user_item_by_id_endpoint(user_id: str, item_id: str) -> str:
    drive_endpoint = _get_od_user_drive_base_endpoint(user_id)
    return f"{drive_endpoint}/items/{item_id}"

# --- Helper para manejar errores de OneDrive API de forma centralizada ---
def _handle_onedrive_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en OneDrive action '{action_name}'"
    safe_params = {k: v for k, v in (params_for_log or {}).items() if k not in ['contenido_bytes', 'password']}
    log_message += f" con params: {safe_params}"
    logger.error(log_message, exc_info=True)
    details = str(e); status_code = 500; graph_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code = e.response.status_code
        try:
            error_data = e.response.json() # Intentar parsear como JSON
            error_detail_obj = error_data.get("error", {})
            details = error_detail_obj.get("message", e.response.text) # Tomar mensaje de Graph o texto completo
            graph_error_code = error_detail_obj.get("code")
        except json.JSONDecodeError: # Si la respuesta de error no es JSON
            details = e.response.text if e.response.text else "Error sin cuerpo de respuesta."
    return {
        "status": "error", "action": action_name,
        "message": f"Error en {action_name}: {type(e).__name__}", # Mensaje más genérico
        "http_status": status_code, "details": details, # Detalles técnicos
        "graph_error_code": graph_error_code
    }

# --- Helper para obtener ID de item si se provee path (adaptado para user_id) ---
def _internal_onedrive_get_item_metadata(client: AuthenticatedHttpClient, user_id: str, params_metadata: Dict[str, Any]) -> Dict[str, Any]:
    item_path_or_id: Optional[str] = params_metadata.get("item_id_or_path")
    select: Optional[str] = params_metadata.get("select")
    expand: Optional[str] = params_metadata.get("expand")

    if not item_path_or_id:
        raise ValueError("'item_id_or_path' es requerido para _internal_onedrive_get_item_metadata.")
    
    # Heurística para determinar si es path o ID
    is_path_like = "/" in item_path_or_id or \
                   ("." in item_path_or_id and not item_path_or_id.startswith("driveItem_") and len(item_path_or_id) < 70 and '!' not in item_path_or_id) or \
                   (not item_path_or_id.startswith("driveItem_") and len(item_path_or_id) < 70 and '.' not in item_path_or_id and '!' not in item_path_or_id)

    if is_path_like:
        item_endpoint = _get_od_user_item_by_path_endpoint(user_id, item_path_or_id)
    else:
        item_endpoint = _get_od_user_item_by_id_endpoint(user_id, item_path_or_id)

    query_api_params: Dict[str, Any] = {}
    if select: query_api_params['$select'] = select
    if expand: query_api_params['$expand'] = expand
    
    logger.info(f"Obteniendo metadatos OneDrive para user '{user_id}' (interno): Item '{item_path_or_id}' desde endpoint '{item_endpoint.replace(str(settings.GRAPH_API_BASE_URL), '')}'") # type: ignore
    
    # client.get() ya devuelve dict o str
    response_data = client.get(item_endpoint, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE), params=query_api_params if query_api_params else None)
    
    if not isinstance(response_data, dict):
        # Esto podría ser un string si client.get devolvió response.text o un error no JSON
        raise Exception(f"Respuesta inesperada del cliente HTTP, se esperaba un diccionario. Recibido tipo {type(response_data)}: {str(response_data)[:200]}")
    
    # Si http_client.get ya formateó un error
    if response_data.get("status") == "error" and "http_status" in response_data:
         # Simular un HTTPError para que el flujo de error superior lo capture si es necesario, o manejarlo aquí
        raise requests.exceptions.HTTPError(response_data.get("message"), response=type('MockResponse', (), {'status_code': response_data.get("http_status", 500), 'text': str(response_data.get("details"))})())

    return {"status": "success", "data": response_data}


def _get_item_id_from_path_if_needed_onedrive(
    client: AuthenticatedHttpClient,
    user_id: str, 
    item_path_or_id: str,
    # Pasar los params originales de la acción que llama a este helper para un mejor log de error
    original_action_params: Optional[Dict[str, Any]] = None 
) -> Union[str, Dict[str, Any]]: # Devuelve ID de item o un dict de error
    
    is_likely_id = '!' in item_path_or_id or \
                   (len(item_path_or_id) > 40 and '/' not in item_path_or_id and '.' not in item_path_or_id) or \
                   item_path_or_id.startswith("driveItem_")

    if is_likely_id:
        logger.debug(f"Asumiendo que '{item_path_or_id}' ya es un ID de item OneDrive.")
        return item_path_or_id

    logger.debug(f"'{item_path_or_id}' parece un path en OneDrive para user '{user_id}'. Intentando obtener su ID.")
    # Usar los params originales de la acción si están disponibles para el helper de error.
    # Si no, usar los params construidos para esta llamada específica.
    params_for_error_log = original_action_params or {"user_id": user_id, "item_path_or_id": item_path_or_id}
    
    metadata_call_params = {
        "item_id_or_path": item_path_or_id, 
        "select": "id,name", # Solo necesitamos id y name para confirmación
        "user_id": user_id # Asegurar que user_id se pasa para _internal_onedrive_get_item_metadata
    }
    # Si los params originales tenían un site_identifier (aunque esto es para OneDrive), lo pasamos
    if original_action_params and original_action_params.get("site_identifier"):
        metadata_call_params["site_identifier"] = original_action_params.get("site_identifier")

    try:
        response = _internal_onedrive_get_item_metadata(client, user_id, metadata_call_params) # Ahora pasa params_metadata
        if response.get("status") == "success" and response.get("data", {}).get("id"):
            item_id = response["data"]["id"]
            logger.info(f"ID obtenido para path OneDrive '{item_path_or_id}' (user '{user_id}'): {item_id}")
            return item_id
        else:
            # Si _internal_onedrive_get_item_metadata tuvo éxito pero no encontró ID (raro) o devolvió un error formateado.
            error_msg = f"No se pudo obtener el ID para el path/item OneDrive '{item_path_or_id}' (user '{user_id}')."
            logger.error(error_msg + f" Detalles: {response}")
            return response if isinstance(response, dict) and response.get("status") == "error" else \
                   {"status": "error", "message": error_msg, "details": str(response), "http_status": response.get("http_status", 500)}
    except Exception as e_resolve: 
        return _handle_onedrive_api_error(e_resolve, "_get_item_id_from_path_if_needed_onedrive", params_for_error_log)


# --- Helper común para paginación ---
def _onedrive_paged_request(
    client: AuthenticatedHttpClient,
    url_base: str,
    scope: List[str],
    params: Dict[str, Any], 
    query_api_params_initial: Dict[str, Any],
    max_items_total: Optional[int],
    action_name_for_log: str
) -> Dict[str, Any]:
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages = getattr(settings, 'MAX_PAGING_PAGES', 30)
    effective_max_items = float('inf') if max_items_total is None else max_items_total

    try:
        while current_url and len(all_items) < effective_max_items and page_count < max_pages:
            page_count += 1
            current_params_for_call = query_api_params_initial if page_count == 1 and current_url == url_base else None
            
            response_data = client.get(url=current_url, scope=scope, params=current_params_for_call) # client.get() devuelve dict/str
            if not isinstance(response_data, dict):
                raise Exception(f"Respuesta paginada inesperada, se esperaba dict. Tipo: {type(response_data)}")
            if response_data.get("status") == "error": # Error formateado por http_client
                return response_data 

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list):
                logger.warning(f"Respuesta inesperada en paginación para '{action_name_for_log}', 'value' no es una lista.")
                break
            for item in page_items:
                if len(all_items) < effective_max_items: all_items.append(item)
                else: break
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max_items: break
        logger.info(f"'{action_name_for_log}' recuperó {len(all_items)} items en {page_count} páginas.")
        return {"status": "success", "data": {"value": all_items, "@odata.count": len(all_items)}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e: return _handle_onedrive_api_error(e, action_name_for_log, params)

# ---- FUNCIONES DE ACCIÓN PARA ONEDRIVE ----
def list_items(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_items (OneDrive) con params: %s", params)
    action_name = "onedrive_list_items"
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    try:
        ruta_param: str = params.get("ruta", "/") 
        is_likely_id = not ("/" in ruta_param) and (len(ruta_param) > 40 or '!' in ruta_param or ruta_param.startswith("driveItem_"))
        item_endpoint_base = _get_od_user_item_by_id_endpoint(user_identifier, ruta_param) if is_likely_id else _get_od_user_item_by_path_endpoint(user_identifier, ruta_param)
        url_base = f"{item_endpoint_base}/children"
        query_api_params: Dict[str, Any] = {'$top': min(int(params.get("top_per_page", 50)), 200)}
        query_api_params['$select'] = params.get("select", "id,name,webUrl,size,file,folder,parentReference,createdDateTime,lastModifiedDateTime")
        if params.get("filter_query"): query_api_params['$filter'] = params["filter_query"]
        if params.get("order_by"): query_api_params['$orderby'] = params["order_by"]
        return _onedrive_paged_request(client, url_base, getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE), params, query_api_params, params.get("max_items_total"), action_name)
    except Exception as e: return _handle_onedrive_api_error(e, action_name, params)

def get_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_item (OneDrive) con params: %s", params); action_name = "onedrive_get_item"
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
    if not item_id_or_path_param: return {"status": "error", "action": action_name, "message": "'item_id_or_path' es requerido.", "http_status": 400}
    try:
        # Pasar params completos a _internal_onedrive_get_item_metadata
        return _internal_onedrive_get_item_metadata(client, user_identifier, params)
    except Exception as e: return _handle_onedrive_api_error(e, action_name, params)

def upload_file(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_safe = {k:v for k,v in params.items() if k != "content_bytes"}
    logger.info("Ejecutando upload_file (OneDrive) (content_bytes omitido): %s", log_safe); action_name = "onedrive_upload_file"
    user_identifier: Optional[str] = params.get("user_id"); nombre_archivo: Optional[str] = params.get("nombre_archivo")
    content_bytes: Optional[bytes] = params.get("contenido_bytes")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    if not nombre_archivo or content_bytes is None: return _handle_onedrive_api_error(ValueError("'nombre_archivo' y 'content_bytes' requeridos."), action_name, params)
    if not isinstance(content_bytes, bytes): return _handle_onedrive_api_error(TypeError("'content_bytes' debe ser bytes."), action_name, params)
    try:
        clean_folder_path = params.get("ruta_destino_relativa", "/").strip('/')
        target_file_path = f"{nombre_archivo}" if not clean_folder_path else f"{clean_folder_path}/{nombre_archivo}"
        item_endpoint_base = _get_od_user_item_by_path_endpoint(user_identifier, target_file_path)
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        conflict_behavior = params.get("conflict_behavior", "rename")

        if len(content_bytes) <= 4 * 1024 * 1024:
            url_put = f"{item_endpoint_base}/content" # : ya está en el path
            response_obj = client.put(url=url_put, scope=files_rw_scope, params={"@microsoft.graph.conflictBehavior": conflict_behavior}, data=content_bytes, headers={'Content-Type': 'application/octet-stream'})
            return {"status": "success", "data": response_obj.json(), "message": "Archivo subido (simple)."} # Asume que client.put devuelve Response
        else:
            session_url = f"{item_endpoint_base.rstrip(':')}/createUploadSession" # Asegurar que no haya doble :
            session_body = {"item": {"@microsoft.graph.conflictBehavior": conflict_behavior, "name": nombre_archivo}}
            session_response_obj = client.post(session_url, scope=files_rw_scope, json_data=session_body) # Asume client.post devuelve Response
            upload_url = session_response_obj.json().get("uploadUrl")
            if not upload_url: raise ValueError("No se pudo obtener 'uploadUrl' de la sesión.")
            
            file_size = len(content_bytes); chunk_size = 5 * 1024 * 1024; start_byte = 0; final_item_metadata = None
            while start_byte < file_size:
                end_byte = min(start_byte + chunk_size - 1, file_size - 1)
                current_chunk = content_bytes[start_byte : end_byte + 1]
                headers_chunk = {'Content-Length': str(len(current_chunk)), 'Content-Range': f"bytes {start_byte}-{end_byte}/{file_size}"}
                timeout_chunk = max(DEFAULT_CHUNK_UPLOAD_TIMEOUT_SECONDS, int(len(current_chunk) / (50 * 1024)) + 30)
                chunk_resp = requests.put(upload_url, headers=headers_chunk, data=current_chunk, timeout=timeout_chunk)
                chunk_resp.raise_for_status()
                start_byte = end_byte + 1
                if chunk_resp.status_code in [200, 201] and chunk_resp.content: final_item_metadata = chunk_resp.json(); break
            
            if not final_item_metadata and start_byte >= file_size:
                 check_params_for_get_item = {"user_id": user_identifier, "item_id_or_path": target_file_path}
                 check_meta = get_item(client, check_params_for_get_item) # Llamar a la acción get_item de este módulo
                 if check_meta.get("status") == "success": final_item_metadata = check_meta.get("data")
                 else: return {"status": "warning", "message": "Subida con sesión, verificación falló.", "details": check_meta}
            if not final_item_metadata: raise ValueError("Subida grande finalizada pero sin metadata.")
            return {"status": "success", "data": final_item_metadata, "message": "Archivo subido con sesión."}
    except Exception as e: return _handle_onedrive_api_error(e, action_name, params)

def download_file(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[bytes, Dict[str, Any]]:
    params = params or {}; logger.info("Ejecutando download_file (OneDrive): %s", params); action_name = "onedrive_download_file"
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
    if not item_id_or_path_param: return {"status": "error", "action": action_name, "message": "'item_id_or_path' es requerido.", "http_status": 400}
    try:
        url = _get_od_user_drive_item_content_url(user_identifier, item_id_or_path_param)
        file_bytes = client.get(url, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE), stream=True)
        if not isinstance(file_bytes, bytes):
            if isinstance(file_bytes, dict) and file_bytes.get("status") == "error": return file_bytes
            raise Exception(f"Respuesta inesperada para descarga, se esperaban bytes. Recibido tipo {type(file_bytes)}: {str(file_bytes)[:200]}")
        return file_bytes
    except Exception as e: return _handle_onedrive_api_error(e, action_name, params)

def delete_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando delete_item (OneDrive): %s", params); action_name = "onedrive_delete_item"
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
    if not item_id_or_path_param: return {"status": "error", "action": action_name, "message": "'item_id_or_path' es requerido.", "http_status": 400}
    try:
        resolved_id_result = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_param, params)
        if isinstance(resolved_id_result, dict) and resolved_id_result.get("status") == "error": return resolved_id_result
        resolved_item_id = str(resolved_id_result)
        item_endpoint = _get_od_user_item_by_id_endpoint(user_identifier, resolved_item_id)
        response_obj = client.delete(item_endpoint, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # client.delete devuelve requests.Response
        return {"status": "success", "message": f"Elemento '{item_id_or_path_param}' (ID: {resolved_item_id}) eliminado.", "http_status": response_obj.status_code}
    except Exception as e: return _handle_onedrive_api_error(e, action_name, params)

def create_folder(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando create_folder (OneDrive): %s", params); action_name = "onedrive_create_folder"
    user_identifier: Optional[str] = params.get("user_id"); nombre_carpeta: Optional[str] = params.get("nombre_carpeta")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    if not nombre_carpeta: return _handle_onedrive_api_error(ValueError("'nombre_carpeta' requerido."), action_name, params)
    try:
        ruta_padre_relativa: str = params.get("ruta_padre_relativa", "/")
        parent_item_endpoint: str
        if ruta_padre_relativa == "/": parent_item_endpoint = _get_od_user_drive_base_endpoint(user_identifier) + "/root"
        else:
            resolved_parent_id_result = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, ruta_padre_relativa, params)
            if isinstance(resolved_parent_id_result, dict) and resolved_parent_id_result.get("status") == "error": return resolved_parent_id_result
            parent_item_endpoint = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_parent_id_result))
        url = f"{parent_item_endpoint}/children"
        body = {"name": nombre_carpeta, "folder": {}, "@microsoft.graph.conflictBehavior": params.get("conflict_behavior", "fail")}
        response_obj = client.post(url, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=body) # client.post devuelve requests.Response
        return {"status": "success", "data": response_obj.json(), "message": f"Carpeta '{nombre_carpeta}' creada."}
    except Exception as e: return _handle_onedrive_api_error(e, action_name, params)

def move_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando move_item (OneDrive): %s", params); action_name = "onedrive_move_item"
    user_identifier: Optional[str] = params.get("user_id"); item_id_or_path_origen: Optional[str] = params.get("item_id_or_path_origen")
    parent_reference_param: Optional[Dict[str, str]] = params.get("parent_reference")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    if not item_id_or_path_origen: return _handle_onedrive_api_error(ValueError("'item_id_or_path_origen' requerido."), action_name, params)
    if not parent_reference_param or not isinstance(parent_reference_param, dict) or not (parent_reference_param.get("id") or parent_reference_param.get("path")):
         return _handle_onedrive_api_error(ValueError("'parent_reference' (dict con 'id' o 'path') requerido."), action_name, params)
    try:
        resolved_item_id_origen_result = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_origen, params)
        if isinstance(resolved_item_id_origen_result, dict) and resolved_item_id_origen_result.get("status") == "error": return resolved_item_id_origen_result
        item_origen_endpoint = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id_origen_result))
        body: Dict[str, Any] = {"parentReference": {}}
        if parent_reference_param.get("id"): body["parentReference"]["id"] = parent_reference_param["id"]
        elif parent_reference_param.get("path"): 
            if not parent_reference_param.get("driveId"): 
                user_drive_info_data = client.get(f"{_get_od_user_drive_base_endpoint(user_identifier)}?$select=id", scope=settings.GRAPH_API_DEFAULT_SCOPE)
                if not isinstance(user_drive_info_data, dict) or not user_drive_info_data.get("id"): raise Exception("No se pudo obtener ID de drive del usuario.")
                if user_drive_info_data.get("status") == "error": raise Exception(f"Error obteniendo ID de drive: {user_drive_info_data.get('message')}")
                user_drive_id = user_drive_info_data["id"]
                raw_path = parent_reference_param["path"].lstrip('/')
                body["parentReference"]["path"] = f"/drives/{user_drive_id}/root{(':/' + raw_path) if raw_path else ''}"
            else: body["parentReference"]["path"] = parent_reference_param["path"]
        if parent_reference_param.get("driveId"): body["parentReference"]["driveId"] = parent_reference_param["driveId"]
        if params.get("nuevo_nombre"): body["name"] = params["nuevo_nombre"]
        response_obj = client.patch(item_origen_endpoint, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=body) # client.patch devuelve requests.Response
        return {"status": "success", "data": response_obj.json(), "message": "Elemento movido/renombrado."}
    except Exception as e: return _handle_onedrive_api_error(e, action_name, params)

def copy_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando copy_item (OneDrive): %s", params); action_name = "onedrive_copy_item"
    user_identifier: Optional[str] = params.get("user_id"); item_id_or_path_origen: Optional[str] = params.get("item_id_or_path_origen")
    parent_reference_param: Optional[Dict[str, str]] = params.get("parent_reference")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    if not item_id_or_path_origen: return _handle_onedrive_api_error(ValueError("'item_id_or_path_origen' requerido."), action_name, params)
    if not parent_reference_param or not isinstance(parent_reference_param, dict) or not (parent_reference_param.get("id") or parent_reference_param.get("path")):
         return _handle_onedrive_api_error(ValueError("'parent_reference' (dict con 'id' o 'path') requerido."), action_name, params)
    try:
        resolved_item_id_origen_result = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_origen, params)
        if isinstance(resolved_item_id_origen_result, dict) and resolved_item_id_origen_result.get("status") == "error": return resolved_item_id_origen_result
        item_origen_endpoint_base = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id_origen_result))
        url_copy = f"{item_origen_endpoint_base}/copy"
        body_copy_payload: Dict[str, Any] = {"parentReference": {}}
        if parent_reference_param.get("id"): body_copy_payload["parentReference"]["id"] = parent_reference_param["id"]
        elif parent_reference_param.get("path"):
            if not parent_reference_param.get("driveId"):
                user_drive_info_data = client.get(f"{_get_od_user_drive_base_endpoint(user_identifier)}?$select=id", scope=settings.GRAPH_API_DEFAULT_SCOPE)
                if not isinstance(user_drive_info_data, dict) or not user_drive_info_data.get("id"): raise Exception("No se pudo obtener ID de drive del usuario.")
                if user_drive_info_data.get("status") == "error": raise Exception(f"Error obteniendo ID de drive: {user_drive_info_data.get('message')}")
                user_drive_id = user_drive_info_data["id"]
                raw_path = parent_reference_param["path"].lstrip('/')
                body_copy_payload["parentReference"]["path"] = f"/drives/{user_drive_id}/root{(':/' + raw_path) if raw_path else ''}"
            else: body_copy_payload["parentReference"]["path"] = parent_reference_param["path"]
        if parent_reference_param.get("driveId"): body_copy_payload["parentReference"]["driveId"] = parent_reference_param["driveId"]
        if params.get("nuevo_nombre_copia"): body_copy_payload["name"] = params["nuevo_nombre_copia"]
        response_obj = client.post(url_copy, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=body_copy_payload)
        monitor_url = response_obj.headers.get('Location') 
        if response_obj.status_code == 202 and monitor_url:
            return {"status": "pending", "message": "Copia en progreso.", "monitor_url": monitor_url, "data": response_obj.json() if response_obj.content else {}, "http_status": 202}
        return {"status": "success", "data": response_obj.json(), "message": "Item copiado (síncrono)."}
    except Exception as e: return _handle_onedrive_api_error(e, action_name, params)

def update_item_metadata(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_params_safe = {k:v for k,v in params.items() if k != "nuevos_valores"}
    logger.info("Ejecutando update_item_metadata (OneDrive) (payload omitido): %s", log_params_safe); action_name = "onedrive_update_item_metadata"
    user_identifier: Optional[str] = params.get("user_id"); item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
    nuevos_valores_payload: Optional[Dict[str, Any]] = params.get("nuevos_valores")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    if not item_id_or_path_param: return _handle_onedrive_api_error(ValueError("'item_id_or_path' requerido."), action_name, params)
    if not nuevos_valores_payload or not isinstance(nuevos_valores_payload, dict): return _handle_onedrive_api_error(ValueError("'nuevos_valores' (dict) requerido."), action_name, params)
    try:
        resolved_item_id_result = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_param, params)
        if isinstance(resolved_item_id_result, dict) and resolved_item_id_result.get("status") == "error": return resolved_item_id_result
        item_endpoint_update = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id_result))
        custom_headers = {}; etag = nuevos_valores_payload.pop('@odata.etag', params.get('etag'))
        if etag: custom_headers['If-Match'] = etag
        response_obj = client.patch(item_endpoint_update, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=nuevos_valores_payload, headers=custom_headers)
        return {"status": "success", "data": response_obj.json(), "message": "Metadatos actualizados."}
    except Exception as e: return _handle_onedrive_api_error(e, action_name, params)

def search_items(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando search_items (OneDrive): %s", params); action_name = "onedrive_search_items"
    user_identifier: Optional[str] = params.get("user_id"); query_text: Optional[str] = params.get("query_text")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    if not query_text: return _handle_onedrive_api_error(ValueError("'query_text' requerido."), action_name, params)
    try:
        base_drive_endpoint = _get_od_user_drive_base_endpoint(user_identifier)
        search_folder_path = params.get("search_scope_path", "").strip('/')
        search_path_segment = f"/root:{search_folder_path}:" if search_folder_path else "/root" # Ajuste para asegurar : al final si hay path
        url_base = f"{base_drive_endpoint}{search_path_segment}/search(q='{query_text}')"
        query_api_params: Dict[str, Any] = {'$top': min(int(params.get("top_per_page", 50)), 200)}
        query_api_params['$select'] = params.get("select", "id,name,webUrl,size,file,folder,parentReference,searchResult,createdDateTime,lastModifiedDateTime")
        
        response_data = client.get(url=url_base, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE), params=query_api_params)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada de búsqueda: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        found_items = response_data.get('value', [])
        if not isinstance(found_items, list) and isinstance(response_data.get("hitsContainers"), list) :
            processed_hits = [hit["resource"] for hc in response_data.get("hitsContainers", []) for hit in hc.get("hits", []) if hit.get("resource")]
            found_items = processed_hits
        return {"status": "success", "data": {"value": found_items, "@odata.count": len(found_items)}, "total_retrieved": len(found_items)}
    except Exception as e: return _handle_onedrive_api_error(e, action_name, params)

def get_sharing_link(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_params_safe = {k:v for k,v in params.items() if k != 'password'}
    logger.info("Ejecutando get_sharing_link (OneDrive) (password omitido): %s", log_params_safe); action_name = "onedrive_get_sharing_link"
    user_identifier: Optional[str] = params.get("user_id"); item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    if not item_id_or_path_param: return _handle_onedrive_api_error(ValueError("'item_id_or_path' requerido."), action_name, params)
    scope_param: str = params.get("scope", "organization")
    if scope_param == "users" and not params.get("recipients"): return _handle_onedrive_api_error(ValueError("Si scope es 'users', 'recipients' es requerido."), action_name, params)
    try:
        resolved_item_id_result = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_param, params)
        if isinstance(resolved_item_id_result, dict) and resolved_item_id_result.get("status") == "error": return resolved_item_id_result
        item_endpoint = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id_result))
        url_create_link = f"{item_endpoint}/createLink"
        body: Dict[str, Any] = {"type": params.get("type", "view"), "scope": scope_param}
        if params.get("password"): body["password"] = params["password"]
        if params.get("expirationDateTime"): body["expirationDateTime"] = params["expirationDateTime"]
        if scope_param == "users" and params.get("recipients"): body["recipients"] = params["recipients"]
        response_obj = client.post(url_create_link, scope=getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE), json_data=body) # client.post devuelve requests.Response
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_onedrive_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/onedrive_actions.py ---