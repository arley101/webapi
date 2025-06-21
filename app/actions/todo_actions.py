# app/actions/todo_actions.py
import logging
import requests # Para requests.exceptions.HTTPError
import json # Para el helper de error
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone as dt_timezone

# Importar la configuración y el cliente HTTP autenticado
from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# Helper de _parse_and_utc_datetime_str (copiado del original)
def _parse_and_utc_datetime_str(datetime_str: Any, field_name_for_log: str) -> str:
    if isinstance(datetime_str, datetime):
        dt_obj = datetime_str
    elif isinstance(datetime_str, str):
        try:
            if datetime_str.endswith('Z'):
                dt_obj = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            elif '+' in datetime_str[10:] or '-' in datetime_str[10:]: # Check for timezone offset
                 dt_obj = datetime.fromisoformat(datetime_str)
            else: # No timezone info, assume it's intended to be UTC or local (less safe)
                dt_obj = datetime.fromisoformat(datetime_str)
        except ValueError as e:
            logger.error(f"Formato de fecha/hora inválido para '{field_name_for_log}': '{datetime_str}'. Error: {e}")
            raise ValueError(f"Formato de fecha/hora inválido para '{field_name_for_log}': '{datetime_str}'. Se esperaba ISO 8601.") from e
    else:
        raise ValueError(f"Tipo inválido para '{field_name_for_log}': se esperaba string o datetime.")

    if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
        logger.debug(f"Fecha/hora '{datetime_str}' para '{field_name_for_log}' es naive. Asumiendo y estableciendo a UTC.")
        dt_obj_utc = dt_obj.replace(tzinfo=dt_timezone.utc)
    else:
        dt_obj_utc = dt_obj.astimezone(dt_timezone.utc)
    return dt_obj_utc.isoformat(timespec='seconds').replace('+00:00', 'Z')

def _handle_todo_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en ToDo action '{action_name}'"
    if params_for_log:
        log_message += f" con params: {params_for_log}" # Asumir params no sensibles o filtrar
    logger.error(f"{log_message}: {type(e).__name__} - {e}", exc_info=True)
    details = str(e)
    status_code = 500
    graph_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code = e.response.status_code
        try:
            error_data = e.response.json()
            error_info = error_data.get("error", {})
            details = error_info.get("message", e.response.text)
            graph_error_code = error_info.get("code")
        except json.JSONDecodeError:
            details = e.response.text
    return {
        "status": "error", 
        "action": action_name,
        "message": f"Error en {action_name}: {details}", 
        "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details,
        "http_status": status_code,
        "graph_error_code": graph_error_code
        }

# =================================
# ==== FUNCIONES ACCIÓN TO-DO  ====
# =================================

