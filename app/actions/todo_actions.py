# app/actions/todo_actions.py
import logging
import requests 
import json 
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone as dt_timezone

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

def _parse_and_utc_datetime_str(datetime_str: Any, field_name_for_log: str) -> Optional[str]: # Copiado de planner_actions
    if datetime_str is None: return None
    if isinstance(datetime_str, datetime): dt_obj = datetime_str
    elif isinstance(datetime_str, str):
        try:
            if datetime_str.upper().endswith('Z'): dt_obj = datetime.fromisoformat(datetime_str[:-1] + '+00:00')
            elif '+' in datetime_str[10:] or '-' in datetime_str[10:]: dt_obj = datetime.fromisoformat(datetime_str)
            else: dt_obj = datetime.fromisoformat(datetime_str)
        except ValueError as e: raise ValueError(f"Formato inválido para '{field_name_for_log}': '{datetime_str}'. Error: {e}") from e
    else: raise ValueError(f"Tipo inválido para '{field_name_for_log}': {type(datetime_str)}.")
    if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
        dt_obj_utc = dt_obj.replace(tzinfo=dt_timezone.utc)
    else: dt_obj_utc = dt_obj.astimezone(dt_timezone.utc)
    return dt_obj_utc.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def _handle_todo_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en ToDo action '{action_name}'"
    if params_for_log: log_message += f" con params: {params_for_log}"
    logger.error(f"{log_message}: {type(e).__name__} - {e}", exc_info=True)
    details = str(e); status_code = 500; graph_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code = e.response.status_code
        try:
            error_data = e.response.json(); error_info = error_data.get("error", {})
            details = error_info.get("message", e.response.text); graph_error_code = error_info.get("code")
        except json.JSONDecodeError: details = e.response.text
    return {"status": "error", "action": action_name, "message": f"Error en {action_name}: {details}", 
            "details": str(e), "http_status": status_code, "graph_error_code": graph_error_code}

