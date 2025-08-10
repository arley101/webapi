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
            elif '+' in datetime_str[10:] or '-' in datetime_str[10:]: # Ya tiene offset
                 dt_obj = datetime.fromisoformat(datetime_str)
            else: # Asumir que es naive, o un formato que fromisoformat pueda parsear
                dt_obj = datetime.fromisoformat(datetime_str)
        except ValueError as e:
            logger.error(f"Formato de fecha/hora inválido para '{field_name_for_log}': '{datetime_str}'. Error: {e}")
            raise ValueError(f"Formato de fecha/hora inválido para '{field_name_for_log}': '{datetime_str}'. Se esperaba ISO 8601 (ej: YYYY-MM-DDTHH:MM:SSZ).") from e
    else:
        raise ValueError(f"Tipo inválido para '{field_name_for_log}': se esperaba string ISO 8601 o datetime, se recibió {type(datetime_str)}.")

    if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
        # Si es naive, se asume que está en la zona horaria local y se convierte a UTC.
        # O, si se espera que el string ya sea UTC pero sin designador, se localiza a UTC.
        # Para Planner, las fechas se esperan en UTC.
        dt_obj_utc = dt_obj.replace(tzinfo=dt_timezone.utc)
        logger.debug(f"Fecha/hora '{datetime_str}' para '{field_name_for_log}' era naive. Asumiendo y convirtiendo a UTC: {dt_obj_utc.isoformat()}")
    else:
        dt_obj_utc = dt_obj.astimezone(dt_timezone.utc)
    
    # Formato específico que Planner espera (con 'Z')
    return dt_obj_utc.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


# --- Helper para manejo de errores ---
def _handle_planner_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Planner action '{action_name}'"
    safe_params = {} # Inicializar
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

