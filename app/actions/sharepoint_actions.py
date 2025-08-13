# app/actions/sharepoint_actions.py
import logging
import requests
import json
import csv
from io import StringIO
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone as dt_timezone
from urllib.parse import quote

# Importar la configuración y el cliente HTTP autenticado
from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient


logger = logging.getLogger(__name__)

# Scope por defecto con fallback seguro
DEFAULT_SCOPE = getattr(settings, 'GRAPH_API_DEFAULT_SCOPE', 'https://graph.microsoft.com/.default')

# --- Helper para validar si un input parece un Graph Site ID ---
def _is_valid_graph_site_id_format(site_id_string: str) -> bool:
    """
    Verifica si el string tiene formato de Graph Site ID.
    Formato esperado: tenant.sharepoint.com,{guid},{guid}
    """
    if not site_id_string or not isinstance(site_id_string, str):
        return False
    
    parts = site_id_string.split(',')
    if len(parts) != 3:
        return False
    
    # Verificar que tenga formato de dominio SharePoint
    if not parts[0].endswith('.sharepoint.com'):
        return False
    
    # Verificar que las otras partes parezcan GUIDs
    import re
    guid_pattern = r'^[a-fA-F0-9\-]{36}$'
    
    return bool(re.match(guid_pattern, parts[1]) and re.match(guid_pattern, parts[2]))