def _todo_paged_request( # Helper específico para paginación de ToDo si es necesario, similar a otros
    client: AuthenticatedHttpClient, url_base: str, scope: List[str],
    params_input: Dict[str, Any], query_api_params_initial: Dict[str, Any],
    max_items_total: Optional[int], action_name_for_log: str
) -> Dict[str, Any]:
    all_items: List[Dict[str, Any]] = []; current_url: Optional[str] = url_base; page_count = 0
    max_pages = getattr(settings, 'MAX_PAGING_PAGES', 20)
    effective_max_items = float('inf') if max_items_total is None else max_items_total
    try:
        while current_url and len(all_items) < effective_max_items and page_count < max_pages:
            page_count += 1
            current_call_params = query_api_params_initial if page_count == 1 and current_url == url_base else None
            response_data = client.get(url=current_url, scope=scope, params=current_call_params)
            if not isinstance(response_data, dict): raise Exception(f"Respuesta paginada inesperada: {type(response_data)}")
            if response_data.get("status") == "error": return response_data
            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            for item in page_items:
                if len(all_items) < effective_max_items: all_items.append(item)
                else: break
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max_items: break
        return {"status": "success", "data": {"value": all_items, "@odata.count": len(all_items)}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e: return _handle_todo_api_error(e, action_name_for_log, params_input)


def list_task_lists(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_task_lists: %s", params); action_name = "todo_list_task_lists"
    user_identifier: Optional[str] = params.get("user_identifier_for_todo")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_identifier_for_todo' requerido.", "http_status": 400}
    url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists"
    query_params: Dict[str, Any] = {'$top': min(int(params.get('top_per_page', 25)), getattr(settings, 'MAX_GRAPH_TOP_VALUE_PAGING', 100))}
    query_params['$select'] = params.get('select', "id,displayName,isOwner,isShared,wellknownListName")
    if params.get('filter_query'): query_params['$filter'] = params['filter_query']
    if params.get('order_by'): query_params['$orderby'] = params['order_by']
    scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READ', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    return _todo_paged_request(client, url_base, scope, params, query_params, params.get('max_items_total'), action_name)

def create_task_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando create_task_list: %s", params); action_name = "todo_create_task_list"
    user_identifier: Optional[str] = params.get("user_identifier_for_todo")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_identifier_for_todo' requerido.", "http_status": 400}
    displayName: Optional[str] = params.get("displayName")
    if not displayName: return {"status": "error", "action": action_name, "message": "'displayName' requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists"
    body = {"displayName": displayName}
    scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_obj = client.post(url, scope=scope, json_data=body) # client.post devuelve requests.Response
        return {"status": "success", "data": response_obj.json(), "message": "Lista ToDo creada."}
    except Exception as e: return _handle_todo_api_error(e, action_name, params)

def list_tasks(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_tasks: %s", params); action_name = "todo_list_tasks"
    user_identifier: Optional[str] = params.get("user_identifier_for_todo")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_identifier_for_todo' requerido.", "http_status": 400}
    list_id: Optional[str] = params.get("list_id")
    if not list_id: return {"status": "error", "action": action_name, "message": "'list_id' requerido.", "http_status": 400}
    url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks"
    query_params: Dict[str, Any] = {'$top': min(int(params.get('top_per_page', 25)), getattr(settings, 'MAX_GRAPH_TOP_VALUE_PAGING', 100))}
    query_params['$select'] = params.get('select', "id,title,status,importance,isReminderOn,createdDateTime,lastModifiedDateTime,dueDateTime,completedDateTime")
    if params.get('filter_query'): query_params['$filter'] = params['filter_query']
    if params.get('order_by'): query_params['$orderby'] = params['order_by']
    scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READ', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    return _todo_paged_request(client, url_base, scope, params, query_params, params.get('max_items_total'), action_name)

def create_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando create_task: %s", params); action_name = "todo_create_task"
    user_identifier: Optional[str] = params.get("user_identifier_for_todo")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_identifier_for_todo' requerido.", "http_status": 400}
    list_id = params.get("list_id"); title = params.get("title")
    if not list_id or not title: return {"status": "error", "action": action_name, "message": "'list_id' y 'title' requeridos.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks"
    body: Dict[str, Any] = {"title": title}
    for field in ["importance", "isReminderOn", "status"]:
        if params.get(field) is not None: body[field] = params[field]
    if params.get("body_content"): body["body"] = {"content": params["body_content"], "contentType": params.get("body_contentType", "text")}
    for pk, gk in {"dueDateTime": "dueDateTime", "reminderDateTime": "reminderDateTime", "startDateTime": "startDateTime", "completedDateTime": "completedDateTime"}.items():
        if params.get(pk):
            try: body[gk] = {"dateTime": _parse_and_utc_datetime_str(params[pk], pk), "timeZone": "UTC"}
            except ValueError as ve: return {"status": "error", "action": action_name, "message": f"Formato inválido para '{pk}': {ve}", "http_status": 400}
    scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_obj = client.post(url, scope=scope, json_data=body)
        return {"status": "success", "data": response_obj.json(), "message": "Tarea ToDo creada."}
    except Exception as e: return _handle_todo_api_error(e, action_name, params)

def get_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_task: %s", params); action_name = "todo_get_task"
    user_identifier: Optional[str] = params.get("user_identifier_for_todo")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_identifier_for_todo' requerido.", "http_status": 400}
    list_id = params.get("list_id"); task_id = params.get("task_id")
    if not list_id or not task_id: return {"status": "error", "action": action_name, "message": "'list_id' y 'task_id' requeridos.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks/{task_id}"
    query_api_params: Dict[str, Any] = {'$select': params['select']} if params.get('select') else {}
    scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READ', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_data = client.get(url, scope=scope, params=query_api_params if query_api_params else None)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_todo_api_error(e, action_name, params)

def update_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando update_task: %s", params); action_name = "todo_update_task"
    user_identifier: Optional[str] = params.get("user_identifier_for_todo")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_identifier_for_todo' requerido.", "http_status": 400}
    list_id = params.get("list_id"); task_id = params.get("task_id"); update_payload = params.get("update_payload")
    if not list_id or not task_id or not update_payload or not isinstance(update_payload, dict) or not update_payload:
        return {"status": "error", "action": action_name, "message": "'list_id', 'task_id', y 'update_payload' (dict no vacío) requeridos.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks/{task_id}"
    body_update = update_payload.copy()
    try:
        for pk, gk in {"dueDateTime": "dueDateTime", "reminderDateTime": "reminderDateTime", "startDateTime": "startDateTime", "completedDateTime": "completedDateTime"}.items():
            if gk in body_update and body_update[gk] is not None:
                dt_input = body_update[gk]; dt_val_str = dt_input.get("dateTime") if isinstance(dt_input, dict) else dt_input
                body_update[gk] = {"dateTime": _parse_and_utc_datetime_str(dt_val_str, f"update_payload.{gk}"), "timeZone": "UTC"}
            elif gk in body_update and body_update[gk] is None: body_update[gk] = None 
    except ValueError as ve: return {"status": "error", "action": action_name, "message": f"Error en formato de fecha: {ve}", "http_status": 400}
    scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_obj = client.patch(url, scope=scope, json_data=body_update) # client.patch devuelve requests.Response
        return {"status": "success", "data": response_obj.json(), "message": f"Tarea ToDo '{task_id}' actualizada."}
    except Exception as e: return _handle_todo_api_error(e, action_name, params)

def delete_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando delete_task: %s", params); action_name = "todo_delete_task"
    user_identifier: Optional[str] = params.get("user_identifier_for_todo")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_identifier_for_todo' requerido.", "http_status": 400}
    list_id = params.get("list_id"); task_id = params.get("task_id")
    if not list_id or not task_id: return {"status": "error", "action": action_name, "message": "'list_id' y 'task_id' requeridos.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks/{task_id}"
    scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_obj = client.delete(url, scope=scope) # client.delete devuelve requests.Response
        return {"status": "success", "message": f"Tarea ToDo '{task_id}' eliminada.", "http_status": response_obj.status_code}
    except Exception as e: return _handle_todo_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/todo_actions.py ---