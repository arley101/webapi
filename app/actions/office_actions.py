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
    # item_path_in_drive: ej. "Documentos/informe.docx" o "/test.xlsx"
    base_url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/drive"
    clean_path = item_path_in_drive.strip('/')
    if not clean_path: # Referencia al root del drive
        return f"{base_url}/root"
    return f"{base_url}/root:/{clean_path}"

def _get_user_drive_item_id_url(user_id: str, item_id: str) -> str:
    """Devuelve la URL para un item en el drive de un usuario por su ID."""
    return f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/drive/items/{item_id}"

def _get_user_drive_item_content_url(user_id: str, item_path_or_id: str) -> str:
    """Devuelve la URL para el CONTENIDO de un item en el drive de un usuario."""
    # Determinar si es path o ID (heurística simple)
    if "/" in item_path_or_id or \
       ("." in item_path_or_id and not item_path_or_id.startswith("driveItem_") and len(item_path_or_id) < 70 and not '!' in item_path_or_id) or \
       (not item_path_or_id.startswith("driveItem_") and len(item_path_or_id) < 70 and '.' not in item_path_or_id and '!' not in item_path_or_id) :
        # Asumir que es una ruta relativa a la raíz del drive
        base_item_url = _get_user_drive_item_path_url(user_id, item_path_or_id)
        return f"{base_item_url}:/content" # El path ya incluye /root:/...:
    else:
        # Asumir que es un ID de item
        base_item_url = _get_user_drive_item_id_url(user_id, item_path_or_id)
        return f"{base_item_url}/content"


def _get_user_drive_item_workbook_url_base(user_id: str, item_id: str) -> str:
    """Devuelve la URL base para operaciones de Workbook en el drive de un usuario."""
    # Requiere el ID del DriveItem (archivo Excel).
    return f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/drive/items/{item_id}/workbook"

# --- Helper para manejo de errores de Office/Graph ---
def _handle_office_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Office Action '{action_name}'"
    safe_params = {} # Inicializar
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
        "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
        "http_status": status_code_int,
        "graph_error_code": graph_error_code
    }


# --- Acciones de Word (Operando sobre OneDrive de un usuario específico) ---