# --- Helper Interno para Obtener Site ID (versión robusta) ---
def _obtener_site_id_sp(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> str:
    """Obtiene el Site ID de SharePoint de manera robusta."""
    
    # 1. Si se proporciona site_id directamente
    site_id = params.get("site_id")
    if site_id and _is_valid_graph_site_id_format(site_id):
        return site_id
    
    # 2. Si se proporciona site_name
    site_name = params.get("site_name")
    if site_name:
        # Buscar el sitio por nombre
        search_url = f"{settings.GRAPH_API_BASE_URL}/sites?search={quote(site_name)}"
        response = client.get(search_url, scope=DEFAULT_SCOPE)
        
        if response.get("value"):
            # Retornar el primer sitio encontrado
            return response["value"][0]["id"]
        else:
            raise ValueError(f"No se encontró el sitio con nombre: {site_name}")
    
    # 3. Usar el site_id por defecto de la configuración
    default_site_id = settings.SHAREPOINT_DEFAULT_SITE_ID
    if default_site_id:
        return default_site_id
    
    # 4. Si no hay nada configurado, obtener el sitio raíz
    root_url = f"{settings.GRAPH_API_BASE_URL}/sites/root"
    response = client.get(root_url, scope=DEFAULT_SCOPE)
    
    if response.get("id"):
        return response["id"]
    
    raise ValueError("No se pudo determinar el Site ID de SharePoint")

# --- Helper Interno para Obtener Drive ID ---
def _get_drive_id(client: AuthenticatedHttpClient, site_id: str, drive_id_or_name_input: Optional[str] = None) -> str:
    """Obtiene el Drive ID basado en ID o nombre."""
    
    # Si no se proporciona input, usar el default
    drive_input = drive_id_or_name_input or settings.SHAREPOINT_DEFAULT_DRIVE_ID_OR_NAME or "Documents"
    
    # Si parece ser un ID (tiene formato GUID), retornarlo directamente
    import re
    if re.match(r'^[a-fA-F0-9\-]{36}$', drive_input):
        return drive_input
    
    # Si es un nombre, buscar el drive
    drives_url = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives"
    response = client.get(drives_url, scope=DEFAULT_SCOPE)
    
    if not response.get("value"):
        raise ValueError(f"No se encontraron drives en el sitio {site_id}")
    
    # Buscar por nombre
    for drive in response["value"]:
        if drive.get("name", "").lower() == drive_input.lower():
            return drive["id"]
    
    # Si no se encuentra por nombre exacto, buscar parcialmente
    for drive in response["value"]:
        if drive_input.lower() in drive.get("name", "").lower():
            return drive["id"]
    
    # Si no se encuentra, usar el primer drive disponible
    logger.warning(f"No se encontró el drive '{drive_input}', usando el primero disponible")
    return response["value"][0]["id"]

def _get_sp_item_endpoint_by_path(site_id: str, drive_id: str, item_path: str) -> str:
    """Construye el endpoint para acceder a un item por path."""
    # Limpiar el path
    clean_path = item_path.strip()
    if not clean_path.startswith('/'):
        clean_path = '/' + clean_path
    
    # Codificar el path para URL
    encoded_path = quote(clean_path, safe='')
    
    return f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/root:{encoded_path}"

def _get_sp_item_endpoint_by_id(site_id: str, drive_id: str, item_id: str) -> str:
    """Construye el endpoint para acceder a un item por ID."""
    return f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/items/{item_id}"

def _handle_graph_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Maneja errores de la API de Graph de manera consistente."""
    error_msg = str(e)
    error_details = {}
    
    # Intentar extraer detalles del error si es una respuesta HTTP
    if hasattr(e, 'response') and e.response:
        try:
            error_data = e.response.json()
            error_details = {
                "code": error_data.get("error", {}).get("code"),
                "message": error_data.get("error", {}).get("message"),
                "status_code": e.response.status_code
            }
            error_msg = error_details.get("message", error_msg)
        except:
            error_details["status_code"] = getattr(e.response, 'status_code', 'Unknown')
    
    logger.error(f"Error in {action_name}: {error_msg}", extra={
        "action": action_name,
        "params": params_for_log,
        "error_details": error_details
    })
    
    return {
        "success": False,
        "error": error_msg,
        "error_details": error_details,
        "action": action_name
    }

def _get_current_timestamp_iso_z() -> str:
    """Obtiene el timestamp actual en formato ISO con Z."""
    return datetime.now(dt_timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def _sp_paged_request(
    client: AuthenticatedHttpClient, url_base: str, scope: List[str],
    params_input: Dict[str, Any], query_api_params_initial: Dict[str, Any],
    max_items_total: Optional[int], action_name_for_log: str
) -> Dict[str, Any]:
    """Realiza una petición paginada a SharePoint/Graph API."""
    
    all_items = []
    next_link = None
    page_count = 0
    max_pages = 50  # Límite de seguridad
    
    # Primera petición
    if not next_link:
        response = client.get(url_base, params=query_api_params_initial, scope=scope)
    else:
        response = client.get(next_link, scope=scope)
    
    while True:
        page_count += 1
        
        # Agregar items de esta página
        if "value" in response:
            all_items.extend(response["value"])
        
        # Verificar si alcanzamos el límite
        if max_items_total and len(all_items) >= max_items_total:
            all_items = all_items[:max_items_total]
            break
        
        # Verificar si hay más páginas
        next_link = response.get("@odata.nextLink")
        if not next_link or page_count >= max_pages:
            break
        
        # Obtener siguiente página
        logger.debug(f"Obteniendo página {page_count + 1} para {action_name_for_log}")
        response = client.get(next_link, scope=scope)
    
    return {
        "success": True,
        "data": all_items,
        "count": len(all_items),
        "pages_retrieved": page_count
    }

def _get_item_id_from_path_if_needed_sp(
    client: AuthenticatedHttpClient, item_path_or_id: str,
    site_id: str, drive_id: str,
    params_for_metadata: Optional[Dict[str, Any]] = None
) -> Union[str, Dict[str, Any]]:
    """
    Determina si el input es un path o ID, y obtiene el ID si es necesario.
    Retorna el item_id o un dict con error.
    """
    import re
    
    # Si parece ser un ID (formato GUID), retornarlo
    if re.match(r'^[a-fA-F0-9\-]{36}$', item_path_or_id):
        return item_path_or_id
    
    # Si parece ser un path, obtener metadatos para conseguir el ID
    try:
        endpoint = _get_sp_item_endpoint_by_path(site_id, drive_id, item_path_or_id)
        response = client.get(endpoint, scope=DEFAULT_SCOPE)
        
        if response.get("id"):
            return response["id"]
        else:
            return {
                "success": False,
                "error": f"No se pudo obtener el ID del item en path: {item_path_or_id}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error obteniendo ID del item: {str(e)}"
        }


# ============================================
# ==== ACCIONES PÚBLICAS (Mapeadas) ====
# ============================================
def get_site_info(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene información detallada de un sitio de SharePoint."""
    try:
        site_id = _obtener_site_id_sp(client, params)
        
        # Obtener información del sitio
        site_url = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}"
        site_info = client.get(site_url, scope=DEFAULT_SCOPE)
        
        # Obtener drives del sitio
        drives_url = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives"
        drives_response = client.get(drives_url, scope=DEFAULT_SCOPE)
        
        # Obtener listas del sitio
        lists_url = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/lists"
        lists_response = client.get(lists_url, scope=DEFAULT_SCOPE)
        
        return {
            "success": True,
            "data": {
                "site": site_info,
                "drives": drives_response.get("value", []),
                "lists": lists_response.get("value", [])[:10],  # Limitar a 10 listas
                "summary": {
                    "name": site_info.get("name"),
                    "displayName": site_info.get("displayName"),
                    "webUrl": site_info.get("webUrl"),
                    "id": site_info.get("id"),
                    "drives_count": len(drives_response.get("value", [])),
                    "lists_count": len(lists_response.get("value", []))
                }
            }
        }
    except Exception as e:
        return _handle_graph_api_error(e, "get_site_info", params)

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
    """Crea una nueva lista en SharePoint con columnas opcionales"""
    try:
        site_id = params.get("site_id")
        list_name = params.get("name")
        description = params.get("description", "")
        columns = params.get("columns", [])
        
        if not site_id or not list_name:
            return {
                "success": False,
                "error": "site_id and name are required"
            }
        
        # Preparar el payload
        list_data = {
            "displayName": list_name,
            "description": description,
            "list": {
                "template": "genericList"
            }
        }

        # Hacer la llamada a la API
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists"
        response = client.post(url, scope=DEFAULT_SCOPE, json_data=list_data)

        created_list = response or {}
        if created_list.get("id"):
            list_id = created_list["id"]
            
            # Crear columnas adicionales si se especificaron
            for column in columns:
                column_result = _create_list_column(client, site_id, list_id, column)
                if not column_result.get("success"):
                    logger.warning(f"Failed to create column {column.get('name')}: {column_result.get('error')}")
            
            # Auto-registrar en el sistema (best-effort)
            try:
                from app.actions import resolver_actions
                register_result = resolver_actions.smart_save_resource(client, {
                    "resource_type": "sharepoint_list",
                    "resource_data": {
                        "id": list_id,
                        "name": list_name,
                        "webUrl": created_list.get("webUrl"),
                        "site_id": site_id,
                        "columns": columns
                    },
                    "action_name": "sp_create_list",
                    "tags": ["sharepoint", "list", "created"]
                })
            except Exception as _e:
                logger.warning(f"Auto-registro falló o no disponible: {_e}")
                register_result = {"success": False}
            
            return {
                "success": True,
                "data": {
                    "id": list_id,
                    "name": created_list.get("displayName") or created_list.get("name"),
                    "webUrl": created_list.get("webUrl"),
                    "createdDateTime": created_list.get("createdDateTime"),
                    "description": created_list.get("description"),
                    "list": created_list,
                    "auto_registered": register_result.get("success", False),
                    "registry_id": register_result.get("registry_id") if register_result.get("success") else None
                },
                "message": f"List '{list_name}' created successfully"
            }
        else:
            return {
                "success": False,
                "error": "Failed to create list",
                "details": created_list
            }
            
    except Exception as e:
        logger.error(f"Error creating SharePoint list: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def _create_list_column(client: Any, site_id: str, list_id: str, column_config: Dict[str, Any]) -> Dict[str, Any]:
    """Crea una columna en una lista"""
    try:
        column_type = column_config.get("type", "text")
        column_name = column_config.get("name")
        
        if not column_name:
            return {"success": False, "error": "Column name is required"}
        
        # Mapear tipos de columna
        type_mapping = {
            "text": {"text": {}},
            "note": {"text": {"allowMultipleLines": True}},
            "number": {"number": {"decimalPlaces": "automatic"}},
            "boolean": {"boolean": {}},
            "dateTime": {"dateTime": {"format": "dateTime"}},
            "choice": {"choice": {"choices": column_config.get("choices", [])}},
            "url": {"hyperlinkOrPicture": {}}
        }
        
        column_definition = type_mapping.get(column_type, {"text": {}})
        
        column_data = {
            "name": column_name,
            "displayName": column_config.get("displayName", column_name),
            "required": column_config.get("required", False),
            **column_definition
        }
        
        if column_config.get("defaultValue"):
            column_data["defaultValue"] = {"value": str(column_config["defaultValue"])}
        
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/columns"
        response = client.post(url, scope=DEFAULT_SCOPE, json_data=column_data)
        if isinstance(response, dict) and (response.get("id") or response.get("name")):
            return {"success": True, "data": response}
        else:
            return {"success": False, "error": "Failed to create column", "details": response}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

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
        return {"status": "success", "data": response}
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
        _ = client.delete(url, scope=sites_manage_scope)
        # Delete devuelve 204 No Content
        return {"status": "success", "message": f"Lista '{list_id_or_name}' eliminada exitosamente de sitio '{target_site_id}'.", "http_status": 204}
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def add_list_item(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Añade un item a una lista de SharePoint con auto-registro"""
    try:
        site_id = params.get("site_id")
        list_id = params.get("list_id")
        fields = params.get("fields", {})
        
        if not site_id or not list_id:
            return {
                "success": False,
                "error": "site_id and list_id are required"
            }
        
        # Preparar el payload
        item_data = {
            "fields": fields
        }

        # Hacer la llamada a la API
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items"
        response = client.post(url, scope=DEFAULT_SCOPE, json_data=item_data)

        created_item = response or {}
        if created_item.get("id"):
            # Auto-registrar si el item es importante
            if len(json.dumps(fields)) > 100:  # Si tiene contenido significativo
                try:
                    from app.actions import resolver_actions
                    _ = resolver_actions.smart_save_resource(client, {
                        "resource_type": "sharepoint_item",
                        "resource_data": {
                            "id": created_item.get("id"),
                            "list_id": list_id,
                            "site_id": site_id,
                            "fields": fields,
                            "webUrl": created_item.get("webUrl")
                        },
                        "action_name": "sp_add_list_item",
                        "tags": ["sharepoint", "list_item", "created"]
                    })
                except Exception as _e:
                    logger.debug(f"Auto-registro no disponible: {_e}")

            return {
                "success": True,
                "data": {
                    "id": created_item.get("id"),
                    "webUrl": created_item.get("webUrl"),
                    "createdDateTime": created_item.get("createdDateTime"),
                    "fields": created_item.get("fields", {}),
                    "item": created_item
                },
                "message": "Item added successfully to list"
            }
        else:
            return {
                "success": False,
                "error": "Failed to add item",
                "details": response
            }
            
    except Exception as e:
        logger.error(f"Error adding item to SharePoint list: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

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
        return {"status": "success", "data": response}
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
        _ = client.delete(url, scope=sites_manage_scope, headers=request_headers)
        # Delete devuelve 204 No Content
        return {"status": "success", "message": f"Item '{item_id}' eliminado de lista '{list_id_or_name}'.", "http_status": 204}
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
    clave: Optional[str] = params.get("clave")

    if not session_id or not clave: 
        return _handle_graph_api_error(ValueError("'session_id' y 'clave' son requeridos para memory_get."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        
        # Asegurar que la lista exista
        if not _ensure_memory_list_exists(client, target_site_id):
            return {"status": "error", "action": action_name, "message": f"No se pudo asegurar/crear la lista memoria '{MEMORIA_LIST_NAME_FROM_SETTINGS}' en sitio '{target_site_id}'."}

        # Buscar el item con esa SessionID y Clave
        filter_q = f"fields/SessionID eq '{session_id}' and fields/Clave eq '{clave}'"
        list_params = {
            "site_id": target_site_id,
            "site_identifier": params.get("site_identifier", params.get("site_id")),
            "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, 
            "filter_query": filter_q, 
            "top_per_page": 1, 
            "max_items_total": 1,
            "expand": "fields(select=*)"
        }
        
        items_response = list_list_items(client, list_params)
        
        if items_response.get("status") == "success":
            items_value = items_response.get("data", [])
            if items_value and len(items_value) > 0:
                item = items_value[0]
                fields = item.get("fields", {})
                valor_str = fields.get("Valor", "")
                
                # Deserializar el valor
                try:
                    valor = json.loads(valor_str)
                except:
                    valor = valor_str  # Si no es JSON válido, devolver como string
                
                return {
                    "status": "success",
                    "data": {
                        "session_id": session_id,
                        "clave": clave,
                        "valor": valor,
                        "timestamp": fields.get("Timestamp"),
                        "item_id": item.get("id")
                    }
                }
            else:
                return {
                    "status": "not_found",
                    "message": f"No se encontró valor para SessionID: {session_id}, Clave: {clave}"
                }
        else:
            return items_response  # Propagar el error
            
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def memory_delete(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando memory_delete con params: %s", params)
    action_name = "memory_delete"

    session_id: Optional[str] = params.get("session_id")
    clave: Optional[str] = params.get("clave")

    if not session_id or not clave: 
        return _handle_graph_api_error(ValueError("'session_id' y 'clave' son requeridos para memory_delete."), action_name, params)
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        
        # Buscar el item a eliminar
        filter_q = f"fields/SessionID eq '{session_id}' and fields/Clave eq '{clave}'"
        list_params = {
            "site_id": target_site_id,
            "site_identifier": params.get("site_identifier", params.get("site_id")),
            "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS, 
            "filter_query": filter_q, 
            "top_per_page": 1, 
            "max_items_total": 1,
            "select": "id"
        }
        
        items_response = list_list_items(client, list_params)
        
        if items_response.get("status") == "success":
            items_value = items_response.get("data", [])
            if items_value and len(items_value) > 0:
                item_id = items_value[0].get("id")
                
                # Eliminar el item
                delete_params = {
                    "site_id": target_site_id,
                    "site_identifier": params.get("site_identifier", params.get("site_id")),
                    "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS,
                    "item_id": item_id
                }
                
                return delete_list_item(client, delete_params)
            else:
                return {
                    "status": "not_found",
                    "message": f"No se encontró item para eliminar con SessionID: {session_id}, Clave: {clave}"
                }
        else:
            return items_response  # Propagar el error
            
    except Exception as e: 
        return _handle_graph_api_error(e, action_name, params)

def memory_list_keys(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Lista todas las keys en memoria con filtros opcionales"""
    params = params or {}
    logger.info("Ejecutando memory_list_keys con params: %s", params)
    action_name = "memory_list_keys"
    
    try:
        target_site_id = _obtener_site_id_sp(client, params)
        # Construir filtro
        filters = []
        if params.get("session_id"):
            filters.append(f"fields/SessionID eq '{params['session_id']}'")
        
        # Obtener items
        list_params = {
            "site_id": target_site_id,
            "site_identifier": params.get("site_identifier", params.get("site_id")),
            "lista_id_o_nombre": MEMORIA_LIST_NAME_FROM_SETTINGS,
            "expand": "fields(select=*)",
            "top_per_page": params.get("limit", 100),
            "max_items_total": params.get("limit", 100)
        }
        
        if filters:
            list_params["filter_query"] = " and ".join(filters)
        
        items_response = list_list_items(client, list_params)
        
        if items_response.get("status") != "success":
            return items_response
        
        # Formatear respuesta
        keys_data = []
        items_value = items_response.get("data", [])
        for item in items_value:
            fields = item.get("fields", {})
            
            keys_data.append({
                "session_id": fields.get("SessionID"),
                "clave": fields.get("Clave"),
                "timestamp": fields.get("Timestamp"),
                "item_id": item.get("id")
            })
        
        return {
            "status": "success",
            "data": {
                "keys": keys_data,
                "total": len(keys_data),
                "site_id": target_site_id
            }
        }
        
    except Exception as e:
        return _handle_graph_api_error(e, action_name, params)

def memory_export_session(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
    """Exporta toda la memoria de una sesión"""
    params = params or {}
    logger.info("Ejecutando memory_export_session con params: %s", params)
    action_name = "memory_export_session"
    
    try:
        session_id = params.get("session_id")
        export_format = params.get("format", "json")  # json, csv
        
        if not session_id:
            raise ValueError("'session_id' es requerido")
        
        # Obtener todas las claves de la sesión
        keys_result = memory_list_keys(client, params)
        
        if keys_result.get("status") != "success":
            return keys_result
        
        # Obtener todos los valores
        session_data = {}
        for key_info in keys_result["data"]["keys"]:
            get_result = memory_get(client, {
                **params,
                "session_id": session_id,
                "clave": key_info["clave"]
            })
            
            if get_result.get("status") == "success":
                session_data[key_info["clave"]] = {
                    "valor": get_result["data"]["valor"],
                    "timestamp": get_result["data"]["timestamp"]
                }
        
        # Formatear según el formato solicitado
        if export_format == "csv":
            # Crear CSV
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["session_id", "clave", "valor", "timestamp"])
            
            for clave, data in session_data.items():
                writer.writerow([
                    session_id,
                    clave,
                    json.dumps(data["valor"]) if isinstance(data["valor"], (dict, list)) else data["valor"],
                    data["timestamp"]
                ])
            
            return output.getvalue()
        else:
            # JSON por defecto
            return {
                "status": "success",
                "action": action_name,
                "data": {
                    "session_id": session_id,
                    "export_date": datetime.now().isoformat(),
                    "total_keys": len(session_data),
                    "session_data": session_data
                }
            }
            
    except Exception as e:
        return _handle_graph_api_error(e, action_name, params)

def sp_export_list_to_format(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
    """Exporta los items de una lista a CSV o JSON"""
    params = params or {}
    logger.info("Ejecutando sp_export_list_to_format con params: %s", params)
    action_name = "sp_export_list_to_format"
    
    try:
        # Obtener todos los items de la lista
        items_result = list_list_items(client, params)
        
        if items_result.get("status") != "success":
            return items_result
        
        items = items_result.get("data", [])
        export_format = params.get("format", "json").lower()
        
        if export_format == "csv":
            # Crear CSV
            output = StringIO()
            
            if items:
                # Obtener todas las columnas únicas
                all_fields = set()
                for item in items:
                    if "fields" in item:
                        all_fields.update(item["fields"].keys())
                
                # Escribir encabezados
                fieldnames = ["id"] + sorted(all_fields)
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                # Escribir datos
                for item in items:
                    row = {"id": item.get("id", "")}
                    fields = item.get("fields", {})
                    for field in all_fields:
                        value = fields.get(field, "")
                        # Convertir valores complejos a string
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value)
                        row[field] = value
                    writer.writerow(row)
            
            return output.getvalue()
        else:
            # JSON por defecto
            return {
                "status": "success",
                "action": action_name,
                "data": {
                    "list_name": params.get("lista_id_o_nombre", ""),
                    "export_date": datetime.now().isoformat(),
                    "total_items": len(items),
                    "items": items
                }
            }
            
    except Exception as e:
        return _handle_graph_api_error(e, action_name, params)

# --- Función prefijada para el proxy ---
# Todas las funciones que comienzan con sp_ para el proxy
sp_get_site_info = get_site_info
sp_search_sites = search_sites
sp_list_document_libraries = list_document_libraries
sp_create_list = create_list
sp_list_lists = list_lists
sp_get_list = get_list
sp_update_list = update_list
sp_delete_list = delete_list
sp_add_list_item = add_list_item
sp_list_list_items = list_list_items
sp_get_list_item = get_list_item
sp_update_list_item = update_list_item
sp_delete_list_item = delete_list_item
sp_search_list_items = search_list_items
sp_list_folder_contents = list_folder_contents
sp_get_file_metadata = get_file_metadata
sp_upload_document = upload_document
sp_download_document = download_document
sp_delete_document = delete_document
sp_delete_item = delete_item
sp_create_folder = create_folder
sp_move_item = move_item
sp_copy_item = copy_item
sp_update_file_metadata = update_file_metadata
sp_get_sharing_link = get_sharing_link
sp_list_item_permissions = list_item_permissions
sp_add_item_permissions = add_item_permissions
sp_remove_item_permissions = remove_item_permissions
sp_memory_ensure_list = memory_ensure_list
sp_memory_save = memory_save
sp_memory_get = memory_get
sp_memory_delete = memory_delete
sp_memory_list_keys = memory_list_keys
sp_memory_export_session = memory_export_session