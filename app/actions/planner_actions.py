# app/actions/planner_actions.py
import logging
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone as dt_timezone

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

def _parse_and_utc_datetime_str(datetime_str: Any, field_name_for_log: str) -> Optional[str]:
    if datetime_str is None:
        return None
    if isinstance(datetime_str, datetime):
        dt_obj = datetime_str
    elif isinstance(datetime_str, str):
        try:
            if datetime_str.upper().endswith('Z'):
                dt_obj = datetime.fromisoformat(datetime_str[:-1] + '+00:00')
            elif '+' in datetime_str[10:] or '-' in datetime_str[10:]:
                 dt_obj = datetime.fromisoformat(datetime_str)
            else:
                dt_obj = datetime.fromisoformat(datetime_str)
        except ValueError as e:
            raise ValueError(f"Formato de fecha/hora inválido para '{field_name_for_log}': '{datetime_str}'. Error: {e}") from e
    else:
        raise ValueError(f"Tipo inválido para '{field_name_for_log}': se esperaba string ISO 8601 o datetime, se recibió {type(datetime_str)}.")

    if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
        dt_obj_utc = dt_obj.replace(tzinfo=dt_timezone.utc)
    else:
        dt_obj_utc = dt_obj.astimezone(dt_timezone.utc)
    
    return dt_obj_utc.isoformat(timespec='milliseconds').replace('+00:00', 'Z')

def _handle_planner_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Planner action '{action_name}'"
    safe_params = {}
    if params_for_log:
        sensitive_keys = ['details_payload', 'update_payload_task', 'update_payload_details']
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

async def _planner_paged_request(client: AuthenticatedHttpClient, url_base: str, scope: List[str], params_input: Dict[str, Any], query_api_params_initial: Dict[str, Any], max_items_total: Optional[int], action_name_for_log: str) -> Dict[str, Any]:
    all_items = []
    current_url = url_base
    page_count = 0
    max_pages = getattr(settings, 'MAX_PAGING_PAGES_PLANNER_TASKS', 20)
    effective_max_items = float('inf') if max_items_total is None else max_items_total

    try:
        response_data = {}
        while current_url and len(all_items) < effective_max_items and page_count < max_pages:
            page_count += 1
            current_params = query_api_params_initial if page_count == 1 else None
            
            response_data = client.get(url=current_url, scope=scope, params=current_params)
            
            if not isinstance(response_data, dict):
                raise TypeError(f"Respuesta inesperada durante la paginación: se esperaba dict, se recibió {type(response_data)}")
            if response_data.get("status") == "error":
                return response_data

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            
            for item in page_items:
                if len(all_items) < effective_max_items:
                    all_items.append(item)
                else: break
            
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max_items: break
        
        total_count = response_data.get("@odata.count", len(all_items))
        return {"status": "success", "data": {"value": all_items, "@odata.count": total_count}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e:
        return _handle_planner_api_error(e, action_name_for_log, params_input)

async def list_plans(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "planner_list_plans"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        owner_type: str = params.get("owner_type", "user").lower()
        owner_id: Optional[str] = params.get("owner_id")

        if owner_type == "user":
            user_identifier = owner_id or params.get("user_id")
            if not user_identifier:
                raise ValueError("Para 'owner_type=user', se requiere 'owner_id' o 'user_id'.")
            url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/planner/plans"
        elif owner_type == "group":
            if not owner_id:
                raise ValueError("Si 'owner_type' es 'group', se requiere 'owner_id'.")
            url_base = f"{settings.GRAPH_API_BASE_URL}/groups/{owner_id}/planner/plans"
        else:
            raise ValueError("Parámetro 'owner_type' debe ser 'user' o 'group'.")

        odata_params: Dict[str, Any] = {'$select': params.get('select', "id,title,owner,createdDateTime,container")}
        
        planner_scope = getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        
        response_data = client.get(url_base, scope=planner_scope, params=odata_params)
        
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data.get("value", [])}
        else:
            raise TypeError(f"Respuesta inesperada: {type(response_data)}")
            
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

async def get_plan(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "planner_get_plan"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        plan_id: Optional[str] = params.get("plan_id")
        if not plan_id:
            raise ValueError("'plan_id' es requerido.")

        url = f"{settings.GRAPH_API_BASE_URL}/planner/plans/{plan_id}"
        
        odata_params: Dict[str, Any] = {
            '$select': params.get('select', "id,title,owner,createdDateTime,container"),
            '$expand': params.get('expand', "details,buckets,tasks")
        }

        planner_scope = getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_data = client.get(url, scope=planner_scope, params=odata_params)
        
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data}
        else:
            raise TypeError(f"Respuesta inesperada: {type(response_data)}")

    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

async def list_tasks(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "planner_list_tasks"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        plan_id: Optional[str] = params.get("plan_id")
        bucket_id: Optional[str] = params.get("bucket_id")

        if not plan_id and not bucket_id:
            raise ValueError("Se requiere 'plan_id' o 'bucket_id'.")

        url_base = f"{settings.GRAPH_API_BASE_URL}/planner/buckets/{bucket_id}/tasks" if bucket_id else f"{settings.GRAPH_API_BASE_URL}/planner/plans/{plan_id}/tasks"
        
        top_per_page: int = min(int(params.get('top_per_page', 50)), 100)
        max_items_total: Optional[int] = params.get('max_items_total')
        
        query_api_params_initial: Dict[str, Any] = {'$top': top_per_page}
        query_api_params_initial['$select'] = params.get('select', "id,title,percentComplete,dueDateTime,assignments,bucketId,planId")
        if params.get('expand_details', False): query_api_params_initial['$expand'] = 'details'
        
        planner_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE)
        return _planner_paged_request(client, url_base, planner_scope, params, query_api_params_initial, max_items_total, action_name)
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)


