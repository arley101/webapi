# app/actions/planner_actions.py
import logging
import requests # Solo para tipos de excepción
import json # Para el helper de error
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone as dt_timezone

# Importar la configuración y el cliente HTTP autenticado
from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# --- Helper para parsear y formatear datetimes (ISO 8601 UTC con Z) ---
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
            else: # Asumir que es naive, o un formato que fromisoformat pueda parsear
                dt_obj = datetime.fromisoformat(datetime_str)
        except ValueError as e:
            logger.error(f"Formato de fecha/hora inválido para '{field_name_for_log}': '{datetime_str}'. Error: {e}")
            raise ValueError(f"Formato de fecha/hora inválido para '{field_name_for_log}': '{datetime_str}'. Se esperaba ISO 8601 (ej: YYYY-MM-DDTHH:MM:SSZ).") from e
    else:
        raise ValueError(f"Tipo inválido para '{field_name_for_log}': se esperaba string ISO 8601 o datetime, se recibió {type(datetime_str)}.")

    if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
        dt_obj_utc = dt_obj.replace(tzinfo=dt_timezone.utc)
    else:
        dt_obj_utc = dt_obj.astimezone(dt_timezone.utc)
    return dt_obj_utc.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


# --- Helper para manejo de errores ---
def _handle_planner_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Planner action '{action_name}'"
    safe_params = {} 
    if params_for_log:
        sensitive_keys = ['details_payload', 'update_payload_task', 'update_payload_details']
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
        
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    details_str = str(e); status_code_int = 500; graph_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json(); error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text); graph_error_code = error_info.get("code")
        except json.JSONDecodeError: details_str = e.response.text[:500] if e.response.text else "No response body"
    return {"status": "error", "action": action_name, "message": f"Error en {action_name}: {details_str}", 
            "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
            "http_status": status_code_int, "graph_error_code": graph_error_code}

