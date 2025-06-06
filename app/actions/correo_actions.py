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
    top_per_page = query_api_params_initial.get('$top', getattr(settings, "DEFAULT_PAGING_SIZE_MAIL", 25))
    effective_max_items = float('inf') if max_items_total is None else max_items_total


    logger.debug(f"Iniciando solicitud paginada para '{action_name_for_log}' desde '{url_base.split('?')[0]}...'. Max total: {max_items_total or 'todos'}, por pág: {top_per_page}, max_págs: {max_pages_to_fetch}")
    try:
        while current_url and len(all_items) < effective_max_items and page_count < max_pages_to_fetch:
            page_count += 1
            is_first_call = (current_url == url_base and page_count == 1)
            current_params_for_call = query_api_params_initial if is_first_call else None
            logger.debug(f"Página {page_count} para '{action_name_for_log}': GET {current_url.split('?')[0]} con params: {current_params_for_call}")
            
            response_data = client.get(url=current_url, scope=scope_list, params=current_params_for_call)
            
            if not isinstance(response_data, dict): # Si no es dict, es un error o tipo inesperado
                logger.error(f"{action_name_for_log}: Paginación falló, client.get devolvió tipo {type(response_data)}")
                # params es el original de la acción llamante
                return _handle_email_api_error(Exception(f"Respuesta inesperada tipo {type(response_data)} durante paginación."), action_name_for_log, params)

            if response_data.get("status") == "error" and "http_status" in response_data: # Error del http_client
                 response_data["action"] = action_name_for_log
                 return response_data

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            for item in page_items:
                if len(all_items) < effective_max_items: all_items.append(item)
                else: break
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max_items: break
        
        total_matching = response_data.get('@odata.count', len(all_items)) if isinstance(response_data, dict) else len(all_items)

        logger.info(f"'{action_name_for_log}' recuperó {len(all_items)} items (de {total_matching} total si disponible) en {page_count} páginas.")
        return {"status": "success", "data": {"value": all_items, "@odata.count": total_matching}, "total_retrieved": len(all_items), "pages_processed": page_count}
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
    else:
        logger.warning(f"Entrada para '{type_name}' inválida (tipo {type(rec_input)}), se esperaba str o List. Se ignorará.")
        return []
    for item in input_list_to_process:
        if isinstance(item, str) and item.strip() and "@" in item:
            recipients_list.append({"emailAddress": {"address": item.strip()}})
        elif isinstance(item, dict) and isinstance(item.get("emailAddress"), dict) and isinstance(item["emailAddress"].get("address"), str) and item["emailAddress"]["address"].strip() and "@" in item["emailAddress"]["address"]:
            recipients_list.append(item)
        else:
            logger.warning(f"Item '{item}' en lista de '{type_name}' no es email válido o formato Graph esperado. Se ignorará.")
    if not recipients_list and rec_input:
        logger.warning(f"Entrada '{rec_input}' para '{type_name}' no resultó en destinatarios válidos.")
    return recipients_list

def list_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "email_list_messages"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    folder_id: str = params.get('folder_id', 'Inbox')
    top_per_page: int = min(int(params.get('top_per_page', 25)), getattr(settings, "DEFAULT_PAGING_SIZE_MAIL", 50))
    max_items_total: Optional[int] = params.get('max_items_total')
    select_fields: Optional[str] = params.get('select')
    filter_query: Optional[str] = params.get('filter_query')
    order_by: Optional[str] = params.get('order_by', 'receivedDateTime desc')
    search_query: Optional[str] = params.get('search')

    user_path = f"users/{user_identifier}"
    url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path}/mailFolders/{folder_id}/messages"
    
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = select_fields or "id,receivedDateTime,subject,sender,from,toRecipients,ccRecipients,isRead,hasAttachments,importance,webLink"
    
    if search_query:
        query_api_params['$search'] = f'"{search_query}"'
        query_api_params['$count'] = "true" # $count es bueno con $search
    elif filter_query:
        query_api_params['$filter'] = filter_query
    if order_by: query_api_params['$orderby'] = order_by # order_by puede ser usado con/sin search/filter
    
    logger.info(f"{action_name}: Listando mensajes para usuario '{user_identifier}', carpeta '{folder_id}'. Query: {query_api_params}")
    # _email_paged_request maneja la excepción y los params originales para el log de error
    return _email_paged_request(client, url_base, MAIL_READ_SCOPE, params, query_api_params, max_items_total, action_name)