def list_task_lists(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_task_lists con params: %s", params)
    action_name = "todo_list_task_lists"

    user_identifier: Optional[str] = params.get("user_identifier_for_todo")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_identifier_for_todo' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_identifier_for_todo' (UPN o ID de objeto del usuario) es requerido.", "http_status": 400}

    url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists"
    top_per_page: int = min(int(params.get('top_per_page', 25)), getattr(settings, 'MAX_GRAPH_TOP_VALUE_PAGING', 100))
    max_items_total: Optional[int] = params.get('max_items_total') # Permitir None para todos los items
    
    query_api_params_initial: Dict[str, Any] = {'$top': top_per_page}
    query_api_params_initial['$select'] = params.get('select', "id,displayName,isOwner,isShared,wellknownListName")
    if params.get('filter_query'): query_api_params_initial['$filter'] = params.get('filter_query')
    if params.get('order_by'): query_api_params_initial['$orderby'] = params.get('order_by')

    all_lists: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages = getattr(settings, 'MAX_PAGING_PAGES', 20)
    logger.info(f"Listando listas de ToDo para usuario '{user_identifier}' (Max total: {max_items_total if max_items_total is not None else 'todos'}, Por pág: {top_per_page})")
    todo_read_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READ', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        while current_url and (max_items_total is None or len(all_lists) < max_items_total) and page_count < max_pages :
            page_count += 1
            current_call_params = query_api_params_initial if page_count == 1 else None
            response = client.get(current_url, scope=todo_read_scope, params=current_call_params)
            
            # --- CORRECCIÓN ---
            response_data = response

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            for item in page_items:
                if max_items_total is None or len(all_lists) < max_items_total: 
                    all_lists.append(item)
                else: break # Alcanzado max_items_total
            current_url = response_data.get('@odata.nextLink')
            if not current_url or (max_items_total is not None and len(all_lists) >= max_items_total): break
        logger.info(f"Total listas ToDo recuperadas para '{user_identifier}': {len(all_lists)} ({page_count} pág procesadas).")
        return {"status": "success", "data": {"value": all_lists, "@odata.count": len(all_lists)}, "total_retrieved": len(all_lists), "pages_processed": page_count}
    except Exception as e:
        return _handle_todo_api_error(e, action_name)

def create_task_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando create_task_list con params: %s", params)
    action_name = "todo_create_task_list"

    user_identifier: Optional[str] = params.get("user_identifier_for_todo")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_identifier_for_todo' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_identifier_for_todo' (UPN o ID de objeto del usuario) es requerido.", "http_status": 400}
    
    displayName: Optional[str] = params.get("displayName")
    if not displayName:
        return {"status": "error", "action": action_name, "message": "Parámetro 'displayName' es requerido.", "http_status": 400}
    
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists"
    body = {"displayName": displayName}
    logger.info(f"Creando lista de ToDo '{displayName}' para usuario '{user_identifier}'")
    todo_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.post(url, scope=todo_rw_scope, json_data=body)
        list_data = response.json()
        return {"status": "success", "data": list_data, "message": "Lista ToDo creada."}
    except Exception as e:
        return _handle_todo_api_error(e, action_name)

def list_tasks(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_tasks con params: %s", params)
    action_name = "todo_list_tasks"

    user_identifier: Optional[str] = params.get("user_identifier_for_todo")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_identifier_for_todo' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_identifier_for_todo' (UPN o ID de objeto del usuario) es requerido.", "http_status": 400}

    list_id: Optional[str] = params.get("list_id")
    if not list_id:
        return {"status": "error", "action": action_name, "message": "Parámetro 'list_id' es requerido.", "http_status": 400}
    
    top_per_page: int = min(int(params.get('top_per_page', 25)), getattr(settings, 'MAX_GRAPH_TOP_VALUE_PAGING', 100))
    max_items_total: Optional[int] = params.get('max_items_total')
    
    query_api_params_initial: Dict[str, Any] = {'$top': top_per_page}
    query_api_params_initial['$select'] = params.get('select', "id,title,status,importance,isReminderOn,createdDateTime,lastModifiedDateTime,dueDateTime,completedDateTime")
    if params.get('filter_query'): query_api_params_initial['$filter'] = params.get('filter_query')
    if params.get('order_by'): query_api_params_initial['$orderby'] = params.get('order_by')
    
    url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks"
    all_tasks: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages = getattr(settings, 'MAX_PAGING_PAGES', 20)
    logger.info(f"Listando tareas ToDo para usuario '{user_identifier}', lista '{list_id}' (Max total: {max_items_total if max_items_total is not None else 'todos'}, Por pág: {top_per_page})")
    todo_read_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READ', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        while current_url and (max_items_total is None or len(all_tasks) < max_items_total) and page_count < max_pages:
            page_count += 1
            current_call_params = query_api_params_initial if page_count == 1 else None
            response = client.get(current_url, scope=todo_read_scope, params=current_call_params)

            # --- CORRECCIÓN ---
            response_data = response

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            for item in page_items:
                if max_items_total is None or len(all_tasks) < max_items_total: 
                    all_tasks.append(item)
                else: break
            current_url = response_data.get('@odata.nextLink')
            if not current_url or (max_items_total is not None and len(all_tasks) >= max_items_total): break
        logger.info(f"Total tareas ToDo recuperadas de lista '{list_id}' para '{user_identifier}': {len(all_tasks)} ({page_count} pág procesadas).")
        return {"status": "success", "data": {"value": all_tasks, "@odata.count": len(all_tasks)}, "total_retrieved": len(all_tasks), "pages_processed": page_count}
    except Exception as e:
        return _handle_todo_api_error(e, action_name)

def create_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando create_task con params: %s", params)
    action_name = "todo_create_task"

    user_identifier: Optional[str] = params.get("user_identifier_for_todo")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_identifier_for_todo' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_identifier_for_todo' (UPN o ID de objeto del usuario) es requerido.", "http_status": 400}

    list_id: Optional[str] = params.get("list_id")
    title: Optional[str] = params.get("title")
    if not list_id or not title:
        return {"status": "error", "action": action_name, "message": "Parámetros 'list_id' y 'title' son requeridos.", "http_status": 400}
    
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks"
    body: Dict[str, Any] = {"title": title}
    
    optional_fields_direct = ["importance", "isReminderOn", "status"]
    for field in optional_fields_direct:
        if params.get(field) is not None: body[field] = params[field]
    
    if params.get("body_content"):
        body["body"] = {"content": params["body_content"], "contentType": params.get("body_contentType", "text")}
    
    datetime_fields_map = {
        "dueDateTime": "dueDateTime", 
        "reminderDateTime": "reminderDateTime",
        "startDateTime": "startDateTime", # No es un campo estándar directo en todoTask, puede que no funcione así
        "completedDateTime": "completedDateTime"
    }
    for param_key, graph_key in datetime_fields_map.items():
        dt_input = params.get(param_key)
        if dt_input:
            try:
                # Asumir que dt_input puede ser un string ISO o un dict {"dateTime": "...", "timeZone": "..."}
                dt_val_str = dt_input.get("dateTime") if isinstance(dt_input, dict) else dt_input
                body[graph_key] = {"dateTime": _parse_and_utc_datetime_str(dt_val_str, param_key), "timeZone": "UTC"}
            except ValueError as ve: 
                return {"status": "error", "action": action_name, "message": f"Formato inválido para '{param_key}': {ve}", "http_status": 400}

    logger.info(f"Creando tarea ToDo '{title}' para usuario '{user_identifier}' en lista '{list_id}'")
    todo_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.post(url, scope=todo_rw_scope, json_data=body)
        return {"status": "success", "data": response.json(), "message": "Tarea ToDo creada."}
    except Exception as e:
        return _handle_todo_api_error(e, action_name)

def get_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_task con params: %s", params)
    action_name = "todo_get_task"

    user_identifier: Optional[str] = params.get("user_identifier_for_todo")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_identifier_for_todo' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_identifier_for_todo' (UPN o ID de objeto del usuario) es requerido.", "http_status": 400}

    list_id: Optional[str] = params.get("list_id")
    task_id: Optional[str] = params.get("task_id")
    if not list_id or not task_id:
        return {"status": "error", "action": action_name, "message": "Parámetros 'list_id' y 'task_id' requeridos.", "http_status": 400}
    
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks/{task_id}"
    query_api_params: Dict[str, Any] = {}
    if params.get('select'): query_api_params['$select'] = params.get('select')
    
    logger.info(f"Obteniendo tarea ToDo '{task_id}' para usuario '{user_identifier}' de lista '{list_id}'")
    todo_read_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READ', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.get(url, scope=todo_read_scope, params=query_api_params if query_api_params else None)
        
        # --- CORRECCIÓN ---
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_todo_api_error(e, action_name)

def update_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando update_task con params: %s", params)
    action_name = "todo_update_task"

    user_identifier: Optional[str] = params.get("user_identifier_for_todo")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_identifier_for_todo' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_identifier_for_todo' (UPN o ID de objeto del usuario) es requerido.", "http_status": 400}

    list_id: Optional[str] = params.get("list_id")
    task_id: Optional[str] = params.get("task_id")
    update_payload: Optional[Dict[str, Any]] = params.get("update_payload")
    if not list_id or not task_id or not update_payload or not isinstance(update_payload, dict) or not update_payload:
        return {"status": "error", "action": action_name, "message": "'list_id', 'task_id', y 'update_payload' (dict no vacío) requeridos.", "http_status": 400}
    
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks/{task_id}"
    body_update = update_payload.copy() # Evitar modificar el dict original de params
    try:
        datetime_fields_map = {
            "dueDateTime": "dueDateTime", 
            "reminderDateTime": "reminderDateTime",
            "startDateTime": "startDateTime",
            "completedDateTime": "completedDateTime"
        }
        for param_key, graph_key in datetime_fields_map.items():
            if graph_key in body_update and body_update[graph_key] is not None:
                dt_input = body_update[graph_key]
                dt_val_str = dt_input.get("dateTime") if isinstance(dt_input, dict) else dt_input
                body_update[graph_key] = {"dateTime": _parse_and_utc_datetime_str(dt_val_str, f"update_payload.{graph_key}"), "timeZone": "UTC"}
            elif graph_key in body_update and body_update[graph_key] is None: # Permitir pasar null para borrar fecha
                body_update[graph_key] = None 
    except ValueError as ve: 
        return {"status": "error", "action": action_name, "message": f"Error en formato de fecha en 'update_payload': {ve}", "http_status": 400}

    logger.info(f"Actualizando tarea ToDo '{task_id}' para usuario '{user_identifier}' en lista '{list_id}'")
    todo_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.patch(url, scope=todo_rw_scope, json_data=body_update)
        return {"status": "success", "data": response.json(), "message": f"Tarea ToDo '{task_id}' actualizada."}
    except Exception as e:
        return _handle_todo_api_error(e, action_name)

def delete_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando delete_task con params: %s", params)
    action_name = "todo_delete_task"

    user_identifier: Optional[str] = params.get("user_identifier_for_todo")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_identifier_for_todo' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_identifier_for_todo' (UPN o ID de objeto del usuario) es requerido.", "http_status": 400}

    list_id: Optional[str] = params.get("list_id")
    task_id: Optional[str] = params.get("task_id")
    if not list_id or not task_id:
        return {"status": "error", "action": action_name, "message": "'list_id' y 'task_id' requeridos.", "http_status": 400}
    
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks/{task_id}"
    logger.info(f"Eliminando tarea ToDo '{task_id}' para usuario '{user_identifier}' de lista '{list_id}'")
    todo_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.delete(url, scope=todo_rw_scope)
        return {"status": "success", "message": f"Tarea ToDo '{task_id}' eliminada.", "http_status": response.status_code}
    except Exception as e:
        return _handle_todo_api_error(e, action_name)

# --- FIN DEL MÓDULO actions/todo_actions.py ---