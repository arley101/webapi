# app/actions/notion_actions.py
import logging
import requests
import json
from typing import Dict, Any, Optional, List, Union, Callable
from functools import wraps

from app.core.config import settings
# ✅ IMPORTACIÓN DIRECTA DEL RESOLVER PARA EVITAR CIRCULARIDAD
def _get_resolver():
    from app.actions.resolver_actions import Resolver
    return Resolver()
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# Constantes
NOTION_API_BASE_URL = "https://api.notion.com/v1"

# Tipo específico para los resultados de las acciones de Notion
NotionResult = Dict[str, Any]

# Enum para objetos de Notion (utilizando constantes)
NOTION_OBJECT_TYPES = {
    "DATABASE": "database",
    "PAGE": "page",
    "BLOCK": "block",
    "LIST": "list",
    "USER": "user",
    "ERROR": "error"
}

# Enum para propiedades de filtro
NOTION_FILTER_PROPERTIES = {
    "OBJECT": "object",
    "TITLE": "title",
    "CREATED_TIME": "created_time",
    "LAST_EDITED_TIME": "last_edited_time"
}

# Enum para tipos de bloques
NOTION_BLOCK_TYPES = {
    "PARAGRAPH": "paragraph",
    "HEADING_1": "heading_1",
    "HEADING_2": "heading_2",
    "HEADING_3": "heading_3",
    "BULLETED_LIST_ITEM": "bulleted_list_item",
    "NUMBERED_LIST_ITEM": "numbered_list_item",
    "TO_DO": "to_do",
    "TOGGLE": "toggle",
    "CODE": "code",
    "IMAGE": "image",
    "VIDEO": "video",
    "FILE": "file",
    "PDF": "pdf",
    "BOOKMARK": "bookmark",
    "CALLOUT": "callout",
    "QUOTE": "quote",
    "DIVIDER": "divider",
    "TABLE_OF_CONTENTS": "table_of_contents",
    "COLUMN_LIST": "column_list",
    "COLUMN": "column",
    "LINK_PREVIEW": "link_preview",
    "SYNCED_BLOCK": "synced_block",
    "CHILD_PAGE": "child_page",
    "CHILD_DATABASE": "child_database",
    "EMBED": "embed",
    "TEMPLATE": "template",
    "LINK_TO_PAGE": "link_to_page",
    "TABLE": "table",
    "TABLE_ROW": "table_row"
}

def _get_notion_api_headers(params: Dict[str, Any]) -> Dict[str, str]:
    """Prepara los headers para las solicitudes a la Notion API."""
    # CORRECCIÓN: Se usa settings.NOTION_API_KEY que es el nombre correcto de la propiedad.
    notion_token: Optional[str] = params.get("access_token", settings.NOTION_API_KEY)
    notion_version: str = params.get("notion_version", settings.NOTION_API_VERSION) 

    if not notion_token:
        raise ValueError("Se requiere el Token de Integración de Notion (NOTION_API_TOKEN en variables de entorno).")
    if not notion_version:
        raise ValueError("Se requiere la versión de la API de Notion (NOTION_API_VERSION).")

    return {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": notion_version,
        "Content-Type": "application/json"
    }