# ---- FUNCIONES DE ACCIÓN PARA PLANNER ----
def list_plans(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "list_plans"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    owner_type: str = params.get("owner_type", "user").lower() # 'user' o 'group'
    owner_id: Optional[str] = params.get("owner_id") # ID del usuario o grupo

    url_base: str
    log_owner_description: str

    if owner_type == "user":
        user_identifier = owner_id or params.get("user_id") # Aceptar owner_id o user_id para el usuario
        if not user_identifier:
            # En un contexto de app-only, /me/planner/plans no tiene sentido.
            # Se requiere un user_id explícito.
            return {"status": "error", "action": action_name, "message": "Para 'owner_type=user' con permisos de aplicación, se requiere 'owner_id' (o 'user_id') del usuario.", "http_status": 400}
        url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/planner/plans"
        log_owner_description = f"usuario '{user_identifier}'"
    elif owner_type == "group":
        if not owner_id:
            return {"status": "error", "action": action_name, "message": "Si 'owner_type' es 'group', se requiere 'owner_id' del grupo.", "http_status": 400}
        url_base = f"{settings.GRAPH_API_BASE_URL}/groups/{owner_id}/planner/plans"
        log_owner_description = f"grupo '{owner_id}'"
    else:
        return {"status": "error", "action": action_name, "message": "Parámetro 'owner_type' debe ser 'user' o 'group'.", "http_status": 400}

    # Parámetros OData (no todos son soportados por /plans)
    odata_params: Dict[str, Any] = {}
    default_select = "id,title,owner,createdDateTime,container" # Campos comunes
    odata_params['$select'] = params.get('select', default_select)
    if params.get('$top'): odata_params['$top'] = params['$top']
    # $filter, $orderby no son explícitamente documentados para /planner/plans, pero se pueden probar.
    if params.get('$filter'): odata_params['$filter'] = params['$filter']
    if params.get('$orderby'): odata_params['$orderby'] = params['$orderby']


    logger.info(f"Listando planes de Planner para {log_owner_description}. Select: {odata_params['$select']}, Top: {odata_params.get('$top')}")
    # Scope: Group.Read.All o Group.ReadWrite.All para planes de grupo. Tasks.Read o Tasks.ReadWrite para planes de usuario.
    # .default debería cubrirlo si los permisos de app están bien.
    planner_scope = getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # Asumiendo que group scope es más común
    try:
        response = client.get(url_base, scope=planner_scope, params=odata_params)
        # CORRECCIÓN: 'response' ya es un dict, no llamar a .json()
        return {"status": "success", "data": response.get("value", [])}
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

def get_plan(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "get_plan"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    plan_id: Optional[str] = params.get("plan_id")
    if not plan_id:
        return {"status": "error", "action": action_name, "message": "Parámetro 'plan_id' es requerido.", "http_status": 400}

    url = f"{settings.GRAPH_API_BASE_URL}/planner/plans/{plan_id}"
    
    odata_params: Dict[str, Any] = {}
    # Por defecto, obtener también detalles y buckets para tener info completa del plan.
    default_select = "id,title,owner,createdDateTime,container"
    default_expand = "details,buckets,tasks" 
    odata_params['$select'] = params.get('select', default_select)
    odata_params['$expand'] = params.get('expand', default_expand)


    logger.info(f"Obteniendo detalles del plan de Planner '{plan_id}'. Select: {odata_params['$select']}, Expand: {odata_params['$expand']}")
    planner_scope = getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.get(url, scope=planner_scope, params=odata_params)
        # CORRECCIÓN: 'response' ya es un dict, no llamar a .json()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

def list_tasks(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "list_tasks"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    plan_id: Optional[str] = params.get("plan_id")
    bucket_id: Optional[str] = params.get("bucket_id") # Opcional, para listar tareas de un bucket específico

    if not plan_id and not bucket_id: # Se necesita al menos uno para definir el scope de las tareas
        return {"status": "error", "action": action_name, "message": "Se requiere 'plan_id' o 'bucket_id' para listar tareas.", "http_status": 400}

    url_base: str
    if bucket_id:
        # El endpoint /planner/buckets/{id}/tasks es más directo si se tiene el bucket ID.
        url_base = f"{settings.GRAPH_API_BASE_URL}/planner/buckets/{bucket_id}/tasks"
        logger.info(f"Listando tareas del bucket de Planner '{bucket_id}'.")
    elif plan_id: # Si no hay bucket_id pero sí plan_id
        url_base = f"{settings.GRAPH_API_BASE_URL}/planner/plans/{plan_id}/tasks"
        logger.info(f"Listando tareas del plan de Planner '{plan_id}'.")
    else: # No debería llegar aquí por la validación anterior.
        return {"status": "error", "action": action_name, "message": "Error interno de lógica para determinar URL de tareas.", "http_status": 500}


    top_per_page: int = min(int(params.get('top_per_page', 25)), getattr(settings, 'MAX_GRAPH_TOP_VALUE_PAGING', 100))
    max_items_total: Optional[int] = params.get('max_items_total') # Puede ser None para "todos"
    
    query_api_params_initial: Dict[str, Any] = {'$top': top_per_page}
    query_api_params_initial['$select'] = params.get('select', "id,title,percentComplete,priority,dueDateTime,assigneePriority,assignments,bucketId,planId,orderHint,createdDateTime,completedDateTime,referenceCount,checklistItemCount")
    if params.get('filter_query'): query_api_params_initial['$filter'] = params['filter_query']
    if params.get('order_by'): query_api_params_initial['$orderby'] = params['order_by']
    if params.get('expand_details', str(params.get('expand',"")).lower() == 'details'): # Si se pide expandir detalles
        query_api_params_initial['$expand'] = 'details'


    # Paginación manual para /tasks
    all_tasks: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages = getattr(settings, 'MAX_PAGING_PAGES_PLANNER_TASKS', 20) # Límite de páginas específico
    effective_max_items = max_items_total if max_items_total is not None else float('inf')

    log_context_for_paged = f"{action_name} (Plan: {plan_id}, Bucket: {bucket_id})"
    logger.debug(f"Iniciando paginación para {log_context_for_paged}. Max total: {max_items_total or 'todos'}, Por pág: {top_per_page}")
    
    planner_scope = getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', # Tasks.ReadWrite sería más granular
                            getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', settings.GRAPH_API_DEFAULT_SCOPE))
    try:
        while current_url and len(all_tasks) < effective_max_items and page_count < max_pages:
            page_count += 1
            current_call_params = query_api_params_initial if page_count == 1 and current_url == url_base else None
            logger.debug(f"Página {page_count} para '{log_context_for_paged}': GET {current_url.split('?')[0]} con params: {current_call_params}")
            
            response_data = client.get(current_url, scope=planner_scope, params=current_call_params)
            # CORRECCIÓN: 'response_data' ya es un dict
            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            
            for item in page_items:
                if len(all_tasks) < effective_max_items: 
                    all_tasks.append(item)
                else: break
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_tasks) >= effective_max_items: break
        
        logger.info(f"Total tareas Planner recuperadas para {log_context_for_paged}: {len(all_tasks)} ({page_count} pág procesadas).")
        return {"status": "success", "data": {"value": all_tasks, "@odata.count": len(all_tasks)}, "total_retrieved": len(all_tasks), "pages_processed": page_count}
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)


def create_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "create_task"
    log_params = {k:v for k,v in params.items() if k not in ['details_payload']} # Omitir details del log principal
    if 'details_payload' in params : log_params['details_payload_provided'] = True
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    plan_id: Optional[str] = params.get("plan_id")
    title: Optional[str] = params.get("title")
    if not plan_id or not title:
        return {"status": "error", "action": action_name, "message": "Parámetros 'plan_id' y 'title' son requeridos.", "http_status": 400}

    bucket_id: Optional[str] = params.get("bucket_id")
    assignments: Optional[Dict[str, Any]] = params.get("assignments") # Ej: {"user-guid": {"@odata.type": "#microsoft.graph.plannerAssignment", "orderHint": " !"}, ...}
    details_payload: Optional[Dict[str, Any]] = params.get("details_payload") # Para plannerTaskDetails

    url_task = f"{settings.GRAPH_API_BASE_URL}/planner/tasks"
    body: Dict[str, Any] = {"planId": plan_id, "title": title}
    if bucket_id: body["bucketId"] = bucket_id
    if assignments and isinstance(assignments, dict): body["assignments"] = assignments
    
    optional_fields = ["priority", "percentComplete", "assigneePriority", "orderHint", "appliedCategories", "conversationThreadId"]
    for field in optional_fields:
        if params.get(field) is not None:
            body[field] = params[field]
    
    datetime_fields_planner = ["dueDateTime", "startDateTime", "completedDateTime"]
    for field_name in datetime_fields_planner:
        dt_str_input = params.get(field_name)
        if dt_str_input:
            try:
                body[field_name] = _parse_and_utc_datetime_str(dt_str_input, field_name)
            except ValueError as ve: 
                return {"status": "error", "action": action_name, "message": f"Formato inválido para '{field_name}': {ve}", "http_status": 400}

    logger.info(f"Creando tarea Planner '{title}' en plan '{plan_id}'. Bucket: {bucket_id or 'N/A'}. Assignments: {bool(assignments)}")
    planner_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', 
                               getattr(settings, 'GRAPH_SCOPE_GROUP_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
    try:
        response_task = client.post(url_task, scope=planner_rw_scope, json_data=body)
        task_data = response_task.json()
        task_id = task_data.get("id")
        
        if details_payload and isinstance(details_payload, dict) and task_id:
            logger.info(f"Tarea Planner '{task_id}' creada. Procediendo a actualizar/crear sus detalles.")
            details_url = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}/details"
            
            etag_details: Optional[str] = None
            try:
                logger.debug(f"Obteniendo ETag para detalles de la nueva tarea '{task_id}'.")
                etag_details = task_data.get("details@odata.etag")
                if not etag_details and task_data.get("details") and isinstance(task_data["details"], dict):
                    etag_details = task_data["details"].get("@odata.etag")

                if not etag_details:
                    get_details_response_data = client.get(details_url, scope=planner_rw_scope, params={"$select": "@odata.etag"})
                    # CORRECCIÓN: get_details_response_data ya es un dict
                    etag_details = get_details_response_data.get("@odata.etag")
            except requests.exceptions.HTTPError as http_e_details:
                if http_e_details.response is not None and http_e_details.response.status_code == 404:
                    logger.warning(f"Detalles para tarea '{task_id}' no encontrados (404) inmediatamente después de crearla. Se intentará PATCH sin ETag, podría crear los detalles.")
                    etag_details = "*"
                else: raise
            except Exception as get_etag_err:
                logger.warning(f"Error obteniendo ETag para detalles de tarea '{task_id}': {get_etag_err}. Se intentará PATCH sin ETag.")
                etag_details = "*"
            
            details_custom_headers = {'If-Match': etag_details} if etag_details else {}
            if not etag_details: logger.warning(f"Intentando PATCH de detalles para tarea '{task_id}' sin ETag. Podría fallar o sobreescribir.")
            
            response_details = client.patch(details_url, scope=planner_rw_scope, json_data=details_payload, headers=details_custom_headers)
            task_data["details_updated_data"] = response_details.json()
            task_data["details_update_status"] = "success"
            logger.info(f"Detalles de tarea Planner '{task_id}' actualizados/creados exitosamente.")
            
        return {"status": "success", "data": task_data, "message": "Tarea Planner creada (y detalles actualizados si se proveyeron)."}
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

def get_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "get_task"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    task_id: Optional[str] = params.get("task_id")
    if not task_id:
        return {"status": "error", "action": action_name, "message": "Parámetro 'task_id' es requerido.", "http_status": 400}
    
    url = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}"
    
    odata_params: Dict[str, Any] = {}
    default_select = "id,planId,bucketId,title,orderHint,assigneePriority,percentComplete,priority,dueDateTime,assignments,details" # Incluir details por defecto
    odata_params['$select'] = params.get('select', default_select)
    if params.get('expand_details', str(params.get('expand', "")).lower() == 'details'):
        odata_params['$expand'] = 'details'
        if '$select' in odata_params and 'details' not in odata_params['$select'].split(','):
             odata_params['$select'] += ",details"

    logger.info(f"Obteniendo tarea Planner '{task_id}'. Select: {odata_params.get('$select')}, Expand: {odata_params.get('$expand')}")
    planner_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READ', 
                            getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
    try:
        response = client.get(url, scope=planner_scope, params=odata_params)
        # CORRECCIÓN: 'response' ya es un dict
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