def get_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "email_get_message"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    message_id: Optional[str] = params.get('message_id')
    if not message_id:
        return {"status": "error", "action": action_name, "message": "'message_id' es requerido.", "http_status": 400}
        
    select_fields: Optional[str] = params.get('select')
    expand_fields: Optional[str] = params.get('expand')

    user_path = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/messages/{message_id}"
    
    query_api_params: Dict[str, Any] = {}
    query_api_params['$select'] = select_fields or "id,receivedDateTime,subject,sender,from,toRecipients,ccRecipients,bccRecipients,body,bodyPreview,importance,isRead,isDraft,hasAttachments,webLink,conversationId,parentFolderId"
    if expand_fields: query_api_params['$expand'] = expand_fields
    
    logger.info(f"{action_name}: Leyendo correo '{message_id}' para usuario '{user_identifier}'")
    try:
        response_data = client.get(url, scope=MAIL_READ_SCOPE, params=query_api_params)
        if isinstance(response_data, dict):
            if response_data.get("status") == "error" and "http_status" in response_data:
                response_data["action"] = action_name
                return response_data
            return {"status": "success", "data": response_data}
        else:
            logger.error(f"{action_name}: Respuesta inesperada de client.get (no dict): {type(response_data)}")
            return _handle_email_api_error(Exception(f"Tipo de respuesta inesperado del cliente HTTP: {type(response_data)}"), action_name, params)
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

def send_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "email_send_message"
    # Omitir el contenido del mensaje y adjuntos del log principal
    log_params = {k:v for k,v in params.items() if k not in ['body_content', 'attachments']}
    if 'body_content' in params: log_params['body_content_provided'] = True
    if 'attachments' in params: log_params['attachments_count'] = len(params['attachments']) if isinstance(params.get('attachments'),list) else 0
    logger.info(f"Ejecutando {action_name} con params: {log_params}")
    
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN del remitente) es requerido.", "http_status": 400}

    to_recipients_in = params.get('to_recipients')
    subject: Optional[str] = params.get('subject')
    body_content: Optional[str] = params.get('body_content')
    body_type: str = params.get('body_type', 'HTML').upper()
    cc_recipients_in = params.get('cc_recipients')
    bcc_recipients_in = params.get('bcc_recipients')
    attachments_payload: Optional[List[dict]] = params.get('attachments')
    save_to_sent_items: bool = str(params.get('save_to_sent_items', "true")).lower() == "true"

    if not to_recipients_in or subject is None or body_content is None:
        return {"status": "error", "action": action_name, "message": "'to_recipients', 'subject', y 'body_content' son requeridos.", "http_status": 400}
    if body_type not in ["HTML", "TEXT"]:
        return {"status": "error", "action": action_name, "message": "'body_type' debe ser HTML o TEXT.", "http_status": 400}

    to_list = _normalize_recipients(to_recipients_in, "to_recipients")
    if not to_list:
        return {"status": "error", "action": action_name, "message": "Se requiere al menos un destinatario válido en 'to_recipients'.", "http_status": 400}
    
    message_obj: Dict[str, Any] = {
        "subject": subject,
        "body": {"contentType": body_type, "content": body_content},
        "toRecipients": to_list
    }
    if cc_recipients_in: message_obj["ccRecipients"] = _normalize_recipients(cc_recipients_in, "cc_recipients")
    if bcc_recipients_in: message_obj["bccRecipients"] = _normalize_recipients(bcc_recipients_in, "bcc_recipients")
    if attachments_payload and isinstance(attachments_payload, list): message_obj["attachments"] = attachments_payload
    
    sendmail_payload = {"message": message_obj, "saveToSentItems": save_to_sent_items}
    
    user_path = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/sendMail"
    
    logger.info(f"{action_name}: Enviando correo desde '{user_identifier}'. Asunto: '{subject}'")
    try:
        # client.post devuelve un objeto requests.Response
        response_obj = client.post(url, scope=MAIL_SEND_SCOPE, json_data=sendmail_payload)
        # sendMail devuelve 202 Accepted
        # El cuerpo de la respuesta de un 202 es usualmente vacío.
        if response_obj.status_code == 202:
            return {"status": "success", "message": "Solicitud de envío de correo aceptada.", "http_status": response_obj.status_code, "data": None}
        else: # Respuesta inesperada
            logger.warning(f"Respuesta inesperada {response_obj.status_code} al enviar correo: {response_obj.text[:200]}")
            response_obj.raise_for_status()
            return {} # No debería llegar aquí
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