async def create_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "planner_create_task"
    logger.info(f"Ejecutando {action_name}")

    try:
        plan_id: Optional[str] = params.get("plan_id")
        title: Optional[str] = params.get("title")
        if not plan_id or not title:
            raise ValueError("'plan_id' y 'title' son requeridos.")

        url_task = f"{settings.GRAPH_API_BASE_URL}/planner/tasks"
        body: Dict[str, Any] = {"planId": plan_id, "title": title}
        if params.get("bucket_id"): body["bucketId"] = params["bucket_id"]
        if params.get("assignments"): body["assignments"] = params["assignments"]
        if params.get("dueDateTime"): body["dueDateTime"] = _parse_and_utc_datetime_str(params["dueDateTime"], "dueDateTime")
        
        planner_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE)
        
        response_task_obj = client.post(url_task, scope=planner_rw_scope, json_data=body)
        task_data = response_task_obj.json()
        task_id = task_data.get("id")

        if params.get("details_payload") and task_id:
            details_payload = params["details_payload"]
            details_url = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}/details"
            etag_details = task_data.get("details@odata.etag")

            if not etag_details:
                try:
                    get_details_resp = client.get(details_url, scope=planner_rw_scope, params={"$select": "@odata.etag"})
                    if isinstance(get_details_resp, dict): etag_details = get_details_resp.get("@odata.etag")
                except Exception as get_etag_err:
                    logger.warning(f"No se pudo obtener ETag para detalles de nueva tarea: {get_etag_err}")

            headers_details = {'If-Match': etag_details} if etag_details else {}
            details_resp_obj = client.patch(details_url, scope=planner_rw_scope, json_data=details_payload, headers=headers_details)
            task_data["details_update_response"] = details_resp_obj.json()

        return {"status": "success", "data": task_data, "http_status": response_task_obj.status_code}
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

