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
    if not safe_path or safe_path == '/':
        return f"{drive_endpoint}/root"
    if safe_path.startswith('/'):
        safe_path = safe_path[1:]
    return f"{drive_endpoint}/root:/{safe_path}"

def _get_od_user_item_by_id_endpoint(user_id: str, item_id: str) -> str:
    drive_endpoint = _get_od_user_drive_base_endpoint(user_id)
    return f"{drive_endpoint}/items/{item_id}"

# --- Helper para manejar errores de OneDrive API de forma centralizada ---
def _handle_onedrive_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # Esta función helper no toma 'params' del action_map directamente
    log_message = f"Error en OneDrive action '{action_name}'"
    if params_for_log:
        safe_params = {k: v for k, v in params_for_log.items() if k not in ['contenido_bytes', 'password']}
        log_message += f" con params: {safe_params}"
    log_message += f": {type(e).__name__} - {e}"
    logger.error(log_message, exc_info=True)
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

# --- Helper para obtener ID de item si se provee path (adaptado para user_id) ---
def _internal_onedrive_get_item_metadata(client: AuthenticatedHttpClient, user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    # Esta función es interna, el logging principal y 'params or {}' se maneja en la pública
    item_path_or_id: Optional[str] = params.get("item_id_or_path")
    select: Optional[str] = params.get("select")
    expand: Optional[str] = params.get("expand")

    if not item_path_or_id:
        # Este error debería ser capturado por la función pública que llama a esta.
        raise ValueError("'item_id_or_path' es requerido para _internal_onedrive_get_item_metadata.")
    
    try:
        is_path_like = "/" in item_path_or_id or \
                       ("." in item_path_or_id and not item_path_or_id.startswith("driveItem_") and len(item_path_or_id) < 70) or \
                       (not item_path_or_id.startswith("driveItem_") and len(item_path_or_id) < 70 and '.' not in item_path_or_id and '!' not in item_path_or_id)

        if is_path_like:
            item_endpoint = _get_od_user_item_by_path_endpoint(user_id, item_path_or_id)
        else:
            item_endpoint = _get_od_user_item_by_id_endpoint(user_id, item_path_or_id)

        query_api_params: Dict[str, Any] = {}
        if select: query_api_params['$select'] = select
        if expand: query_api_params['$expand'] = expand
        
        logger.info(f"Obteniendo metadatos OneDrive para user '{user_id}' (interno): Item '{item_path_or_id}' desde endpoint '{item_endpoint.replace(settings.GRAPH_API_BASE_URL, '')}'")
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.get(item_endpoint, scope=files_read_scope, params=query_api_params if query_api_params else None)
        
        # --- CORRECCIÓN ---
        # `client.get` ya devuelve un dict, no un objeto response. Se elimina `.json()`.
        return {"status": "success", "data": response}
    except Exception as e:
        # Re-lanzar para que la función pública lo maneje con _handle_onedrive_api_error
        raise e


def _get_item_id_from_path_if_needed_onedrive(
    client: AuthenticatedHttpClient,
    user_id: str, # Necesario para llamar a _internal_onedrive_get_item_metadata
    item_path_or_id: str
) -> Union[str, Dict[str, Any]]:
    is_likely_id = '!' in item_path_or_id or \
                   (len(item_path_or_id) > 40 and '/' not in item_path_or_id and '.' not in item_path_or_id) or \
                   item_path_or_id.startswith("driveItem_")

    if is_likely_id:
        logger.debug(f"Asumiendo que '{item_path_or_id}' ya es un ID de item OneDrive.")
        return item_path_or_id

    logger.debug(f"'{item_path_or_id}' parece un path en OneDrive para user '{user_id}'. Intentando obtener su ID.")
    metadata_params = {"item_id_or_path": item_path_or_id, "select": "id,name"} # Params para _internal_onedrive_get_item_metadata

    try:
        # Llamada interna directa, ya no a la acción pública get_item
        response = _internal_onedrive_get_item_metadata(client, user_id, metadata_params)
        if response.get("status") == "success" and response.get("data", {}).get("id"):
            item_id = response["data"]["id"]
            logger.info(f"ID obtenido para path OneDrive '{item_path_or_id}' (user '{user_id}'): {item_id}")
            return item_id
        else:
            error_msg = f"No se pudo obtener el ID para el path/item OneDrive '{item_path_or_id}' (user '{user_id}')."
            logger.error(error_msg + f" Detalles: {response}")
            # Devolver la estructura de error si _internal_onedrive_get_item_metadata ya la formateó.
            # Esto es poco probable ya que _internal_onedrive_get_item_metadata relanza la excepción.
            return response if isinstance(response, dict) and response.get("status") == "error" else \
                   {"status": "error", "message": error_msg, "details": str(response), "http_status": response.get("http_status", 500)}
    except Exception as e_resolve: # Captura excepciones de _internal_onedrive_get_item_metadata
        # Formatear el error usando el helper estándar
        return _handle_onedrive_api_error(e_resolve, "_get_item_id_from_path_if_needed_onedrive", {"user_id": user_id, "item_path_or_id": item_path_or_id})


# --- Helper común para paginación ---
def _onedrive_paged_request(
    client: AuthenticatedHttpClient,
    url_base: str,
    scope: List[str],
    params: Dict[str, Any], # params originales de la acción para logging
    query_api_params_initial: Dict[str, Any],
    max_items_total: Optional[int],
    action_name_for_log: str
) -> Dict[str, Any]:
    # El logging principal y 'params or {}' se hacen en la función llamante
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages = getattr(settings, 'MAX_PAGING_PAGES', 30)
    top_per_page = query_api_params_initial.get('$top', getattr(settings, 'DEFAULT_PAGING_SIZE', 50))

    logger.debug(f"Iniciando solicitud paginada para '{action_name_for_log}' desde '{url_base.split('?')[0]}...'. Max total: {max_items_total or 'todos'}, por página: {top_per_page}, max_págs: {max_pages}")
    try:
        while current_url and (max_items_total is None or len(all_items) < max_items_total) and page_count < max_pages:
            page_count += 1
            is_first_call = (current_url == url_base and page_count == 1)
            current_params_for_call = query_api_params_initial if is_first_call else None
            logger.debug(f"Página {page_count} para '{action_name_for_log}': GET {current_url.split('?')[0]} con params: {current_params_for_call}")
            response = client.get(
                url=current_url,
                scope=scope,
                params=current_params_for_call
            )
            # --- CORRECCIÓN ---
            # `client.get` ya devuelve un dict, no un objeto response. Se elimina `.json()`.
            response_data = response

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list):
                logger.warning(f"Respuesta inesperada en paginación para '{action_name_for_log}', 'value' no es una lista: {response_data}")
                break
            for item in page_items:
                if max_items_total is None or len(all_items) < max_items_total:
                    all_items.append(item)
                else:
                    break
            current_url = response_data.get('@odata.nextLink')
            if not current_url or (max_items_total is not None and len(all_items) >= max_items_total):
                break
        logger.info(f"'{action_name_for_log}' recuperó {len(all_items)} items en {page_count} páginas.")
        return {"status": "success", "data": {"value": all_items, "@odata.count": len(all_items)}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name_for_log, params)

