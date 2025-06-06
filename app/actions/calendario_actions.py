# app/actions/calendario_actions.py
import logging
import requests
import json
from typing import Dict, List, Optional, Any

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

CALENDARS_READ_SCOPE = getattr(settings, "GRAPH_SCOPE_CALENDARS_READ", settings.GRAPH_API_DEFAULT_SCOPE)
CALENDARS_READ_WRITE_SCOPE = getattr(settings, "GRAPH_SCOPE_CALENDARS_READ_WRITE", settings.GRAPH_API_DEFAULT_SCOPE)
CALENDARS_READ_SHARED_SCOPE = getattr(settings, "GRAPH_SCOPE_CALENDARS_READ_SHARED", settings.GRAPH_API_DEFAULT_SCOPE)


def _handle_calendar_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Calendar action '{action_name}'"
    if params_for_log:
        sensitive_keys = ['event_payload', 'update_payload', 'meeting_params_body', 'schedule_params_body', 'attendees']
        safe_params = {k: v for k, v in params_for_log.items() if k not in sensitive_keys}
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
        "message": f"Error en {action_name}: {type(e).__name__}",
        "http_status": status_code_int,
        "details": details_str,
        "graph_error_code": graph_error_code
    }

def _calendar_paged_request(
    client: AuthenticatedHttpClient,
    url_base: str,
    scope_list: List[str],
    params: Dict[str, Any],
    query_api_params_initial: Dict[str, Any],
    max_items_total: Optional[int],
    action_name_for_log: str
) -> Dict[str, Any]:
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages_to_fetch = getattr(settings, "MAX_PAGING_PAGES", 20) 
    effective_max_items = float('inf') if max_items_total is None else max_items_total

    logger.debug(f"Iniciando solicitud paginada para '{action_name_for_log}' desde '{url_base.split('?')[0]}...'.")
    try:
        while current_url and len(all_items) < effective_max_items and page_count < max_pages_to_fetch:
            page_count += 1
            is_first_call = (current_url == url_base and page_count == 1)
            
            current_params_for_call = query_api_params_initial if is_first_call else None
            
            response_data = client.get(url=current_url, scope=scope_list, params=current_params_for_call)
            
            if not isinstance(response_data, dict):
                return _handle_calendar_api_error(Exception(f"Respuesta inesperada: {type(response_data)}"), action_name_for_log, params)
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
        
        total_matching = response_data.get('@odata.count', len(all_items)) if 'response_data' in locals() and isinstance(response_data, dict) else len(all_items)

        logger.info(f"'{action_name_for_log}' recuperó {len(all_items)} items en {page_count} páginas.")
        return {"status": "success", "data": {"value": all_items, "@odata.count": total_matching}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e:
        return _handle_calendar_api_error(e, action_name_for_log, params)

def calendar_list_events(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "calendar_list_events"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    user_identifier: Optional[str] = params.get("mailbox")
    if not user_identifier:
        return _handle_calendar_api_error(ValueError("'mailbox' (user_id o UPN) es requerido."), action_name, params)

    calendar_id: Optional[str] = params.get("calendar_id") 
    start_datetime_str: Optional[str] = params.get('start_datetime')
    end_datetime_str: Optional[str] = params.get('end_datetime')
    top_per_page: int = min(int(params.get('top_per_page', 25)), 100)
    max_items_total: Optional[int] = params.get('max_items_total')
    select_fields: Optional[str] = params.get('select')
    filter_query: Optional[str] = params.get('filter_query')
    order_by: Optional[str] = params.get('orderby', 'start/dateTime')

    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = select_fields or "id,subject,bodyPreview,start,end,organizer,attendees,location,isAllDay,webLink,onlineMeeting"
    if order_by: query_api_params['$orderby'] = order_by

    user_path_segment = f"users/{user_identifier}"
    calendar_path_segment = f"calendars/{calendar_id}" if calendar_id else "calendar"

    url_base: str
    log_action_detail: str

    if start_datetime_str and end_datetime_str:
        query_api_params['startDateTime'] = start_datetime_str
        query_api_params['endDateTime'] = end_datetime_str
        if filter_query: logger.warning("$filter provisto con calendarView; podría ser ignorado por la API.")
        
        url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/{calendar_path_segment}/calendarView"
        log_action_detail = f"eventos en calendarView para '{user_identifier}'"
    else:
        if filter_query: query_api_params['$filter'] = filter_query
        url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/{calendar_path_segment}/events"
        log_action_detail = f"eventos para '{user_identifier}'"
    
    logger.info(f"Listando {log_action_detail}. Query: {query_api_params}")
    return _calendar_paged_request(client, url_base, CALENDARS_READ_SCOPE, params, query_api_params, max_items_total, action_name)

def calendar_create_event(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "calendar_create_event"
    log_params = {k:v for k,v in params.items() if k not in ['event_payload']}
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    user_identifier: Optional[str] = params.get("mailbox")
    if not user_identifier:
        return _handle_calendar_api_error(ValueError("'mailbox' es requerido."), action_name, params)

    event_payload: Optional[Dict[str, Any]] = params.get("event_payload")

    if not event_payload or not isinstance(event_payload, dict):
        return _handle_calendar_api_error(ValueError("'event_payload' (dict) es requerido."), action_name, params)

    required_fields = ["subject", "start", "end"]
    if not all(field in event_payload for field in required_fields):
        missing = [field for field in required_fields if field not in event_payload]
        return _handle_calendar_api_error(ValueError(f"Faltan campos requeridos en 'event_payload': {missing}."), action_name, params)
    
    for field_name in ["start", "end"]:
        if not isinstance(event_payload.get(field_name), dict) or \
           not event_payload[field_name].get("dateTime") or \
           not event_payload[field_name].get("timeZone"):
            return _handle_calendar_api_error(ValueError(f"Campo '{field_name}' debe ser un dict con 'dateTime' y 'timeZone'."), action_name, params)

    user_path_segment = f"users/{user_identifier}"
    calendar_path_segment = f"calendars/{params.get('calendar_id')}" if params.get('calendar_id') else "calendar"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/{calendar_path_segment}/events"
    
    logger.info(f"Creando evento para '{user_identifier}'. Asunto: {event_payload.get('subject')}")
    try:
        response_obj = client.post(url, scope=CALENDARS_READ_WRITE_SCOPE, json_data=event_payload)
        created_event = response_obj.json()
        logger.info(f"Evento creado con ID: {created_event.get('id')}")
        return {"status": "success", "data": created_event, "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_calendar_api_error(e, action_name, params)

def get_event(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "get_event"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    user_identifier: Optional[str] = params.get("mailbox")
    if not user_identifier:
        return _handle_calendar_api_error(ValueError("'mailbox' es requerido."), action_name, params)

    event_id: Optional[str] = params.get("event_id")
    if not event_id:
        return _handle_calendar_api_error(ValueError("'event_id' es requerido."), action_name, params)
    
    select_fields: Optional[str] = params.get("select")
    user_path_segment = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/events/{event_id}"
    
    query_api_params = {'$select': select_fields} if select_fields else None
    logger.info(f"Obteniendo evento ID '{event_id}' para '{user_identifier}'")
    try:
        response_data = client.get(url, scope=CALENDARS_READ_SCOPE, params=query_api_params)
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data}
        else:
            return _handle_calendar_api_error(Exception(f"Respuesta inesperada: {type(response_data)}"), action_name, params)
    except Exception as e:
        return _handle_calendar_api_error(e, action_name, params)

def update_event(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "calendar_update_event"
    log_params = {k:v for k,v in params.items() if k not in ['update_payload']}
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    user_identifier: Optional[str] = params.get("mailbox")
    if not user_identifier:
        return _handle_calendar_api_error(ValueError("'mailbox' es requerido."), action_name, params)

    event_id: Optional[str] = params.get("event_id")
    if not event_id:
        return _handle_calendar_api_error(ValueError("'event_id' es requerido."), action_name, params)

    update_payload: Optional[Dict[str, Any]] = params.get("update_payload")
    if not update_payload or not isinstance(update_payload, dict) or not update_payload:
        return _handle_calendar_api_error(ValueError("'update_payload' (dict no vacío) es requerido."), action_name, params)

    for field_name in ["start", "end"]:
        if field_name in update_payload:
            field_value = update_payload[field_name]
            if not isinstance(field_value, dict) or not all(k in field_value for k in ["dateTime", "timeZone"]):
                return _handle_calendar_api_error(ValueError(f"Si actualiza '{field_name}', debe ser un dict con 'dateTime' y 'timeZone'."), action_name, params)

    user_path_segment = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/events/{event_id}"
    
    logger.info(f"Actualizando evento ID '{event_id}' para '{user_identifier}'")
    try:
        response_obj = client.patch(url, scope=CALENDARS_READ_WRITE_SCOPE, json_data=update_payload)
        updated_event = response_obj.json()
        return {"status": "success", "data": updated_event, "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_calendar_api_error(e, action_name, params)

def delete_event(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "calendar_delete_event"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    user_identifier: Optional[str] = params.get("mailbox")
    if not user_identifier:
        return _handle_calendar_api_error(ValueError("'mailbox' es requerido."), action_name, params)

    event_id: Optional[str] = params.get("event_id")
    if not event_id:
        return _handle_calendar_api_error(ValueError("'event_id' es requerido."), action_name, params)

    user_path_segment = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/events/{event_id}"
    
    logger.info(f"Eliminando evento ID '{event_id}' para '{user_identifier}'")
    try:
        response_obj = client.delete(url, scope=CALENDARS_READ_WRITE_SCOPE)
        if response_obj.status_code == 204:
            return {"status": "success", "message": f"Evento '{event_id}' eliminado exitosamente.", "http_status": 204}
        else:
            response_obj.raise_for_status()
            return {}
    except Exception as e:
        return _handle_calendar_api_error(e, action_name, params)

def find_meeting_times(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "calendar_find_meeting_times"
    log_params = {k:v for k,v in params.items() if k not in ['meeting_time_suggestion_payload']}
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return _handle_calendar_api_error(ValueError("'user_id' es requerido."), action_name, params)
        
    meeting_time_suggestion_payload: Optional[Dict[str, Any]] = params.get("meeting_time_suggestion_payload")

    if not meeting_time_suggestion_payload or not isinstance(meeting_time_suggestion_payload, dict):
        return _handle_calendar_api_error(ValueError("'meeting_time_suggestion_payload' (dict) es requerido."), action_name, params)
    if not meeting_time_suggestion_payload.get("timeConstraint"):
        return _handle_calendar_api_error(ValueError("Campo 'timeConstraint' es requerido en el payload."), action_name, params)

    user_path_segment = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/findMeetingTimes"
    
    logger.info(f"Buscando horarios de reunión para usuario '{user_identifier}'")
    try:
        response_obj = client.post(url, scope=CALENDARS_READ_SHARED_SCOPE, json_data=meeting_time_suggestion_payload)
        response_data = response_obj.json()
        return {"status": "success", "data": response_data, "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_calendar_api_error(e, action_name, params)

def get_schedule(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "calendar_get_schedule"
    log_params = {k:v for k,v in params.items() if k not in ['schedule_information_payload']}
    logger.info(f"Ejecutando {action_name} con params: {log_params}")
    
    schedule_information_payload: Optional[Dict[str, Any]] = params.get("schedule_information_payload")

    if not schedule_information_payload or not isinstance(schedule_information_payload, dict):
        return _handle_calendar_api_error(ValueError("'schedule_information_payload' (dict) es requerido."), action_name, params)

    required_keys = ["schedules", "startTime", "endTime"]
    if not all(key in schedule_information_payload for key in required_keys):
        missing = [key for key in required_keys if key not in schedule_information_payload]
        return _handle_calendar_api_error(ValueError(f"Faltan campos requeridos en payload: {missing}."), action_name, params)
    if not isinstance(schedule_information_payload.get("schedules"), list) or not schedule_information_payload["schedules"]:
        return _handle_calendar_api_error(ValueError("'schedules' debe ser una lista no vacía de correos."), action_name, params)

    # El endpoint /me/calendar/getSchedule es el correcto para esta acción,
    # ya que opera en el contexto de la aplicación para buscar la disponibilidad
    # de los usuarios listados en el payload.
    url = f"{settings.GRAPH_API_BASE_URL}/me/calendar/getSchedule"
    
    logger.info("Consultando disponibilidad para usuarios en payload.")
    try:
        response_obj = client.post(url, scope=CALENDARS_READ_SHARED_SCOPE, json_data=schedule_information_payload)
        response_data = response_obj.json()
        return {"status": "success", "data": response_data.get("value", []), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_calendar_api_error(e, action_name, params)