def update_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "update_task"
    log_params = {k:v for k,v in params.items() if k not in ['update_payload_task', 'update_payload_details']}
    if 'update_payload_task' in params : log_params['update_payload_task_keys'] = list(params['update_payload_task'].keys())
    if 'update_payload_details' in params : log_params['update_payload_details_keys'] = list(params['update_payload_details'].keys())
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    task_id: Optional[str] = params.get("task_id")
    if not task_id:
        return {"status": "error", "action": action_name, "message": "Parámetro 'task_id' es requerido.", "http_status": 400}
    
    update_payload_task: Optional[Dict[str, Any]] = params.get("update_payload_task")
    update_payload_details: Optional[Dict[str, Any]] = params.get("update_payload_details")
    
    etag_task: Optional[str] = params.get("etag_task")
    etag_details: Optional[str] = params.get("etag_details")

    if not update_payload_task and not update_payload_details:
        get_task_response = get_task(client, {"task_id": task_id})
        return get_task_response if get_task_response.get("status") == "success" else \
               {"status": "success", "message": "No se especificaron cambios para la tarea.", "data": {"id": task_id}}

    final_task_data_response: Dict[str, Any] = {"id": task_id}
    planner_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', 
                               getattr(settings, 'GRAPH_SCOPE_GROUP_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE))

    if update_payload_task and isinstance(update_payload_task, dict):
        url_task = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}"
        current_etag_task = etag_task or update_payload_task.pop('@odata.etag', None)
        if not current_etag_task:
            logger.warning(f"Actualizando tarea Planner '{task_id}' (principal) SIN ETag. Podría fallar si el item ha cambiado.")
        
        custom_headers_task = {'If-Match': current_etag_task} if current_etag_task else {}
        
        for field_name in ["dueDateTime", "startDateTime", "completedDateTime"]:
            if field_name in update_payload_task and update_payload_task[field_name] is not None:
                try: 
                    update_payload_task[field_name] = _parse_and_utc_datetime_str(update_payload_task[field_name], field_name)
                except ValueError as ve: 
                    return {"status": "error", "action": action_name, "message": f"Formato inválido para '{field_name}' en 'update_payload_task': {ve}", "http_status": 400}
            elif field_name in update_payload_task and update_payload_task[field_name] is None:
                update_payload_task[field_name] = None 

        logger.info(f"Actualizando tarea Planner '{task_id}' (campos principales). ETag usado: {current_etag_task or 'Ninguno'}. Payload keys: {list(update_payload_task.keys())}")
        try:
            response_task = client.patch(url_task, scope=planner_rw_scope, json_data=update_payload_task, headers=custom_headers_task)
            if response_task.status_code == 204:
                logger.info(f"Tarea Planner '{task_id}' (principal) actualizada (204). Es necesario re-obtener para ver cambios y nuevo ETag.")
                final_task_data_response["_task_updated_needs_refresh_for_details_etag"] = True
            elif response_task.status_code == 200:
                final_task_data_response = response_task.json()
                logger.info(f"Tarea Planner '{task_id}' (principal) actualizada (200).")
            else:
                 logger.warning(f"Respuesta inesperada {response_task.status_code} al actualizar tarea Planner '{task_id}'. Respuesta: {response_task.text[:200]}")
                 response_task.raise_for_status()

            final_task_data_response["task_update_status"] = "success"
        except Exception as e_task:
            logger.error(f"Fallo al actualizar la parte principal de la tarea Planner '{task_id}'.")
            return _handle_planner_api_error(e_task, f"{action_name} (task_part)", params)

    if update_payload_details and isinstance(update_payload_details, dict):
        url_details = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}/details"
        current_etag_details = etag_details or update_payload_details.pop('@odata.etag', None)
        
        if not current_etag_details:
            logger.debug(f"ETag para detalles de tarea '{task_id}' no provisto. Intentando obtenerlo...")
            try:
                if final_task_data_response.get("details@odata.etag"):
                    current_etag_details = final_task_data_response["details@odata.etag"]
                elif final_task_data_response.get("details", {}).get("@odata.etag"):
                    current_etag_details = final_task_data_response["details"]["@odata.etag"]
                
                if not current_etag_details:
                    get_details_response_data = client.get(details_url, scope=planner_rw_scope, params={"$select": "@odata.etag"})
                    # CORRECCIÓN: get_details_response_data ya es un dict
                    current_etag_details = get_details_response_data.get("@odata.etag")
                
                if current_etag_details:
                    logger.info(f"ETag obtenido para detalles de tarea '{task_id}': {current_etag_details}")
                else:
                    logger.warning(f"No se pudo obtener ETag para detalles de tarea '{task_id}'.")
            except requests.exceptions.HTTPError as http_e_get_details:
                 if http_e_get_details.response is not None and http_e_get_details.response.status_code == 404:
                     logger.warning(f"No se encontraron detalles existentes para tarea '{task_id}' (404).")
                     return {"status": "error", "action": f"{action_name} (details_part)", "message": f"No se encontraron detalles para la tarea '{task_id}'. No se pueden actualizar.", "http_status": 404}
                 else:
                     logger.error(f"Error HTTP obteniendo ETag para detalles de tarea '{task_id}': {http_e_get_details}")
                     return _handle_planner_api_error(http_e_get_details, f"{action_name} (get_details_etag)", params)
            except Exception as get_etag_err:
                logger.warning(f"Error inesperado obteniendo ETag para detalles de tarea '{task_id}': {get_etag_err}.")
        
        custom_headers_details = {'If-Match': current_etag_details} if current_etag_details else {}
        if not current_etag_details: logger.warning(f"Intentando PATCH de detalles para tarea '{task_id}' sin ETag.")
            
        logger.info(f"Actualizando detalles para tarea Planner '{task_id}'. ETag usado: {current_etag_details or 'Ninguno'}. Payload keys: {list(update_payload_details.keys())}")
        try:
            response_details = client.patch(url_details, scope=planner_rw_scope, json_data=update_payload_details, headers=custom_headers_details)
            updated_details_data = {}
            if response_details.status_code == 204:
                logger.info(f"Detalles de tarea Planner '{task_id}' actualizados (204). Re-obteniendo para confirmar y obtener nuevo ETag.")
                get_task_params_for_details = {"task_id": task_id, "expand_details": True, "select": "id,details"}
                get_task_result_for_details = get_task(client, get_task_params_for_details)
                if get_task_result_for_details.get("status") == "success":
                    updated_details_data = get_task_result_for_details.get("data", {}).get("details", {})
                else:
                    logger.warning(f"Fallo al re-obtener detalles de tarea '{task_id}' post-actualización 204.")
            elif response_details.status_code == 200:
                 updated_details_data = response_details.json()
                 logger.info(f"Detalles de tarea Planner '{task_id}' actualizados (200).")
            else:
                logger.warning(f"Respuesta inesperada {response_details.status_code} al actualizar detalles de tarea '{task_id}'.")
                response_details.raise_for_status()

            if isinstance(final_task_data_response, dict):
                final_task_data_response.setdefault("details", {}).update(updated_details_data)
                final_task_data_response["details_update_status"] = "success"
            else:
                final_task_data_response = {"id": task_id, "details": updated_details_data, "details_update_status": "success"}

        except Exception as e_details:
            logger.error(f"Fallo al actualizar los detalles de la tarea Planner '{task_id}'.")
            if isinstance(final_task_data_response, dict):
                final_task_data_response["details_update_status"] = f"error: {type(e_details).__name__} - {str(e_details)[:100]}"
            if not update_payload_task:
                return _handle_planner_api_error(e_details, f"{action_name} (details_part)", params)
            logger.warning(f"Actualización de tarea '{task_id}' tuvo éxito para la parte principal, pero falló para los detalles.")

    return {"status": "success", "data": final_task_data_response, "message": "Actualización de tarea procesada."}


