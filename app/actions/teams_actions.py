# app/actions/teams_actions.py
import logging
import requests # Para requests.exceptions.HTTPError
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime # Para schedule_meeting

# Importar la configuración y el cliente HTTP autenticado
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
    top_per_page = query_api_params_initial.get('$top', getattr(settings, 'DEFAULT_PAGING_SIZE', 50))
    
    effective_max_items = max_items_total if max_items_total is not None else float('inf')

    logger.debug(f"Iniciando solicitud paginada para '{action_name_for_log}' desde '{url_base.split('?')[0]}...'. Max total: {max_items_total or 'todos'}, por pág: {top_per_page}, max_págs: {max_pages_to_fetch}")
    try:
        while current_url and len(all_items) < effective_max_items and page_count < max_pages_to_fetch:
            page_count += 1
            is_first_call = (page_count == 1 and current_url == url_base)
            current_call_params = query_api_params_initial if is_first_call else None
            
            logger.debug(f"Página {page_count} para '{action_name_for_log}': GET {current_url.split('?')[0]} con params: {current_call_params}")
            response = client.get(url=current_url, scope=scope, params=current_call_params)
            response_data = response.json()
            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            
            for item in page_items:
                if len(all_items) < effective_max_items:
                    all_items.append(item)
                else:
                    break 
            
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max_items : 
                break
        
        logger.info(f"'{action_name_for_log}' recuperó {len(all_items)} items en {page_count} páginas.")
        return {"status": "success", "data": {"value": all_items, "@odata.count": len(all_items)}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e:
        return _handle_teams_api_error(e, action_name_for_log, params_input)

def list_joined_teams(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_joined_teams con params: %s", params)
    action_name = "teams_list_joined_teams"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/joinedTeams"
    
    top_per_page: int = min(int(params.get('top_per_page', 25)), getattr(settings, 'DEFAULT_PAGING_SIZE', 50))
    
    raw_max_items = params.get('max_items_total')
    max_items_total: Optional[int] = None
    if raw_max_items is not None:
        try:
            max_items_total = int(raw_max_items)
        except ValueError:
            logger.warning(f"{action_name}: 'max_items_total' ('{raw_max_items}') no es un entero válido. Se recuperarán todos los items hasta el límite de paginación.")

    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,displayName,description,isArchived,webUrl")
    if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    
    teams_read_scope = getattr(settings, 'GRAPH_SCOPE_TEAMS_READ_BASIC_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    logger.info(f"{action_name}: Listando equipos unidos para usuario '{user_identifier}'. Query: {query_api_params}, Max_items: {max_items_total or 'todos'}")
    return _teams_paged_request(client, url_base, teams_read_scope, params, query_api_params, max_items_total, action_name)

# ... (El resto de las funciones de teams_actions.py: get_team, list_channels, get_channel, 
# send_channel_message, list_channel_messages, reply_to_message, list_chats, get_chat, 
# create_chat, send_chat_message, list_chat_messages, schedule_meeting, get_meeting_details, 
# list_members permanecen idénticas a la versión que te proporcioné en la respuesta del
# Vie, 31 de May de 2024 a la(s) 12:53 PM, ya que esa versión es la que está en tu ZIP y
# ya contiene las correcciones para user_id y el helper de paginación)
# --- CONTINUACIÓN DEL CÓDIGO DE app/actions/teams_actions.py ---
# (Asegúrate de copiar el resto de las funciones desde la versión completa que te di anteriormente,
#  o la que está en tu ZIP elitedynamicsapi_DEPLOY_CLEAN.zip/app/actions/teams_actions.py
#  ya que es extenso y el contenido del ZIP es el que considero base ahora)

def get_team(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_team con params: %s", params)
    action_name = "teams_get_team"
    
    team_id: Optional[str] = params.get("team_id")
    if not team_id:
        return _handle_teams_api_error(ValueError("'team_id' es requerido."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}"
    query_params = {'$select': params['select']} if params.get("select") else None
    
    logger.info(f"Obteniendo detalles del equipo '{team_id}'")
    teams_read_scope = getattr(settings, 'GRAPH_SCOPE_TEAMS_READ_BASIC_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.get(url, scope=teams_read_scope, params=query_params)
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def list_channels(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_channels con params: %s", params)
    action_name = "teams_list_channels"
    
    team_id: Optional[str] = params.get("team_id")
    if not team_id:
        return _handle_teams_api_error(ValueError("'team_id' es requerido."), action_name, params)
        
    url_base = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels"
    top_per_page: int = min(int(params.get('top_per_page', 25)), getattr(settings, 'DEFAULT_PAGING_SIZE', 50))
    
    raw_max_items = params.get('max_items_total')
    max_items_total: Optional[int] = None
    if raw_max_items is not None:
        try:
            max_items_total = int(raw_max_items)
        except ValueError:
            logger.warning(f"{action_name}: 'max_items_total' ('{raw_max_items}') no es un entero válido. Se recuperarán todos los items hasta el límite de paginación.")

    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,displayName,description,webUrl,email,membershipType")
    if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    
    channel_read_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_READ_ALL', 
                                 getattr(settings, 'GRAPH_SCOPE_TEAMS_READ_BASIC_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
    logger.info(f"{action_name}: Listando canales para equipo '{team_id}'. Query: {query_api_params}, Max_items: {max_items_total or 'todos'}")
    return _teams_paged_request(client, url_base, channel_read_scope, params, query_api_params, max_items_total, f"{action_name} (team: {team_id})")

def get_channel(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_channel con params: %s", params)
    action_name = "teams_get_channel"

    team_id: Optional[str] = params.get("team_id")
    channel_id: Optional[str] = params.get("channel_id")
    if not team_id or not channel_id:
        return _handle_teams_api_error(ValueError("'team_id' y 'channel_id' requeridos."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels/{channel_id}"
    query_params = {'$select': params['select']} if params.get("select") else None
    
    logger.info(f"Obteniendo detalles del canal '{channel_id}' en equipo '{team_id}'")
    channel_read_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.get(url, scope=channel_read_scope, params=query_params)
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def send_channel_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando send_channel_message con params (omitiendo contenido): %s", {k:v for k,v in params.items() if k != 'content'})
    action_name = "teams_send_channel_message"

    team_id: Optional[str] = params.get("team_id")
    channel_id: Optional[str] = params.get("channel_id")
    message_content: Optional[str] = params.get("content")
    content_type: str = params.get("content_type", "HTML").upper()
    
    if not team_id or not channel_id or message_content is None:
        return _handle_teams_api_error(ValueError("'team_id', 'channel_id', 'content' requeridos."), action_name, params)
    if content_type not in ["HTML", "TEXT"]:
        return _handle_teams_api_error(ValueError("'content_type' debe ser HTML o TEXT."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels/{channel_id}/messages"
    payload = {"body": {"contentType": content_type, "content": message_content}}
    if params.get("subject"): payload["subject"] = params["subject"]
    
    logger.info(f"Enviando mensaje al canal '{channel_id}' del equipo '{team_id}'")
    message_send_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_MESSAGE_SEND', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.post(url, scope=message_send_scope, json_data=payload)
        return {"status": "success", "data": response.json(), "message": "Mensaje enviado al canal."}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def list_channel_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_channel_messages con params: %s", params)
    action_name = "teams_list_channel_messages"

    team_id: Optional[str] = params.get("team_id")
    channel_id: Optional[str] = params.get("channel_id")
    if not team_id or not channel_id:
        return _handle_teams_api_error(ValueError("'team_id' y 'channel_id' requeridos."), action_name, params)
        
    url_base = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels/{channel_id}/messages"
    top_per_page: int = min(int(params.get('top_per_page', 25)), 50)
    
    raw_max_items = params.get('max_items_total')
    max_items_total: Optional[int] = None
    if raw_max_items is not None:
        try:
            max_items_total = int(raw_max_items)
        except ValueError:
            logger.warning(f"{action_name}: 'max_items_total' ('{raw_max_items}') no es un entero válido. Se recuperarán todos los items hasta el límite de paginación.")
    
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,subject,summary,body,from,createdDateTime,lastModifiedDateTime,importance,webUrl")
    if str(params.get('expand_replies', "false")).lower() == "true": query_api_params['$expand'] = "replies"
    
    channel_read_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_MESSAGE_READ_ALL', 
                                 getattr(settings, 'GRAPH_SCOPE_CHANNEL_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
    log_context_detail = f"{action_name} (team: {team_id}, channel: {channel_id})"
    logger.info(f"{log_context_detail}. Query: {query_api_params}, Max_items: {max_items_total or 'todos'}")
    return _teams_paged_request(client, url_base, channel_read_scope, params, query_api_params, max_items_total, log_context_detail)

def reply_to_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando reply_to_message con params (omitiendo contenido): %s", {k:v for k,v in params.items() if k != 'content'})
    action_name = "teams_reply_to_message"

    team_id: Optional[str] = params.get("team_id")
    channel_id: Optional[str] = params.get("channel_id")
    message_id: Optional[str] = params.get("message_id")
    reply_content: Optional[str] = params.get("content")
    content_type: str = params.get("content_type", "HTML").upper()
    
    if not team_id or not channel_id or not message_id or reply_content is None:
        return _handle_teams_api_error(ValueError("'team_id', 'channel_id', 'message_id', 'content' requeridos."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/teams/{team_id}/channels/{channel_id}/messages/{message_id}/replies"
    payload = {"body": {"contentType": content_type, "content": reply_content}}
    
    logger.info(f"Enviando respuesta al mensaje '{message_id}' en canal '{channel_id}', equipo '{team_id}'")
    message_send_scope = getattr(settings, 'GRAPH_SCOPE_CHANNEL_MESSAGE_SEND', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.post(url, scope=message_send_scope, json_data=payload)
        return {"status": "success", "data": response.json(), "message": "Respuesta enviada."}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def list_chats(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_chats con params: %s", params)
    action_name = "teams_list_chats"

    user_identifier: Optional[str] = params.get("user_id")
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'user_id' es requerido.", "http_status": 400}

    url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/chats"
    
    top_per_page: int = min(int(params.get('top_per_page', 25)), 50)
    
    raw_max_items = params.get('max_items_total')
    max_items_total: Optional[int] = None
    if raw_max_items is not None:
        try:
            max_items_total = int(raw_max_items)
        except ValueError:
            logger.warning(f"{action_name}: 'max_items_total' ('{raw_max_items}') no es un entero válido. Se recuperarán todos los items hasta el límite de paginación.")

    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,topic,chatType,createdDateTime,lastUpdatedDateTime,webUrl")
    if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    if str(params.get('expand_members', "false")).lower() == "true": query_api_params['$expand'] = "members"
    
    chat_read_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_READ_ALL', 
                              getattr(settings, 'GRAPH_SCOPE_CHAT_READBASIC_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
    logger.info(f"{action_name}: Listando chats para usuario '{user_identifier}'. Query: {query_api_params}, Max_items: {max_items_total or 'todos'}")
    return _teams_paged_request(client, url_base, chat_read_scope, params, query_api_params, max_items_total, f"{action_name} (user: {user_identifier})")

def get_chat(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_chat con params: %s", params)
    action_name = "teams_get_chat"

    chat_id: Optional[str] = params.get("chat_id")
    if not chat_id:
        return _handle_teams_api_error(ValueError("'chat_id' es requerido."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/chats/{chat_id}"
    
    query_api_params: Dict[str, Any] = {}
    query_api_params['$select'] = params.get('select', "id,topic,chatType,createdDateTime,lastUpdatedDateTime,webUrl,members")
    
    expand_members_str = str(params.get('expand_members', "true")).lower() 
    if expand_members_str == "true":
        query_api_params['$expand'] = "members"

    logger.info(f"Obteniendo detalles del chat '{chat_id}'")
    chat_rw_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_READWRITE_ALL', getattr(settings, 'GRAPH_SCOPE_CHAT_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
    try:
        response = client.get(url, scope=chat_rw_scope, params=query_api_params if query_api_params else None)
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def create_chat(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando create_chat con params: %s", params)
    action_name = "teams_create_chat"

    chat_type: str = params.get("chat_type", "group").lower()
    members_payload: Optional[List[Dict[str, Any]]] = params.get("members")
    topic: Optional[str] = params.get("topic")

    if not members_payload or not isinstance(members_payload, list):
        return _handle_teams_api_error(ValueError("'members' (lista de objetos de miembro) requerido."), action_name, params)
    
    if chat_type == "oneonone" and len(members_payload) != 2 :
         return _handle_teams_api_error(ValueError(f"Para chat 'oneOnOne', 'members' debe tener exactamente 2 miembros (incluyendo el user@odata.bind)."), action_name, params)
    elif chat_type == "group" and len(members_payload) < 2:
         return _handle_teams_api_error(ValueError(f"Para chat 'group', 'members' debe tener al menos 2 miembros."), action_name, params)

    if chat_type == "group" and not topic:
        return _handle_teams_api_error(ValueError("'topic' es requerido para chats grupales."), action_name, params)
    if chat_type not in ["oneonone", "group", "meeting"]:
        return _handle_teams_api_error(ValueError("'chat_type' debe ser 'oneOnOne', 'group', o 'meeting'."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/chats"
    payload: Dict[str, Any] = {"chatType": chat_type, "members": members_payload}
    if chat_type == "group" and topic: payload["topic"] = topic
    
    logger.info(f"Creando chat tipo '{chat_type}'" + (f" con tópico '{topic}'" if topic else ""))
    chat_create_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_CREATE', getattr(settings, 'GRAPH_SCOPE_CHAT_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
    try:
        response = client.post(url, scope=chat_create_scope, json_data=payload)
        return {"status": "success", "data": response.json(), "message": "Chat creado."}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def send_chat_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando send_chat_message con params (omitiendo contenido): %s", {k:v for k,v in params.items() if k != 'content'})
    action_name = "teams_send_chat_message"

    chat_id: Optional[str] = params.get("chat_id")
    message_content: Optional[str] = params.get("content")
    content_type: str = params.get("content_type", "HTML").upper()
    
    if not chat_id or message_content is None:
        return _handle_teams_api_error(ValueError("'chat_id' y 'content' son requeridos."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/chats/{chat_id}/messages"
    payload = {"body": {"contentType": content_type, "content": message_content}}
    
    logger.info(f"Enviando mensaje al chat '{chat_id}'")
    chat_send_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_SEND', getattr(settings, 'GRAPH_SCOPE_CHAT_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
    try:
        response = client.post(url, scope=chat_send_scope, json_data=payload)
        return {"status": "success", "data": response.json(), "message": "Mensaje enviado al chat."}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def list_chat_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_chat_messages con params: %s", params)
    action_name = "teams_list_chat_messages"

    chat_id: Optional[str] = params.get("chat_id")
    if not chat_id:
        return _handle_teams_api_error(ValueError("'chat_id' es requerido."), action_name, params)
        
    url_base = f"{settings.GRAPH_API_BASE_URL}/chats/{chat_id}/messages"
    top_per_page: int = min(int(params.get('top_per_page', 25)), 50)
    
    raw_max_items = params.get('max_items_total')
    max_items_total: Optional[int] = None
    if raw_max_items is not None:
        try:
            max_items_total = int(raw_max_items)
        except ValueError:
            logger.warning(f"{action_name}: 'max_items_total' ('{raw_max_items}') no es un entero válido. Se recuperarán todos los items hasta el límite de paginación.")

    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,subject,body,from,createdDateTime,lastModifiedDateTime,importance,webUrl")
    
    chat_rw_scope = getattr(settings, 'GRAPH_SCOPE_CHAT_READ_ALL', getattr(settings, 'GRAPH_SCOPE_CHAT_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
    log_context_detail = f"{action_name} (chat: {chat_id})"
    logger.info(f"{log_context_detail}. Query: {query_api_params}, Max_items: {max_items_total or 'todos'}")
    return _teams_paged_request(client, url_base, chat_rw_scope, params, query_api_params, max_items_total, log_context_detail)

def schedule_meeting(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando schedule_meeting con params (omitiendo attendees/body): %s", {k:v for k,v in params.items() if k not in ['attendees', 'body_content']})
    action_name = "teams_schedule_meeting"

    user_identifier_organizer: Optional[str] = params.get("organizer_user_id")
    if not user_identifier_organizer:
        logger.error(f"{action_name}: El parámetro 'organizer_user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'organizer_user_id' es requerido.", "http_status": 400}

    subject: Optional[str] = params.get("subject")
    start_datetime_str: Optional[str] = params.get("start_datetime")
    end_datetime_str: Optional[str] = params.get("end_datetime")
    timezone: Optional[str] = params.get("timezone", "UTC") 
    attendees_payload: Optional[List[Dict[str, Any]]] = params.get("attendees")
    body_content: Optional[str] = params.get("body_content")
    body_type: str = params.get("body_type", "HTML").upper()
    
    if not subject or not start_datetime_str or not end_datetime_str:
        return _handle_teams_api_error(ValueError("'subject', 'start_datetime', 'end_datetime' requeridos."), action_name, params)
        
    try:
        datetime.fromisoformat(start_datetime_str.replace('Z', '+00:00'))
        datetime.fromisoformat(end_datetime_str.replace('Z', '+00:00'))
    except ValueError as ve:
        return _handle_teams_api_error(ValueError(f"Formato de fecha inválido: {ve}. Usar ISO 8601 (ej: YYYY-MM-DDTHH:MM:SSZ)"), action_name, params)

    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier_organizer}/events"
    
    payload = {
        "subject": subject,
        "start": {"dateTime": start_datetime_str, "timeZone": timezone},
        "end": {"dateTime": end_datetime_str, "timeZone": timezone},
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness"
    }
    if attendees_payload and isinstance(attendees_payload, list): payload["attendees"] = attendees_payload
    if body_content: payload["body"] = {"contentType": body_type, "content": body_content}
    if params.get("location"): payload["location"] = {"displayName": params.get("location")}
    if params.get("allowNewTimeProposals") is not None: payload["allowNewTimeProposals"] = bool(params.get("allowNewTimeProposals"))
    
    logger.info(f"Programando reunión de Teams para organizador '{user_identifier_organizer}': '{subject}'")
    meeting_rw_scope = getattr(settings, 'GRAPH_SCOPE_CALENDARS_READ_WRITE', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.post(url, scope=meeting_rw_scope, json_data=payload)
        return {"status": "success", "data": response.json(), "message": "Reunión programada."}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def get_meeting_details(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_meeting_details con params: %s", params)
    action_name = "teams_get_meeting_details"

    user_identifier_owner: Optional[str] = params.get("owner_user_id")
    if not user_identifier_owner:
        logger.error(f"{action_name}: El parámetro 'owner_user_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'owner_user_id' es requerido.", "http_status": 400}
        
    event_id: Optional[str] = params.get("event_id")
    if not event_id:
        return _handle_teams_api_error(ValueError("'event_id' es requerido."), action_name, params)
        
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier_owner}/events/{event_id}"
    query_params = {'$select': params.get('select', 'id,subject,start,end,organizer,attendees,body,onlineMeeting,webLink,isOnlineMeeting,onlineMeetingProvider')}
    
    logger.info(f"Obteniendo detalles de reunión (evento) '{event_id}' del calendario de '{user_identifier_owner}'")
    meeting_read_scope = getattr(settings, 'GRAPH_SCOPE_CALENDARS_READ', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.get(url, scope=meeting_read_scope, params=query_params)
        event_data = response.json()
        if not event_data.get("isOnlineMeeting") or event_data.get("onlineMeetingProvider", "").lower() != "teamsforbusiness":
            return {"status": "warning", "data": event_data, "message": "Evento obtenido, pero no parece ser una reunión online de Teams válida."}
        return {"status": "success", "data": event_data}
    except Exception as e:
        return _handle_teams_api_error(e, action_name, params)

def list_members(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_members (Teams/Chat) con params: %s", params)
    action_name = "teams_list_members"

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
        scope_to_use = getattr(settings, 'GRAPH_SCOPE_TEAM_MEMBER_READ_ALL', 
                               getattr(settings, 'GRAPH_SCOPE_GROUP_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
    else: # chat_id
        url_base = f"{settings.GRAPH_API_BASE_URL}/chats/{chat_id}/members"
        scope_to_use = getattr(settings, 'GRAPH_SCOPE_CHAT_MEMBER_READ_ALL', 
                               getattr(settings, 'GRAPH_SCOPE_CHAT_READBASIC_ALL', settings.GRAPH_API_DEFAULT_SCOPE))
                                
    top_per_page: int = min(int(params.get('top_per_page', 25)), getattr(settings, 'DEFAULT_PAGING_SIZE', 50))
    
    raw_max_items = params.get('max_items_total')
    max_items_total: Optional[int] = None
    if raw_max_items is not None:
        try:
            max_items_total = int(raw_max_items)
        except ValueError:
            logger.warning(f"{action_name}: 'max_items_total' ('{raw_max_items}') no es un entero válido. Se recuperarán todos los items hasta el límite de paginación.")

    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,displayName,userId,email,roles")
    if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    
    log_context_detail = f"{action_name} ({parent_type}: {parent_id})"
    logger.info(f"{log_context_detail}. Query: {query_api_params}, Max_items: {max_items_total or 'todos'}")
    return _teams_paged_request(client, url_base, scope_to_use, params, query_api_params, max_items_total, log_context_detail)

# --- FIN DEL MÓDULO actions/teams_actions.py ---