async def get_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "planner_get_task"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        task_id: Optional[str] = params.get("task_id")
        if not task_id: raise ValueError("'task_id' es requerido.")
        
        url = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}"
        odata_params: Dict[str, Any] = {}
        if params.get('expand_details', True):
            odata_params['$expand'] = 'details'

        planner_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READ', settings.GRAPH_API_DEFAULT_SCOPE)
        response_data = client.get(url, scope=planner_scope, params=odata_params)
        
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data}
        else:
            raise TypeError(f"Respuesta inesperada: {type(response_data)}")
            
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

async def update_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "planner_update_task"
    logger.info(f"Ejecutando {action_name}")

    try:
        task_id: Optional[str] = params.get("task_id")
        if not task_id: raise ValueError("'task_id' es requerido.")
        
        update_payload_task: Optional[Dict[str, Any]] = params.get("update_payload_task")
        update_payload_details: Optional[Dict[str, Any]] = params.get("update_payload_details")
        etag_task: Optional[str] = params.get("etag_task")
        etag_details: Optional[str] = params.get("etag_details")

        if not update_payload_task and not update_payload_details:
            return {"status": "success", "message": "No se especificaron cambios para la tarea."}

        planner_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE)
        final_response_data: Dict[str, Any] = {"id": task_id}

        if update_payload_task:
            url_task = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}"
            headers_task = {'If-Match': etag_task or update_payload_task.pop('@odata.etag', None)}
            if "dueDateTime" in update_payload_task and update_payload_task["dueDateTime"] is not None:
                update_payload_task["dueDateTime"] = _parse_and_utc_datetime_str(update_payload_task["dueDateTime"], "dueDateTime")
            
            resp_task_obj = client.patch(url_task, scope=planner_rw_scope, json_data=update_payload_task, headers=headers_task)
            final_response_data.update(resp_task_obj.json())
            final_response_data["task_update_status"] = "success"

        if update_payload_details:
            url_details = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}/details"
            headers_details = {'If-Match': etag_details or update_payload_details.pop('@odata.etag', None)}
            resp_details_obj = client.patch(url_details, scope=planner_rw_scope, json_data=update_payload_details, headers=headers_details)
            final_response_data.setdefault("details", {}).update(resp_details_obj.json())
            final_response_data["details_update_status"] = "success"

        return {"status": "success", "data": final_response_data}
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

async def delete_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "planner_delete_task"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        task_id: Optional[str] = params.get("task_id")
        etag: Optional[str] = params.get("etag")
        if not task_id: raise ValueError("'task_id' es requerido.")
        
        url = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}"
        headers = {'If-Match': etag} if etag else {}
        if not etag: logger.warning(f"Eliminando tarea Planner '{task_id}' sin ETag.")
            
        planner_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.delete(url, scope=planner_rw_scope, headers=headers)
        
        if response_obj.status_code == 204:
            return {"status": "success", "message": f"Tarea '{task_id}' eliminada.", "http_status": 204}
        else:
            response_obj.raise_for_status()
            return {}
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

async def list_buckets(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "planner_list_buckets"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        plan_id: Optional[str] = params.get("plan_id")
        if not plan_id: raise ValueError("'plan_id' es requerido.")
        
        url = f"{settings.GRAPH_API_BASE_URL}/planner/plans/{plan_id}/buckets"
        odata_params: Dict[str, Any] = {'$select': params.get('select', "id,name,orderHint,planId")}

        planner_scope = getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_data = client.get(url, scope=planner_scope, params=odata_params)
        
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data.get("value", [])}
        else:
            raise TypeError(f"Respuesta inesperada: {type(response_data)}")
            
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

async def create_bucket(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "planner_create_bucket"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        plan_id: Optional[str] = params.get("plan_id")
        name: Optional[str] = params.get("name")
        if not plan_id or not name:
            raise ValueError("'plan_id' y 'name' son requeridos.")
        
        url = f"{settings.GRAPH_API_BASE_URL}/planner/buckets"
        body: Dict[str, Any] = {"name": name, "planId": plan_id}
        if params.get("orderHint"): body["orderHint"] = params["orderHint"]
        
        planner_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.post(url, scope=planner_rw_scope, json_data=body)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)