def delete_task(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "delete_task"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    task_id: Optional[str] = params.get("task_id")
    etag: Optional[str] = params.get("etag") # ETag del objeto plannerTask
    if not task_id:
        return {"status": "error", "action": action_name, "message": "Parámetro 'task_id' es requerido.", "http_status": 400}
    
    url = f"{settings.GRAPH_API_BASE_URL}/planner/tasks/{task_id}"
    custom_headers = {'If-Match': etag} if etag else {}
    if not etag: 
        logger.warning(f"Eliminando tarea Planner '{task_id}' sin ETag. La operación podría fallar si el item ha cambiado.")
        
    logger.info(f"Intentando eliminar tarea Planner '{task_id}'. ETag: {etag or 'Ninguno'}")
    planner_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', 
                               getattr(settings, 'GRAPH_SCOPE_GROUP_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
    try:
        response = client.delete(url, scope=planner_rw_scope, headers=custom_headers)
        return {"status": "success", "message": f"Tarea Planner '{task_id}' eliminada exitosamente.", "http_status": response.status_code}
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

def list_buckets(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "list_buckets"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    plan_id: Optional[str] = params.get("plan_id")
    if not plan_id:
        return {"status": "error", "action": action_name, "message": "Parámetro 'plan_id' es requerido.", "http_status": 400}
    
    url = f"{settings.GRAPH_API_BASE_URL}/planner/plans/{plan_id}/buckets"
    
    odata_params: Dict[str, Any] = {}
    odata_params['$select'] = params.get('select', "id,name,orderHint,planId,orderHint") # orderHint es importante para el orden
    if params.get('$filter'): odata_params['$filter'] = params['$filter']
    if params.get('$top'): odata_params['$top'] = params['$top']

    logger.info(f"Listando buckets para el plan Planner '{plan_id}'. Select: {odata_params['$select']}")
    planner_scope = getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', 
                            getattr(settings, 'GRAPH_SCOPE_TASKS_READ', settings.GRAPH_API_DEFAULT_SCOPE))
    try:
        response = client.get(url, scope=planner_scope, params=odata_params)
        # CORRECCIÓN: 'response' ya es un dict
        return {"status": "success", "data": response.get("value", [])}
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

def create_bucket(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "create_bucket"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    plan_id: Optional[str] = params.get("plan_id")
    name: Optional[str] = params.get("name") # Nombre del nuevo bucket
    if not plan_id or not name:
        return {"status": "error", "action": action_name, "message": "Parámetros 'plan_id' y 'name' (del bucket) son requeridos.", "http_status": 400}
    
    order_hint: Optional[str] = params.get("orderHint") # Para especificar la posición del bucket
    url = f"{settings.GRAPH_API_BASE_URL}/planner/buckets"
    body: Dict[str, Any] = {"name": name, "planId": plan_id}
    if order_hint: 
        body["orderHint"] = order_hint
    
    logger.info(f"Creando bucket '{name}' en plan Planner '{plcolectivan_id}'. OrderHint: {order_hint or 'Default'}")
    planner_rw_scope = getattr(settings, 'GRAPH_SCOPE_TASKS_READWRITE', 
                               getattr(settings, 'GRAPH_SCOPE_GROUP_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
    try:
        response = client.post(url, scope=planner_rw_scope, json_data=body)
        bucket_data = response.json()
        return {"status": "success", "data": bucket_data, "message": "Bucket creado."}
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

def planner_get_plan_by_name(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Busca un plan por nombre para un usuario específico."""
    action_name = "planner_get_plan_by_name"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    plan_name = params.get("name")
    user_id = params.get("user_id")

    if not plan_name or not user_id:
        return {
            "status": "error", 
            "action": action_name, 
            "message": "Se requieren los parámetros 'name' y 'user_id'.", 
            "http_status": 400
        }
    
    try:
        # Reutilizamos la función list_plans existente
        list_params = {
            "owner_type": "user",
            "owner_id": user_id,
            "filter_query": f"title eq '{plan_name}'"
        }
        all_plans_response = list_plans(client, list_params)

        if all_plans_response.get("status") != "success":
            return all_plans_response

        found_plans = all_plans_response.get("data", [])
        if not found_plans:
            return {
                "status": "error", 
                "action": action_name, 
                "message": f"No se encontró ningún plan con el nombre '{plan_name}'.", 
                "http_status": 404
            }
        
        if len(found_plans) > 1:
            logger.warning(f"Se encontraron múltiples planes con el nombre '{plan_name}'. Devolviendo el primero.")

        return {"status": "success", "data": found_plans[0]}
        
    except Exception as e:
        return _handle_planner_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/planner_actions.py ---