# ... (Aplicar el mismo patrón de revisión para client.post/patch/delete en las demás funciones:
# reply_message, forward_message, delete_message, move_message, create_folder, search_messages)
# Asegurarse que el `response_obj` se maneje correctamente y no se asuma .json() si el status code indica
# que no habrá cuerpo (ej. 204 No Content) o si el cuerpo no es JSON.

# Ejemplo para delete_message:
def delete_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "email_delete_message"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    message_id: Optional[str] = params.get('message_id')
    if not message_id:
        return {"status": "error", "action": action_name, "message": "'message_id' es requerido.", "http_status": 400}
        
    user_path = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/messages/{message_id}"
    
    logger.info(f"{action_name}: Eliminando correo '{message_id}' para usuario '{user_identifier}'")
    try:
        response_obj = client.delete(url, scope=MAIL_READ_WRITE_SCOPE)
        # DELETE devuelve 204 No Content
        if response_obj.status_code == 204:
            return {"status": "success", "message": "Correo movido a elementos eliminados.", "http_status": response_obj.status_code}
        else:
            logger.warning(f"Respuesta inesperada {response_obj.status_code} al eliminar correo: {response_obj.text[:200]}")
            response_obj.raise_for_status()
            return {}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

# (El resto de las funciones de correo_actions.py deben ser revisadas con este patrón)
# Por brevedad, no las repito todas aquí, pero el principio es el mismo.

# --- COMPLETANDO EL RESTO DE FUNCIONES DE correo_actions.py CON EL PATRÓN ---

def reply_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "email_reply_message"
    log_params = {k:v for k,v in params.items() if k not in ['comment', 'message_payload_override']}
    logger.info(f"Ejecutando {action_name} con params: {log_params}")
    
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        return _handle_email_api_error(ValueError("'mailbox' (user_id o UPN) es requerido."), action_name, params)

    message_id: Optional[str] = params.get('message_id')
    comment_content: Optional[str] = params.get('comment') 
    reply_all: bool = str(params.get('reply_all', "false")).lower() == "true"
    message_payload_override: Optional[Dict[str, Any]] = params.get("message_payload_override")

    if not message_id:
        return _handle_email_api_error(ValueError("'message_id' es requerido."), action_name, params)

    action_segment = "replyAll" if reply_all else "reply"
    user_path = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/messages/{message_id}/{action_segment}"
    
    payload_reply: Dict[str, Any] = {}
    if comment_content is not None: payload_reply["comment"] = comment_content
    if message_payload_override and isinstance(message_payload_override, dict):
        payload_reply["message"] = message_payload_override
    
    log_operation = "Respondiendo a todos" if reply_all else "Respondiendo"
    logger.info(f"{action_name}: {log_operation} al correo '{message_id}' para usuario '{user_identifier}'")
    try:
        response_obj = client.post(url, scope=MAIL_SEND_SCOPE, json_data=payload_reply)
        if response_obj.status_code == 202: # Accepted
            return {"status": "success", "message": f"Solicitud de {log_operation.lower()} aceptada.", "http_status": response_obj.status_code, "data": None}
        else:
            logger.warning(f"Respuesta inesperada {response_obj.status_code} al {log_operation.lower()}: {response_obj.text[:200]}")
            response_obj.raise_for_status()
            return {}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