def crear_documento_word(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "office_crear_documento_word"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    user_identifier: Optional[str] = params.get("user_id") # UPN o ID del usuario
    if not user_identifier:
        return {"status": "error", "action": action_name, "message": "'user_id' (UPN o ID del usuario) es requerido para especificar el OneDrive de destino.", "http_status": 400}

    nombre_archivo: Optional[str] = params.get("nombre_archivo")
    ruta_destino_en_drive: str = params.get("ruta_onedrive", "/") # Relativa a la raíz del drive del usuario
    conflict_behavior: str = params.get("conflict_behavior", "rename")

    if not nombre_archivo:
        return {"status": "error", "action": action_name, "message": "'nombre_archivo' es requerido.", "http_status": 400}
    if not nombre_archivo.lower().endswith(".docx"):
        nombre_archivo += ".docx"

    clean_folder_path = ruta_destino_en_drive.strip('/')
    # target_file_path_in_drive es el path relativo al root del drive. ej "Documentos/MiWord.docx" o "MiWord.docx"
    target_file_path_in_drive = f"{nombre_archivo}" if not clean_folder_path else f"{clean_folder_path}/{nombre_archivo}"
    
    # URL para crear archivo por path: /users/{id}/drive/root:/folder/file.docx:/content
    # _get_user_drive_item_path_url ya construye /users/{uid}/drive/root:/path...
    # así que solo necesitamos añadir /content al final.
    base_item_url = _get_user_drive_item_path_url(user_identifier, target_file_path_in_drive)
    url = f"{base_item_url}:/content" # el path ya incluye /root:/...:
                                    # o si target_file_path_in_drive es solo "file.docx", se convertirá en /root:/file.docx:

    query_api_params = {"@microsoft.graph.conflictBehavior": conflict_behavior}
    headers_upload = {'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
    
    logger.info(f"Creando documento Word vacío '{nombre_archivo}' en OneDrive del usuario '{user_identifier}', ruta: '{target_file_path_in_drive}'")
    files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.put(url, scope=files_rw_scope, params=query_api_params, data=b'', headers=headers_upload)
        return {"status": "success", "data": response.json(), "message": f"Documento Word '{nombre_archivo}' creado."}
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)

def reemplazar_contenido_word(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "office_reemplazar_contenido_word"
    log_params = {k:v for k,v in params.items() if k not in ['nuevo_contenido']}
    if 'nuevo_contenido' in params : log_params['nuevo_contenido_type'] = type(params['nuevo_contenido']).__name__
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id_o_ruta: Optional[str] = params.get("item_id_o_ruta") # ID del archivo o ruta en el drive del usuario
    nuevo_contenido: Optional[Union[str, bytes]] = params.get("nuevo_contenido")
    content_type_param: Optional[str] = params.get("content_type") # Opcional, para anular el default

    if not item_id_o_ruta or nuevo_contenido is None:
        return {"status": "error", "action": action_name, "message": "'item_id_o_ruta' y 'nuevo_contenido' son requeridos.", "http_status": 400}

    url = _get_user_drive_item_content_url(user_identifier, item_id_o_ruta)
    headers_upload: Dict[str,str] = {}
    data_to_send: bytes

    if isinstance(nuevo_contenido, str):
        data_to_send = nuevo_contenido.encode('utf-8')
        headers_upload['Content-Type'] = content_type_param or 'text/plain' # O 'application/msword' si es .doc antiguo?
        logger.warning(f"Reemplazando contenido Word ('{item_id_o_ruta}') para usuario '{user_identifier}' con texto plano. Se perderá el formato Word si el original era .docx.")
    elif isinstance(nuevo_contenido, bytes):
        data_to_send = nuevo_contenido
        # Si son bytes, el usuario debe asegurar que son bytes .docx válidos.
        headers_upload['Content-Type'] = content_type_param or 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    else:
        return {"status": "error", "action": action_name, "message": "'nuevo_contenido' debe ser string o bytes.", "http_status": 400}

    logger.info(f"Reemplazando contenido de Word '{item_id_o_ruta}' en OneDrive del usuario '{user_identifier}'. Content-Type: {headers_upload['Content-Type']}")
    files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.put(url, scope=files_rw_scope, data=data_to_send, headers=headers_upload)
        return {"status": "success", "data": response.json(), "message": "Contenido de Word reemplazado."}
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)

def obtener_documento_word_binario(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[bytes, Dict[str, Any]]:
    params = params or {}
    action_name = "office_obtener_documento_word_binario"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id_o_ruta: Optional[str] = params.get("item_id_o_ruta") 
    if not item_id_o_ruta:
        return {"status": "error", "action": action_name, "message": "'item_id_o_ruta' es requerido.", "http_status": 400}

    url = _get_user_drive_item_content_url(user_identifier, item_id_o_ruta)
    logger.info(f"Obteniendo binario de Word '{item_id_o_ruta}' desde OneDrive del usuario '{user_identifier}'.")
    files_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.get(url, scope=files_read_scope, stream=True) 
        file_bytes = response.content
        logger.info(f"Documento Word '{item_id_o_ruta}' (usuario '{user_identifier}') descargado ({len(file_bytes)} bytes).")
        return file_bytes 
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)


# --- Acciones de Excel (Operando sobre OneDrive de un usuario específico) ---

def crear_libro_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "office_crear_libro_excel"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
        
    nombre_archivo: Optional[str] = params.get("nombre_archivo")
    ruta_destino_en_drive: str = params.get("ruta_onedrive", "/")
    conflict_behavior: str = params.get("conflict_behavior", "rename")

    if not nombre_archivo:
        return {"status": "error", "action": action_name, "message": "'nombre_archivo' es requerido.", "http_status": 400}
    if not nombre_archivo.lower().endswith((".xlsx", ".xls")): # Permitir .xls también aunque menos común
        nombre_archivo += ".xlsx"
    
    clean_folder_path = ruta_destino_en_drive.strip('/')
    target_file_path_in_drive = f"{nombre_archivo}" if not clean_folder_path else f"{clean_folder_path}/{nombre_archivo}"
    
    base_item_url = _get_user_drive_item_path_url(user_identifier, target_file_path_in_drive)
    url = f"{base_item_url}:/content"

    query_api_params = {"@microsoft.graph.conflictBehavior": conflict_behavior}
    headers_upload = {'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}

    logger.info(f"Creando libro Excel '{nombre_archivo}' en OneDrive del usuario '{user_identifier}', ruta: '{target_file_path_in_drive}'")
    files_rw_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.put(url, scope=files_rw_scope, params=query_api_params, data=b'', headers=headers_upload)
        return {"status": "success", "data": response.json(), "message": f"Libro Excel '{nombre_archivo}' creado."}
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)

def leer_celda_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "office_leer_celda_excel"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id: Optional[str] = params.get("item_id") # ID del archivo Excel en el drive del usuario
    hoja_nombre_o_id: Optional[str] = params.get("hoja") 
    celda_o_rango_direccion: Optional[str] = params.get("celda_o_rango") # Ej: "A1" o "Sheet1!A1:C5"

    if not all([item_id, hoja_nombre_o_id, celda_o_rango_direccion]):
        return {"status": "error", "action": action_name, "message": "'item_id' (del archivo Excel), 'hoja' (nombre o ID), y 'celda_o_rango' son requeridos.", "http_status": 400}

    # Construir la dirección completa del rango si no se proveyó con la hoja
    address_param_for_api = celda_o_rango_direccion
    if "!" not in celda_o_rango_direccion: 
        address_param_for_api = f"'{hoja_nombre_o_id}'!{celda_o_rango_direccion}"
    
    # URL para acceder a un rango específico: /users/{uid}/drive/items/{item-id}/workbook/range(address='Sheet1!A1')
    # O /users/{uid}/drive/items/{item-id}/workbook/worksheets/{sheet-id|name}/range(address='A1')
    # Usaremos la primera forma si la dirección es completa, la segunda si solo se da la celda/rango.
    
    # Para este caso, la API `/range(address='fullAddress')` es más flexible.
    url_workbook_base = _get_user_drive_item_workbook_url_base(user_identifier, item_id)
    url_range_api = f"{url_workbook_base}/range(address='{address_param_for_api}')"
    # Por defecto, la API de rango devuelve propiedades como 'address', 'values', 'text', 'formulas', 'numberFormat', etc.
    # No se necesita un $select explícito para estas propiedades básicas del rango.
    
    logger.info(f"Leyendo Excel (usuario '{user_identifier}', item '{item_id}'), address='{address_param_for_api}'")
    # Scope para Workbook API: Files.ReadWrite.All (o más específico si existe como Workbook.Read.All)
    workbook_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE) 
    try:
        response = client.get(url_range_api, scope=workbook_scope)
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)