# ---- FUNCIONES DE ACCIÓN PARA ONEDRIVE (ahora para /users/{user_id}/drive) ----

def list_items(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_items (OneDrive) con params: %s", params)
    action_name = "onedrive_list_items"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' (UPN o ID de objeto) es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' (UPN o ID de objeto) es requerido.", "http_status": 400}

    ruta_param: str = params.get("ruta", "/") # Ruta relativa dentro del drive del usuario
    top_per_page: int = min(int(params.get("top_per_page", 50)), 200)
    max_items_total: Optional[int] = params.get("max_items_total") # None para todos hasta límite de paginación
    select: Optional[str] = params.get("select")
    filter_query: Optional[str] = params.get("filter_query")
    order_by: Optional[str] = params.get("order_by")

    try:
        is_likely_id = not ("/" in ruta_param) and \
                       (len(ruta_param) > 40 or '!' in ruta_param or ruta_param.startswith("driveItem_")) and \
                       not ("." in ruta_param and len(ruta_param) < 70)

        if is_likely_id: # ruta_param es un ID de carpeta
            item_endpoint_base = _get_od_user_item_by_id_endpoint(user_identifier, ruta_param)
        else: # ruta_param es un path relativo
            item_endpoint_base = _get_od_user_item_by_path_endpoint(user_identifier, ruta_param)
        
        url_base = f"{item_endpoint_base}/children"

        query_api_params: Dict[str, Any] = {'$top': top_per_page}
        if select: query_api_params['$select'] = select
        else: query_api_params['$select'] = "id,name,webUrl,size,file,folder,parentReference,createdDateTime,lastModifiedDateTime"
        if filter_query: query_api_params['$filter'] = filter_query
        if order_by: query_api_params['$orderby'] = order_by
        
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        logger.info(f"{action_name}: Listando items para user '{user_identifier}', ruta/ID '{ruta_param}'. Query: {query_api_params}")
        return _onedrive_paged_request(client, url_base, files_read_scope, params, query_api_params, max_items_total, action_name)
    except Exception as e: # Captura excepciones de construcción de URL o de _onedrive_paged_request
        return _handle_onedrive_api_error(e, action_name, params)


def get_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_item (OneDrive) con params: %s", params)
    action_name = "onedrive_get_item"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id_or_path_param: Optional[str] = params.get("item_id_or_path") # Nuevo nombre de parámetro
    if not item_id_or_path_param:
        logger.error(f"{action_name}: El parámetro 'item_id_or_path' es requerido.")
        return {"status": "error", "action": action_name, "message": "'item_id_or_path' es requerido.", "http_status": 400}

    try:
        # _internal_onedrive_get_item_metadata ahora toma user_id
        return _internal_onedrive_get_item_metadata(client, user_identifier, params)
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)