def forward_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "email_forward_message"
    log_params = {k:v for k,v in params.items() if k not in ['comment', 'message_payload_override']}
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        return _handle_email_api_error(ValueError("'mailbox' (user_id o UPN) es requerido."), action_name, params)
        
    message_id: Optional[str] = params.get('message_id')
    to_recipients_in = params.get('to_recipients')
    comment_content: Optional[str] = params.get('comment')
    message_payload_override: Optional[Dict[str, Any]] = params.get("message_payload_override")

    if not message_id or not to_recipients_in:
        return _handle_email_api_error(ValueError("'message_id' y 'to_recipients' son requeridos."), action_name, params)
    
    to_list = _normalize_recipients(to_recipients_in, "to_recipients (forward)")
    if not to_list:
        return _handle_email_api_error(ValueError("Se requiere al menos un destinatario válido en 'to_recipients' para reenviar."), action_name, params)

    user_path = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/messages/{message_id}/forward"
    
    payload_forward: Dict[str, Any] = {"toRecipients": to_list}
    if comment_content is not None: payload_forward["comment"] = comment_content
    if message_payload_override and isinstance(message_payload_override, dict):
        payload_forward["message"] = message_payload_override

    logger.info(f"{action_name}: Reenviando correo '{message_id}' para usuario '{user_identifier}'")
    try:
        response_obj = client.post(url, scope=MAIL_SEND_SCOPE, json_data=payload_forward)
        if response_obj.status_code == 202: # Accepted
            return {"status": "success", "message": "Solicitud de reenvío aceptada.", "http_status": response_obj.status_code, "data": None}
        else:
            logger.warning(f"Respuesta inesperada {response_obj.status_code} al reenviar: {response_obj.text[:200]}")
            response_obj.raise_for_status()
            return {}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

def move_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "email_move_message"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        return _handle_email_api_error(ValueError("'mailbox' (user_id o UPN) es requerido."), action_name, params)

    message_id: Optional[str] = params.get('message_id')
    destination_folder_id: Optional[str] = params.get('destination_folder_id')
    if not message_id or not destination_folder_id:
        return _handle_email_api_error(ValueError("'message_id' y 'destination_folder_id' son requeridos."), action_name, params)
        
    user_path = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/messages/{message_id}/move"
    payload = {"destinationId": destination_folder_id}
    
    logger.info(f"{action_name}: Moviendo correo '{message_id}' para usuario '{user_identifier}' a carpeta '{destination_folder_id}'")
    try:
        response_data = client.post(url, scope=MAIL_READ_WRITE_SCOPE, json_data=payload) # client.post devuelve un objeto Response
        # move devuelve el mensaje movido (201 Created o 200 OK) con el cuerpo del mensaje.
        # Aquí asumimos que http_client.post devolvió el cuerpo procesado (dict)
        if isinstance(response_data, dict):
            if response_data.get("status") == "error" and "http_status" in response_data:
                response_data["action"] = action_name
                return response_data
            return {"status": "success", "data": response_data, "message": "Correo movido."}
        else:
            logger.error(f"{action_name}: Respuesta inesperada de client.post (no dict): {type(response_data)}")
            return _handle_email_api_error(Exception(f"Tipo de respuesta inesperado del cliente HTTP: {type(response_data)}"), action_name, params)
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

def list_folders(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "email_list_folders"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        return _handle_email_api_error(ValueError("'mailbox' (user_id o UPN) es requerido."), action_name, params)
        
    parent_folder_id: Optional[str] = params.get('parent_folder_id')
    top_per_page: int = min(int(params.get('top_per_page', 10)), getattr(settings, "DEFAULT_PAGING_SIZE", 25))
    max_items_total: Optional[int] = params.get('max_items_total')
    select_fields: Optional[str] = params.get('select')
    filter_query: Optional[str] = params.get('filter_query')

    user_path = f"users/{user_identifier}"
    if parent_folder_id:
        url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path}/mailFolders/{parent_folder_id}/childFolders"
    else:
        url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path}/mailFolders"
        
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = select_fields or "id,displayName,parentFolderId,childFolderCount,unreadItemCount,totalItemCount"
    if filter_query: query_api_params['$filter'] = filter_query
    
    log_ctx = f"carpetas para usuario '{user_identifier}'" + (f" bajo '{parent_folder_id}'" if parent_folder_id else " (raíz)")
    logger.info(f"{action_name}: Listando {log_ctx}")
    return _email_paged_request(client, url_base, MAIL_READ_SCOPE, params, query_api_params, max_items_total, f"{action_name} ({log_ctx})")