def escribir_celda_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "office_escribir_celda_excel"
    log_params = {k:v for k,v in params.items() if k != 'valores'}
    if 'valores' in params : log_params['valores_shape'] = f"{len(params['valores'])}x{len(params['valores'][0]) if params['valores'] and params['valores'][0] else 0}"
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id: Optional[str] = params.get("item_id")
    hoja_nombre_o_id: Optional[str] = params.get("hoja")
    celda_o_rango_direccion: Optional[str] = params.get("celda_o_rango")
    valores: Optional[List[List[Any]]] = params.get("valores") 

    if not all([item_id, hoja_nombre_o_id, celda_o_rango_direccion, valores is not None]): # valores puede ser lista vacía para borrar
        return {"status": "error", "action": action_name, "message": "'item_id', 'hoja', 'celda_o_rango', y 'valores' (List[List[Any]]) son requeridos.", "http_status": 400}
    if not isinstance(valores, list) or not all(isinstance(row, list) for row in valores):
        return {"status": "error", "action": action_name, "message": "'valores' debe ser una lista de listas.", "http_status": 400}

    address_param_for_api = celda_o_rango_direccion
    if "!" not in celda_o_rango_direccion:
        address_param_for_api = f"'{hoja_nombre_o_id}'!{celda_o_rango_direccion}"
    
    url_workbook_base = _get_user_drive_item_workbook_url_base(user_identifier, item_id)
    url_range_api = f"{url_workbook_base}/range(address='{address_param_for_api}')"
    
    # El payload para PATCH en un rango actualiza las propiedades del rango.
    # Para escribir valores, se actualiza la propiedad 'values'.
    payload = {"values": valores}
    # Opcionalmente, se pueden enviar 'formulas', 'numberFormat', etc.

    logger.info(f"Escribiendo en Excel (usuario '{user_identifier}', item '{item_id}'), address='{address_param_for_api}'. Shape: {len(valores)}x{len(valores[0]) if valores and valores[0] else 0}")
    workbook_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.patch(url_range_api, scope=workbook_scope, json_data=payload) 
        return {"status": "success", "data": response.json(), "message": "Celda/rango de Excel actualizado."}
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)