def _handle_notion_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> NotionResult:
    """
    Helper para manejar errores de Notion API.
    
    Args:
        e: La excepción capturada.
        action_name: Nombre de la acción que generó el error.
        params_for_log: Parámetros de la acción para incluir en el registro (se omiten valores sensibles).
        
    Returns:
        Diccionario con información estructurada sobre el error.
    """
    log_message = f"Error en Notion API Action '{action_name}'"
    safe_params = {k: (v if k not in ['access_token', 'payload', 'query'] else f"[{type(v).__name__} OMITIDO]") for k, v in (params_for_log or {}).items()}
    log_message += f" con params: {safe_params}"
    
    logger.error(log_message, exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    notion_error_code = None
    notion_error_message = str(e)

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json()
            if error_data.get("object") == "error":
                notion_error_code = error_data.get("code")
                notion_error_message = error_data.get("message", e.response.text)
            details_str = json.dumps(error_data)
        except json.JSONDecodeError:
            details_str = e.response.text[:500] if e.response.text else "No response body"
            notion_error_message = details_str
            
    return {
        "status": "error", "action": action_name,
        "message": f"Error interactuando con Notion API: {notion_error_message}",
        "details": {"notion_error_code": notion_error_code, "raw_response": details_str},
        "http_status": status_code_int
    }

# Decorador para manejar errores de forma consistente
def notion_error_handler(action_func: Callable) -> Callable:
    """
    Decorador que maneja los errores de las acciones de Notion de manera consistente.
    
    Args:
        action_func: La función de acción a decorar.
        
    Returns:
        Función envuelta que maneja errores.
    """
    @wraps(action_func)  # Preserva el nombre y metadatos de la función original
    def wrapper(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
        action_name = action_func.__name__
        try:
            return action_func(client, params)
        except Exception as e:
            return _handle_notion_api_error(e, action_name, params)
    return wrapper

# --- ACCIONES CRUD ESTÁNDAR Y DE BÚSQUEDA ---

@notion_error_handler
def notion_search_general(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Busca objetos en Notion basados en un texto de consulta.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener search_query_text, puede incluir sort, filter, start_cursor, y page_size.
        
    Returns:
        Resultado de la búsqueda en Notion.
    """
    payload_search = {
        "query": params.get("search_query_text"),
        "sort": params.get("sort"),
        "filter": params.get("filter"),
        "start_cursor": params.get("start_cursor"),
        "page_size": params.get("page_size")
    }
    payload_search = {k: v for k, v in payload_search.items() if v is not None}

    headers = _get_notion_api_headers(params)
    response = requests.post(f"{NOTION_API_BASE_URL}/search", headers=headers, json=payload_search, timeout=settings.DEFAULT_API_TIMEOUT)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}

@notion_error_handler
def notion_get_database(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Obtiene información detallada sobre una base de datos de Notion.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener database_id.
        
    Returns:
        Información detallada de la base de datos.
        
    Raises:
        ValueError: Si no se proporciona database_id.
    """
    database_id = params.get("database_id")
    if not database_id: raise ValueError("'database_id' es requerido.")
    headers = _get_notion_api_headers(params)
    response = requests.get(f"{NOTION_API_BASE_URL}/databases/{database_id}", headers=headers, timeout=settings.DEFAULT_API_TIMEOUT)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}

@notion_error_handler
def notion_query_database(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Consulta registros de una base de datos de Notion.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener database_id, puede incluir query_payload para filtrado y ordenamiento.
        
    Returns:
        Resultados de la consulta a la base de datos.
        
    Raises:
        ValueError: Si no se proporciona database_id.
    """
    database_id = params.get("database_id")
    query_payload = params.get("query_payload", {})
    if not database_id: raise ValueError("'database_id' es requerido.")
    headers = _get_notion_api_headers(params)
    response = requests.post(f"{NOTION_API_BASE_URL}/databases/{database_id}/query", headers=headers, json=query_payload, timeout=settings.DEFAULT_API_TIMEOUT)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}

@notion_error_handler
def notion_retrieve_page(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Obtiene información detallada sobre una página de Notion.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener page_id.
        
    Returns:
        Información detallada de la página.
        
    Raises:
        ValueError: Si no se proporciona page_id.
    """
    page_id = params.get("page_id")
    if not page_id: raise ValueError("'page_id' es requerido.")
    headers = _get_notion_api_headers(params)
    response = requests.get(f"{NOTION_API_BASE_URL}/pages/{page_id}", headers=headers, timeout=settings.DEFAULT_API_TIMEOUT)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}

@notion_error_handler
def notion_create_page(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Crea una nueva página en Notion.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener page_payload con parent.
        
    Returns:
        Información de la página creada.
        
    Raises:
        ValueError: Si no se proporciona page_payload con parent.
    """
    page_payload = params.get("page_payload")
    if not page_payload or not page_payload.get("parent"):
        raise ValueError("'page_payload' con una clave 'parent' es requerido.")
    headers = _get_notion_api_headers(params)
    response = requests.post(f"{NOTION_API_BASE_URL}/pages", headers=headers, json=page_payload, timeout=settings.DEFAULT_API_TIMEOUT)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}

@notion_error_handler
def notion_update_page(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Actualiza propiedades de una página de Notion.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener page_id y update_payload.
        
    Returns:
        Información actualizada de la página.
        
    Raises:
        ValueError: Si no se proporciona page_id o update_payload.
    """
    page_id = params.get("page_id")
    update_payload = params.get("update_payload")
    if not page_id or not update_payload:
        raise ValueError("'page_id' y 'update_payload' son requeridos.")
    headers = _get_notion_api_headers(params)
    response = requests.patch(f"{NOTION_API_BASE_URL}/pages/{page_id}", headers=headers, json=update_payload, timeout=settings.DEFAULT_API_TIMEOUT)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}

@notion_error_handler
def notion_delete_block(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Elimina un bloque de contenido de Notion.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener block_id.
        
    Returns:
        Confirmación de la eliminación del bloque.
        
    Raises:
        ValueError: Si no se proporciona block_id.
    """
    block_id = params.get("block_id")
    if not block_id: raise ValueError("'block_id' es requerido.")
    headers = _get_notion_api_headers(params)
    response = requests.delete(f"{NOTION_API_BASE_URL}/blocks/{block_id}", headers=headers, timeout=settings.DEFAULT_API_TIMEOUT)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}

# --- ACCIONES AVANZADAS Y "RESOLVERS" DE LA AUDITORÍA ---

@notion_error_handler
def notion_find_database_by_name(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Busca una base de datos de Notion por nombre.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener query_name.
        
    Returns:
        Información de la base de datos encontrada o error si no se encuentra.
        
    Raises:
        ValueError: Si no se proporciona query_name.
    """
    query_name = params.get("query_name")
    if not query_name: raise ValueError("'query_name' es requerido.")
    
    search_params = {
        "search_query_text": query_name,
        "filter": {"value": NOTION_OBJECT_TYPES["DATABASE"], "property": NOTION_FILTER_PROPERTIES["OBJECT"]}
    }
    search_params.update(params) # Para pasar access_token etc.
    
    search_result = notion_search_general(client, search_params)
    
    if search_result.get("status") != "success":
        return search_result
        
    databases = search_result.get("data", {}).get("results", [])
    if not databases:
        return {"status": "error", "message": f"No se encontró base de datos con el nombre '{query_name}'.", "http_status": 404}

    # Podría haber múltiples resultados, devolvemos el primero por simplicidad.
    return {"status": "success", "data": databases[0]}

@notion_error_handler
def notion_create_page_in_database(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Crea una nueva página en una base de datos de Notion.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener database_id y properties_payload.
        
    Returns:
        Información de la página creada en la base de datos.
        
    Raises:
        ValueError: Si no se proporciona database_id o properties_payload.
    """
    database_id = params.get("database_id")
    properties_payload = params.get("properties_payload")
    if not database_id or not properties_payload:
        raise ValueError("'database_id' y 'properties_payload' son requeridos.")
    
    page_payload = {
        "parent": {"database_id": database_id},
        "properties": properties_payload
    }
    
    # Agregar contenido si se proporciona
    if params.get("content"):
        page_payload["children"] = params.get("content")
    
    create_params = {"page_payload": page_payload}
    create_params.update(params) # Para pasar access_token etc.

    return notion_create_page(client, create_params)

@notion_error_handler
def notion_append_text_block_to_page(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Añade un bloque de texto al contenido de una página de Notion.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener page_id y text_content.
        
    Returns:
        Confirmación de la adición del bloque de texto.
        
    Raises:
        ValueError: Si no se proporciona page_id o text_content.
    """
    page_id = params.get("page_id")
    text_content = params.get("text_content")
    if not page_id or text_content is None:
        raise ValueError("'page_id' y 'text_content' son requeridos.")

    headers = _get_notion_api_headers(params)
    url = f"{NOTION_API_BASE_URL}/blocks/{page_id}/children"
    
    payload = {
        "children": [{
            "object": NOTION_OBJECT_TYPES["BLOCK"],
            "type": NOTION_BLOCK_TYPES["PARAGRAPH"],
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": text_content}}]
            }
        }]
    }

    response = requests.patch(url, headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}

@notion_error_handler
def notion_get_page_content(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Obtiene el contenido de una página de Notion.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener page_id.
        
    Returns:
        Contenido de la página.
        
    Raises:
        ValueError: Si no se proporciona page_id.
    """
    page_id = params.get("page_id")
    if not page_id: raise ValueError("'page_id' es requerido.")

    headers = _get_notion_api_headers(params)
    url = f"{NOTION_API_BASE_URL}/blocks/{page_id}/children"
    
    response = requests.get(url, headers=headers, timeout=settings.DEFAULT_API_TIMEOUT)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}

# Nuevas acciones adicionales para manejo de bloques

@notion_error_handler
def notion_update_block(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Actualiza un bloque existente en Notion.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener block_id y block_content.
        
    Returns:
        Información del bloque actualizado.
        
    Raises:
        ValueError: Si no se proporciona block_id o block_content.
    """
    block_id = params.get("block_id")
    block_content = params.get("block_content")
    if not block_id or not block_content:
        raise ValueError("'block_id' y 'block_content' son requeridos.")

    headers = _get_notion_api_headers(params)
    url = f"{NOTION_API_BASE_URL}/blocks/{block_id}"
    
    response = requests.patch(url, headers=headers, json=block_content, timeout=settings.DEFAULT_API_TIMEOUT)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}

@notion_error_handler
def notion_get_block(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Obtiene información detallada sobre un bloque específico.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener block_id.
        
    Returns:
        Información detallada del bloque.
        
    Raises:
        ValueError: Si no se proporciona block_id.
    """
    block_id = params.get("block_id")
    if not block_id: raise ValueError("'block_id' es requerido.")

    headers = _get_notion_api_headers(params)
    url = f"{NOTION_API_BASE_URL}/blocks/{block_id}"
    
    response = requests.get(url, headers=headers, timeout=settings.DEFAULT_API_TIMEOUT)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}

@notion_error_handler
def notion_create_database(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Crea una nueva base de datos en Notion.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener parent (página padre) y properties (esquema de la base de datos).
        
    Returns:
        Información de la base de datos creada.
        
    Raises:
        ValueError: Si no se proporcionan parent o properties.
    """
    parent = params.get("parent")
    properties = params.get("properties")
    title = params.get("title", [])
    
    if not parent or not properties:
        raise ValueError("'parent' y 'properties' son requeridos.")

    headers = _get_notion_api_headers(params)
    payload = {
        "parent": parent,
        "title": title,
        "properties": properties,
    }
    
    response = requests.post(f"{NOTION_API_BASE_URL}/databases", headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}

@notion_error_handler
def notion_add_users_to_page(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Comparte una página con usuarios específicos.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener page_id y user_ids.
        
    Returns:
        Resultado de la operación de compartir.
        
    Raises:
        ValueError: Si no se proporciona page_id o user_ids.
    """
    page_id = params.get("page_id")
    user_ids = params.get("user_ids", [])
    
    if not page_id or not user_ids:
        raise ValueError("'page_id' y 'user_ids' son requeridos.")

    headers = _get_notion_api_headers(params)
    url = f"{NOTION_API_BASE_URL}/pages/{page_id}/users"
    
    payload = {
        "users": user_ids
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}

@notion_error_handler
def notion_archive_page(client: Optional[Any], params: Dict[str, Any]) -> NotionResult:
    """
    Archiva una página en Notion.
    
    Args:
        client: Cliente HTTP (no utilizado en esta implementación).
        params: Debe contener page_id.
        
    Returns:
        Confirmación del archivo de la página.
        
    Raises:
        ValueError: Si no se proporciona page_id.
    """
    page_id = params.get("page_id")
    if not page_id:
        raise ValueError("'page_id' es requerido.")

    headers = _get_notion_api_headers(params)
    url = f"{NOTION_API_BASE_URL}/pages/{page_id}"
    
    payload = {
        "archived": True
    }
    
    response = requests.patch(url, headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}