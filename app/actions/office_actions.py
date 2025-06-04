# app/actions/office_actions.py
import logging
import requests # Para requests.exceptions.HTTPError y manejar respuestas binarias
import json # Para el helper de error
from typing import Dict, List, Optional, Union, Any

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# --- Helpers Específicos para construir URLs de Office (adaptados para /users/{user_id}/drive) ---

def _get_user_drive_item_path_url(user_id: str, item_path_in_drive: str) -> str:
    """Devuelve la URL para un item en el drive de un usuario por path relativo a la raíz."""
    base_url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/drive"
    clean_path = item_path_in_drive.strip('/')
    if not clean_path: 
        return f"{base_url}/root"
    return f"{base_url}/root:/{clean_path}"

def _get_user_drive_item_id_url(user_id: str, item_id: str) -> str:
    """Devuelve la URL para un item en el drive de un usuario por su ID."""
    return f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/drive/items/{item_id}"

def _get_user_drive_item_content_url(user_id: str, item_path_or_id: str) -> str:
    """Devuelve la URL para el CONTENIDO de un item en el drive de un usuario."""
    is_path_like = "/" in item_path_or_id or \
                   ("." in item_path_or_id and not item_path_or_id.startswith("driveItem_") and len(item_path_or_id) < 70 and '!' not in item_path_or_id) or \
                   (not item_path_or_id.startswith("driveItem_") and len(item_path_or_id) < 70 and '.' not in item_path_or_id and '!' not in item_path_or_id)
    
    base_item_url = _get_user_drive_item_path_url(user_id, item_path_or_id) if is_path_like else _get_user_drive_item_id_url(user_id, item_path_or_id)
    
    # El path para content es diferente si el base_item_url ya incluye ":/" (para paths) o no (para IDs)
    if ":/" in base_item_url: # Vino de _get_user_drive_item_path_url y no es el root
        return f"{base_item_url}:/content"
    else: # Vino de _get_user_drive_item_id_url o es el root
        return f"{base_item_url}/content"


def _get_user_drive_item_workbook_url_base(user_id: str, item_id: str) -> str:
    """Devuelve la URL base para operaciones de Workbook en el drive de un usuario."""
    return f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/drive/items/{item_id}/workbook"

# --- Helper para manejo de errores de Office/Graph ---
def _handle_office_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Office Action '{action_name}'"
    safe_params = {} 
    if params_for_log:
        sensitive_keys = ['nuevo_contenido', 'valores', 'valores_filas', 'contenido_bytes']
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    details_str = str(e); status_code_int = 500; graph_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json(); error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text); graph_error_code = error_info.get("code")
        except json.JSONDecodeError: 
            details_str = e.response.text[:500] if e.response.text else "No response body"
    return {"status": "error", "action": action_name, "message": f"Error en {action_name}: {details_str}", 
            "details": str(e), "http_status": status_code_int, "graph_error_code": graph_error_code}

