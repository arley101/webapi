# app/actions/teams_actions.py
import logging
import requests # Para requests.exceptions.HTTPError
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime # Para schedule_meeting

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

    logger.debug(f"Iniciando solicitud paginada para '{action_name_for_log}' desde '{url_base.split('?')[0]}...'. Max total: {max_items_total or 'todos'}")
    try:
        while current_url and len(all_items) < effective_max_items and page_count < max_pages_to_fetch:
            page_count += 1
            is_first_call = (page_count == 1 and current_url == url_base)
            current_call_params = query_api_params_initial if is_first_call else None
            
            logger.debug(f"Página {page_count} para '{action_name_for_log}': GET {current_url.split('?')[0]} con params: {current_call_params}")
            
            response_data = client.get(url=current_url, scope=scope, params=current_call_params)
            if not isinstance(response_data, dict):
                raise Exception(f"Respuesta paginada inesperada, se esperaba dict. Tipo: {type(response_data)}")
            if response_data.get("status") == "error" and "http_status" in response_data:
                return response_data 

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): 
                logger.warning(f"Respuesta paginada, 'value' no es lista: {response_data}")
                break
            
            for item in page_items:
                if len(all_items) < effective_max_items: all_items.append(item)
                else: break 
            
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max_items : break
        
        logger.info(f"'{action_name_for_log}' recuperó {len(all_items)} items en {page_count} páginas.")
        return {"status": "success", "data": {"value": all_items, "@odata.count": len(all_items)}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e:
        return _handle_teams_api_error(e, action_name_for_log, params_input)

def list_joined_teams(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_joined_teams con params: %s", params)
    action_name = "teams_list_joined_teams"
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/joinedTeams"
    top_per_page: int = min(int(params.get('top_per_page', 25)), getattr(settings, 'DEFAULT_PAGING_SIZE', 50))
    max_items_total: Optional[int] = None
    if params.get('max_items_total') is not None:
        try: max_items_total = int(params['max_items_total'])
        except ValueError: logger.warning(f"{action_name}: 'max_items_total' inválido.")
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,displayName,description,isArchived,webUrl")
    if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    teams_read_scope = getattr(settings, 'GRAPH_SCOPE_TEAMS_READ_BASIC_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    return _teams_paged_request(client, url_base, teams_read_scope, params, query_api_params, max_items_total, action_name)

def get_team(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_team con params: %s", params); action_name = "teams_get_team"
    team_id: Optional[str] = params.get("team_id")
    if not team_id: return _handle_teams_api_error(ValueError("'team_id' es requerido."), action_name, params)
    url = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}"
    query_params = {'$select': params['select']} if params.get("select") else None
    teams_read_scope = getattr(settings, 'GRAPH_SCOPE_TEAMS_READ_BASIC_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_data = client.get(url, scope=teams_read_scope, params=query_params)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_teams_api_error(e, action_name, params)

def list_channels(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_channels con params: %s", params); action_name = "teams_list_channels"
    team_id: Optional[str] = params.get("team_id")
    if not team_id: return _handle_teams_api_error(ValueError("'team_id' es requerido."), action_name, params)
    url_base = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels"
    top_per_page: int = min(int(params.get('top_per_page', 25)), getattr(settings, 'DEFAULT_PAGING_SIZE', 50))
    max_items_total: Optional[int] = None
    if params.get('max_items_total') is not None:
        try: max_items_total = int(params['max_items_total'])
        except ValueError: logger.warning(f"{action_name}: 'max_items_total' inválido.")
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,displayName,description,webUrl,email,membershipType")
    if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    channel_read_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_READ_ALL', getattr(settings, 'GRAPH_SCOPE_TEAMS_READ_BASIC_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    return _teams_paged_request(client, url_base, channel_read_scope, params, query_api_params, max_items_total, f"{action_name} (team: {team_id})")

def get_channel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_channel con params: %s", params); action_name = "teams_get_channel"
    team_id = params.get("team_id"); channel_id = params.get("channel_id")
    if not team_id or not channel_id: return _handle_teams_api_error(ValueError("'team_id' y 'channel_id' requeridos."), action_name, params)
    url = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels/{channel_id}"
    query_params = {'$select': params['select']} if params.get("select") else None
    channel_read_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_data = client.get(url, scope=channel_read_scope, params=query_params)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_teams_api_error(e, action_name, params)

def send_channel_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_safe = {k:v for k,v in params.items() if k != 'content'}
    logger.info("Ejecutando send_channel_message (contenido omitido): %s", log_safe); action_name = "teams_send_channel_message"
    team_id = params.get("team_id"); channel_id = params.get("channel_id"); message_content = params.get("content")
    if not team_id or not channel_id or message_content is None: return _handle_teams_api_error(ValueError("'team_id', 'channel_id', 'content' requeridos."), action_name, params)
    content_type: str = params.get("content_type", "HTML").upper()
    if content_type not in ["HTML", "TEXT"]: return _handle_teams_api_error(ValueError("'content_type' debe ser HTML o TEXT."), action_name, params)
    url = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels/{channel_id}/messages"
    payload = {"body": {"contentType": content_type, "content": message_content}}
    if params.get("subject"): payload["subject"] = params["subject"]
    message_send_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_MESSAGE_SEND', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_obj = client.post(url, scope=message_send_scope, json_data=payload) # client.post devuelve requests.Response
        return {"status": "success", "data": response_obj.json(), "message": "Mensaje enviado al canal."}
    except Exception as e: return _handle_teams_api_error(e, action_name, params)

def list_channel_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_channel_messages: %s", params); action_name = "teams_list_channel_messages"
    team_id = params.get("team_id"); channel_id = params.get("channel_id")
    if not team_id or not channel_id: return _handle_teams_api_error(ValueError("'team_id' y 'channel_id' requeridos."), action_name, params)
    url_base = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels/{channel_id}/messages"
    top_per_page: int = min(int(params.get('top_per_page', 25)), 50)
    max_items_total: Optional[int] = None
    if params.get('max_items_total') is not None:
        try: max_items_total = int(params['max_items_total'])
        except ValueError: logger.warning(f"{action_name}: 'max_items_total' inválido.")
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,subject,summary,body,from,createdDateTime,lastModifiedDateTime,importance,webUrl")
    if str(params.get('expand_replies', "false")).lower() == "true": query_api_params['$expand'] = "replies"
    channel_read_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_MESSAGE_READ_ALL', getattr(settings, 'GRAPH_SCOPE_CHANNEL_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    log_ctx = f"{action_name} (team: {team_id}, channel: {channel_id})"
    return _teams_paged_request(client, url_base, channel_read_scope, params, query_api_params, max_items_total, log_ctx)

def reply_to_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_safe = {k:v for k,v in params.items() if k != 'content'}
    logger.info("Ejecutando reply_to_message (contenido omitido): %s", log_safe); action_name = "teams_reply_to_message"
    team_id = params.get("team_id"); channel_id = params.get("channel_id"); message_id = params.get("message_id"); reply_content = params.get("content")
    if not all([team_id, channel_id, message_id, reply_content is not None]): return _handle_teams_api_error(ValueError("'team_id', 'channel_id', 'message_id', 'content' requeridos."), action_name, params)
    content_type: str = params.get("content_type", "HTML").upper()
    url = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels/{channel_id}/messages/{message_id}/replies"
    payload = {"body": {"contentType": content_type, "content": reply_content}}
    message_send_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_MESSAGE_SEND', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_obj = client.post(url, scope=message_send_scope, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "message": "Respuesta enviada."}
    except Exception as e: return _handle_teams_api_error(e, action_name, params)

def list_chats(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_chats: %s", params); action_name = "teams_list_chats"
    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}
    url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/chats"
    top_per_page: int = min(int(params.get('top_per_page', 25)), 50)
    max_items_total: Optional[int] = None
    if params.get('max_items_total') is not None:
        try: max_items_total = int(params['max_items_total'])
        except ValueError: logger.warning(f"{action_name}: 'max_items_total' inválido.")
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,topic,chatType,createdDateTime,lastUpdatedDateTime,webUrl")
    if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    if str(params.get('expand_members', "false")).lower() == "true": query_api_params['$expand'] = "members"
    chat_read_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_READ_ALL', getattr(settings, 'GRAPH_SCOPE_CHAT_READBASIC_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    return _teams_paged_request(client, url_base, chat_read_scope, params, query_api_params, max_items_total, f"{action_name} (user: {user_identifier})")

def get_chat(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_chat: %s", params); action_name = "teams_get_chat"
    chat_id: Optional[str] = params.get("chat_id")
    if not chat_id: return _handle_teams_api_error(ValueError("'chat_id' es requerido."), action_name, params)
    url = f"{settings.GRAPH_API_BASE_URL}/chats/{chat_id}"
    query_api_params: Dict[str, Any] = {'$select': params.get('select', "id,topic,chatType,createdDateTime,lastUpdatedDateTime,webUrl,members")}
    if str(params.get('expand_members', "true")).lower() == "true": query_api_params['$expand'] = "members"
    chat_rw_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_READWRITE_ALL', getattr(settings, 'GRAPH_SCOPE_CHAT_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    try:
        response_data = client.get(url, scope=chat_rw_scope, params=query_api_params if query_api_params else None)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_teams_api_error(e, action_name, params)

def create_chat(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando create_chat: %s", params); action_name = "teams_create_chat"
    chat_type: str = params.get("chat_type", "group").lower()
    members_payload: Optional[List[Dict[str, Any]]] = params.get("members")
    if not members_payload or not isinstance(members_payload, list): return _handle_teams_api_error(ValueError("'members' (lista) requerido."), action_name, params)
    if chat_type == "oneonone" and len(members_payload) != 2 : return _handle_teams_api_error(ValueError("Chat 'oneOnOne' debe tener 2 miembros."), action_name, params)
    if chat_type == "group" and len(members_payload) < 2: return _handle_teams_api_error(ValueError("Chat 'group' debe tener al menos 2 miembros."), action_name, params)
    if chat_type == "group" and not params.get("topic"): return _handle_teams_api_error(ValueError("'topic' requerido para chats grupales."), action_name, params)
    if chat_type not in ["oneonone", "group", "meeting"]: return _handle_teams_api_error(ValueError("'chat_type' debe ser 'oneOnOne', 'group', o 'meeting'."), action_name, params)
    url = f"{settings.GRAPH_API_BASE_URL}/chats"
    payload: Dict[str, Any] = {"chatType": chat_type, "members": members_payload}
    if chat_type == "group" and params.get("topic"): payload["topic"] = params["topic"]
    chat_create_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_CREATE', getattr(settings, 'GRAPH_SCOPE_CHAT_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    try:
        response_obj = client.post(url, scope=chat_create_scope, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "message": "Chat creado."}
    except Exception as e: return _handle_teams_api_error(e, action_name, params)

def send_chat_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_safe = {k:v for k,v in params.items() if k != 'content'}
    logger.info("Ejecutando send_chat_message (contenido omitido): %s", log_safe); action_name = "teams_send_chat_message"
    chat_id = params.get("chat_id"); message_content = params.get("content")
    if not chat_id or message_content is None: return _handle_teams_api_error(ValueError("'chat_id' y 'content' requeridos."), action_name, params)
    content_type: str = params.get("content_type", "HTML").upper()
    url = f"{settings.GRAPH_API_BASE_URL}/chats/{chat_id}/messages"
    payload = {"body": {"contentType": content_type, "content": message_content}}
    chat_send_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_SEND', getattr(settings, 'GRAPH_SCOPE_CHAT_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    try:
        response_obj = client.post(url, scope=chat_send_scope, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "message": "Mensaje enviado al chat."}
    except Exception as e: return _handle_teams_api_error(e, action_name, params)

def list_chat_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_chat_messages: %s", params); action_name = "teams_list_chat_messages"
    chat_id: Optional[str] = params.get("chat_id")
    if not chat_id: return _handle_teams_api_error(ValueError("'chat_id' es requerido."), action_name, params)
    url_base = f"{settings.GRAPH_API_BASE_URL}/chats/{chat_id}/messages"
    top_per_page: int = min(int(params.get('top_per_page', 25)), 50)
    max_items_total: Optional[int] = None
    if params.get('max_items_total') is not None:
        try: max_items_total = int(params['max_items_total'])
        except ValueError: logger.warning(f"{action_name}: 'max_items_total' inválido.")
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,subject,body,from,createdDateTime,lastModifiedDateTime,importance,webUrl")
    chat_rw_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_READ_ALL', getattr(settings, 'GRAPH_SCOPE_CHAT_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    log_ctx = f"{action_name} (chat: {chat_id})"
    return _teams_paged_request(client, url_base, chat_rw_scope, params, query_api_params, max_items_total, log_ctx)

def schedule_meeting(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; log_safe = {k:v for k,v in params.items() if k not in ['attendees', 'body_content']}
    logger.info("Ejecutando schedule_meeting (attendees/body omitido): %s", log_safe); action_name = "teams_schedule_meeting"
    organizer_user_id: Optional[str] = params.get("organizer_user_id")
    if not organizer_user_id: return {"status": "error", "action": action_name, "message": "'organizer_user_id' es requerido.", "http_status": 400}
    subject = params.get("subject"); start_dt_str = params.get("start_datetime"); end_dt_str = params.get("end_datetime")
    if not subject or not start_dt_str or not end_dt_str: return _handle_teams_api_error(ValueError("'subject', 'start_datetime', 'end_datetime' requeridos."), action_name, params)
    try: datetime.fromisoformat(start_dt_str.replace('Z', '+00:00')); datetime.fromisoformat(end_dt_str.replace('Z', '+00:00'))
    except ValueError as ve: return _handle_teams_api_error(ValueError(f"Formato de fecha inválido: {ve}. Usar ISO 8601."), action_name, params)
    url = f"{settings.GRAPH_API_BASE_URL}/users/{organizer_user_id}/events"
    payload: Dict[str, Any] = {"subject": subject, "start": {"dateTime": start_dt_str, "timeZone": params.get("timezone", "UTC")}, 
                               "end": {"dateTime": end_dt_str, "timeZone": params.get("timezone", "UTC")},
                               "isOnlineMeeting": True, "onlineMeetingProvider": "teamsForBusiness"}
    if params.get("attendees"): payload["attendees"] = params["attendees"]
    if params.get("body_content"): payload["body"] = {"contentType": params.get("body_type", "HTML").upper(), "content": params["body_content"]}
    if params.get("location"): payload["location"] = {"displayName": params.get("location")}
    if params.get("allowNewTimeProposals") is not None: payload["allowNewTimeProposals"] = bool(params.get("allowNewTimeProposals"))
    meeting_rw_scope = getattr(settings, 'GRAPH_SCOPE_CALENDARS_READ_WRITE', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_obj = client.post(url, scope=meeting_rw_scope, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "message": "Reunión programada."}
    except Exception as e: return _handle_teams_api_error(e, action_name, params)

def get_meeting_details(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_meeting_details: %s", params); action_name = "teams_get_meeting_details"
    owner_user_id: Optional[str] = params.get("owner_user_id")
    if not owner_user_id: return {"status": "error", "action": action_name, "message": "'owner_user_id' es requerido.", "http_status": 400}
    event_id: Optional[str] = params.get("event_id")
    if not event_id: return _handle_teams_api_error(ValueError("'event_id' es requerido."), action_name, params)
    url = f"{settings.GRAPH_API_BASE_URL}/users/{owner_user_id}/events/{event_id}"
    query_params = {'$select': params.get('select', 'id,subject,start,end,organizer,attendees,body,onlineMeeting,webLink,isOnlineMeeting,onlineMeetingProvider')}
    meeting_read_scope = getattr(settings, 'GRAPH_SCOPE_CALENDARS_READ', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
    try:
        response_data = client.get(url, scope=meeting_read_scope, params=query_params)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        if not response_data.get("isOnlineMeeting") or response_data.get("onlineMeetingProvider", "").lower() != "teamsforbusiness":
            return {"status": "warning", "data": response_data, "message": "Evento obtenido, pero no parece ser una reunión online de Teams."}
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_teams_api_error(e, action_name, params)

def list_members(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_members (Teams/Chat): %s", params); action_name = "teams_list_members"
    team_id = params.get("team_id"); chat_id = params.get("chat_id")
    if not team_id and not chat_id: return _handle_teams_api_error(ValueError("Se requiere 'team_id' o 'chat_id'."), action_name, params)
    if team_id and chat_id: return _handle_teams_api_error(ValueError("Proporcione 'team_id' O 'chat_id', no ambos."), action_name, params)
    parent_type = "equipo" if team_id else "chat"; parent_id = team_id if team_id else chat_id
    url_base: str; scope_to_use: List[str]
    if team_id:
        url_base = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/members"
        scope_to_use = getattr(settings, 'GRAPH_SCOPE_TEAM_MEMBER_READ_ALL', getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    else: # chat_id
        url_base = f"{settings.GRAPH_API_BASE_URL}/chats/{chat_id}/members" # type: ignore
        scope_to_use = getattr(settings, 'GRAPH_SCOPE_CHAT_MEMBER_READ_ALL', getattr(settings, 'GRAPH_SCOPE_CHAT_READBASIC_ALL', settings.GRAPH_API_DEFAULT_SCOPE)) # type: ignore
    top_per_page: int = min(int(params.get('top_per_page', 25)), getattr(settings, 'DEFAULT_PAGING_SIZE', 50))
    max_items_total: Optional[int] = None
    if params.get('max_items_total') is not None:
        try: max_items_total = int(params['max_items_total'])
        except ValueError: logger.warning(f"{action_name}: 'max_items_total' inválido.")
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,displayName,userId,email,roles")
    if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    log_ctx = f"{action_name} ({parent_type}: {parent_id})"
    return _teams_paged_request(client, url_base, scope_to_use, params, query_api_params, max_items_total, log_ctx)

# --- FIN DEL MÓDULO actions/teams_actions.py ---