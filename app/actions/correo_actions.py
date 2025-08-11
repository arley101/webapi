# app/actions/correo_actions.py
import logging
import requests # Para requests.exceptions.HTTPError
import json # Para el helper de error y _handle_email_api_error
from typing import Dict, List, Optional, Union, Any

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# Scopes (asumiendo que settings.GRAPH_API_DEFAULT_SCOPE es el .default)
MAIL_READ_SCOPE = getattr(settings, "GRAPH_SCOPE_MAIL_READ", settings.GRAPH_API_DEFAULT_SCOPE)
MAIL_SEND_SCOPE = getattr(settings, "GRAPH_SCOPE_MAIL_SEND", settings.GRAPH_API_DEFAULT_SCOPE)
MAIL_READ_WRITE_SCOPE = getattr(settings, "GRAPH_SCOPE_MAIL_READ_WRITE", settings.GRAPH_API_DEFAULT_SCOPE)

def _handle_email_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # Esta función helper no toma 'params' del action_map directamente
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
        except json.JSONDecodeError: # Ahora json está importado
            details_str = e.response.text[:500] if e.response.text else "No response body"
    return {
        "status": "error", "action": action_name,
        "message": f"Error en {action_name}: {type(e).__name__}",
        "http_status": status_code_int, "details": details_str,
        "graph_error_code": graph_error_code
    }

def _email_paged_request(
    client: AuthenticatedHttpClient, url_base: str, scope_list: List[str],
    params: Dict[str, Any], query_api_params_initial: Dict[str, Any], # params es el original de la acción
    max_items_total: Optional[int], action_name_for_log: str
) -> Dict[str, Any]:
    # Esta función helper es llamada por otras, el logging principal y 'params or {}' se hacen en la llamante
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages_to_fetch = getattr(settings, "MAX_PAGING_PAGES", 20)
    top_per_page = query_api_params_initial.get('$top', getattr(settings, "DEFAULT_PAGING_SIZE_MAIL", 25))

    # El logger.info principal ya se hizo en la función llamante
    logger.debug(f"Iniciando solicitud paginada para '{action_name_for_log}' desde '{url_base.split('?')[0]}...'. Max total: {max_items_total or 'todos'}, por pág: {top_per_page}, max_págs: {max_pages_to_fetch}")
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
            if not isinstance(page_items, list): break
            for item in page_items:
                if max_items_total is None or len(all_items) < max_items_total: all_items.append(item)
                else: break
            current_url = response_data.get('@odata.nextLink')
            if not current_url or (max_items_total is not None and len(all_items) >= max_items_total): break
        logger.info(f"'{action_name_for_log}' recuperó {len(all_items)} items en {page_count} páginas.")
        return {"status": "success", "data": {"value": all_items, "@odata.count": len(all_items)}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e:
        # Pasar los params originales de la acción, no los internos de paginación
        return _handle_email_api_error(e, action_name_for_log, params)

def _normalize_recipients(rec_input: Optional[Union[str, List[str], List[Dict[str, Any]]]], type_name: str = "destinatario") -> List[Dict[str, Any]]:
    # Esta función helper no toma 'params' del action_map directamente
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

# --- Acciones de Correo ---

def list_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_messages con params: %s", params)
    action_name = "email_list_messages"
    
    user_identifier: Optional[str] = params.get('mailbox') # Esperar 'mailbox' como user_id o UPN
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    folder_id: str = params.get('folder_id', 'Inbox') # Default a Inbox si no se especifica
    top_per_page: int = min(int(params.get('top_per_page', 25)), getattr(settings, "DEFAULT_PAGING_SIZE_MAIL", 50))
    max_items_total: Optional[int] = params.get('max_items_total')
    select_fields: Optional[str] = params.get('select')
    filter_query: Optional[str] = params.get('filter_query')
    order_by: Optional[str] = params.get('order_by', 'receivedDateTime desc')
    search_query: Optional[str] = params.get('search')

    user_path = f"users/{user_identifier}" # Siempre usar /users/{id}, no /me
    url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path}/mailFolders/{folder_id}/messages"
    
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = select_fields or "id,receivedDateTime,subject,sender,from,toRecipients,ccRecipients,isRead,hasAttachments,importance,webLink"
    
    if search_query:
        query_api_params['$search'] = f'"{search_query}"' # Encerrar entre comillas como recomienda Graph
        if order_by and '$orderby' not in query_api_params : logger.info("'$orderby' se ignora cuando se usa '$search' en mensajes si no se especifica explícitamente en query_params.")
        # Nota: $search y $orderby pueden combinarse si el $orderby es sobre campos indexados para search.
        # Por defecto, Graph podría no aplicar $orderby con $search a menos que sea un campo específico.
        # Para mayor control, el usuario podría necesitar añadir $orderby a query_params directamente si usa search.
    elif filter_query:
        query_api_params['$filter'] = filter_query
        if order_by: query_api_params['$orderby'] = order_by
    elif order_by:
         query_api_params['$orderby'] = order_by
    
    logger.info(f"{action_name}: Listando mensajes para usuario '{user_identifier}', carpeta '{folder_id}'. Query: {query_api_params}")
    return _email_paged_request(client, url_base, MAIL_READ_SCOPE, params, query_api_params, max_items_total, action_name)