def upload_file(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando upload_file (OneDrive) con params (omitiendo contenido binario del log): %s", {k:v for k,v in params.items() if k != "contenido_bytes"})
    action_name = "onedrive_upload_file"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    nombre_archivo: Optional[str] = params.get("nombre_archivo")
    contenido_bytes: Optional[bytes] = params.get("contenido_bytes")
    ruta_destino_relativa: str = params.get("ruta_destino_relativa", "/") # Relativa a la raíz del drive del usuario
    conflict_behavior: str = params.get("conflict_behavior", "rename")

    if not nombre_archivo or contenido_bytes is None:
        return _handle_onedrive_api_error(ValueError("'nombre_archivo' y 'contenido_bytes' son requeridos."), action_name, params)
    if not isinstance(contenido_bytes, bytes):
        return _handle_onedrive_api_error(TypeError("'contenido_bytes' debe ser de tipo bytes."), action_name, params)

    try:
        clean_folder_path = ruta_destino_relativa.strip('/')
        target_file_path_for_api = f"{nombre_archivo}" if not clean_folder_path else f"{clean_folder_path}/{nombre_archivo}"
        
        # Endpoint para upload usa el path relativo al root del drive del usuario
        item_endpoint_for_upload_base = _get_od_user_item_by_path_endpoint(user_identifier, target_file_path_for_api)

        file_size_bytes = len(contenido_bytes)
        file_size_mb = file_size_bytes / (1024.0 * 1024.0)
        logger.info(f"{action_name}: Subiendo a OneDrive user '{user_identifier}': path API 'root:/{target_file_path_for_api}' ({file_size_mb:.2f} MB), conflict: '{conflict_behavior}'")
        
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)

        if file_size_mb > 4.0: 
            logger.info("Archivo > 4MB. Iniciando sesión de carga para OneDrive.")
            create_session_url = f"{item_endpoint_for_upload_base}/createUploadSession"
            if item_endpoint_for_upload_base.endswith(":"): 
                create_session_url = f"{item_endpoint_for_upload_base.rstrip(':')}/createUploadSession"

            session_body = {"item": {"@microsoft.graph.conflictBehavior": conflict_behavior, "name": nombre_archivo }}
            session_info = client.post(create_session_url, scope=files_rw_scope, json_data=session_body)
            upload_url_from_session = session_info.get("uploadUrl")
            if not upload_url_from_session: raise ValueError("No se pudo obtener 'uploadUrl' de la sesión.")
            logger.info(f"Sesión de carga OD creada. URL (preview): {upload_url_from_session.split('?')[0]}...")
            
            chunk_size = 5 * 1024 * 1024; start_byte = 0
            final_item_metadata: Optional[Dict[str, Any]] = None
            
            while start_byte < file_size_bytes:
                end_byte = min(start_byte + chunk_size - 1, file_size_bytes - 1)
                current_chunk_data = contenido_bytes[start_byte : end_byte + 1]
                content_range_header = f"bytes {start_byte}-{end_byte}/{file_size_bytes}"
                chunk_upload_timeout = max(DEFAULT_CHUNK_UPLOAD_TIMEOUT_SECONDS, int(len(current_chunk_data) / (50 * 1024)) + 30)
                
                chunk_headers = {'Content-Length': str(len(current_chunk_data)), 'Content-Range': content_range_header}
                logger.debug(f"Subiendo chunk OD: {content_range_header}, timeout: {chunk_upload_timeout}s")
                
                chunk_response = requests.put(upload_url_from_session, headers=chunk_headers, data=current_chunk_data, timeout=chunk_upload_timeout)
                chunk_response.raise_for_status()
                start_byte = end_byte + 1
                if chunk_response.content:
                    try:
                        response_json = chunk_response.json()
                        if chunk_response.status_code in [200, 201] and response_json.get("id"):
                            final_item_metadata = response_json; break
                        elif chunk_response.status_code == 202:
                            logger.debug(f"Chunk aceptado. Próximo byte: {response_json.get('nextExpectedRanges')}")
                    except json.JSONDecodeError:
                        logger.warning(f"Respuesta chunk OD (status {chunk_response.status_code}) no JSON: {chunk_response.text[:200]}")
                elif start_byte >= file_size_bytes: 
                    break
            
            if not final_item_metadata and start_byte >= file_size_bytes :
                logger.warning("Subida OD grande parece completa, pero no se recibió metadata del item final. Intentando verificación.")
                get_params = {"user_id": user_identifier, "item_id_or_path": target_file_path_for_api}
                final_item_check = get_item(client, get_params) # Llama a la acción pública
                if final_item_check.get("status") == "success":
                    final_item_metadata = final_item_check["data"]
                else:
                     return {"status": "warning", "message": "Archivo subido con sesión, pero verificación final falló.", "details": final_item_check}

            if not final_item_metadata:
                 raise ValueError(f"Subida grande OD finalizada pero sin metadata. Último status: {chunk_response.status_code if 'chunk_response' in locals() else 'N/A'}")
            return {"status": "success", "data": final_item_metadata, "message": "Archivo subido con sesión."}
        else: 
            logger.info("Archivo <= 4MB. Usando subida simple para OneDrive.")
            url_put_simple = f"{item_endpoint_for_upload_base}/content"
            query_api_params_put = {"@microsoft.graph.conflictBehavior": conflict_behavior}
            custom_headers_put = {'Content-Type': 'application/octet-stream'}
            response = client.put(url=url_put_simple, scope=files_rw_scope, params=query_api_params_put, data=contenido_bytes, headers=custom_headers_put)
            return {"status": "success", "data": response, "message": "Archivo subido (simple)."}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def download_file(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[bytes, Dict[str, Any]]:
    params = params or {}
    logger.info("Ejecutando download_file (OneDrive) con params: %s", params)
    action_name = "onedrive_download_file"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
    if not item_id_or_path_param:
        logger.error(f"{action_name}: El parámetro 'item_id_or_path' es requerido.")
        return {"status": "error", "action": action_name, "message": "'item_id_or_path' es requerido.", "http_status": 400}
        
    try:
        is_path_like = "/" in item_id_or_path_param or \
                       ("." in item_id_or_path_param and not item_id_or_path_param.startswith("driveItem_") and len(item_id_or_path_param) < 70) or \
                       (not item_id_or_path_param.startswith("driveItem_") and len(item_id_or_path_param) < 70 and '.' not in item_id_or_path_param and '!' not in item_id_or_path_param)

        if is_path_like:
            item_endpoint_base = _get_od_user_item_by_path_endpoint(user_identifier, item_id_or_path_param)
        else:
            item_endpoint_base = _get_od_user_item_by_id_endpoint(user_identifier, item_id_or_path_param)
        
        url = f"{item_endpoint_base}/content"

        logger.info(f"{action_name}: Descargando archivo OneDrive para user '{user_identifier}': Item '{item_id_or_path_param}'")
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.get(url, scope=files_read_scope, stream=True)
        
        # --- CORRECCIÓN ---
        # `client.get(stream=True)` devuelve directamente los bytes.
        file_bytes = response
        
        logger.info(f"Archivo OneDrive '{item_id_or_path_param}' (user '{user_identifier}') descargado ({len(file_bytes)} bytes).")
        return file_bytes
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def delete_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando delete_item (OneDrive) con params: %s", params)
    action_name = "onedrive_delete_item"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
    if not item_id_or_path_param:
        logger.error(f"{action_name}: El parámetro 'item_id_or_path' es requerido.")
        return {"status": "error", "action": action_name, "message": "'item_id_or_path' es requerido.", "http_status": 400}
        
    try:
        resolved_item_id = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_param)
        if isinstance(resolved_item_id, dict) and resolved_item_id.get("status") == "error":
            return resolved_item_id 
        
        item_endpoint_for_delete = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id))

        logger.info(f"{action_name}: Eliminando item OneDrive para user '{user_identifier}': ID '{resolved_item_id}' (original: '{item_id_or_path_param}')")
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        _ = client.delete(item_endpoint_for_delete, scope=files_rw_scope)
        return {"status": "success", "message": f"Elemento '{item_id_or_path_param}' (ID: {resolved_item_id}) eliminado para user '{user_identifier}'.", "http_status": 204}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def create_folder(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando create_folder (OneDrive) con params: %s", params)
    action_name = "onedrive_create_folder"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    nombre_carpeta: Optional[str] = params.get("nombre_carpeta")
    if not nombre_carpeta:
        return _handle_onedrive_api_error(ValueError("'nombre_carpeta' es requerido."), action_name, params)
        
    ruta_padre_relativa: str = params.get("ruta_padre_relativa", "/") # Relativa al root del drive del usuario
    conflict_behavior: str = params.get("conflict_behavior", "fail") # fail, rename, replace

    try:
        if ruta_padre_relativa == "/":
            parent_item_endpoint = _get_od_user_item_by_path_endpoint(user_identifier, "/") # Endpoint del root
        else:
            resolved_parent_id = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, ruta_padre_relativa)
            if isinstance(resolved_parent_id, dict) and resolved_parent_id.get("status") == "error":
                return resolved_parent_id
            parent_item_endpoint = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_parent_id))

        url = f"{parent_item_endpoint}/children"
        body = {"name": nombre_carpeta, "folder": {}, "@microsoft.graph.conflictBehavior": conflict_behavior}

        logger.info(f"{action_name}: Creando carpeta OneDrive para user '{user_identifier}': Nombre '{nombre_carpeta}' en ruta padre '{ruta_padre_relativa}'")
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.post(url, scope=files_rw_scope, json_data=body)
        return {"status": "success", "data": response, "message": f"Carpeta '{nombre_carpeta}' creada para user '{user_identifier}'."}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