def crear_tabla_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "office_crear_tabla_excel"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id: Optional[str] = params.get("item_id")
    hoja_nombre_o_id: Optional[str] = params.get("hoja")
    rango_direccion_en_hoja: Optional[str] = params.get("rango") # Ej: "A1:C10" (sin nombre de hoja)
    tiene_headers_tabla: bool = str(params.get("tiene_headers_tabla", "false")).lower() == "true"
    nombre_tabla: Optional[str] = params.get("nombre_tabla") 

    if not all([item_id, hoja_nombre_o_id, rango_direccion_en_hoja]):
        return {"status": "error", "action": action_name, "message": "'item_id', 'hoja', y 'rango' (dirección en la hoja) son requeridos.", "http_status": 400}

    # El endpoint para crear una tabla es POST a .../workbook/worksheets/{id|name}/tables
    # El cuerpo debe incluir la dirección del rango y si tiene encabezados.
    url_workbook_base = _get_user_drive_item_workbook_url_base(user_identifier, item_id)
    url_create_table = f"{url_workbook_base}/worksheets/{hoja_nombre_o_id}/tables"
    
    payload: Dict[str, Any] = {
        "address": f"'{hoja_nombre_o_id}'!{rango_direccion_en_hoja}", # La API de /tables espera la dirección completa aquí.
        "hasHeaders": tiene_headers_tabla
    }
    if nombre_tabla: 
        payload["name"] = nombre_tabla # El nombre es opcional, Graph generará uno si no se provee.

    logger.info(f"Creando tabla Excel en (usuario '{user_identifier}', item '{item_id}'), hoja '{hoja_nombre_o_id}', rango '{rango_direccion_en_hoja}'. Nombre tabla: {nombre_tabla or '(autogenerado)'}")
    workbook_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.post(url_create_table, scope=workbook_scope, json_data=payload)
        return {"status": "success", "data": response.json(), "message": "Tabla de Excel creada."}
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)

def agregar_filas_tabla_excel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "office_agregar_filas_tabla_excel"
    log_params = {k:v for k,v in params.items() if k != 'valores_filas'}
    if 'valores_filas' in params : log_params['valores_filas_count'] = len(params['valores_filas'])
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    item_id: Optional[str] = params.get("item_id")
    hoja_nombre_o_id: Optional[str] = params.get("hoja") 
    tabla_nombre_o_id: Optional[str] = params.get("tabla_nombre_o_id") 
    valores_filas: Optional[List[List[Any]]] = params.get("valores_filas")

    if not all([item_id, hoja_nombre_o_id, tabla_nombre_o_id, valores_filas is not None]):
        return {"status": "error", "action": action_name, "message": "'item_id', 'hoja', 'tabla_nombre_o_id', y 'valores_filas' son requeridos.", "http_status": 400}
    if not isinstance(valores_filas, list) or not all(isinstance(row, list) for row in valores_filas):
        if not (isinstance(valores_filas, list) and not valores_filas): # Permitir lista vacía para no añadir filas
            return {"status": "error", "action": action_name, "message": "'valores_filas' debe ser una lista de listas.", "http_status": 400}
    
    if not valores_filas: # Si la lista está vacía, no hay nada que hacer.
        return {"status": "success", "data": None, "message": "No se proporcionaron filas para agregar."}

    # Endpoint para añadir filas: .../workbook/worksheets/{sheet-id|name}/tables/{table-id|name}/rows/add
    # O directamente a .../rows (POST)
    url_workbook_base = _get_user_drive_item_workbook_url_base(user_identifier, item_id)
    url_add_rows = f"{url_workbook_base}/worksheets/{hoja_nombre_o_id}/tables/{tabla_nombre_o_id}/rows" # POST aquí
    
    # El payload para /rows (POST) es un objeto con una clave "values" que es una lista de listas.
    # También puede tener "index": null para añadir al final.
    payload = {"values": valores_filas, "index": None} # index: null añade al final

    logger.info(f"Agregando {len(valores_filas)} filas a tabla Excel '{tabla_nombre_o_id}' en (usuario '{user_identifier}', item '{item_id}', hoja '{hoja_nombre_o_id}')")
    workbook_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_WRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.post(url_add_rows, scope=workbook_scope, json_data=payload)
        # Devuelve el workbookTableRow creado (o un objeto que indica el rango añadido).
        return {"status": "success", "data": response.json(), "message": f"{len(valores_filas)} fila(s) agregada(s) a la tabla."}
    except Exception as e:
        return _handle_office_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/office_actions.py ---