def get_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando get_message con params: %s", params)
    action_name = "email_get_message"
    
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    message_id: Optional[str] = params.get('message_id')
    if not message_id:
        logger.error(f"{action_name}: El parámetro 'message_id' es requerido.")
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
        response = client.get(url, scope=MAIL_READ_SCOPE, params=query_api_params)
        # --- CORRECCIÓN ---
        # `client.get` ya devuelve un dict, no un objeto response. Se elimina `.json()`.
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

def send_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando send_message con params: %s", params)
    action_name = "email_send_message"
    
    user_identifier: Optional[str] = params.get('mailbox') # Este es el UPN/ID del *remitente*
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN del remitente) es requerido.")
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
    
    # Con permisos de aplicación, Mail.Send permite enviar como cualquier usuario.
    # El remitente se infiere del token de aplicación O se puede especificar en la propiedad 'from' del mensaje si se tiene el permiso adecuado.
    # Aquí user_identifier se usa para construir el path del endpoint /users/{id}/sendMail.
    user_path = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/sendMail"
    
    logger.info(f"{action_name}: Enviando correo desde '{user_identifier}'. Asunto: '{subject}'")
    try:
        client.post(url, scope=MAIL_SEND_SCOPE, json_data=sendmail_payload)
        # sendMail devuelve 202 Accepted (sin cuerpo)
        return {"status": "success", "message": "Solicitud de envío de correo aceptada.", "http_status": 202}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

def reply_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando reply_message con params: %s", params)
    action_name = "email_reply_message"
    
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    message_id: Optional[str] = params.get('message_id')
    comment_content: Optional[str] = params.get('comment') # Graph API usa 'comment', no 'body_content' para la respuesta rápida
    reply_all: bool = str(params.get('reply_all', "false")).lower() == "true"
    message_payload_override: Optional[Dict[str, Any]] = params.get("message_payload_override") # Para anular/complementar el cuerpo del mensaje de respuesta

    if not message_id: # 'comment' puede ser una cadena vacía si no se quiere añadir comentario adicional al cuerpo de la respuesta
        return {"status": "error", "action": action_name, "message": "'message_id' es requerido.", "http_status": 400}

    action_segment = "replyAll" if reply_all else "reply"
    user_path = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/messages/{message_id}/{action_segment}"
    
    payload_reply: Dict[str, Any] = {}
    if comment_content is not None: # El comentario es opcional
        payload_reply["comment"] = comment_content
    
    # Si se quiere anular completamente el mensaje de respuesta (ej. para añadir adjuntos o cambiar destinatarios)
    if message_payload_override and isinstance(message_payload_override, dict):
        payload_reply["message"] = message_payload_override # Esto debe ser un objeto message completo
    
    log_operation = "Respondiendo a todos" if reply_all else "Respondiendo"
    logger.info(f"{action_name}: {log_operation} al correo '{message_id}' para usuario '{user_identifier}'")
    try:
        client.post(url, scope=MAIL_SEND_SCOPE, json_data=payload_reply)
        # reply y replyAll devuelven 202 Accepted (sin cuerpo)
        return {"status": "success", "message": f"Solicitud de {log_operation.lower()} aceptada.", "http_status": 202}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