def move_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando move_item (OneDrive) con params: %s", params)
    action_name = "onedrive_move_item"

    user_identifier: Optional[str] = params.get("user_id") # ID del usuario cuyo drive contiene el item a mover
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id_or_path_origen: Optional[str] = params.get("item_id_or_path_origen")
    parent_reference_param: Optional[Dict[str, str]] = params.get("parent_reference") # Debe contener 'id' o 'path' del nuevo padre
    nuevo_nombre: Optional[str] = params.get("nuevo_nombre")

    if not item_id_or_path_origen:
        return _handle_onedrive_api_error(ValueError("'item_id_or_path_origen' es requerido."), action_name, params)
    if not parent_reference_param or not isinstance(parent_reference_param, dict):
         return _handle_onedrive_api_error(ValueError("'parent_reference' (dict con 'id' o 'path' para el nuevo padre) requerido."), action_name, params)

    # parent_reference.path debe ser relativo al drive especificado en parent_reference.driveId (o el mismo drive si no se especifica)
    # Para /users/{id}/drive, el path en parentReference para ese mismo drive DEBE empezar con /drive/root:
    parent_id = parent_reference_param.get("id")
    parent_path_raw = parent_reference_param.get("path") # Path relativo al root del drive destino, ej: "/Documentos/Destino"
    target_drive_id_in_parent_ref = parent_reference_param.get("driveId")


    if not parent_id and not parent_path_raw: # Se necesita uno de los dos para el destino
        return _handle_onedrive_api_error(ValueError("'parent_reference' debe tener 'id' o 'path'."), action_name, params)
    
    try:
        resolved_item_id_origen = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_origen)
        if isinstance(resolved_item_id_origen, dict) and resolved_item_id_origen.get("status") == "error":
            return resolved_item_id_origen
        
        # El item a mover está en el drive de user_identifier
        item_origen_endpoint_for_patch = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id_origen))

        body: Dict[str, Any] = {"parentReference": {}}
        if parent_id:
            body["parentReference"]["id"] = parent_id
        elif parent_path_raw:
            # Ajustar el path si el movimiento es dentro del mismo drive de este usuario
            # y no se especificó un driveId diferente en parentReference.
            
            # --- CORRECCIÓN ---
            # `client.get` ya devuelve un dict, no un objeto response. Se elimina `.json()`.
            user_drive_info = client.get(f"{_get_od_user_drive_base_endpoint(user_identifier)}?$select=id", scope=settings.GRAPH_API_DEFAULT_SCOPE)
            user_drive_id = user_drive_info.get("id") if isinstance(user_drive_info, dict) else None

            if not target_drive_id_in_parent_ref or target_drive_id_in_parent_ref == user_drive_id:
                if parent_path_raw == "/":
                    body["parentReference"]["path"] = f"/drives/{user_drive_id}/root:"
                else:
                    body["parentReference"]["path"] = f"/drives/{user_drive_id}/root:{parent_path_raw.lstrip('/')}"
            else: # Moviendo a un path en un drive diferente (target_drive_id_in_parent_ref existe y es diferente)
                body["parentReference"]["path"] = parent_path_raw # Asumir que el path es correcto para ese driveId
        
        if target_drive_id_in_parent_ref: # Si se mueve a otro drive
            body["parentReference"]["driveId"] = target_drive_id_in_parent_ref
        # 'siteId' también se puede añadir a parentReference si se mueve a un drive de SharePoint

        if nuevo_nombre: body["name"] = nuevo_nombre
        
        logger.info(f"Moviendo OneDrive item ID '{resolved_item_id_origen}' de user '{user_identifier}' a '{parent_reference_param}'. Nuevo nombre: '{body.get('name')}'")
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.patch(item_origen_endpoint_for_patch, scope=files_rw_scope, json_data=body)
        return {"status": "success", "data": response, "message": "Elemento movido/renombrado."}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)