# --- Acciones de Word (Operando sobre OneDrive de un usuario específico) ---
def crear_documento_word(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "office_crear_documento_word"; logger.info(f"Ejecutando {action_name}: {params}")
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' requerido.", "http_status": 400}
    nombre_archivo: Optional[str] = params.get("nombre_archivo")
    if not nombre_archivo: return {"status": "error", "action": action_name, "message": "'nombre_archivo' requerido.", "http_status": 400}
    if not nombre_archivo.lower().endswith(".docx"): nombre_archivo += ".docx"
    ruta_destino_en_drive: str = params.get("ruta_onedrive", "/").strip('/')
    target_file_path = f"{nombre_archivo}" if not ruta_destino_en_drive else f"{ruta_destino_en_drive}/{nombre_archivo}"
    base_item_url = _get_user_drive_item_path_url(user_identifier, target_file_path)
    # Para crear un archivo nuevo con PUT, el path debe terminar en ':/content' si usa path, o '/content' si usa ID.
    # _get_user_drive_item_path_url devuelve .../root:/path, así que añadimos ':/content'
    # Si es solo root, devuelve .../root, así que añadimos '/content'
    url = f"{base_item_url}:/content" if ":/" in base_item_url else f"{base_item_url}/content"

    query_api_params = {"@microsoft.graph.conflictBehavior": params.get("conflict_behavior", "rename")}
    headers_upload = {'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
    files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_obj = client.put(url, scope=files_rw_scope, params=query_api_params, data=b'', headers=headers_upload) # client.put devuelve requests.Response
        return {"status": "success", "data": response_obj.json(), "message": f"Documento Word '{nombre_archivo}' creado."}
    except Exception as e: return _handle_office_api_error(e, action_name, params)

def reemplazar_contenido_word(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "office_reemplazar_contenido_word"
    log_params = {k:v for k,v in params.items() if k not in ['nuevo_contenido']}
    logger.info(f"Ejecutando {action_name} (contenido omitido): {log_params}")
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    item_id_o_ruta: Optional[str] = params.get("item_id_o_ruta")
    nuevo_contenido: Optional[Union[str, bytes]] = params.get("nuevo_contenido")
    if not item_id_o_ruta or nuevo_contenido is None: return {"status": "error", "action": action_name, "message": "'item_id_o_ruta' y 'nuevo_contenido' requeridos.", "http_status": 400}
    url = _get_user_drive_item_content_url(user_identifier, item_id_o_ruta)
    headers_upload: Dict[str,str] = {}; data_to_send: bytes
    if isinstance(nuevo_contenido, str):
        data_to_send = nuevo_contenido.encode('utf-8')
        headers_upload['Content-Type'] = params.get("content_type") or 'text/plain'
    elif isinstance(nuevo_contenido, bytes):
        data_to_send = nuevo_contenido
        headers_upload['Content-Type'] = params.get("content_type") or 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    else: return {"status": "error", "action": action_name, "message": "'nuevo_contenido' debe ser string o bytes.", "http_status": 400}
    files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_obj = client.put(url, scope=files_rw_scope, data=data_to_send, headers=headers_upload) # client.put devuelve requests.Response
        return {"status": "success", "data": response_obj.json(), "message": "Contenido de Word reemplazado."}
    except Exception as e: return _handle_office_api_error(e, action_name, params)

def obtener_documento_word_binario(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[bytes, Dict[str, Any]]:
    params = params or {}; action_name = "office_obtener_documento_word_binario"; logger.info(f"Ejecutando {action_name}: {params}")
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    item_id_o_ruta: Optional[str] = params.get("item_id_o_ruta") 
    if not item_id_o_ruta: return {"status": "error", "action": action_name, "message": "'item_id_o_ruta' es requerido.", "http_status": 400}
    url = _get_user_drive_item_content_url(user_identifier, item_id_o_ruta)
    files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_content = client.get(url, scope=files_read_scope, stream=True) # client.get devuelve bytes si stream=True
        if isinstance(response_content, bytes): return response_content 
        elif isinstance(response_content, dict) and response_content.get("status") == "error": return response_content 
        else: return _handle_office_api_error(Exception(f"Respuesta inesperada al obtener binario: {type(response_content)}"), action_name, params)
    except Exception as e: return _handle_office_api_error(e, action_name, params)

def crear_libro_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "office_crear_libro_excel"; logger.info(f"Ejecutando {action_name}: {params}")
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    nombre_archivo: Optional[str] = params.get("nombre_archivo")
    if not nombre_archivo: return {"status": "error", "action": action_name, "message": "'nombre_archivo' es requerido.", "http_status": 400}
    if not nombre_archivo.lower().endswith((".xlsx", ".xls")): nombre_archivo += ".xlsx"
    ruta_destino_en_drive: str = params.get("ruta_onedrive", "/").strip('/')
    target_file_path = f"{nombre_archivo}" if not ruta_destino_en_drive else f"{ruta_destino_en_drive}/{nombre_archivo}"
    base_item_url = _get_user_drive_item_path_url(user_identifier, target_file_path)
    url = f"{base_item_url}:/content" if ":/" in base_item_url else f"{base_item_url}/content"
    query_api_params = {"@microsoft.graph.conflictBehavior": params.get("conflict_behavior", "rename")}
    headers_upload = {'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
    files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_obj = client.put(url, scope=files_rw_scope, params=query_api_params, data=b'', headers=headers_upload)
        return {"status": "success", "data": response_obj.json(), "message": f"Libro Excel '{nombre_archivo}' creado."}
    except Exception as e: return _handle_office_api_error(e, action_name, params)

def leer_celda_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "office_leer_celda_excel"; logger.info(f"Ejecutando {action_name}: {params}")
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    item_id = params.get("item_id"); hoja_nombre_o_id = params.get("hoja"); celda_o_rango_direccion = params.get("celda_o_rango")
    if not all([item_id, hoja_nombre_o_id, celda_o_rango_direccion]):
        return {"status": "error", "action": action_name, "message": "'item_id', 'hoja', y 'celda_o_rango' requeridos.", "http_status": 400}
    address_param = celda_o_rango_direccion if "!" in celda_o_rango_direccion else f"'{hoja_nombre_o_id}'!{celda_o_rango_direccion}"
    url = f"{_get_user_drive_item_workbook_url_base(user_identifier, item_id)}/range(address='{address_param}')"
    workbook_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_data = client.get(url, scope=workbook_scope)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_office_api_error(e, action_name, params)

def escribir_celda_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "office_escribir_celda_excel";
    log_params = {k:v for k,v in params.items() if k != 'valores'}
    logger.info(f"Ejecutando {action_name}: {log_params}")
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    item_id = params.get("item_id"); hoja_nombre_o_id = params.get("hoja"); celda_o_rango_direccion = params.get("celda_o_rango"); valores = params.get("valores")
    if not all([item_id, hoja_nombre_o_id, celda_o_rango_direccion, valores is not None]):
        return {"status": "error", "action": action_name, "message": "'item_id', 'hoja', 'celda_o_rango', y 'valores' requeridos.", "http_status": 400}
    if not isinstance(valores, list) or (valores and not all(isinstance(row, list) for row in valores)):
        return {"status": "error", "action": action_name, "message": "'valores' debe ser lista de listas.", "http_status": 400}
    address_param = celda_o_rango_direccion if "!" in celda_o_rango_direccion else f"'{hoja_nombre_o_id}'!{celda_o_rango_direccion}"
    url = f"{_get_user_drive_item_workbook_url_base(user_identifier, item_id)}/range(address='{address_param}')"
    payload = {"values": valores}
    workbook_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_obj = client.patch(url, scope=workbook_scope, json_data=payload) # client.patch devuelve requests.Response
        return {"status": "success", "data": response_obj.json(), "message": "Celda/rango Excel actualizado."}
    except Exception as e: return _handle_office_api_error(e, action_name, params)

def crear_tabla_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "office_crear_tabla_excel"; logger.info(f"Ejecutando {action_name}: {params}")
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    item_id = params.get("item_id"); hoja_nombre_o_id = params.get("hoja"); rango_direccion = params.get("rango")
    if not all([item_id, hoja_nombre_o_id, rango_direccion]):
        return {"status": "error", "action": action_name, "message": "'item_id', 'hoja', y 'rango' requeridos.", "http_status": 400}
    url = f"{_get_user_drive_item_workbook_url_base(user_identifier, item_id)}/worksheets/{hoja_nombre_o_id}/tables"
    payload: Dict[str, Any] = {"address": f"'{hoja_nombre_o_id}'!{rango_direccion}", "hasHeaders": str(params.get("tiene_headers_tabla", "false")).lower() == "true"}
    if params.get("nombre_tabla"): payload["name"] = params["nombre_tabla"]
    workbook_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_obj = client.post(url, scope=workbook_scope, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "message": "Tabla Excel creada."}
    except Exception as e: return _handle_office_api_error(e, action_name, params)

def agregar_filas_tabla_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "office_agregar_filas_tabla_excel"
    log_params = {k:v for k,v in params.items() if k != 'valores_filas'}
    logger.info(f"Ejecutando {action_name}: {log_params}")
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    item_id = params.get("item_id"); hoja_nombre_o_id = params.get("hoja"); tabla_nombre_o_id = params.get("tabla_nombre_o_id"); valores_filas = params.get("valores_filas")
    if not all([item_id, hoja_nombre_o_id, tabla_nombre_o_id, valores_filas is not None]):
        return {"status": "error", "action": action_name, "message": "'item_id', 'hoja', 'tabla_nombre_o_id', y 'valores_filas' requeridos.", "http_status": 400}
    if not isinstance(valores_filas, list) or (valores_filas and not all(isinstance(row, list) for row in valores_filas)):
        return {"status": "error", "action": action_name, "message": "'valores_filas' debe ser lista de listas.", "http_status": 400}
    if not valores_filas: return {"status": "success", "data": None, "message": "No se proporcionaron filas."}
    url = f"{_get_user_drive_item_workbook_url_base(user_identifier, item_id)}/worksheets/{hoja_nombre_o_id}/tables/{tabla_nombre_o_id}/rows"
    payload = {"values": valores_filas, "index": None}
    workbook_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_obj = client.post(url, scope=workbook_scope, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "message": f"{len(valores_filas)} fila(s) agregada(s)."}
    except Exception as e: return _handle_office_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/office_actions.py ---