def forward_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando forward_message con params: %s", params)
    action_name = "email_forward_message"

    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}
        
    message_id: Optional[str] = params.get('message_id')
    to_recipients_in = params.get('to_recipients') # Debe ser una lista para forward
    comment_content: str = params.get('comment', "") # Comentario opcional a añadir
    message_payload_override: Optional[Dict[str, Any]] = params.get("message_payload_override")

    if not message_id or not to_recipients_in:
        return {"status": "error", "action": action_name, "message": "'message_id' y 'to_recipients' son requeridos.", "http_status": 400}
    
    to_list = _normalize_recipients(to_recipients_in, "to_recipients (forward)")
    if not to_list:
        return {"status": "error", "action": action_name, "message": "Se requiere al menos un destinatario válido en 'to_recipients' para reenviar.", "http_status": 400}

    user_path = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/messages/{message_id}/forward"
    
    payload_forward: Dict[str, Any] = {"toRecipients": to_list}
    if comment_content is not None: # El comentario es opcional
        payload_forward["comment"] = comment_content
    if message_payload_override and isinstance(message_payload_override, dict):
        payload_forward["message"] = message_payload_override # Para anular completamente el mensaje reenviado

    logger.info(f"{action_name}: Reenviando correo '{message_id}' para usuario '{user_identifier}'")
    try:
        client.post(url, scope=MAIL_SEND_SCOPE, json_data=payload_forward)
        # forward devuelve 202 Accepted (sin cuerpo)
        return {"status": "success", "message": "Solicitud de reenvío aceptada.", "http_status": 202}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

def delete_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando delete_message con params: %s", params)
    action_name = "email_delete_message"
    
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    message_id: Optional[str] = params.get('message_id')
    if not message_id:
        logger.error(f"{action_name}: El parámetro 'message_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'message_id' es requerido.", "http_status": 400}
        
    user_path = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/messages/{message_id}"
    
    logger.info(f"{action_name}: Eliminando correo '{message_id}' para usuario '{user_identifier}'")
    try:
        client.delete(url, scope=MAIL_READ_WRITE_SCOPE)
        # DELETE devuelve 204 No Content (sin cuerpo)
        return {"status": "success", "message": "Correo movido a elementos eliminados.", "http_status": 204}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

def move_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando move_message con params: %s", params)
    action_name = "email_move_message"

    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    message_id: Optional[str] = params.get('message_id')
    destination_folder_id: Optional[str] = params.get('destination_folder_id')
    if not message_id or not destination_folder_id:
        logger.error(f"{action_name}: 'message_id' y 'destination_folder_id' son requeridos.")
        return {"status": "error", "action": action_name, "message": "'message_id' y 'destination_folder_id' son requeridos.", "http_status": 400}
        
    user_path = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/messages/{message_id}/move"
    payload = {"destinationId": destination_folder_id}
    
    logger.info(f"{action_name}: Moviendo correo '{message_id}' para usuario '{user_identifier}' a carpeta '{destination_folder_id}'")
    try:
        response = client.post(url, scope=MAIL_READ_WRITE_SCOPE, json_data=payload)
        # move devuelve el mensaje movido (201 Created o 200 OK)
        return {"status": "success", "data": response, "message": "Correo movido."}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

def list_folders(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando list_folders con params: %s", params)
    action_name = "email_list_folders"

    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}
        
    parent_folder_id: Optional[str] = params.get('parent_folder_id') # Si se quieren subcarpetas de una específica
    top_per_page: int = min(int(params.get('top_per_page', 10)), getattr(settings, "DEFAULT_PAGING_SIZE", 25))
    max_items_total: Optional[int] = params.get('max_items_total')
    select_fields: Optional[str] = params.get('select')
    filter_query: Optional[str] = params.get('filter_query')

    user_path = f"users/{user_identifier}"
    if parent_folder_id:
        url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path}/mailFolders/{parent_folder_id}/childFolders"
    else:
        url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path}/mailFolders" # Carpetas raíz
        
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = select_fields or "id,displayName,parentFolderId,childFolderCount,unreadItemCount,totalItemCount"
    if filter_query: query_api_params['$filter'] = filter_query
    
    log_ctx = f"carpetas para usuario '{user_identifier}'" + (f" bajo '{parent_folder_id}'" if parent_folder_id else " (raíz)")
    logger.info(f"{action_name}: Listando {log_ctx}")
    return _email_paged_request(client, url_base, MAIL_READ_SCOPE, params, query_api_params, max_items_total, f"{action_name} ({log_ctx})")