def copy_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando copy_item (OneDrive) con params: %s", params)
    action_name = "onedrive_copy_item"

    user_identifier: Optional[str] = params.get("user_id") # ID del usuario cuyo drive contiene el item a copiar
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id_or_path_origen: Optional[str] = params.get("item_id_or_path_origen")
    parent_reference_param: Optional[Dict[str, str]] = params.get("parent_reference") # Destino
    nuevo_nombre_copia: Optional[str] = params.get("nuevo_nombre_copia")

    if not item_id_or_path_origen:
        return _handle_onedrive_api_error(ValueError("'item_id_or_path_origen' es requerido."), action_name, params)
    if not parent_reference_param or not isinstance(parent_reference_param, dict):
         return _handle_onedrive_api_error(ValueError("'parent_reference' (dict con 'id' o 'path' para el nuevo padre) requerido."), action_name, params)
    
    parent_id_dest = parent_reference_param.get("id")
    parent_path_raw_dest = parent_reference_param.get("path")
    target_drive_id_dest = parent_reference_param.get("driveId")

    if not parent_id_dest and not parent_path_raw_dest:
        return _handle_onedrive_api_error(ValueError("'parent_reference' debe tener 'id' o 'path' para el destino."), action_name, params)

    try:
        resolved_item_id_origen = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_origen)
        if isinstance(resolved_item_id_origen, dict) and resolved_item_id_origen.get("status") == "error":
            return resolved_item_id_origen
        
        item_origen_endpoint_base = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id_origen))
        url_copy = f"{item_origen_endpoint_base}/copy"

        body_copy_payload: Dict[str, Any] = {"parentReference": {}}
        if parent_id_dest:
            body_copy_payload["parentReference"]["id"] = parent_id_dest
        elif parent_path_raw_dest:
            # Similar a move, ajustar path si es para el mismo drive del mismo usuario
            # y no se especificó un driveId diferente en parentReference.
            
            # --- CORRECCIÓN ---
            # `client.get` ya devuelve un dict, no un objeto response. Se elimina `.json()`.
            user_drive_info = client.get(f"{_get_od_user_drive_base_endpoint(user_identifier)}?$select=id", scope=settings.GRAPH_API_DEFAULT_SCOPE)
            user_drive_id_for_path = user_drive_info.get("id") if isinstance(user_drive_info, dict) else None

            if not target_drive_id_dest or target_drive_id_dest == user_drive_id_for_path:
                if parent_path_raw_dest == "/":
                    body_copy_payload["parentReference"]["path"] = f"/drives/{user_drive_id_for_path}/root:"
                else:
                    body_copy_payload["parentReference"]["path"] = f"/drives/{user_drive_id_for_path}/root:{parent_path_raw_dest.lstrip('/')}"
            else: # Copiando a un path en un drive diferente
                body_copy_payload["parentReference"]["path"] = parent_path_raw_dest
        
        if target_drive_id_dest:
            body_copy_payload["parentReference"]["driveId"] = target_drive_id_dest
        # 'siteId' también se puede añadir a parentReference si se copia a un drive de SharePoint

        if nuevo_nombre_copia: body_copy_payload["name"] = nuevo_nombre_copia
        
        logger.info(f"{action_name}: Iniciando copia OneDrive item ID '{resolved_item_id_origen}' de user '{user_identifier}' a '{parent_reference_param}'. Nuevo nombre: '{body_copy_payload.get('name')}'")
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.post(url_copy, scope=files_rw_scope, json_data=body_copy_payload)
        # El cliente devuelve dict; algunos detalles (headers/Location) no están disponibles aquí.
        # Devolvemos la respuesta tal cual y permitimos al caller verificar progreso si aplica.
        return {"status": "success", "data": response, "message": "Solicitud de copia enviada."}

    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)