def create_folder(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "email_create_folder"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        return _handle_email_api_error(ValueError("'mailbox' (user_id o UPN) es requerido."), action_name, params)
        
    folder_name: Optional[str] = params.get('folder_name')
    if not folder_name:
        return _handle_email_api_error(ValueError("'folder_name' es requerido."), action_name, params)
        
    parent_folder_id: Optional[str] = params.get('parent_folder_id')
    
    payload = {"displayName": folder_name}
    
    user_path = f"users/{user_identifier}"
    url: str
    if parent_folder_id:
        url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/mailFolders/{parent_folder_id}/childFolders"
    else:
        url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/mailFolders"
        
    log_ctx = f"carpeta de correo '{folder_name}' para usuario '{user_identifier}'" + (f" bajo '{parent_folder_id}'" if parent_folder_id else " (raíz)")
    logger.info(f"{action_name}: Creando {log_ctx}")
    try:
        response_data = client.post(url, scope=MAIL_READ_WRITE_SCOPE, json_data=payload) # client.post devuelve un objeto Response
        if isinstance(response_data, dict):
            if response_data.get("status") == "error" and "http_status" in response_data:
                response_data["action"] = action_name
                return response_data
            return {"status": "success", "data": response_data, "message": "Carpeta de correo creada."}
        else:
            logger.error(f"{action_name}: Respuesta inesperada de client.post (no dict): {type(response_data)}")
            return _handle_email_api_error(Exception(f"Tipo de respuesta inesperado del cliente HTTP: {type(response_data)}"), action_name, params)
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

def search_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "email_search_messages"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        return _handle_email_api_error(ValueError("'mailbox' (user_id o UPN) es requerido."), action_name, params)

    search_query_kql: Optional[str] = params.get('query')
    if not search_query_kql:
        return _handle_email_api_error(ValueError("'query' de búsqueda es requerido."), action_name, params)
    
    top_per_page: int = min(int(params.get('top_per_page', 25)), getattr(settings, "DEFAULT_PAGING_SIZE_MAIL", 50))
    max_items_total: Optional[int] = params.get('max_items_total')
    select_fields: Optional[str] = params.get('select')

    user_path = f"users/{user_identifier}"
    url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path}/messages"
    
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = select_fields or "id,receivedDateTime,subject,sender,from,toRecipients,ccRecipients,isRead,hasAttachments,importance,webLink"
    query_api_params['$search'] = f'"{search_query_kql}"'
    query_api_params['$count'] = "true" 
    
    custom_headers_for_search = {'ConsistencyLevel': 'eventual'}
    
    logger.info(f"{action_name}: Buscando mensajes para usuario '{user_identifier}' con query: '{search_query_kql}'")
    
    # _email_paged_request adaptado para tomar headers
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages_to_fetch = getattr(settings, "MAX_PAGING_PAGES", 20)
    effective_max_items = float('inf') if max_items_total is None else max_items_total
    
    try:
        while current_url and len(all_items) < effective_max_items and page_count < max_pages_to_fetch:
            page_count += 1
            is_first_call = (current_url == url_base and page_count == 1)
            current_call_params = query_api_params if is_first_call else None
            
            logger.debug(f"Página {page_count} para '{action_name}': GET {current_url.split('?')[0]} con params: {current_call_params}")
            response_data = client.get(url=current_url, scope=MAIL_READ_SCOPE, params=current_call_params, headers=custom_headers_for_search)
            
            if not isinstance(response_data, dict):
                logger.error(f"{action_name}: Paginación falló, client.get devolvió tipo {type(response_data)}")
                return _handle_email_api_error(Exception(f"Respuesta inesperada tipo {type(response_data)} durante paginación."), action_name, params)
            if response_data.get("status") == "error" and "http_status" in response_data:
                 response_data["action"] = action_name
                 return response_data

            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            
            for item in page_items:
                if len(all_items) < effective_max_items: all_items.append(item)
                else: break
            
            current_url = response_data.get('@odata.nextLink')
            if not current_url or len(all_items) >= effective_max_items: break
        
        total_matching_count = response_data.get('@odata.count', len(all_items)) if isinstance(response_data, dict) else len(all_items)
        logger.info(f"'{action_name}' recuperó {len(all_items)} items (de {total_matching_count} coincidentes) en {page_count} páginas.")
        return {"status": "success", "data": {"value": all_items, "@odata.count": total_matching_count}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/correo_actions.py ---