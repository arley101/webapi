# app/actions/office_actions.py
import logging
import requests
import json
from typing import Dict, List, Optional, Union, Any

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

def _get_user_drive_item_path_url(user_id: str, item_path_in_drive: str) -> str:
    base_url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/drive"
    clean_path = item_path_in_drive.strip('/')
    if not clean_path:
        return f"{base_url}/root"
    return f"{base_url}/root:/{clean_path}"

def _get_user_drive_item_id_url(user_id: str, item_id: str) -> str:
    return f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/drive/items/{item_id}"

def _get_user_drive_item_content_url(user_id: str, item_path_or_id: str) -> str:
    if "/" in item_path_or_id or ("." in item_path_or_id and not item_path_or_id.startswith("driveItem_")):
        base_item_url = _get_user_drive_item_path_url(user_id, item_path_or_id)
        return f"{base_item_url}:/content"
    else:
        base_item_url = _get_user_drive_item_id_url(user_id, item_path_or_id)
        return f"{base_item_url}/content"

def _get_user_drive_item_workbook_url_base(user_id: str, item_id: str) -> str:
    return f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/drive/items/{item_id}/workbook"

def _handle_office_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Office Action '{action_name}'"
    safe_params = {}
    if params_for_log:
        sensitive_keys = ['nuevo_contenido', 'valores', 'valores_filas', 'contenido_bytes']
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
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
        "message": f"Error en {action_name}: {details_str}", 
        "http_status": status_code_int,
        "details": str(e),
        "graph_error_code": graph_error_code
    }

async async def crear_documento_word(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "office_crear_documento_word"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        nombre_archivo: Optional[str] = params.get("nombre_archivo")
        if not nombre_archivo: raise ValueError("'nombre_archivo' es requerido.")
        if not nombre_archivo.lower().endswith(".docx"): nombre_archivo += ".docx"

        ruta_destino_en_drive: str = params.get("ruta_onedrive", "/")
        conflict_behavior: str = params.get("conflict_behavior", "rename")
        
        target_file_path_in_drive = f"{ruta_destino_en_drive.strip('/')}/{nombre_archivo}".lstrip('/')
        
        url = f"{_get_user_drive_item_path_url(user_identifier, target_file_path_in_drive)}/content"

        query_api_params = {"@microsoft.graph.conflictBehavior": conflict_behavior}
        headers_upload = {'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
        
        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.put(url, scope=files_rw_scope, params=query_api_params, data=b'', headers=headers_upload)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)

async async def reemplazar_contenido_word(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "office_reemplazar_contenido_word"
    logger.info(f"Ejecutando {action_name}")

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        item_id_o_ruta: Optional[str] = params.get("item_id_o_ruta")
        nuevo_contenido: Optional[Union[str, bytes]] = params.get("nuevo_contenido")

        if not item_id_o_ruta or nuevo_contenido is None:
            raise ValueError("'item_id_o_ruta' y 'nuevo_contenido' son requeridos.")

        url = _get_user_drive_item_content_url(user_identifier, item_id_o_ruta)
        
        if isinstance(nuevo_contenido, str):
            data_to_send = nuevo_contenido.encode('utf-8')
            headers_upload = {'Content-Type': 'text/plain'}
        elif isinstance(nuevo_contenido, bytes):
            data_to_send = nuevo_contenido
            headers_upload = {'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
        else:
            raise TypeError("'nuevo_contenido' debe ser string o bytes.")

        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.put(url, scope=files_rw_scope, data=data_to_send, headers=headers_upload)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)

async async def obtener_documento_word_binario(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[bytes, Dict[str, Any]]:
    params = params or {}
    action_name = "office_obtener_documento_word_binario"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        item_id_o_ruta: Optional[str] = params.get("item_id_o_ruta") 
        if not item_id_o_ruta: raise ValueError("'item_id_o_ruta' es requerido.")

        url = _get_user_drive_item_content_url(user_identifier, item_id_o_ruta)
        files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        
        response_content = client.get(url, scope=files_read_scope, stream=True)
        if isinstance(response_content, bytes):
            return response_content 
        else:
            raise TypeError(f"Se esperaban bytes pero se recibió {type(response_content)}.")
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)

async async def crear_libro_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "office_crear_libro_excel"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")
            
        nombre_archivo: Optional[str] = params.get("nombre_archivo")
        if not nombre_archivo: raise ValueError("'nombre_archivo' es requerido.")
        if not nombre_archivo.lower().endswith(".xlsx"): nombre_archivo += ".xlsx"
        
        ruta_destino_en_drive: str = params.get("ruta_onedrive", "/")
        conflict_behavior: str = params.get("conflict_behavior", "rename")
        
        target_file_path_in_drive = f"{ruta_destino_en_drive.strip('/')}/{nombre_archivo}".lstrip("/")
        
        url = f"{_get_user_drive_item_path_url(user_identifier, target_file_path_in_drive)}/content"
        query_api_params = {"@microsoft.graph.conflictBehavior": conflict_behavior}
        headers_upload = {'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}

        files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.put(url, scope=files_rw_scope, params=query_api_params, data=b'', headers=headers_upload)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)

async async def leer_celda_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "office_leer_celda_excel"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        item_id: Optional[str] = params.get("item_id")
        hoja_nombre_o_id: Optional[str] = params.get("hoja") 
        celda_o_rango_direccion: Optional[str] = params.get("celda_o_rango")

        if not all([item_id, hoja_nombre_o_id, celda_o_rango_direccion]):
            raise ValueError("'item_id', 'hoja', y 'celda_o_rango' son requeridos.")

        address_param = f"'{hoja_nombre_o_id}'!{celda_o_rango_direccion}" if "!" not in celda_o_rango_direccion else celda_o_rango_direccion
        
        url_range_api = f"{_get_user_drive_item_workbook_url_base(user_identifier, item_id)}/range(address='{address_param}')"
        
        workbook_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE) 
        response_data = client.get(url_range_api, scope=workbook_scope)
        
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data}
        else:
            raise TypeError(f"Respuesta inesperada: {type(response_data)}")
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)

