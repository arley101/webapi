# app/actions/correo_actions.py
import logging
import requests # Para requests.exceptions.HTTPError
import json 
from typing import Dict, List, Optional, Union, Any

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

MAIL_READ_SCOPE = getattr(settings, "GRAPH_SCOPE_MAIL_READ", settings.GRAPH_API_DEFAULT_SCOPE)
MAIL_SEND_SCOPE = getattr(settings, "GRAPH_SCOPE_MAIL_SEND", settings.GRAPH_API_DEFAULT_SCOPE)
MAIL_READ_WRITE_SCOPE = getattr(settings, "GRAPH_SCOPE_MAIL_READ_WRITE", settings.GRAPH_API_DEFAULT_SCOPE)

def _handle_email_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Email action '{action_name}'"
    safe_params = {}
    if params_for_log:
        sensitive_keys = ['message', 'comment', 'attachments', 'message_payload_override', 'final_sendmail_payload', 'draft_message_payload']
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
        "message": f"Error en {action_name}: {type(e).__name__}",
        "http_status": status_code_int, "details": details_str,
        "graph_error_code": graph_error_code
    }

def _email_paged_request(
    client: AuthenticatedHttpClient, url_base: str, scope_list: List[str],
    params: Dict[str, Any], query_api_params_initial: Dict[str, Any], 
    max_items_total: Optional[int], action_name_for_log: str
) -> Dict[str, Any]:
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages_to_fetch = getattr(settings, "MAX_PAGING_PAGES", 20)
    effective_max_items = float('inf') if max_items_total is None else max_items_total
    
    logger.debug(f"Paginación Email para '{action_name_for_log}'. Max total: {max_items_total or 'todos'}")
    try:
        while current_url and len(all_items) < effective_max_items and page_count < max_pages_to_fetch:
            page_count += 1
            current_params_for_call = query_api_params_initial if page_count == 1 and current_url == url_base else None
            
            response_data = client.get(url=current_url, scope=scope_list, params=current_params_for_call)
            if not isinstance(response_data, dict):
                raise Exception(f"Respuesta paginada inesperada, se esperaba dict. Tipo: {type(response_data)}")
            if response_data.get("status") == "error" and "http_status" in response_data:
                return response_data 

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            for item in page_items:
                if len(all_items) < effective_max_items: all_items.append(item)
                else: break
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max_items: break
        return {"status": "success", "data": {"value": all_items, "@odata.count": len(all_items)}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e:
        return _handle_email_api_error(e, action_name_for_log, params)

def _normalize_recipients(rec_input: Optional[Union[str, List[str], List[Dict[str, Any]]]], type_name: str = "destinatario") -> List[Dict[str, Any]]:
    recipients_list: List[Dict[str, Any]] = []
    if rec_input is None: return recipients_list
    input_list_to_process: List[Any] = []
    if isinstance(rec_input, str):
        emails_from_string = [email.strip() for email in rec_input.replace(';', ',').split(',') if email.strip() and "@" in email]
        input_list_to_process.extend(emails_from_string)
    elif isinstance(rec_input, list):
        input_list_to_process = rec_input
    else: return []
    for item in input_list_to_process:
        if isinstance(item, str) and item.strip() and "@" in item:
            recipients_list.append({"emailAddress": {"address": item.strip()}})
        elif isinstance(item, dict) and isinstance(item.get("emailAddress"), dict) and isinstance(item["emailAddress"].get("address"), str):
            recipients_list.append(item)
    return recipients_list

def list_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_messages: %s", params); action_name = "email_list_messages"
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' es requerido.", "http_status": 400}
    folder_id: str = params.get('folder_id', 'Inbox')
    top_per_page: int = min(int(params.get('top_per_page', 25)), getattr(settings, "DEFAULT_PAGING_SIZE_MAIL", 50))
    url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/mailFolders/{folder_id}/messages"
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = params.get('select', "id,receivedDateTime,subject,sender,from,toRecipients,ccRecipients,isRead,hasAttachments,importance,webLink")
    if params.get('search'): query_api_params['$search'] = f'"{params["search"]}"'
    elif params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    if params.get('order_by') and not params.get('search'): query_api_params['$orderby'] = params['order_by']
    elif params.get('order_by') and params.get('search'): query_api_params['$orderby'] = params['order_by'] # Puede funcionar si el campo está indexado para search
    
    return _email_paged_request(client, url_base, MAIL_READ_SCOPE, params, query_api_params, params.get('max_items_total'), action_name)

def get_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando get_message: %s", params); action_name = "email_get_message"
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' es requerido.", "http_status": 400}
    message_id: Optional[str] = params.get('message_id')
    if not message_id: return {"status": "error", "action": action_name, "message": "'message_id' es requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/messages/{message_id}"
    query_api_params: Dict[str, Any] = {}
    query_api_params['$select'] = params.get('select', "id,receivedDateTime,subject,sender,from,toRecipients,ccRecipients,bccRecipients,body,bodyPreview,importance,isRead,isDraft,hasAttachments,webLink,conversationId,parentFolderId")
    if params.get('expand'): query_api_params['$expand'] = params['expand']
    try:
        response_data = client.get(url, scope=MAIL_READ_SCOPE, params=query_api_params)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_email_api_error(e, action_name, params)

def send_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando send_message: %s", params); action_name = "email_send_message"
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' (remitente) es requerido.", "http_status": 400}
    to_recipients_in = params.get('to_recipients'); subject = params.get('subject'); body_content = params.get('body_content')
    if not to_recipients_in or subject is None or body_content is None: return {"status": "error", "action": action_name, "message": "'to_recipients', 'subject', 'body_content' requeridos.", "http_status": 400}
    body_type: str = params.get('body_type', 'HTML').upper()
    if body_type not in ["HTML", "TEXT"]: return {"status": "error", "action": action_name, "message": "'body_type' debe ser HTML o TEXT.", "http_status": 400}
    to_list = _normalize_recipients(to_recipients_in, "to_recipients")
    if not to_list: return {"status": "error", "action": action_name, "message": "Destinatarios ('to_recipients') válidos requeridos.", "http_status": 400}
    message_obj: Dict[str, Any] = {"subject": subject, "body": {"contentType": body_type, "content": body_content}, "toRecipients": to_list}
    if params.get('cc_recipients'): message_obj["ccRecipients"] = _normalize_recipients(params['cc_recipients'], "cc_recipients")
    if params.get('bcc_recipients'): message_obj["bccRecipients"] = _normalize_recipients(params['bcc_recipients'], "bcc_recipients")
    if params.get('attachments') and isinstance(params['attachments'], list): message_obj["attachments"] = params['attachments']
    sendmail_payload = {"message": message_obj, "saveToSentItems": str(params.get('save_to_sent_items', "true")).lower() == "true"}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/sendMail"
    try:
        response_obj = client.post(url, scope=MAIL_SEND_SCOPE, json_data=sendmail_payload) # client.post devuelve requests.Response
        return {"status": "success", "message": "Solicitud de envío aceptada.", "http_status": response_obj.status_code}
    except Exception as e: return _handle_email_api_error(e, action_name, params)

def reply_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando reply_message: %s", params); action_name = "email_reply_message"
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' es requerido.", "http_status": 400}
    message_id = params.get('message_id')
    if not message_id: return {"status": "error", "action": action_name, "message": "'message_id' es requerido.", "http_status": 400}
    action_segment = "replyAll" if str(params.get('reply_all', "false")).lower() == "true" else "reply"
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/messages/{message_id}/{action_segment}"
    payload_reply: Dict[str, Any] = {}
    if params.get('comment') is not None: payload_reply["comment"] = params['comment']
    if params.get("message_payload_override") and isinstance(params["message_payload_override"], dict): payload_reply["message"] = params["message_payload_override"]
    try:
        response_obj = client.post(url, scope=MAIL_SEND_SCOPE, json_data=payload_reply)
        return {"status": "success", "message": f"Solicitud de respuesta ({action_segment}) aceptada.", "http_status": response_obj.status_code}
    except Exception as e: return _handle_email_api_error(e, action_name, params)

def forward_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando forward_message: %s", params); action_name = "email_forward_message"
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' es requerido.", "http_status": 400}
    message_id = params.get('message_id'); to_recipients_in = params.get('to_recipients')
    if not message_id or not to_recipients_in: return {"status": "error", "action": action_name, "message": "'message_id' y 'to_recipients' requeridos.", "http_status": 400}
    to_list = _normalize_recipients(to_recipients_in, "to_recipients (forward)")
    if not to_list: return {"status": "error", "action": action_name, "message": "Destinatarios válidos ('to_recipients') para reenvío requeridos.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/messages/{message_id}/forward"
    payload_forward: Dict[str, Any] = {"toRecipients": to_list}
    if params.get('comment') is not None: payload_forward["comment"] = params['comment']
    if params.get("message_payload_override") and isinstance(params["message_payload_override"], dict): payload_forward["message"] = params["message_payload_override"]
    try:
        response_obj = client.post(url, scope=MAIL_SEND_SCOPE, json_data=payload_forward)
        return {"status": "success", "message": "Solicitud de reenvío aceptada.", "http_status": response_obj.status_code}
    except Exception as e: return _handle_email_api_error(e, action_name, params)

def delete_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando delete_message: %s", params); action_name = "email_delete_message"
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' es requerido.", "http_status": 400}
    message_id: Optional[str] = params.get('message_id')
    if not message_id: return {"status": "error", "action": action_name, "message": "'message_id' es requerido.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/messages/{message_id}"
    try:
        response_obj = client.delete(url, scope=MAIL_READ_WRITE_SCOPE) # client.delete devuelve requests.Response
        return {"status": "success", "message": "Correo movido a elementos eliminados.", "http_status": response_obj.status_code}
    except Exception as e: return _handle_email_api_error(e, action_name, params)

def move_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando move_message: %s", params); action_name = "email_move_message"
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' es requerido.", "http_status": 400}
    message_id = params.get('message_id'); destination_folder_id = params.get('destination_folder_id')
    if not message_id or not destination_folder_id: return {"status": "error", "action": action_name, "message": "'message_id' y 'destination_folder_id' requeridos.", "http_status": 400}
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/messages/{message_id}/move"
    payload = {"destinationId": destination_folder_id}
    try:
        response_obj = client.post(url, scope=MAIL_READ_WRITE_SCOPE, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "message": "Correo movido."}
    except Exception as e: return _handle_email_api_error(e, action_name, params)

def list_folders(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando list_folders: %s", params); action_name = "email_list_folders"
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' es requerido.", "http_status": 400}
    parent_folder_id: Optional[str] = params.get('parent_folder_id')
    url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/mailFolders/{parent_folder_id}/childFolders" if parent_folder_id else f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/mailFolders"
    query_api_params: Dict[str, Any] = {'$top': min(int(params.get('top_per_page', 10)), getattr(settings, "DEFAULT_PAGING_SIZE", 25))}
    query_api_params['$select'] = params.get('select', "id,displayName,parentFolderId,childFolderCount,unreadItemCount,totalItemCount")
    if params.get('filter_query'): query_api_params['$filter'] = params['filter_query']
    log_ctx = f"{action_name} (user: {user_identifier}, parent: {parent_folder_id or 'root'})"
    return _email_paged_request(client, url_base, MAIL_READ_SCOPE, params, query_api_params, params.get('max_items_total'), log_ctx)

def create_folder(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando create_folder: %s", params); action_name = "email_create_folder"
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' es requerido.", "http_status": 400}
    folder_name: Optional[str] = params.get('folder_name')
    if not folder_name: return {"status": "error", "action": action_name, "message": "'folder_name' es requerido.", "http_status": 400}
    parent_folder_id: Optional[str] = params.get('parent_folder_id')
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/mailFolders/{parent_folder_id}/childFolders" if parent_folder_id else f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/mailFolders"
    payload = {"displayName": folder_name}
    try:
        response_obj = client.post(url, scope=MAIL_READ_WRITE_SCOPE, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "message": "Carpeta de correo creada."}
    except Exception as e: return _handle_email_api_error(e, action_name, params)

def search_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; logger.info("Ejecutando search_messages: %s", params); action_name = "email_search_messages"
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier: return {"status": "error", "action": action_name, "message": "'mailbox' es requerido.", "http_status": 400}
    search_query_kql: Optional[str] = params.get('query')
    if not search_query_kql: return {"status": "error", "action": action_name, "message": "'query' de búsqueda es requerido.", "http_status": 400}
    url_base = f"{settings.GRAPH_API_BASE_URL}/users/{user_identifier}/messages"
    query_api_params: Dict[str, Any] = {'$top': min(int(params.get('top_per_page', 25)), getattr(settings, "DEFAULT_PAGING_SIZE_MAIL", 50))}
    query_api_params['$select'] = params.get('select', "id,receivedDateTime,subject,sender,from,toRecipients,ccRecipients,isRead,hasAttachments,importance,webLink")
    query_api_params['$search'] = f'"{search_query_kql}"'
    query_api_params['$count'] = "true" 
    custom_headers = {'ConsistencyLevel': 'eventual'}
    # _email_paged_request podría necesitar adaptarse para pasar custom_headers en todas las llamadas
    # Por ahora, se asume que la primera llamada con estos params es suficiente para la búsqueda simple.
    # Para una paginación completa de $search, se requeriría un helper de paginación que maneje ConsistencyLevel.
    # Esta implementación actual solo obtendrá la primera página de resultados de la búsqueda.
    try:
        response_data = client.get(url_base, scope=MAIL_READ_SCOPE, params=query_api_params, headers=custom_headers)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        total_matching_count = response_data.get('@odata.count', len(response_data.get("value", [])))
        return {"status": "success", "data": {"value": response_data.get("value", []), "@odata.count": total_matching_count}, 
                "total_retrieved": len(response_data.get("value", [])), "pages_processed": 1} # Simula una página
    except Exception as e: return _handle_email_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/correo_actions.py ---