def create_folder(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando create_folder con params: %s", params)
    action_name = "email_create_folder"

    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}
        
    folder_name: Optional[str] = params.get('folder_name')
    if not folder_name:
        logger.error(f"{action_name}: El parámetro 'folder_name' es requerido.")
        return {"status": "error", "action": action_name, "message": "'folder_name' es requerido.", "http_status": 400}
        
    parent_folder_id: Optional[str] = params.get('parent_folder_id')
    
    payload = {"displayName": folder_name}
    # if params.get('is_hidden') is not None: payload['isHidden'] = bool(params['is_hidden'])
    
    user_path = f"users/{user_identifier}"
    url: str
    if parent_folder_id:
        url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/mailFolders/{parent_folder_id}/childFolders"
    else:
        url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/mailFolders"
        
    log_ctx = f"carpeta de correo '{folder_name}' para usuario '{user_identifier}'" + (f" bajo '{parent_folder_id}'" if parent_folder_id else " (raíz)")
    logger.info(f"{action_name}: Creando {log_ctx}")
    try:
        response = client.post(url, scope=MAIL_READ_WRITE_SCOPE, json_data=payload)
        # POST a /mailFolders o /childFolders devuelve el mailFolder creado (201 Created)
        return {"status": "success", "data": response, "message": "Carpeta de correo creada."}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

def search_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    logger.info("Ejecutando search_messages con params: %s", params)
    action_name = "email_search_messages"
    
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    search_query_kql: Optional[str] = params.get('query') # KQL query
    if not search_query_kql:
        logger.error(f"{action_name}: El parámetro 'query' de búsqueda es requerido.")
        return {"status": "error", "action": action_name, "message": "'query' de búsqueda es requerido.", "http_status": 400}

    # El endpoint de Graph para buscar en *todo* el buzón de un usuario es /users/{id}/messages?$search="..."
    # No se especifica un folder_id.
    
    # Parámetros para la paginación y selección de campos, igual que en list_messages
    top_per_page: int = min(int(params.get('top_per_page', 25)), getattr(settings, "DEFAULT_PAGING_SIZE_MAIL", 50))
    max_items_total: Optional[int] = params.get('max_items_total')
    select_fields: Optional[str] = params.get('select')
    # order_by no se usa con $search usualmente, a menos que sea sobre campos específicos indexados.
    # filter_query no se puede usar con $search.

    user_path = f"users/{user_identifier}"
    url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path}/messages" # Busca en todo el buzón
    
    query_api_params: Dict[str, Any] = {'$top': top_per_page}
    query_api_params['$select'] = select_fields or "id,receivedDateTime,subject,sender,from,toRecipients,ccRecipients,isRead,hasAttachments,importance,webLink"
    query_api_params['$search'] = f'"{search_query_kql}"' # Graph recomienda comillas para el valor de $search
    # $count=true es bueno con $search para saber el total de resultados que coinciden.
    query_api_params['$count'] = "true" 
    
    # $search requiere la cabecera ConsistencyLevel: eventual
    custom_headers_for_search = {'ConsistencyLevel': 'eventual'}

    logger.info(f"{action_name}: Buscando mensajes para usuario '{user_identifier}' con query: '{search_query_kql}'")
    
    # _email_paged_request se puede adaptar si pasamos los headers custom, o hacemos la llamada aquí.
    # Por ahora, una implementación directa de paginación aquí para manejar los headers específicos de $search.
    all_items: List[Dict[str, Any]] = []
    current_url: Optional[str] = url_base
    page_count = 0
    max_pages_to_fetch = getattr(settings, "MAX_PAGING_PAGES", 20)
    
    try:
        while current_url and (max_items_total is None or len(all_items) < max_items_total) and page_count < max_pages_to_fetch:
            page_count += 1
            is_first_call = (current_url == url_base and page_count == 1)
            current_call_params = query_api_params if is_first_call else None # Solo en la primera llamada, nextLink ya tiene params
            
            logger.debug(f"Página {page_count} para '{action_name}': GET {current_url.split('?')[0]} con params: {current_call_params}")
            # La cabecera ConsistencyLevel se aplica a todas las llamadas de la secuencia paginada de $search
            response = client.get(url=current_url, scope=MAIL_READ_SCOPE, params=current_call_params, headers=custom_headers_for_search)
            
            # --- CORRECCIÓN ---
            # `client.get` ya devuelve un dict, no un objeto response. Se elimina `.json()`.
            response_data = response
            
            page_items = response_data.get('value', [])
            if not isinstance(page_items, list): break
            
            for item in page_items:
                if max_items_total is None or len(all_items) < max_items_total: all_items.append(item)
                else: break
            
            current_url = response_data.get('@odata.nextLink')
            if not current_url or (max_items_total is not None and len(all_items) >= max_items_total): break
        
        total_matching_count = response_data.get('@odata.count', len(all_items)) if 'response_data' in locals() else len(all_items)
        logger.info(f"'{action_name}' recuperó {len(all_items)} items (de {total_matching_count} coincidentes) en {page_count} páginas.")
        return {"status": "success", "data": {"value": all_items, "@odata.count": total_matching_count}, "total_retrieved": len(all_items), "pages_processed": page_count}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)


