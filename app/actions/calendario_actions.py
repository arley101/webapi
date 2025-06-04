# app/actions/calendario_actions.py
import logging
import requests 
import json 
from typing import Dict, List, Optional, Any

from app.core.config import settings 
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

CALENDARS_READ_SCOPE = getattr(settings, "GRAPH_SCOPE_CALENDARS_READ", settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
CALENDARS_READ_WRITE_SCOPE = getattr(settings, "GRAPH_SCOPE_CALENDARS_READ_WRITE", settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
CALENDARS_READ_SHARED_SCOPE = getattr(settings, "GRAPH_SCOPE_CALENDARS_READ_SHARED", settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore

def _handle_calendar_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Calendar action '{action_name}'"
    if params_for_log:
        safe_params = {k: v for k, v in params_for_log.items() if k not in ['event_payload', 'update_payload', 'meeting_params_body', 'schedule_params_body', 'attendees']}
        log_message += f" con params: {safe_params}"
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    details_str = str(e); status_code_int = 500; graph_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json(); error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text); graph_error_code = error_info.get("code")
        except json.JSONDecodeError: details_str = e.response.text[:500] if e.response.text else "No response body"
    return {"status": "error", "action": action_name, "message": f"Error en {action_name}: {type(e).__name__}",
            "http_status": status_code_int, "details": details_str, "graph_error_code": graph_error_code}

def _calendar_paged_request(
    client: AuthenticatedHttpClient, url_base: str, scope_list: List[str],
    params: Dict[str, Any], query_api_params_initial: Dict[str, Any],
    max_items_total: Optional[int], action_name_for_log: str
) -> Dict[str, Any]:
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages_to_fetch = getattr(settings, "MAX_PAGING_PAGES", 20) 
    effective_max_items = float('inf') if max_items_total is None else max_items_total
    logger.debug(f"Paginación Calendario para '{action_name_for_log}'. Max total: {max_items_total or 'todos'}")
    try:
        while current_url and len(all_items) < effective_max_items and page_count < max_pages_to_fetch:
            page_count += 1
            current_params_for_call = query_api_params_initial if page_count == 1 and current_url == url_base else None
            response_data = client.get(url=current_url, scope=scope_list, params=current_params_for_call)
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
    except Exception as e: return _handle_calendar_api_error(e, action_name_for_log, params)

def calendar_list_events(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando calendar_list_events: %s", params); action_name = "calendar_list_events"
    user_identifier: Optional[str] = params.get("mailbox")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' es requerido.", "http_status": 400}
    calendar_id: Optional[str] = params.get("calendar_id") 
    query_api_params: Dict[str, Any] = {'$top': min(int(params.get('top_per_page', 25)), 100)}
    query_api_params['$select'] = params.get('select', "id,subject,bodyPreview,start,end,organizer,attendees,location,isAllDay,webLink,onlineMeeting")
    query_api_params['$orderby'] = params.get('orderby', 'start/dateTime')
    user_path = f"users/{user_identifier}"; calendar_path = f"calendars/{calendar_id}" if calendar_id else "calendar"
    url_base: str; log_detail: str
    if params.get('start_datetime') and params.get('end_datetime'):
        query_api_params['startDateTime'] = params['start_datetime']; query_api_params['endDateTime'] = params['end_datetime']
        if params.get('filter_query'): logger.warning("$filter con calendarView podría no ser aplicado.")
        url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path}/{calendar_path}/calendarView"
        log_detail = f"eventos ({calendar_path}/calendarView) para '{user_identifier}'"
    else:
        if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
        url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path}/{calendar_path}/events"
        log_detail = f"eventos ({calendar_path}/events) para '{user_identifier}'"
    return _calendar_paged_request(client, url_base, CALENDARS_READ_SCOPE, params, query_api_params, params.get('max_items_total'), f"{action_name} ({log_detail})")

def calendar_create_event(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando calendar_create_event: %s", params); action_name = "calendar_create_event"
    user_identifier: Optional[str] = params.get("mailbox")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' es requerido.", "http_status": 400}
    event_payload: Optional[Dict[str, Any]] = params.get("event_payload")
    if not event_payload or not isinstance(event_payload, dict): return {"status": "error", "action": action_name, "message": "'event_payload' (dict) requerido.", "http_status": 400}
    required = ["subject", "start", "end"]
    if not all(f in event_payload for f in required) or \
       not isinstance(event_payload.get("start"), dict) or not event_payload["start"].get("dateTime") or \
       not isinstance(event_payload.get("end"), dict) or not event_payload["end"].get("dateTime"):
        return {"status": "error", "action": action_name, "message": f"Faltan campos o 'start'/'end' malformados en 'event_payload'. Requeridos: {required}, y start/end deben ser dict con 'dateTime'.", "http_status": 400}
    user_path = f"users/{user_identifier}"; calendar_path = f"calendars/{params.get('calendar_id')}" if params.get('calendar_id') else "calendar"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/{calendar_path}/events"
    try:
        response_obj = client.post(url, scope=CALENDARS_READ_WRITE_SCOPE, json_data=event_payload) # client.post devuelve requests.Response
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_calendar_api_error(e, action_name, params)

def get_event(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_event: %s", params); action_name = "calendar_get_event"
    user_identifier: Optional[str] = params.get("mailbox")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' es requerido.", "http_status": 400}
    event_id: Optional[str] = params.get("event_id")
    if not event_id: return {"status": "error", "action": action_name, "message": "'event_id' es requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/events/{event_id}"
    query_api_params = {'$select': params['select']} if params.get("select") else None
    try:
        response_data = client.get(url, scope=CALENDARS_READ_SCOPE, params=query_api_params)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_calendar_api_error(e, action_name, params)

def update_event(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando update_event: %s", params); action_name = "calendar_update_event"
    user_identifier: Optional[str] = params.get("mailbox")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' es requerido.", "http_status": 400}
    event_id: Optional[str] = params.get("event_id")
    if not event_id: return {"status": "error", "action": action_name, "message": "'event_id' es requerido.", "http_status": 400}
    update_payload: Optional[Dict[str, Any]] = params.get("update_payload")
    if not update_payload or not isinstance(update_payload, dict) or not update_payload:
        return {"status": "error", "action": action_name, "message": "'update_payload' (dict no vacío) requerido.", "http_status": 400}
    for field_name in ["start", "end"]:
        if field_name in update_payload and (not isinstance(update_payload[field_name], dict) or not update_payload[field_name].get("dateTime")):
            return {"status": "error", "action": action_name, "message": f"Si actualiza '{field_name}', debe ser dict con 'dateTime'.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/events/{event_id}"
    try:
        response_obj = client.patch(url, scope=CALENDARS_READ_WRITE_SCOPE, json_data=update_payload) # client.patch devuelve requests.Response
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_calendar_api_error(e, action_name, params)

def delete_event(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando delete_event: %s", params); action_name = "calendar_delete_event"
    user_identifier: Optional[str] = params.get("mailbox")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' es requerido.", "http_status": 400}
    event_id: Optional[str] = params.get("event_id")
    if not event_id: return {"status": "error", "action": action_name, "message": "'event_id' es requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/events/{event_id}"
    try:
        response_obj = client.delete(url, scope=CALENDARS_READ_WRITE_SCOPE) # client.delete devuelve requests.Response
        return {"status": "success", "message": f"Evento '{event_id}' eliminado.", "http_status": response_obj.status_code}
    except Exception as e: return _handle_calendar_api_error(e, action_name, params)

def find_meeting_times(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando find_meeting_times: %s", params); action_name = "calendar_find_meeting_times"
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    meeting_payload: Optional[Dict[str, Any]] = params.get("meeting_time_suggestion_payload")
    if not meeting_payload or not isinstance(meeting_payload, dict) or not meeting_payload.get("timeConstraint"):
        return {"status": "error", "action": action_name, "message": "'meeting_time_suggestion_payload' (dict con 'timeConstraint') requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/findMeetingTimes"
    try:
        response_obj = client.post(url, scope=CALENDARS_READ_SHARED_SCOPE, json_data=meeting_payload) # client.post devuelve requests.Response
        return {"status": "success", "data": response_obj.json()}
    except Exception as e: return _handle_calendar_api_error(e, action_name, params)

def get_schedule(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_schedule: %s", params); action_name = "calendar_get_schedule"
    user_id_context: Optional[str] = params.get("user_id_context") # Usuario en cuyo contexto se llama
    schedule_payload: Optional[Dict[str, Any]] = params.get("schedule_information_payload")
    if not schedule_payload or not isinstance(schedule_payload, dict) or \
       not all(k in schedule_payload for k in ["schedules", "startTime", "endTime"]) or \
       not isinstance(schedule_payload.get("schedules"), list) or not schedule_payload["schedules"]:
        return {"status": "error", "action": action_name, "message": "'schedule_information_payload' (dict con 'schedules' (lista no vacía), 'startTime', 'endTime') requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id_context}/calendar/getSchedule" if user_id_context else f"{settings.GRAPH_API_BASE_URL}/me/calendar/getSchedule"
    if not user_id_context: logger.warning(f"{action_name}: 'user_id_context' no provisto. Usando '/me/'.")
    try:
        response_obj = client.post(url, scope=CALENDARS_READ_SHARED_SCOPE, json_data=schedule_payload)
        return {"status": "success", "data": response_obj.json().get("value", [])}
    except Exception as e: return _handle_calendar_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/calendario_actions.py ---