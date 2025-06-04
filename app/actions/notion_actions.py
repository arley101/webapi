# app/actions/notion_actions.py
import logging
import requests
import json
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

NOTION_API_BASE_URL = "https://api.notion.com/v1"

def _get_notion_api_headers(params: Dict[str, Any]) -> Dict[str, str]:
    """
    Prepara los headers para las solicitudes a la Notion API.
    Prioriza el token y la versión de params, luego de settings.
    """
    # Priorizar token de params, luego de settings
    notion_token: Optional[str] = params.get("access_token", settings.NOTION_API_TOKEN)
    # Priorizar versión de params, luego de settings
    notion_version: str = params.get("notion_version", settings.NOTION_API_VERSION) 

    if not notion_token:
        raise ValueError("Se requiere el Token de Integración de Notion (en params como 'access_token' o configurado como NOTION_API_TOKEN en el backend).")
    if not notion_version: # Debería tener un default en settings
        raise ValueError("Se requiere la versión de la API de Notion (en params como 'notion_version' o configurada como NOTION_API_VERSION).")

    return {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": notion_version,
        "Content-Type": "application/json"
    }

def _handle_notion_api_error(
    e: Exception,
    action_name: str,
    params_for_log: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Helper para manejar errores de Notion API."""
    log_message = f"Error en Notion API Action '{action_name}'"
    safe_params = {}
    if params_for_log:
        sensitive_keys = ['access_token', 'payload', 'query'] # Ajusta según sea necesario
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    notion_error_obj = None
    notion_error_code = None
    notion_error_message = str(e)

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json()
            # Estructura de error de Notion: {"object": "error", "status": 4XX, "code": "...", "message": "..."}
            if error_data.get("object") == "error":
                notion_error_obj = error_data
                notion_error_code = error_data.get("code")
                notion_error_message = error_data.get("message", e.response.text)
            details_str = json.dumps(error_data)
        except json.JSONDecodeError:
            details_str = e.response.text[:500] if e.response.text else "No response body"
            notion_error_message = details_str
            
    return {
        "status": "error",
        "action": action_name,
        "message": f"Error interactuando con Notion API: {notion_error_message}",
        "details": {
            "raw_exception_type": type(e).__name__,
            "raw_exception_message": str(e),
            "notion_api_error_object": notion_error_obj, # Contiene la estructura del error de Notion
            "response_body_preview": details_str[:500] if isinstance(details_str, str) else details_str
        },
        "http_status": status_code_int,
        "notion_error_code": notion_error_code
    }

# --- ACCIONES ---
# Nota: El parámetro 'client: AuthenticatedHttpClient' no se usa aquí.

def notion_search_general(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Busca páginas y bases de datos a las que tiene acceso la integración.
    Reemplaza la idea de 'list_databases' que no tiene un endpoint directo para listar todas.
    """
    params = params or {}
    action_name = "notion_search_general" # Renombrado para claridad
    logger.info(f"Ejecutando {action_name} con params (query/filter omitidos del log si presentes): %s", {k:v for k,v in params.items() if k not in ['access_token','query','filter']})

    search_query_text: Optional[str] = params.get("search_query_text") # Texto para buscar
    filter_object_type: Optional[str] = params.get("filter_object_type") # "database" o "page"
    sort_direction: Optional[str] = params.get("sort_direction") # "ascending" o "descending"
    sort_timestamp: Optional[str] = params.get("sort_timestamp") # "last_edited_time"
    start_cursor: Optional[str] = params.get("start_cursor")
    page_size: Optional[int] = params.get("page_size")

    payload_search: Dict[str, Any] = {}
    if search_query_text:
        payload_search["query"] = search_query_text
    
    filter_payload: Dict[str, str] = {}
    if filter_object_type and filter_object_type in ["database", "page"]:
        filter_payload["value"] = filter_object_type
        filter_payload["property"] = "object"
        payload_search["filter"] = filter_payload
        
    sort_payload: Dict[str, str] = {}
    if sort_direction and sort_timestamp:
        sort_payload["direction"] = sort_direction
        sort_payload["timestamp"] = sort_timestamp
        payload_search["sort"] = sort_payload
        
    if start_cursor:
        payload_search["start_cursor"] = start_cursor
    if page_size and isinstance(page_size, int) and 0 < page_size <= 100:
        payload_search["page_size"] = page_size

    url = f"{NOTION_API_BASE_URL}/search"
    log_search_details = f"Query: '{search_query_text or 'N/A'}'"
    if filter_object_type: log_search_details += f", FilterType: '{filter_object_type}'"

    logger.info(f"Buscando en Notion. {log_search_details}. Payload keys: {list(payload_search.keys())}")
    try:
        headers = _get_notion_api_headers(params)
        # La API de búsqueda usa POST con un cuerpo JSON
        response = requests.post(url, headers=headers, json=payload_search, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_notion_api_error(e, action_name, params)

def notion_get_database(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "notion_get_database"
    logger.info(f"Ejecutando {action_name} con params: %s", {k:v for k,v in params.items() if k not in ['access_token']})
    
    database_id: Optional[str] = params.get("database_id")
    if not database_id:
        return {"status": "error", "action": action_name, "message": "'database_id' es requerido.", "http_status": 400}

    url = f"{NOTION_API_BASE_URL}/databases/{database_id}"
    logger.info(f"Obteniendo base de datos de Notion ID: '{database_id}'")
    try:
        headers = _get_notion_api_headers(params)
        response = requests.get(url, headers=headers, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_notion_api_error(e, action_name, params)

def notion_query_database(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "notion_query_database"
    log_params = {k:v for k,v in params.items() if k not in ['access_token', 'query_payload']}
    if 'query_payload' in params: log_params['query_payload_keys'] = list(params['query_payload'].keys())
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    database_id: Optional[str] = params.get("database_id")
    query_payload: Optional[Dict[str, Any]] = params.get("query_payload", {}) # El payload de la query (filter, sorts, start_cursor, page_size)

    if not database_id:
        return {"status": "error", "action": action_name, "message": "'database_id' es requerido.", "http_status": 400}
    
    url = f"{NOTION_API_BASE_URL}/databases/{database_id}/query"
    logger.info(f"Consultando base de datos de Notion ID: '{database_id}'. Payload de query presente: {bool(query_payload)}")
    try:
        headers = _get_notion_api_headers(params)
        response = requests.post(url, headers=headers, json=query_payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_notion_api_error(e, action_name, params)

def notion_retrieve_page(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "notion_retrieve_page"
    logger.info(f"Ejecutando {action_name} con params: %s", {k:v for k,v in params.items() if k not in ['access_token']})

    page_id: Optional[str] = params.get("page_id")
    if not page_id:
        return {"status": "error", "action": action_name, "message": "'page_id' es requerido.", "http_status": 400}
        
    url = f"{NOTION_API_BASE_URL}/pages/{page_id}"
    logger.info(f"Obteniendo página de Notion ID: '{page_id}'")
    try:
        headers = _get_notion_api_headers(params)
        response = requests.get(url, headers=headers, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_notion_api_error(e, action_name, params)

def notion_create_page(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "notion_create_page"
    log_params = {k:v for k,v in params.items() if k not in ['access_token', 'page_payload']}
    if 'page_payload' in params: log_params['page_payload_keys'] = list(params['page_payload'].keys())
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    page_payload: Optional[Dict[str, Any]] = params.get("page_payload")
    if not page_payload or not isinstance(page_payload, dict) or not page_payload.get("parent"): # 'parent' es requerido
        return {"status": "error", "action": action_name, "message": "'page_payload' (dict) con al menos 'parent' es requerido.", "http_status": 400}
    if not page_payload.get("properties"): # 'properties' también es fundamental
        return {"status": "error", "action": action_name, "message": "'page_payload' debe incluir 'properties'.", "http_status": 400}

    url = f"{NOTION_API_BASE_URL}/pages"
    logger.info(f"Creando página en Notion. Parent: {page_payload.get('parent')}")
    try:
        headers = _get_notion_api_headers(params)
        response = requests.post(url, headers=headers, json=page_payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_notion_api_error(e, action_name, params)

def notion_update_page(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "notion_update_page"
    log_params = {k:v for k,v in params.items() if k not in ['access_token', 'update_payload']}
    if 'update_payload' in params: log_params['update_payload_keys'] = list(params['update_payload'].keys())
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    page_id: Optional[str] = params.get("page_id")
    update_payload: Optional[Dict[str, Any]] = params.get("update_payload") # Payload para PATCH, usualmente solo con 'properties'

    if not page_id:
        return {"status": "error", "action": action_name, "message": "'page_id' es requerido.", "http_status": 400}
    if not update_payload or not isinstance(update_payload, dict):
        return {"status": "error", "action": action_name, "message": "'update_payload' (dict) es requerido.", "http_status": 400}

    url = f"{NOTION_API_BASE_URL}/pages/{page_id}"
    logger.info(f"Actualizando página de Notion ID: '{page_id}'. Payload keys: {list(update_payload.keys())}")
    try:
        headers = _get_notion_api_headers(params)
        response = requests.patch(url, headers=headers, json=update_payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_notion_api_error(e, action_name, params)

def notion_delete_block(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "notion_delete_block" # Nota: Esto archiva el bloque. La eliminación permanente es diferente.
    logger.info(f"Ejecutando {action_name} con params: %s", {k:v for k,v in params.items() if k not in ['access_token']})

    block_id: Optional[str] = params.get("block_id")
    if not block_id:
        return {"status": "error", "action": action_name, "message": "'block_id' es requerido.", "http_status": 400}
        
    url = f"{NOTION_API_BASE_URL}/blocks/{block_id}"
    logger.info(f"Archivando (eliminando) bloque de Notion ID: '{block_id}'")
    try:
        headers = _get_notion_api_headers(params)
        response = requests.delete(url, headers=headers, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        # DELETE a un bloque devuelve el bloque archivado.
        return {"status": "success", "action": action_name, "data": response.json(), "message": f"Bloque '{block_id}' archivado.", "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_notion_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/notion_actions.py ---