# ============================================================================
# FUNCIONES ADICIONALES RESTAURADAS
# ============================================================================

def correo_get_message_properties(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtener propiedades específicas de un mensaje."""
    params = params or {}
    logger.info("Ejecutando correo_get_message_properties con params: %s", params)
    action_name = "correo_get_message_properties"

    mailbox_identifier: Optional[str] = params.get("mailbox")
    if not mailbox_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    message_id: Optional[str] = params.get("message_id")
    if not message_id:
        logger.error(f"{action_name}: El parámetro 'message_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'message_id' es requerido.", "http_status": 400}

    properties: Optional[str] = params.get("properties")
    if not properties:
        properties = "id,subject,from,receivedDateTime,isRead,importance,hasAttachments"

    mailbox_path_segment = f"users/{mailbox_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{mailbox_path_segment}/messages/{message_id}"
    
    query_params = {"$select": properties}
    
    logger.info(f"{action_name}: Obteniendo propiedades del mensaje '{message_id}' para '{mailbox_identifier}'")
    try:
        response = client.get(url, scope=MAIL_READ_SCOPE, params=query_params)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)


def correo_move_message(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Mover un mensaje a una carpeta específica."""
    params = params or {}
    logger.info("Ejecutando correo_move_message con params: %s", params)
    action_name = "correo_move_message"

    mailbox_identifier: Optional[str] = params.get("mailbox")
    if not mailbox_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    message_id: Optional[str] = params.get("message_id")
    if not message_id:
        logger.error(f"{action_name}: El parámetro 'message_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'message_id' es requerido.", "http_status": 400}

    destination_folder_id: Optional[str] = params.get("destination_folder_id")
    if not destination_folder_id:
        logger.error(f"{action_name}: El parámetro 'destination_folder_id' es requerido.")
        return {"status": "error", "action": action_name, "message": "'destination_folder_id' es requerido.", "http_status": 400}

    mailbox_path_segment = f"users/{mailbox_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{mailbox_path_segment}/messages/{message_id}/move"
    
    move_payload = {"destinationId": destination_folder_id}
    
    logger.info(f"{action_name}: Moviendo mensaje '{message_id}' a carpeta '{destination_folder_id}' para '{mailbox_identifier}'")
    try:
        response = client.post(url, scope=MAIL_READ_WRITE_SCOPE, json_data=move_payload)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)


def correo_create_mail_folder(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crear una nueva carpeta de correo."""
    params = params or {}
    logger.info("Ejecutando correo_create_mail_folder con params: %s", params)
    action_name = "correo_create_mail_folder"

    mailbox_identifier: Optional[str] = params.get("mailbox")
    if not mailbox_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    folder_name: Optional[str] = params.get("folder_name")
    if not folder_name:
        logger.error(f"{action_name}: El parámetro 'folder_name' es requerido.")
        return {"status": "error", "action": action_name, "message": "'folder_name' es requerido.", "http_status": 400}

    parent_folder_id: Optional[str] = params.get("parent_folder_id")
    
    mailbox_path_segment = f"users/{mailbox_identifier}"
    
    if parent_folder_id:
        url = f"{settings.GRAPH_API_BASE_URL}/{mailbox_path_segment}/mailFolders/{parent_folder_id}/childFolders"
    else:
        url = f"{settings.GRAPH_API_BASE_URL}/{mailbox_path_segment}/mailFolders"
    
    folder_payload = {"displayName": folder_name}
    
    logger.info(f"{action_name}: Creando carpeta '{folder_name}' para '{mailbox_identifier}'")
    try:
        response = client.post(url, scope=MAIL_READ_WRITE_SCOPE, json_data=folder_payload)
        created_folder = response
        logger.info(f"Carpeta '{folder_name}' creada con ID: {created_folder.get('id')}")
        return {"status": "success", "data": created_folder}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)


def correo_get_mail_rules(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtener reglas de correo del buzón."""
    params = params or {}
    logger.info("Ejecutando correo_get_mail_rules con params: %s", params)
    action_name = "correo_get_mail_rules"

    mailbox_identifier: Optional[str] = params.get("mailbox")
    if not mailbox_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    mailbox_path_segment = f"users/{mailbox_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{mailbox_path_segment}/mailFolders/inbox/messageRules"
    
    logger.info(f"{action_name}: Obteniendo reglas de correo para '{mailbox_identifier}'")
    try:
        response = client.get(url, scope=MAIL_READ_SCOPE)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/correo_actions.py ---