def _planner_paged_request(
    client: AuthenticatedHttpClient, url_base: str, scope: List[str],
    params_input: Dict[str, Any], query_api_params_initial: Dict[str, Any],
    max_items_total: Optional[int], action_name_for_log: str
) -> Dict[str, Any]:
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages = getattr(settings, 'MAX_PAGING_PAGES_PLANNER_TASKS', 20)
    effective_max_items = float('inf') if max_items_total is None else max_items_total
    try:
        while current_url and len(all_items) < effective_max_items and page_count < max_pages:
            page_count += 1
            current_call_params = query_api_params_initial if page_count == 1 and current_url == url_base else None
            
            response_data = client.get(url=current_url, scope=scope, params=current_call_params)
            if not isinstance(response_data, dict):
                raise Exception(f"Respuesta paginada inesperada, se esperaba dict. Tipo: {type(response_data)}")
            if response_data.get("status") == "error" and "http_status" in response_data: # Error formateado por http_client
                return response_data 

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            for item in page_items:
                if len(all_items) < effective_max_items: all_items.append(item)
                else: break
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max_items: break
        return {"status": "success", "data": {"value": all_items, "@odata.count": len(all_items)}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e: return _handle_planner_api_error(e, action_name_for_log, params_input)


def list_plans(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "list_plans"; logger.info(f"Ejecutando {action_name}: {params}")
    owner_type: str = params.get("owner_type", "user").lower(); owner_id: Optional[str] = params.get("owner_id")
    url_base: str
    if owner_type == "user":
        user_identifier = owner_id or params.get("user_id")
        if not user_identifier: return {"status": "error", "action": action_name, "message": "Para 'owner_type=user', 'owner_id' o 'user_id' es requerido.", "http_status": 400}
        url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/planner/plans"
    elif owner_type == "group":
        if not owner_id: return {"status": "error", "action": action_name, "message": "Si 'owner_type' es 'group', 'owner_id' es requerido.", "http_status": 400}
        url_base = f"{settings.GRAPH_API_BASE_URL}/groups/{owner_id}/planner/plans"
    else: return {"status": "error", "action": action_name, "message": "'owner_type' debe ser 'user' o 'group'.", "http_status": 400}
    
    odata_params: Dict[str, Any] = {'$select': params.get('select', "id,title,owner,createdDateTime,container")}
    if params.get('$top'): odata_params['$top'] = params['$top']
    if params.get('$filter'): odata_params['$filter'] = params['$filter']
    if params.get('$orderby'): odata_params['$orderby'] = params['$orderby']
    planner_scope = getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_data = client.get(url_base, scope=planner_scope, params=odata_params)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada de client.get: {type(response_data)}")
        if response_data.get("status") == "error" and "http_status" in response_data: return response_data
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_planner_api_error(e, action_name, params)

def get_plan(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "get_plan"; logger.info(f"Ejecutando {action_name}: {params}")
    plan_id: Optional[str] = params.get("plan_id")
    if not plan_id: return {"status": "error", "action": action_name, "message": "'plan_id' es requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/planner/plans/{plan_id}"
    odata_params: Dict[str, Any] = {
        '$select': params.get('select', "id,title,owner,createdDateTime,container"),
        '$expand': params.get('expand', "details,buckets,tasks")
    }
    planner_scope = getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_data = client.get(url, scope=planner_scope, params=odata_params)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada de client.get: {type(response_data)}")
        if response_data.get("status") == "error" and "http_status" in response_data: return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_planner_api_error(e, action_name, params)

def list_tasks(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "list_tasks"; logger.info(f"Ejecutando {action_name}: {params}")
    plan_id = params.get("plan_id"); bucket_id = params.get("bucket_id")
    if not plan_id and not bucket_id: return {"status": "error", "action": action_name, "message": "Se requiere 'plan_id' o 'bucket_id'.", "http_status": 400}
    url_base = f"{settings.GRAPH_API_BASE_URL}/planner/buckets/{bucket_id}/tasks" if bucket_id else f"{settings.GRAPH_API_BASE_URL}/planner/plans/{plan_id}/tasks" # type: ignore
    query_api_params: Dict[str, Any] = {'$top': min(int(params.get('top_per_page', 25)), getattr(settings, 'MAX_GRAPH_TOP_VALUE_PAGING', 100))}
    query_api_params['$select'] = params.get('select', "id,title,percentComplete,priority,dueDateTime,assigneePriority,assignments,bucketId,planId,orderHint,createdDateTime,completedDateTime,referenceCount,checklistItemCount")
    if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    if params.get('order_by'): query_api_params['$orderby'] = params['order_by']
    if params.get('expand_details', str(params.get('expand',"")).lower() == 'details'): query_api_params['$expand'] = 'details'
    scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    return _planner_paged_request(client, url_base, scope, params, query_api_params, params.get('max_items_total'), f"{action_name} (Plan: {plan_id}, Bucket: {bucket_id})")

def create_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "create_task"
    log_params = {k:v for k,v in params.items() if k not in ['details_payload']}; 
    if 'details_payload' in params : log_params['details_payload_provided'] = True
    logger.info(f"Ejecutando {action_name} con params: {log_params}")
    plan_id = params.get("plan_id"); title = params.get("title")
    if not plan_id or not title: return {"status": "error", "action": action_name, "message": "'plan_id' y 'title' requeridos.", "http_status": 400}
    url_task = f"{settings.GRAPH_API_BASE_URL}/planner/tasks"
    body: Dict[str, Any] = {"planId": plan_id, "title": title}
    if params.get("bucket_id"): body["bucketId"] = params["bucket_id"]
    if params.get("assignments") and isinstance(params["assignments"], dict): body["assignments"] = params["assignments"]
    for field in ["priority", "percentComplete", "assigneePriority", "orderHint", "appliedCategories", "conversationThreadId"]:
        if params.get(field) is not None: body[field] = params[field]
    for field_name in ["dueDateTime", "startDateTime", "completedDateTime"]:
        if params.get(field_name):
            try: body[field_name] = _parse_and_utc_datetime_str(params[field_name], field_name)
            except ValueError as ve: return {"status": "error", "action": action_name, "message": f"Formato inválido para '{field_name}': {ve}", "http_status": 400}
    scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', getattr(settings, 'GRAPH_SCOPE_GROUP_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    try:
        response_task_obj = client.post(url_task, scope=scope, json_data=body) # client.post devuelve requests.Response
        task_data = response_task_obj.json()
        task_id = task_data.get("id")
        if params.get("details_payload") and isinstance(params["details_payload"], dict) and task_id:
            details_url = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}/details"
            etag_details = task_data.get("details@odata.etag") or (task_data.get("details", {}).get("@odata.etag"))
            if not etag_details:
                try:
                    details_resp_data = client.get(details_url, scope=scope, params={"$select": "@odata.etag"})
                    if isinstance(details_resp_data, dict): etag_details = details_resp_data.get("@odata.etag")
                except Exception as e_etag: logger.warning(f"No se pudo obtener ETag para detalles '{task_id}': {e_etag}")
            headers_details = {'If-Match': etag_details} if etag_details else {}
            if not etag_details: logger.warning(f"Intentando PATCH de detalles para '{task_id}' sin ETag.")
            response_details_obj = client.patch(details_url, scope=scope, json_data=params["details_payload"], headers=headers_details)
            task_data["details_updated_data"] = response_details_obj.json()
        return {"status": "success", "data": task_data, "message": "Tarea Planner creada."}
    except Exception as e: return _handle_planner_api_error(e, action_name, params)

def get_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "get_task"; logger.info(f"Ejecutando {action_name}: {params}")
    task_id: Optional[str] = params.get("task_id")
    if not task_id: return {"status": "error", "action": action_name, "message": "'task_id' es requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}"
    odata_params: Dict[str, Any] = {'$select': params.get('select', "id,planId,bucketId,title,orderHint,assigneePriority,percentComplete,priority,dueDateTime,assignments,details")}
    if params.get('expand_details', str(params.get('expand', "")).lower() == 'details'):
        odata_params['$expand'] = 'details'
        if 'details' not in odata_params['$select'].split(','): odata_params['$select'] += ",details" # type: ignore
    scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READ', getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    try:
        response_data = client.get(url, scope=scope, params=odata_params)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_planner_api_error(e, action_name, params)

def update_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "update_task";
    log_params = {k:v for k,v in params.items() if k not in ['update_payload_task', 'update_payload_details']}
    logger.info(f"Ejecutando {action_name} con params: {log_params}")
    task_id: Optional[str] = params.get("task_id")
    if not task_id: return {"status": "error", "action": action_name, "message": "'task_id' es requerido.", "http_status": 400}
    update_payload_task: Optional[Dict[str, Any]] = params.get("update_payload_task")
    update_payload_details: Optional[Dict[str, Any]] = params.get("update_payload_details")
    if not update_payload_task and not update_payload_details: return {"status": "success", "message": "No se especificaron cambios.", "data": {"id": task_id}}
    
    final_task_data: Dict[str, Any] = {"id": task_id}
    scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', getattr(settings, 'GRAPH_SCOPE_GROUP_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore

    if update_payload_task and isinstance(update_payload_task, dict):
        url_task = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}"
        etag_task = params.get("etag_task") or update_payload_task.pop('@odata.etag', None)
        headers_task = {'If-Match': etag_task} if etag_task else {}
        if not etag_task: logger.warning(f"Actualizando tarea '{task_id}' SIN ETag.")
        for field_name in ["dueDateTime", "startDateTime", "completedDateTime"]:
            if field_name in update_payload_task and update_payload_task[field_name] is not None:
                try: update_payload_task[field_name] = _parse_and_utc_datetime_str(update_payload_task[field_name], field_name)
                except ValueError as ve: return {"status": "error", "action": action_name, "message": f"Formato fecha inválido '{field_name}': {ve}", "http_status": 400}
            elif field_name in update_payload_task and update_payload_task[field_name] is None: update_payload_task[field_name] = None 
        try:
            response_task_obj = client.patch(url_task, scope=scope, json_data=update_payload_task, headers=headers_task)
            if response_task_obj.status_code == 204: final_task_data["_task_updated_needs_refresh"] = True
            elif response_task_obj.status_code == 200: final_task_data = response_task_obj.json()
            else: response_task_obj.raise_for_status()
            final_task_data["task_update_status"] = "success"
        except Exception as e_task: return _handle_planner_api_error(e_task, f"{action_name} (task_part)", params)

    if update_payload_details and isinstance(update_payload_details, dict):
        url_details = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}/details"
        etag_details = params.get("etag_details") or update_payload_details.pop('@odata.etag', None)
        if not etag_details:
            try:
                if final_task_data.get("details@odata.etag"): etag_details = final_task_data["details@odata.etag"]
                elif final_task_data.get("details", {}).get("@odata.etag"): etag_details = final_task_data["details"]["@odata.etag"]
                if not etag_details: # Fetch ETag
                    details_resp_data = client.get(details_url, scope=scope, params={"$select": "@odata.etag"})
                    if isinstance(details_resp_data, dict): etag_details = details_resp_data.get("@odata.etag")
            except Exception as e_get_etag: logger.warning(f"No se pudo obtener ETag para detalles de '{task_id}': {e_get_etag}")
        headers_details = {'If-Match': etag_details} if etag_details else {}
        if not etag_details: logger.warning(f"Actualizando detalles de tarea '{task_id}' SIN ETag.")
        try:
            response_details_obj = client.patch(url_details, scope=scope, json_data=update_payload_details, headers=headers_details)
            updated_details_data = {}
            if response_details_obj.status_code == 204: # Re-obtener
                get_details_resp = client.get(details_url, scope=scope) # type: ignore
                if isinstance(get_details_resp, dict): updated_details_data = get_details_resp
            elif response_details_obj.status_code == 200: updated_details_data = response_details_obj.json()
            else: response_details_obj.raise_for_status()
            final_task_data.setdefault("details", {}).update(updated_details_data)
            final_task_data["details_update_status"] = "success"
        except Exception as e_details:
            final_task_data["details_update_status"] = f"error: {type(e_details).__name__}"
            if not update_payload_task: return _handle_planner_api_error(e_details, f"{action_name} (details_part)", params)
    
    if final_task_data.pop("_task_updated_needs_refresh", False) and not update_payload_details:
        get_task_resp = get_task(client, {"task_id": task_id, "expand_details": True})
        if get_task_resp.get("status") == "success": final_task_data = get_task_resp.get("data", final_task_data)
        
    return {"status": "success", "data": final_task_data, "message": "Actualización de tarea procesada."}

def delete_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "delete_task"; logger.info(f"Ejecutando {action_name}: {params}")
    task_id: Optional[str] = params.get("task_id"); etag: Optional[str] = params.get("etag")
    if not task_id: return {"status": "error", "action": action_name, "message": "'task_id' es requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}"
    headers = {'If-Match': etag} if etag else {}
    if not etag: logger.warning(f"Eliminando tarea '{task_id}' sin ETag.")
    scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_obj = client.delete(url, scope=scope, headers=headers) # client.delete devuelve requests.Response
        return {"status": "success", "message": f"Tarea Planner '{task_id}' eliminada.", "http_status": response_obj.status_code}
    except Exception as e: return _handle_planner_api_error(e, action_name, params)

def list_buckets(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "list_buckets"; logger.info(f"Ejecutando {action_name}: {params}")
    plan_id: Optional[str] = params.get("plan_id")
    if not plan_id: return {"status": "error", "action": action_name, "message": "'plan_id' es requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/planner/plans/{plan_id}/buckets"
    odata_params: Dict[str, Any] = {'$select': params.get('select', "id,name,orderHint,planId")} # orderHint es String
    if params.get('$filter'): odata_params['$filter'] = params['$filter']
    if params.get('$top'): odata_params['$top'] = params['$top']
    scope = getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', getattr(settings, 'GRAPH_SCOPE_TASKS_READ', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    try:
        response_data = client.get(url, scope=scope, params=odata_params)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_planner_api_error(e, action_name, params)

def create_bucket(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "create_bucket"; logger.info(f"Ejecutando {action_name}: {params}")
    plan_id = params.get("plan_id"); name = params.get("name")
    if not plan_id or not name: return {"status": "error", "action": action_name, "message": "'plan_id' y 'name' requeridos.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/planner/buckets"
    body: Dict[str, Any] = {"name": name, "planId": plan_id}
    if params.get("orderHint"): body["orderHint"] = params["orderHint"]
    scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', getattr(settings, 'GRAPH_SCOPE_GROUP_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    try:
        response_obj = client.post(url, scope=scope, json_data=body) # client.post devuelve requests.Response
        return {"status": "success", "data": response_obj.json(), "message": "Bucket creado."}
    except Exception as e: return _handle_planner_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/planner_actions.py ---