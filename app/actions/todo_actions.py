# app/actions/todo_actions.py
import logging
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone as dt_timezone

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

def _parse_and_utc_datetime_str(datetime_str: Any, field_name_for_log: str) -> str:
    if isinstance(datetime_str, datetime):
        dt_obj = datetime_str
    elif isinstance(datetime_str, str):
        try:
            if datetime_str.endswith('Z'):
                dt_obj = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            else:
                dt_obj = datetime.fromisoformat(datetime_str)
        except ValueError as e:
            raise ValueError(f"Formato de fecha/hora inválido para '{field_name_for_log}': '{datetime_str}'.") from e
    else:
        raise ValueError(f"Tipo inválido para '{field_name_for_log}'.")

    if dt_obj.tzinfo is None:
        dt_obj_utc = dt_obj.replace(tzinfo=dt_timezone.utc)
    else:
        dt_obj_utc = dt_obj.astimezone(dt_timezone.utc)
    return dt_obj_utc.isoformat(timespec='seconds').replace('+00:00', 'Z')

def _handle_todo_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en ToDo action '{action_name}'"
    if params_for_log:
        log_message += f" con params: {params_for_log}"
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
        "http_status": status_code,
        "graph_error_code": graph_error_code,
        "details": str(e)
    }

async def _todo_paged_request(client: AuthenticatedHttpClient, url_base: str, scope: List[str], params_input: Dict[str, Any], query_api_params_initial: Dict[str, Any], max_items_total: Optional[int], action_name_for_log: str) -> Dict[str, Any]:
    all_items = []
    current_url = url_base
    page_count = 0
    max_pages = getattr(settings, 'MAX_PAGING_PAGES', 20)
    effective_max = float('inf') if max_items_total is None else max_items_total

    try:
        response_data = {}
        while current_url and len(all_items) < effective_max and page_count < max_pages:
            page_count += 1
            current_params = query_api_params_initial if page_count == 1 else None
            
            response_data = client.get(url=current_url, scope=scope, params=current_params)
            
            if not isinstance(response_data, dict): raise TypeError(f"Respuesta inesperada: {type(response_data)}")
            if response_data.get("status") == "error": return response_data

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            
            for item in page_items:
                if len(all_items) < effective_max: all_items.append(item)
                else: break
            
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max: break
        
        total_count = response_data.get("@odata.count", len(all_items))
        return {"status": "success", "data": {"value": all_items, "@odata.count": total_count}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e:
        return _handle_todo_api_error(e, action_name_for_log, params_input)

async def list_task_lists(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "todo_list_task_lists"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        user_identifier: Optional[str] = params.get("user_identifier_for_todo")
        if not user_identifier: raise ValueError("'user_identifier_for_todo' es requerido.")

        url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists"
        
        top_per_page: int = min(int(params.get('top_per_page', 25)), 100)
        max_items_total: Optional[int] = params.get('max_items_total')
        
        query_api_params_initial: Dict[str, Any] = {'$top': top_per_page}
        query_api_params_initial['$select'] = params.get('select', "id,displayName,isOwner,isShared,wellknownListName")
        if params.get('filter_query'): query_api_params_initial['$filter'] = params.get('filter_query')
        if params.get('orderby'): query_api_params_initial['$orderby'] = params.get('orderby')

        todo_read_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READ', settings.GRAPH_API_DEFAULT_SCOPE)
        return _todo_paged_request(client, url_base, todo_read_scope, params, query_api_params_initial, max_items_total, action_name)
    except Exception as e:
        return _handle_todo_api_error(e, action_name, params)

async def create_task_list(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "todo_create_task_list"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        user_identifier: Optional[str] = params.get("user_identifier_for_todo")
        if not user_identifier: raise ValueError("'user_identifier_for_todo' es requerido.")
        
        displayName: Optional[str] = params.get("displayName")
        if not displayName: raise ValueError("'displayName' es requerido.")
        
        url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists"
        body = {"displayName": displayName}
        
        todo_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.post(url, scope=todo_rw_scope, json_data=body)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_todo_api_error(e, action_name, params)

async def list_tasks(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "todo_list_tasks"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        user_identifier: Optional[str] = params.get("user_identifier_for_todo")
        if not user_identifier: raise ValueError("'user_identifier_for_todo' es requerido.")

        list_id: Optional[str] = params.get("list_id")
        if not list_id: raise ValueError("'list_id' es requerido.")
        
        top_per_page: int = min(int(params.get('top_per_page', 25)), 100)
        max_items_total: Optional[int] = params.get('max_items_total')
        
        query_api_params_initial: Dict[str, Any] = {'$top': top_per_page}
        query_api_params_initial['$select'] = params.get('select', "id,title,status,importance,isReminderOn,createdDateTime,lastModifiedDateTime,dueDateTime")
        if params.get('filter_query'): query_api_params_initial['$filter'] = params.get('filter_query')
        if params.get('orderby'): query_api_params_initial['$orderby'] = params.get('orderby')
        
        url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks"
        
        todo_read_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READ', settings.GRAPH_API_DEFAULT_SCOPE)
        return _todo_paged_request(client, url_base, todo_read_scope, params, query_api_params_initial, max_items_total, action_name)
    except Exception as e:
        return _handle_todo_api_error(e, action_name, params)

async def create_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "todo_create_task"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        user_identifier: Optional[str] = params.get("user_identifier_for_todo")
        if not user_identifier: raise ValueError("'user_identifier_for_todo' es requerido.")

        list_id: Optional[str] = params.get("list_id")
        title: Optional[str] = params.get("title")
        if not list_id or not title: raise ValueError("'list_id' y 'title' son requeridos.")
        
        url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks"
        body: Dict[str, Any] = {"title": title}
        
        if params.get("dueDateTime"):
            body["dueDateTime"] = {"dateTime": _parse_and_utc_datetime_str(params["dueDateTime"], "dueDateTime"), "timeZone": "UTC"}

        todo_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.post(url, scope=todo_rw_scope, json_data=body)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_todo_api_error(e, action_name, params)

async def get_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "todo_get_task"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        user_identifier: Optional[str] = params.get("user_identifier_for_todo")
        if not user_identifier: raise ValueError("'user_identifier_for_todo' es requerido.")

        list_id: Optional[str] = params.get("list_id")
        task_id: Optional[str] = params.get("task_id")
        if not list_id or not task_id: raise ValueError("'list_id' y 'task_id' requeridos.")
        
        url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks/{task_id}"
        query_api_params: Dict[str, Any] = {}
        if params.get('select'): query_api_params['$select'] = params.get('select')
        
        todo_read_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READ', settings.GRAPH_API_DEFAULT_SCOPE)
        response_data = client.get(url, scope=todo_read_scope, params=query_api_params if query_api_params else None)

        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data}
        else:
            raise TypeError(f"Respuesta inesperada: {type(response_data)}")
            
    except Exception as e:
        return _handle_todo_api_error(e, action_name, params)

async def update_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "todo_update_task"
    logger.info(f"Ejecutando {action_name}")

    try:
        user_identifier: Optional[str] = params.get("user_identifier_for_todo")
        if not user_identifier: raise ValueError("'user_identifier_for_todo' es requerido.")

        list_id: Optional[str] = params.get("list_id")
        task_id: Optional[str] = params.get("task_id")
        update_payload: Optional[Dict[str, Any]] = params.get("update_payload")
        if not all([list_id, task_id, update_payload]):
            raise ValueError("Parámetros requeridos faltan.")
        
        url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks/{task_id}"
        
        body_update = update_payload.copy()
        if "dueDateTime" in body_update and body_update["dueDateTime"] is not None:
            body_update["dueDateTime"] = {"dateTime": _parse_and_utc_datetime_str(body_update["dueDateTime"], "dueDateTime"), "timeZone": "UTC"}
        
        todo_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.patch(url, scope=todo_rw_scope, json_data=body_update)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_todo_api_error(e, action_name, params)

async def delete_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "todo_delete_task"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        user_identifier: Optional[str] = params.get("user_identifier_for_todo")
        if not user_identifier: raise ValueError("'user_identifier_for_todo' es requerido.")

        list_id: Optional[str] = params.get("list_id")
        task_id: Optional[str] = params.get("task_id")
        if not list_id or not task_id: raise ValueError("'list_id' y 'task_id' requeridos.")
        
        url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/todo/lists/{list_id}/tasks/{task_id}"
        
        todo_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.delete(url, scope=todo_rw_scope)
        
        if response_obj.status_code == 204:
            return {"status": "success", "message": f"Tarea '{task_id}' eliminada.", "http_status": 204}
        else:
            response_obj.raise_for_status()
            return {}
    except Exception as e:
        return _handle_todo_api_error(e, action_name, params)