def update_item_metadata(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando update_item_metadata (OneDrive) con params: %s", {k:v for k,v in params.items() if k != "nuevos_valores"})
    action_name = "onedrive_update_item_metadata"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
    nuevos_valores_payload: Optional[Dict[str, Any]] = params.get("nuevos_valores")
    
    if not item_id_or_path_param:
        return _handle_onedrive_api_error(ValueError("'item_id_or_path' es requerido."), action_name, params)
    if not nuevos_valores_payload or not isinstance(nuevos_valores_payload, dict):
        return _handle_onedrive_api_error(ValueError("'nuevos_valores' (dict) es requerido."), action_name, params)
        
    try:
        resolved_item_id = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_param)
        if isinstance(resolved_item_id, dict) and resolved_item_id.get("status") == "error":
            return resolved_item_id
        
        item_endpoint_for_update = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id))

        custom_headers = {}
        etag = nuevos_valores_payload.pop('@odata.etag', params.get('etag')) # Permitir etag en payload o como param
        if etag: custom_headers['If-Match'] = etag

        logger.info(f"{action_name}: Actualizando metadatos OneDrive para user '{user_identifier}': ID '{resolved_item_id}' (original: '{item_id_or_path_param}')")
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.patch(item_endpoint_for_update, scope=files_rw_scope, json_data=nuevos_valores_payload, headers=custom_headers)
        return {"status": "success", "data": response, "message": "Metadatos actualizados."}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)


def search_items(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando search_items (OneDrive) con params: %s", params)
    action_name = "onedrive_search_items"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    query_text: Optional[str] = params.get("query_text")
    if not query_text:
        return _handle_onedrive_api_error(ValueError("'query_text' es requerido."), action_name, params)

    top_per_page: int = min(int(params.get("top_per_page", 50)), 200)
    max_items_total: Optional[int] = params.get("max_items_total")
    select: Optional[str] = params.get("select")
    # search_scope_path ahora se interpreta como relativo al root del drive del usuario
    search_folder_path_relative: str = params.get("search_scope_path", "") 

    base_drive_endpoint_str = _get_od_user_drive_base_endpoint(user_identifier)
    
    if search_folder_path_relative and search_folder_path_relative != "/":
        # Para buscar dentro de una carpeta, se usa el ID del item de la carpeta.
        # O se usa /drives/{drive-id}/root:/path/to/folder:/search(q='...')
        # Por simplicidad, vamos a construir el path para /drives/{drive-id}/root:/path:/search(q='...')
        search_path_segment = f"/root:{search_folder_path_relative.strip('/')}:"
        log_search_scope = f"OneDrive user '{user_identifier}' (Scope Path: '{search_folder_path_relative}', Query: '{query_text}')"
    else: # Búsqueda en todo el drive del usuario
        search_path_segment = "/root" # O directamente sobre el drive /search(q='...')
        log_search_scope = f"OneDrive user '{user_identifier}' (Todo el drive, Query: '{query_text}')"

    # La API de búsqueda de Drive es /drives/{drive-id}/search(q='{searchText}')
    # o /drives/{drive-id}/root/search(q='{searchText}') para buscar desde la raíz
    # o /drives/{drive-id}/items/{item-id}/search(q='{searchText}') para buscar bajo un item
    
    # Usaremos /drives/{drive-id}/root:/search(q='...') para buscar en todo el drive del usuario
    # o /drives/{drive-id}/root:/folder:/search(q='...')
    url_base = f"{base_drive_endpoint_str}{search_path_segment}/search(q='{query_text}')"

    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    if select: query_api_params['$select'] = select
    else: query_api_params['$select'] = "id,name,webUrl,size,file,folder,parentReference,searchResult,createdDateTime,lastModifiedDateTime"

    logger.info(f"{action_name}: {log_search_scope}")
    # _onedrive_paged_request ya maneja la paginación para respuestas estándar de 'value' y '@odata.nextLink'
    # La respuesta de /search es un poco diferente, puede tener 'hitsContainers'.
    # Adaptamos la lógica de paginación aquí para /search.
    
    all_found_resources: List[Dict[str, Any]] = []
    current_url_search: Optional[str] = url_base
    page_count_search = 0
    max_pages_search = getattr(settings, 'MAX_PAGING_PAGES', 10)
    files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)

    try:
        while current_url_search and (max_items_total is None or len(all_found_resources) < max_items_total) and page_count_search < max_pages_search:
            page_count_search += 1
            is_first_search_call = (current_url_search == url_base and page_count_search == 1)
            
            response = client.get(
                url=current_url_search,
                scope=files_read_scope,
                params=query_api_params if is_first_search_call else None # Los params OData van en la URL inicial
            )
            # --- CORRECCIÓN ---
            # `client.get` ya devuelve un dict, no un objeto response. Se elimina `.json()`.
            search_page_data = response

            items_from_page: List[Dict[str, Any]] = search_page_data.get('value', [])
            
            if not isinstance(items_from_page, list):
                logger.warning(f"Respuesta inesperada de búsqueda, 'value' no es lista: {items_from_page}")
                break

            for item_res in items_from_page: # Cada item_res es un DriveItem
                if max_items_total is None or len(all_found_resources) < max_items_total:
                    all_found_resources.append(item_res)
                else: break
            
            current_url_search = search_page_data.get('@odata.nextLink')
            if not current_url_search or (max_items_total is not None and len(all_found_resources) >= max_items_total): break

        logger.info(f"Búsqueda OneDrive encontró {len(all_found_resources)} items en {page_count_search} páginas para user '{user_identifier}'.")
        return {"status": "success", "data": {"value": all_found_resources, "@odata.count": len(all_found_resources)}, "total_retrieved": len(all_found_resources), "pages_processed": page_count_search}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)


