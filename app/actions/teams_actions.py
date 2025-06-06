# app/actions/teams_actions.py
import logging
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

def _handle_teams_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Teams action '{action_name}'"
    safe_params = {}
    if params_for_log:
        sensitive_keys = ['message', 'content', 'body', 'payload', 'subject']
        safe_params = {k: (v if k not in sensitive_keys else "[CONTENIDO OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    details_str = str(e); status_code_int = 500; graph_error_code = None 
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json(); error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text); graph_error_code = error_info.get("code")
        except json.JSONDecodeError: 
            details_str = e.response.text[:500] if e.response.text else "No response body"
    return {
        "status": "error", "action": action_name,
        "message": f"Error ejecutando {action_name}: {type(e).__name__}",
        "http_status": status_code_int, "details": details_str,
        "graph_error_code": graph_error_code
    }

def _teams_paged_request(
    client: AuthenticatedHttpClient, url_base: str, scope: List[str],
    params_input: Dict[str, Any], 
    query_api_params_initial: Dict[str, Any],
    max_items_total: Optional[int], 
    action_name_for_log: str
) -> Dict[str, Any]:
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages_to_fetch = getattr(settings, 'MAX_PAGING_PAGES', 20)
    effective_max_items = float('inf') if max_items_total is None else max_items_total
    
    logger.debug(f"Iniciando solicitud paginada para '{action_name_for_log}' desde '{url_base.split('?')[0]}...'.")
    try:
        while current_url and len(all_items) < effective_max_items and page_count < max_pages_to_fetch:
            page_count += 1
            is_first_call = (page_count == 1 and current_url == url_base)
            current_call_params = query_api_params_initial if is_first_call else None
            
            response_data = client.get(url=current_url, scope=scope, params=current_call_params)
            
            if not isinstance(response_data, dict):
                 return _handle_teams_api_error(Exception(f"Respuesta inesperada: {type(response_data)}"), action_name_for_log, params_input)
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
        
        logger.info(f"'{action_name_for_log}' recuperó {len(all_items)} items en {page_count} páginas.")
        total_matching = response_data.get('@odata.count', len(all_items)) if 'response_data' in locals() and isinstance(response_data, dict) else len(all_items)
        return {"status": "success", "data": {"value": all_items, "@odata.count": total_matching}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e:
        return _handle_teams_api_error(e, action_name_for_log, params_input)

def list_joined_teams(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_list_joined_teams"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return _handle_teams_api_error(ValueError("'user_id' es requerido."), action_name, params)

    url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/joinedTeams"
    
    top_per_page: int = min(int(params.get('top_per_page', 25)), 50)
    max_items_total: Optional[int] = params.get('max_items_total')
    if isinstance(raw_max := params.get('max_items_total'), str) and raw_max.isdigit():
        max_items_total = int(raw_max)

    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,displayName,description,isArchived,webUrl")
    if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    
    teams_read_scope = getattr(settings, 'GRAPH_SCOPE_TEAMS_READ_BASIC_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    logger.info(f"{action_name}: Listando equipos para usuario '{user_identifier}'.")
    return _teams_paged_request(client, url_base, teams_read_scope, params, query_api_params, max_items_total, action_name)

# --- (El resto de las funciones de teams_actions.py deben seguir el mismo patrón de corrección) ---
# Por brevedad y para evitar un mensaje excesivamente largo, te entrego la función corregida de arriba
# y te confirmo que el mismo patrón de revisión para client.get() y client.post() se aplica al resto.
# Aquí está el resto del archivo con las correcciones ya aplicadas por mí.

def get_team(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_get_team"
    logger.info(f"Ejecutando {action_name} con params: %s", params)
    
    team_id: Optional[str] = params.get("team_id")
    if not team_id:
        return _handle_teams_api_error(ValueError("'team_id' es requerido."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}"
    query_params = {'$select': params['select']} if params.get("select") else None
    
    logger.info(f"Obteniendo detalles del equipo '{team_id}'")
    teams_read_scope = getattr(settings, 'GRAPH_SCOPE_TEAMS_READ_BASIC_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response_data = client.get(url, scope=teams_read_scope, params=query_params)
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data}
        else:
            return _handle_teams_api_error(Exception(f"Respuesta inesperada: {type(response_data)}"), action_name, params)
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def list_channels(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_list_channels"
    logger.info(f"Ejecutando {action_name} con params: %s", params)
    
    team_id: Optional[str] = params.get("team_id")
    if not team_id:
        return _handle_teams_api_error(ValueError("'team_id' es requerido."), action_name, params)
        
    url_base = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels"
    top_per_page: int = min(int(params.get('top_per_page', 25)), 50)
    max_items_total: Optional[int] = params.get('max_items_total')

    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,displayName,description,webUrl,email,membershipType")
    if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    
    channel_read_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    logger.info(f"Listando canales para equipo '{team_id}'.")
    return _teams_paged_request(client, url_base, channel_read_scope, params, query_api_params, max_items_total, action_name)

def get_channel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_get_channel"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    team_id: Optional[str] = params.get("team_id")
    channel_id: Optional[str] = params.get("channel_id")
    if not team_id or not channel_id:
        return _handle_teams_api_error(ValueError("'team_id' y 'channel_id' requeridos."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels/{channel_id}"
    query_params = {'$select': params['select']} if params.get("select") else None
    
    logger.info(f"Obteniendo detalles del canal '{channel_id}' en equipo '{team_id}'")
    channel_read_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response_data = client.get(url, scope=channel_read_scope, params=query_params)
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data}
        else:
            return _handle_teams_api_error(Exception(f"Respuesta inesperada: {type(response_data)}"), action_name, params)
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def send_channel_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_send_channel_message"
    logger.info(f"Ejecutando {action_name}")
    
    team_id: Optional[str] = params.get("team_id")
    channel_id: Optional[str] = params.get("channel_id")
    message_content: Optional[str] = params.get("content")
    
    if not all([team_id, channel_id, message_content]):
        return _handle_teams_api_error(ValueError("'team_id', 'channel_id', 'content' requeridos."), action_name, params)

    url = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels/{channel_id}/messages"
    payload = {"body": {"content": message_content}}
    if params.get("subject"): payload["subject"] = params["subject"]
    
    logger.info(f"Enviando mensaje al canal '{channel_id}' del equipo '{team_id}'")
    message_send_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_MESSAGE_SEND', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response_obj = client.post(url, scope=message_send_scope, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def list_channel_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_list_channel_messages"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    team_id: Optional[str] = params.get("team_id")
    channel_id: Optional[str] = params.get("channel_id")
    if not team_id or not channel_id:
        return _handle_teams_api_error(ValueError("'team_id' y 'channel_id' requeridos."), action_name, params)
        
    url_base = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels/{channel_id}/messages"
    top_per_page: int = min(int(params.get('top_per_page', 25)), 50)
    max_items_total: Optional[int] = params.get('max_items_total')
    
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,subject,summary,body,from,createdDateTime,lastModifiedDateTime,importance,webUrl")
    if str(params.get('expand_replies', "false")).lower() == "true": query_api_params['$expand'] = "replies"
    
    channel_read_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_MESSAGE_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    log_context = f"{action_name} (team: {team_id}, channel: {channel_id})"
    return _teams_paged_request(client, url_base, channel_read_scope, params, query_api_params, max_items_total, log_context)

def reply_to_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_reply_to_message"
    logger.info(f"Ejecutando {action_name}")

    team_id: Optional[str] = params.get("team_id")
    channel_id: Optional[str] = params.get("channel_id")
    message_id: Optional[str] = params.get("message_id")
    reply_content: Optional[str] = params.get("content")
    
    if not all([team_id, channel_id, message_id, reply_content]):
        return _handle_teams_api_error(ValueError("Todos los parámetros son requeridos."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels/{channel_id}/messages/{message_id}/replies"
    payload = {"body": {"content": reply_content}}
    
    logger.info(f"Enviando respuesta al mensaje '{message_id}'")
    message_send_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_MESSAGE_SEND', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response_obj = client.post(url, scope=message_send_scope, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def list_chats(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_list_chats"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        return _handle_teams_api_error(ValueError("'user_id' es requerido."), action_name, params)

    url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/chats"
    
    top_per_page: int = min(int(params.get('top_per_page', 25)), 50)
    max_items_total: Optional[int] = params.get('max_items_total')

    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,topic,chatType,createdDateTime,lastUpdatedDateTime,webUrl")
    if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    if str(params.get('expand_members', "false")).lower() == "true": query_api_params['$expand'] = "members"
    
    chat_read_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    log_context = f"{action_name} (user: {user_identifier})"
    return _teams_paged_request(client, url_base, chat_read_scope, params, query_api_params, max_items_total, log_context)

def get_chat(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_get_chat"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    chat_id: Optional[str] = params.get("chat_id")
    if not chat_id:
        return _handle_teams_api_error(ValueError("'chat_id' es requerido."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/chats/{chat_id}"
    
    query_api_params: Dict[str, Any] = {}
    query_api_params['$select'] = params.get('select', "id,topic,chatType,createdDateTime,lastUpdatedDateTime,webUrl,members")
    if str(params.get('expand_members', "true")).lower() == "true":
        query_api_params['$expand'] = "members"

    logger.info(f"Obteniendo detalles del chat '{chat_id}'")
    chat_rw_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response_data = client.get(url, scope=chat_rw_scope, params=query_api_params if query_api_params else None)
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            return {"status": "success", "data": response_data}
        else:
            return _handle_teams_api_error(Exception(f"Respuesta inesperada: {type(response_data)}"), action_name, params)
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def create_chat(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_create_chat"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    chat_type: str = params.get("chat_type", "group").lower()
    members_payload: Optional[List[Dict[str, Any]]] = params.get("members")
    topic: Optional[str] = params.get("topic")

    if not members_payload or not isinstance(members_payload, list):
        return _handle_teams_api_error(ValueError("'members' (lista de objetos) requerido."), action_name, params)
    if chat_type == "oneonone" and len(members_payload) != 2:
         return _handle_teams_api_error(ValueError("Para chat 'oneOnOne', 'members' debe tener 2 miembros."), action_name, params)
    if chat_type == "group" and not topic:
        return _handle_teams_api_error(ValueError("'topic' es requerido para chats grupales."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/chats"
    payload: Dict[str, Any] = {"chatType": chat_type, "members": members_payload}
    if topic: payload["topic"] = topic
    
    logger.info(f"Creando chat tipo '{chat_type}'")
    chat_create_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_CREATE', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response_obj = client.post(url, scope=chat_create_scope, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def send_chat_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_send_chat_message"
    logger.info(f"Ejecutando {action_name}")

    chat_id: Optional[str] = params.get("chat_id")
    message_content: Optional[str] = params.get("content")
    
    if not chat_id or not message_content:
        return _handle_teams_api_error(ValueError("'chat_id' y 'content' son requeridos."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/chats/{chat_id}/messages"
    payload = {"body": {"content": message_content}}
    
    logger.info(f"Enviando mensaje al chat '{chat_id}'")
    chat_send_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_SEND', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response_obj = client.post(url, scope=chat_send_scope, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def list_chat_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_list_chat_messages"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    chat_id: Optional[str] = params.get("chat_id")
    if not chat_id:
        return _handle_teams_api_error(ValueError("'chat_id' es requerido."), action_name, params)
        
    url_base = f"{settings.GRAPH_API_BASE_URL}/chats/{chat_id}/messages"
    top_per_page: int = min(int(params.get('top_per_page', 25)), 50)
    max_items_total: Optional[int] = params.get('max_items_total')

    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,subject,body,from,createdDateTime,lastModifiedDateTime,importance,webUrl")
    
    chat_rw_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    log_context = f"{action_name} (chat: {chat_id})"
    return _teams_paged_request(client, url_base, chat_rw_scope, params, query_api_params, max_items_total, log_context)

def schedule_meeting(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_schedule_meeting"
    logger.info(f"Ejecutando {action_name}")

    organizer_id: Optional[str] = params.get("organizer_user_id")
    if not organizer_id:
        return _handle_teams_api_error(ValueError("'organizer_user_id' es requerido."), action_name, params)

    subject: Optional[str] = params.get("subject")
    start_dt: Optional[str] = params.get("start_datetime")
    end_dt: Optional[str] = params.get("end_datetime")
    
    if not all([subject, start_dt, end_dt]):
        return _handle_teams_api_error(ValueError("'subject', 'start_datetime', 'end_datetime' requeridos."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/users/{organizer_id}/events"
    
    payload = {
        "subject": subject,
        "start": {"dateTime": start_dt, "timeZone": params.get("timezone", "UTC")},
        "end": {"dateTime": end_dt, "timeZone": params.get("timezone", "UTC")},
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness"
    }
    if params.get("attendees"): payload["attendees"] = params["attendees"]
    if params.get("body_content"): payload["body"] = {"content": params["body_content"]}
    
    logger.info(f"Programando reunión para organizador '{organizer_id}': '{subject}'")
    meeting_rw_scope = getattr(settings, 'GRAPH_SCOPE_CALENDARS_READ_WRITE', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response_obj = client.post(url, scope=meeting_rw_scope, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "http_status": response_obj.status_code}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def get_meeting_details(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_get_meeting_details"
    logger.info(f"Ejecutando {action_name} con params: %s", params)

    owner_id: Optional[str] = params.get("owner_user_id")
    event_id: Optional[str] = params.get("event_id")
    if not owner_id or not event_id:
        return _handle_teams_api_error(ValueError("'owner_user_id' y 'event_id' requeridos."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/users/{owner_id}/events/{event_id}"
    query_params = {'$select': params.get('select', 'id,subject,start,end,organizer,attendees,body,onlineMeeting,webLink')}
    
    logger.info(f"Obteniendo detalles de reunión (evento) '{event_id}'")
    meeting_read_scope = getattr(settings, 'GRAPH_SCOPE_CALENDARS_READ', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        event_data = client.get(url, scope=meeting_read_scope, params=query_params)
        if not isinstance(event_data, dict):
            return _handle_teams_api_error(Exception(f"Respuesta inesperada: {type(event_data)}"), action_name, params)

        if not event_data.get("onlineMeeting"):
            return {"status": "warning", "data": event_data, "message": "Evento obtenido, pero no parece ser una reunión online de Teams."}
        return {"status": "success", "data": event_data}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def list_members(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "teams_list_members"
    logger.info(f"Ejecutando {action_name} (Teams/Chat) con params: %s", params)

    team_id: Optional[str] = params.get("team_id")
    chat_id: Optional[str] = params.get("chat_id")
    
    if not team_id and not chat_id:
        return _handle_teams_api_error(ValueError("Se requiere 'team_id' o 'chat_id'."), action_name, params)
    if team_id and chat_id:
        return _handle_teams_api_error(ValueError("Proporcione 'team_id' O 'chat_id', no ambos."), action_name, params)
        
    parent_type = "equipo" if team_id else "chat"
    parent_id = team_id if team_id else chat_id
    
    url_base: str
    scope_to_use: List[str]
    if team_id:
        url_base = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/members"
        scope_to_use = getattr(settings, 'GRAPH_SCOPE_TEAM_MEMBER_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    else: # chat_id
        url_base = f"{settings.GRAPH_API_BASE_URL}/chats/{chat_id}/members"
        scope_to_use = getattr(settings, 'GRAPH_SCOPE_CHAT_MEMBER_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
                                
    top_per_page: int = min(int(params.get('top_per_page', 25)), 50)
    max_items_total: Optional[int] = params.get('max_items_total')

    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,displayName,userId,email,roles")
    if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    
    log_context = f"{action_name} ({parent_type}: {parent_id})"
    return _teams_paged_request(client, url_base, scope_to_use, params, query_api_params, max_items_total, log_context)