async async def escribir_celda_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "office_escribir_celda_excel"
    logger.info(f"Ejecutando {action_name}")

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        item_id: Optional[str] = params.get("item_id")
        hoja_nombre_o_id: Optional[str] = params.get("hoja")
        celda_o_rango_direccion: Optional[str] = params.get("celda_o_rango")
        valores: Optional[List[List[Any]]] = params.get("valores") 

        if not all([item_id, hoja_nombre_o_id, celda_o_rango_direccion, valores]):
            raise ValueError("Todos los parámetros son requeridos.")
        if not isinstance(valores, list) or not all(isinstance(row, list) for row in valores):
            raise TypeError("'valores' debe ser una lista de listas.")

        address_param = f"'{hoja_nombre_o_id}'!{celda_o_rango_direccion}" if "!" not in celda_o_rango_direccion else celda_o_rango_direccion
        
        url_range_api = f"{_get_user_drive_item_workbook_url_base(user_identifier, item_id)}/range(address='{address_param}')"
        payload = {"values": valores}

        workbook_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.patch(url_range_api, scope=workbook_scope, json_data=payload) 
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)

async async def crear_tabla_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "office_crear_tabla_excel"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        item_id: Optional[str] = params.get("item_id")
        hoja_nombre_o_id: Optional[str] = params.get("hoja")
        rango_direccion_en_hoja: Optional[str] = params.get("rango")
        
        if not all([item_id, hoja_nombre_o_id, rango_direccion_en_hoja]):
            raise ValueError("'item_id', 'hoja', y 'rango' son requeridos.")

        url_create_table = f"{_get_user_drive_item_workbook_url_base(user_identifier, item_id)}/worksheets/{hoja_nombre_o_id}/tables"
        
        payload: Dict[str, Any] = {
            "address": f"'{hoja_nombre_o_id}'!{rango_direccion_en_hoja}",
            "hasHeaders": str(params.get("tiene_headers_tabla", "false")).lower() == "true"
        }
        if params.get("nombre_tabla"): payload["name"] = params["nombre_tabla"]

        workbook_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.post(url_create_table, scope=workbook_scope, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)

async async def agregar_filas_tabla_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "office_agregar_filas_tabla_excel"
    logger.info(f"Ejecutando {action_name}")

    try:
        user_identifier: Optional[str] = params.get("user_id")
        if not user_identifier: raise ValueError("'user_id' es requerido.")

        item_id: Optional[str] = params.get("item_id")
        hoja_nombre_o_id: Optional[str] = params.get("hoja") 
        tabla_nombre_o_id: Optional[str] = params.get("tabla_nombre_o_id") 
        valores_filas: Optional[List[List[Any]]] = params.get("valores_filas")

        if not all([item_id, hoja_nombre_o_id, tabla_nombre_o_id, valores_filas]):
            raise ValueError("Todos los parámetros son requeridos.")
        if not isinstance(valores_filas, list) or (valores_filas and not all(isinstance(row, list) for row in valores_filas)):
            raise TypeError("'valores_filas' debe ser una lista de listas.")
        if not valores_filas:
            return {"status": "success", "message": "No se proporcionaron filas para agregar."}

        url_add_rows = f"{_get_user_drive_item_workbook_url_base(user_identifier, item_id)}/worksheets/{hoja_nombre_o_id}/tables/{tabla_nombre_o_id}/rows"
        
        payload = {"values": valores_filas, "index": None}

        workbook_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.post(url_add_rows, scope=workbook_scope, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)