def get_sharing_link(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_sharing_link (OneDrive) con params: %s", {k:v for k,v in params.items() if k != "password"})
    action_name = "onedrive_get_sharing_link"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id_or_path_param: Optional[str] = params.get("item_id_or_path")
    if not item_id_or_path_param:
        return _handle_onedrive_api_error(ValueError("'item_id_or_path' es requerido."), action_name, params)
        
    link_type: str = params.get("type", "view") # 'view', 'edit', 'embed'
    scope: str = params.get("scope", "organization") # 'anonymous', 'organization', 'users'
    password: Optional[str] = params.get("password")
    expiration_datetime: Optional[str] = params.get("expirationDateTime") # ISO 8601

    try:
        resolved_item_id = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_param)
        if isinstance(resolved_item_id, dict) and resolved_item_id.get("status") == "error":
            return resolved_item_id

        item_endpoint_for_link = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id))
        url_create_link = f"{item_endpoint_for_link}/createLink"

        body: Dict[str, Any] = {"type": link_type, "scope": scope}
        if password: body["password"] = password
        if expiration_datetime: body["expirationDateTime"] = expiration_datetime
        # Para scope='users', se necesitaría 'recipients' en el body, que no está en los params actuales.

        logger.info(f"{action_name}: Creando/obteniendo enlace para OneDrive item ID '{resolved_item_id}' (user '{user_identifier}')")
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.post(url_create_link, scope=files_rw_scope, json_data=body)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)


# ============================================================================
# FUNCIONES ADICIONALES RESTAURADAS
# ============================================================================

def onedrive_create_folder_structure(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crear una estructura de carpetas completa en OneDrive."""
    params = params or {}
    logger.info("Ejecutando onedrive_create_folder_structure con params: %s", params)
    action_name = "onedrive_create_folder_structure"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    folder_structure: Optional[List[str]] = params.get("folder_structure")
    if not folder_structure or not isinstance(folder_structure, list):
        logger.error(f"{action_name}: El parámetro 'folder_structure' debe ser una lista de rutas.")
        return {"status": "error", "action": action_name, "message": "'folder_structure' debe ser una lista de rutas.", "http_status": 400}

    base_path: str = params.get("base_path", "/")
    created_folders = []
    errors = []

    try:
        for folder_path in folder_structure:
            full_path = f"{base_path.rstrip('/')}/{folder_path.strip('/')}"
            
            # Dividir la ruta en partes y crear cada carpeta padre si no existe
            path_parts = [part for part in full_path.split('/') if part]
            current_path = ""
            
            for part in path_parts:
                current_path = f"{current_path}/{part}"
                
                try:
                    # Verificar si la carpeta ya existe
                    check_endpoint = _get_od_user_item_by_path_endpoint(user_identifier, current_path)
                    files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
                    
                    try:
                        existing_item = client.get(check_endpoint, scope=files_read_scope)
                        if existing_item.get("folder"):
                            continue  # La carpeta ya existe
                    except:
                        # La carpeta no existe, la creamos
                        pass
                    
                    # Crear la carpeta
                    parent_path = "/".join(current_path.split("/")[:-1]) or "/"
                    parent_endpoint = _get_od_user_item_by_path_endpoint(user_identifier, parent_path)
                    create_url = f"{parent_endpoint}/children"
                    
                    folder_data = {
                        "name": part,
                        "folder": {},
                        "@microsoft.graph.conflictBehavior": "rename"
                    }
                    
                    files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
                    created_folder = client.post(create_url, scope=files_rw_scope, json_data=folder_data)
                    created_folders.append({
                        "path": current_path,
                        "id": created_folder.get("id"),
                        "name": created_folder.get("name")
                    })
                    
                except Exception as folder_error:
                    errors.append({
                        "path": current_path,
                        "error": str(folder_error)
                    })
                    logger.warning(f"Error creando carpeta '{current_path}': {folder_error}")

        logger.info(f"{action_name}: Estructura de carpetas creada. {len(created_folders)} carpetas exitosas, {len(errors)} errores.")
        return {
            "status": "success" if not errors else "partial_success",
            "data": {
                "created_folders": created_folders,
                "errors": errors,
                "total_attempted": len(folder_structure),
                "successful": len(created_folders),
                "failed": len(errors)
            }
        }
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)


def onedrive_get_file_versions(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtener versiones de un archivo en OneDrive."""
    params = params or {}
    logger.info("Ejecutando onedrive_get_file_versions con params: %s", params)
    action_name = "onedrive_get_file_versions"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id_or_path_param: Optional[str] = params.get("item_id") or params.get("file_path")
    if not item_id_or_path_param:
        logger.error(f"{action_name}: Se requiere 'item_id' o 'file_path'.")
        return {"status": "error", "action": action_name, "message": "Se requiere 'item_id' o 'file_path'.", "http_status": 400}

    try:
        resolved_item_id = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_param)
        if isinstance(resolved_item_id, dict) and resolved_item_id.get("status") == "error":
            return resolved_item_id

        item_endpoint = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id))
        versions_url = f"{item_endpoint}/versions"

        logger.info(f"{action_name}: Obteniendo versiones del archivo OneDrive item ID '{resolved_item_id}' (user '{user_identifier}')")
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.get(versions_url, scope=files_read_scope)
        
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)


