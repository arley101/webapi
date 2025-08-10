# app/actions/calendario_actions.py
import logging
import requests # Para requests.exceptions.HTTPError
import json # Para el helper de error
from typing import Dict, List, Optional, Any

from app.core.config import settings # Para acceder a GRAPH_API_BASE_URL y scopes
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# Scopes específicos para calendario (si se definen en settings, de lo contrario usa el default)
CALENDARS_READ_SCOPE = getattr(settings, "GRAPH_SCOPE_CALENDARS_READ", settings.GRAPH_API_DEFAULT_SCOPE)
CALENDARS_READ_WRITE_SCOPE = getattr(settings, "GRAPH_SCOPE_CALENDARS_READ_WRITE", settings.GRAPH_API_DEFAULT_SCOPE)
CALENDARS_READ_SHARED_SCOPE = getattr(settings, "GRAPH_SCOPE_CALENDARS_READ_SHARED", settings.GRAPH_API_DEFAULT_SCOPE)


def _handle_calendar_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Helper para manejar errores de Calendar API de forma centralizada."""
    # Esta función helper no toma 'params' del action_map directamente
    log_message = f"Error en Calendar action '{action_name}'"
    if params_for_log:
        safe_params = {k: v for k, v in params_for_log.items() if k not in ['event_payload', 'update_payload', 'meeting_params_body', 'schedule_params_body', 'attendees']}
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
    params: Dict[str, Any], # params originales de la acción para logging de error
    query_api_params_initial: Dict[str, Any],
    max_items_total: Optional[int],
    action_name_for_log: str
) -> Dict[str, Any]:
    """Helper común para paginación de resultados de Calendario."""
    # El logging principal y 'params or {}' se hacen en la función llamante
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages_to_fetch = getattr(settings, "MAX_PAGING_PAGES", 20) 
    top_per_page = query_api_params_initial.get('$top', 50)

    logger.debug(f"Iniciando solicitud paginada para '{action_name_for_log}' desde '{url_base.split('?')[0]}...'. Max total items: {max_items_total or 'todos'}, por página: {top_per_page}, max_páginas: {max_pages_to_fetch}")
    try:
        while current_url and (max_items_total is None or len(all_items) < max_items_total) and page_count < max_pages_to_fetch:
            page_count += 1
            is_first_call = (current_url == url_base and page_count == 1)
            
            current_params_for_call = query_api_params_initial if is_first_call else None
            logger.debug(f"Página {page_count} para '{action_name_for_log}': GET {current_url.split('?')[0]} con params: {current_params_for_call}")
            
            response = client.get(url=current_url, scope=scope_list, params=current_params_for_call)
            
            # --- CORRECCIÓN ---
            # `client.get` ya devuelve un dict, no un objeto response. Se elimina `.json()`.
            response_data = response
            
            page_items = response_data.get('value', [])
            if not isinstance(page_items, list):
                logger.warning(f"Respuesta inesperada en paginación para '{action_name_for_log}', 'value' no es una lista. Respuesta: {response_data}")
                break 
            
            for item in page_items:
                if max_items_total is None or len(all_items) < max_items_total:
                    all_items.append(item)
                else:
                    break 
            
            current_url = response_data.get('@odata.nextLink')
            if not current_url or (max_items_total is not None and len(all_items) >= max_items_total):
                logger.debug(f"'{action_name_for_log}': Fin de paginación. nextLink: {'Sí' if current_url else 'No'}, Items actuales: {len(all_items)}.")
                break
        
        if page_count >= max_pages_to_fetch and current_url:
            logger.warning(f"'{action_name_for_log}' alcanzó el límite de {max_pages_to_fetch} páginas procesadas. Pueden existir más resultados no recuperados.")

        logger.info(f"'{action_name_for_log}' recuperó {len(all_items)} items en {page_count} páginas.")
        return {"status": "success", "data": {"value": all_items, "@odata.count": len(all_items)}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e:
        # Pasar los params originales de la acción para un logging de error más completo
        return _handle_calendar_api_error(e, action_name_for_log, params)


def calendar_list_events(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando calendar_list_events con params: %s", params)
    action_name = "calendar_list_events"

    user_identifier: Optional[str] = params.get("mailbox") # Esperar 'mailbox' como user_id o UPN
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    calendar_id: Optional[str] = params.get("calendar_id") 
    start_datetime_str: Optional[str] = params.get('start_datetime')
    end_datetime_str: Optional[str] = params.get('end_datetime')
    top_per_page: int = min(int(params.get('top_per_page', 25)), 100)
    max_items_total: Optional[int] = params.get('max_items_total')
    select_fields: Optional[str] = params.get('select')
    filter_query: Optional[str] = params.get('filter_query')
    order_by: Optional[str] = params.get('orderby', 'start/dateTime')

    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    if select_fields: 
        query_api_params['$select'] = select_fields
    else:
        query_api_params['$select'] = "id,subject,bodyPreview,start,end,organizer,attendees,location,isAllDay,webLink,onlineMeeting"
    if order_by:
        query_api_params['$orderby'] = order_by

    user_path_segment = f"users/{user_identifier}" # Siempre /users/{id}
    calendar_path_segment = f"calendars/{calendar_id}" if calendar_id else "calendar"

    url_base: str
    log_action_detail: str

    if start_datetime_str and end_datetime_str:
        query_api_params['startDateTime'] = start_datetime_str
        query_api_params['endDateTime'] = end_datetime_str
        if '$filter' in query_api_params: 
            logger.warning("Parámetro '$filter' provisto con start/end datetime para calendarView; $filter podría no ser aplicado.")
        
        url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/{calendar_path_segment}/calendarView"
        log_action_detail = f"eventos ({calendar_path_segment}/calendarView) para '{user_identifier}' entre {start_datetime_str} y {end_datetime_str}"
    else:
        if filter_query: 
            query_api_params['$filter'] = filter_query
        url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/{calendar_path_segment}/events"
        log_action_detail = f"eventos ({calendar_path_segment}/events) para '{user_identifier}'"
    
    logger.info(f"{action_name}: Listando {log_action_detail}. Query: {query_api_params}")
    return _calendar_paged_request(
        client, url_base, CALENDARS_READ_SCOPE, 
        params, query_api_params, max_items_total, 
        f"{action_name} ({log_action_detail})"
    )

def calendar_create_event(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando calendar_create_event con params: %s", params)
    action_name = "calendar_create_event"

    user_identifier: Optional[str] = params.get("mailbox")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    calendar_id: Optional[str] = params.get("calendar_id")
    event_payload: Optional[Dict[str, Any]] = params.get("event_payload")

    if not event_payload or not isinstance(event_payload, dict):
        return {"status": "error", "action": action_name, "message": "'event_payload' (dict) es requerido.", "http_status": 400}

    required_fields = ["subject", "start", "end"]
    if not all(field in event_payload for field in required_fields):
        missing = [field for field in required_fields if field not in event_payload]
        return {"status": "error", "action": action_name, "message": f"Faltan campos requeridos en 'event_payload': {missing}.", "http_status": 400}
    
    for field_name in ["start", "end"]:
        if not isinstance(event_payload.get(field_name), dict) or \
           not event_payload[field_name].get("dateTime") or \
           not event_payload[field_name].get("timeZone"):
            return {"status": "error", "action": action_name, "message": f"Campo '{field_name}' en 'event_payload' debe ser un dict con 'dateTime' y 'timeZone'.", "http_status": 400}

    user_path_segment = f"users/{user_identifier}"
    calendar_path_segment = f"calendars/{calendar_id}" if calendar_id else "calendar"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/{calendar_path_segment}/events"
    
    logger.info(f"{action_name}: Creando evento en {calendar_path_segment} para '{user_identifier}'. Asunto: {event_payload.get('subject')}")
    try:
        response = client.post(url, scope=CALENDARS_READ_WRITE_SCOPE, json_data=event_payload)
        created_event = response.json()
        logger.info(f"Evento '{event_payload.get('subject')}' creado con ID: {created_event.get('id')}")
        return {"status": "success", "data": created_event}
    except Exception as e:
        return _handle_calendar_api_error(e, action_name, params)

def get_event(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_event con params: %s", params)
    action_name = "calendar_get_event"

    user_identifier: Optional[str] = params.get("mailbox")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    event_id: Optional[str] = params.get("event_id")
    if not event_id:
        logger.error(f"{action_name}: El parámetro 'event_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'event_id' es requerido.", "http_status": 400}
    
    select_fields: Optional[str] = params.get("select")
    user_path_segment = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/events/{event_id}"
    
    query_api_params = {'$select': select_fields} if select_fields else None
    logger.info(f"{action_name}: Obteniendo evento ID '{event_id}' para '{user_identifier}' (Select: {select_fields or 'default'})")
    try:
        response = client.get(url, scope=CALENDARS_READ_SCOPE, params=query_api_params)
        # --- CORRECCIÓN ---
        # `client.get` ya devuelve un dict, no un objeto response. Se elimina `.json()`.
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_calendar_api_error(e, action_name, params)

def update_event(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando update_event con params: %s", params)
    action_name = "calendar_update_event"

    user_identifier: Optional[str] = params.get("mailbox")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    event_id: Optional[str] = params.get("event_id")
    if not event_id:
        logger.error(f"{action_name}: El parámetro 'event_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'event_id' es requerido.", "http_status": 400}

    update_payload: Optional[Dict[str, Any]] = params.get("update_payload")
    if not update_payload or not isinstance(update_payload, dict) or not update_payload:
        return {"status": "error", "action": action_name, "message": "'update_payload' (dict con campos a actualizar) es requerido y no puede estar vacío.", "http_status": 400}

    for field_name in ["start", "end"]:
        if field_name in update_payload:
            field_value = update_payload[field_name]
            if not isinstance(field_value, dict) or \
               not field_value.get("dateTime") or \
               not field_value.get("timeZone"):
                return {"status": "error", "action": action_name, "message": f"Si actualiza '{field_name}', debe ser un dict con 'dateTime' y 'timeZone'.", "http_status": 400}

    user_path_segment = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/events/{event_id}"
    
    logger.info(f"{action_name}: Actualizando evento ID '{event_id}' para '{user_identifier}'")
    try:
        response = client.patch(url, scope=CALENDARS_READ_WRITE_SCOPE, json_data=update_payload)
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_calendar_api_error(e, action_name, params)

def delete_event(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando delete_event con params: %s", params)
    action_name = "calendar_delete_event"

    user_identifier: Optional[str] = params.get("mailbox")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    event_id: Optional[str] = params.get("event_id")
    if not event_id:
        logger.error(f"{action_name}: El parámetro 'event_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'event_id' es requerido.", "http_status": 400}

    user_path_segment = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/events/{event_id}"
    
    logger.info(f"{action_name}: Eliminando evento ID '{event_id}' para '{user_identifier}'")
    try:
        response = client.delete(url, scope=CALENDARS_READ_WRITE_SCOPE)
        return {"status": "success", "message": f"Evento '{event_id}' eliminado exitosamente.", "http_status": response.status_code}
    except Exception as e:
        return _handle_calendar_api_error(e, action_name, params)

def find_meeting_times(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando find_meeting_times con params: %s", params)
    action_name = "calendar_find_meeting_times"

    # El endpoint /findMeetingTimes opera en el contexto de un usuario específico.
    user_identifier: Optional[str] = params.get("user_id") # UPN o ID del usuario organizador o para quien se buscan horarios
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' (UPN o ID del usuario) es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
        
    meeting_time_suggestion_payload: Optional[Dict[str, Any]] = params.get("meeting_time_suggestion_payload")

    if not meeting_time_suggestion_payload or not isinstance(meeting_time_suggestion_payload, dict):
        return {"status": "error", "action": action_name, "message": "'meeting_time_suggestion_payload' (dict) es requerido.", "http_status": 400}
    
    if not meeting_time_suggestion_payload.get("timeConstraint"):
        return {"status": "error", "action": action_name, "message": "Campo 'timeConstraint' es requerido en 'meeting_time_suggestion_payload'.", "http_status": 400}

    user_path_segment = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/findMeetingTimes"
    
    logger.info(f"{action_name}: Buscando horarios de reunión (findMeetingTimes) para usuario '{user_identifier}'")
    try:
        # Requiere Calendars.Read.Shared o Calendars.Read
        response = client.post(url, scope=CALENDARS_READ_SHARED_SCOPE, json_data=meeting_time_suggestion_payload)
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_calendar_api_error(e, action_name, params)

def get_schedule(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_schedule con params: %s", params)
    action_name = "calendar_get_schedule"
    
    # El endpoint /getSchedule opera en el contexto del usuario cuya información de calendario se está utilizando para la llamada,
    # pero los 'schedules' en el payload son las personas cuya disponibilidad se consulta.
    # Con permisos de aplicación, el 'me' en /me/calendar/getSchedule no tiene un contexto de usuario directo.
    # Es más común usar /users/{id}/calendar/getSchedule si se quiere basar en el calendario de un usuario específico
    # para alguna lógica, O si la app tiene un "usuario de servicio" asociado.
    # Sin embargo, la API de /getSchedule es para obtener la información de disponibilidad de las personas en el payload.
    # La documentación indica /me/calendar/getSchedule, pero con App Permissions, el "me" es la propia app.
    # Una alternativa, si se quiere que la consulta se origine "desde" un usuario específico,
    # sería /users/{some-user-id}/calendar/getSchedule, pero la clave es lo que va en el payload 'schedules'.
    # Por consistencia y para evitar el "me", si se requiere un "organizador" o "consultador" específico:
    
    user_identifier_context: Optional[str] = params.get("user_id_context") # Opcional: UPN/ID del usuario en cuyo contexto se hace la llamada
    
    schedule_information_payload: Optional[Dict[str, Any]] = params.get("schedule_information_payload")

    if not schedule_information_payload or not isinstance(schedule_information_payload, dict):
        return {"status": "error", "action": action_name, "message": "'schedule_information_payload' (dict) es requerido.", "http_status": 400}

    required_payload_keys = ["schedules", "startTime", "endTime"]
    if not all(key in schedule_information_payload for key in required_payload_keys):
        missing = [key for key in required_payload_keys if key not in schedule_information_payload]
        return {"status": "error", "action": action_name, "message": f"Faltan campos requeridos en 'schedule_information_payload': {missing}.", "http_status": 400}
    if not isinstance(schedule_information_payload.get("schedules"), list) or not schedule_information_payload["schedules"]:
        return {"status": "error", "action": action_name, "message": "'schedules' debe ser una lista no vacía de direcciones de correo.", "http_status": 400}

    url: str
    if user_identifier_context:
        url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier_context}/calendar/getSchedule"
        logger.info(f"{action_name}: Obteniendo información de calendario (getSchedule) en contexto de '{user_identifier_context}'.")
    else:
        # Si no se provee user_id_context, el endpoint /me/calendar/getSchedule con app token puede no tener sentido
        # o tener un comportamiento no deseado. Es mejor que la acción requiera un user_id_context o
        # se documente claramente que la llamada se hace en el contexto de la aplicación.
        # Por ahora, vamos a requerir un user_id_context si no se usa 'me' (que no deberíamos)
        logger.error(f"{action_name}: 'user_id_context' es recomendado para getSchedule con permisos de aplicación para definir el contexto de la llamada.")
        # Alternativamente, podríamos permitir que la API falle si /me/calendar/getSchedule no es lo que se quiere.
        # Para ser más explícitos con permisos de aplicación, consideremos este flujo como menos prioritario o que requiere un user_id_context.
        # Por ahora, si no hay user_id_context, usaremos 'me' advirtiendo que puede no ser lo esperado.
        logger.warning(f"{action_name}: 'user_id_context' no provisto. Usando '/me/calendar/getSchedule'. El comportamiento con token de aplicación puede ser limitado o referirse a la propia aplicación.")
        url = f"{settings.GRAPH_API_BASE_URL}/me/calendar/getSchedule"


    logger.info(f"{action_name}: Consultando disponibilidad para usuarios en payload.")
    try:
        response = client.post(url, scope=CALENDARS_READ_SHARED_SCOPE, json_data=schedule_information_payload)
        return {"status": "success", "data": response.json().get("value", [])}
    except Exception as e:
        return _handle_calendar_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/calendario_actions.py ---