def onedrive_set_file_permissions(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Establecer permisos específicos para un archivo en OneDrive."""
    params = params or {}
    logger.info("Ejecutando onedrive_set_file_permissions con params: %s", params)
    action_name = "onedrive_set_file_permissions"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id_or_path_param: Optional[str] = params.get("item_id") or params.get("file_path")
    if not item_id_or_path_param:
        logger.error(f"{action_name}: Se requiere 'item_id' o 'file_path'.")
        return {"status": "error", "action": action_name, "message": "Se requiere 'item_id' o 'file_path'.", "http_status": 400}

    permission_data: Optional[Dict[str, Any]] = params.get("permission_data")
    if not permission_data or not isinstance(permission_data, dict):
        logger.error(f"{action_name}: El parámetro 'permission_data' es requerido.")
        return {"status": "error", "action": action_name, "message": "'permission_data' (dict) es requerido.", "http_status": 400}

    # Validar campos requeridos en permission_data
    required_fields = ["recipients", "roles"]
    if not all(field in permission_data for field in required_fields):
        missing = [field for field in required_fields if field not in permission_data]
        return {"status": "error", "action": action_name, "message": f"Faltan campos requeridos en 'permission_data': {missing}.", "http_status": 400}

    try:
        resolved_item_id = _get_item_id_from_path_if_needed_onedrive(client, user_identifier, item_id_or_path_param)
        if isinstance(resolved_item_id, dict) and resolved_item_id.get("status") == "error":
            return resolved_item_id

        item_endpoint = _get_od_user_item_by_id_endpoint(user_identifier, str(resolved_item_id))
        permissions_url = f"{item_endpoint}/invite"

        # Preparar payload para invitación/permisos
        invite_payload = {
            "recipients": permission_data["recipients"],
            "roles": permission_data["roles"],
            "sendInvitation": permission_data.get("send_invitation", True),
            "message": permission_data.get("message", ""),
            "requireSignIn": permission_data.get("require_sign_in", True)
        }

        logger.info(f"{action_name}: Estableciendo permisos para OneDrive item ID '{resolved_item_id}' (user '{user_identifier}')")
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.post(permissions_url, scope=files_rw_scope, json_data=invite_payload)
        
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)


def onedrive_get_storage_quota(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtener información de cuota de almacenamiento de OneDrive."""
    params = params or {}
    logger.info("Ejecutando onedrive_get_storage_quota con params: %s", params)
    action_name = "onedrive_get_storage_quota"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    try:
        drive_endpoint = _get_od_user_drive_base_endpoint(user_identifier)
        quota_url = f"{drive_endpoint}?$select=quota"

        logger.info(f"{action_name}: Obteniendo cuota de almacenamiento OneDrive para user '{user_identifier}'")
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.get(quota_url, scope=files_read_scope)
        
        # Extraer información de cuota y calcular valores útiles
        quota_info = response.get("quota", {})
        if quota_info:
            total = quota_info.get("total", 0)
            used = quota_info.get("used", 0)
            remaining = quota_info.get("remaining", 0)
            deleted = quota_info.get("deleted", 0)
            
            # Calcular porcentajes
            usage_percentage = (used / total * 100) if total > 0 else 0
            
            enhanced_quota = {
                **quota_info,
                "usage_percentage": round(usage_percentage, 2),
                "total_gb": round(total / (1024**3), 2) if total else 0,
                "used_gb": round(used / (1024**3), 2) if used else 0,
                "remaining_gb": round(remaining / (1024**3), 2) if remaining else 0,
                "deleted_gb": round(deleted / (1024**3), 2) if deleted else 0
            }
            
            return {"status": "success", "data": enhanced_quota}
        else:
            return {"status": "success", "data": response}
            
    except Exception as e:
        return _handle_onedrive_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/onedrive_actions.py ---