# app/actions/email_optimized_actions.py
"""
🚀 ACCIONES DE CORREO OPTIMIZADAS PARA OPENAI ASSISTANT
Versiones ligeras de las acciones de correo que evitan respuestas muy grandes
"""
import logging
from typing import Dict, List, Optional, Any

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient
from app.actions.correo_actions import _handle_email_api_error, _email_paged_request

logger = logging.getLogger(__name__)

# Scopes reutilizados
MAIL_READ_SCOPE = getattr(settings, "GRAPH_SCOPE_MAIL_READ", settings.GRAPH_API_DEFAULT_SCOPE)

def email_list_messages_summary(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    🎯 VERSIÓN OPTIMIZADA PARA OPENAI ASSISTANT
    Lista mensajes con información resumida - sin contenido pesado
    """
    params = params or {}
    logger.info("Ejecutando email_list_messages_summary (OPTIMIZADA) con params: %s", params)
    action_name = "email_list_messages_summary"
    
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        logger.error(f"{action_name}: El parámetro 'mailbox' (user_id o UPN) es requerido.")
        return {"status": "error", "action": action_name, "message": "'mailbox' (user_id o UPN) es requerido.", "http_status": 400}

    folder_id: str = params.get('folder_id', 'Inbox')
    # LÍMITES OPTIMIZADOS PARA OPENAI
    top_per_page: int = min(int(params.get('top_per_page', 10)), 15)  # Máximo 15
    max_items_total: int = min(int(params.get('max_items_total', 10)), 20)  # Máximo 20
    filter_query: Optional[str] = params.get('filter_query')
    order_by: str = params.get('order_by', 'receivedDateTime desc')

    user_path = f"users/{user_identifier}"
    url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path}/mailFolders/{folder_id}/messages"
    
    # CAMPOS OPTIMIZADOS - SIN CONTENIDO PESADO
    optimized_fields = "id,receivedDateTime,subject,sender,from,isRead,importance,hasAttachments,webLink"
    
    query_api_params: Dict[str, Any] = {
        '$top': top_per_page,
        '$select': optimized_fields,
        '$orderby': order_by
    }
    
    if filter_query:
        query_api_params['$filter'] = filter_query
    
    logger.info(f"{action_name}: OPTIMIZADO para OpenAI - Máximo {max_items_total} mensajes con campos: {optimized_fields}")
    
    result = _email_paged_request(client, url_base, MAIL_READ_SCOPE, params, query_api_params, max_items_total, action_name)
    
    # AGREGAR METADATA OPTIMIZADA
    if result.get("status") == "success":
        result["optimization_info"] = {
            "optimized_for": "OpenAI Assistant",
            "fields_included": optimized_fields.split(','),
            "fields_excluded": ["body", "bodyPreview", "toRecipients", "ccRecipients", "bccRecipients"],
            "max_characters_estimate": len(str(result)) if len(str(result)) < 10000 else "Large response detected"
        }
    
    return result

def email_get_message_preview(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    🎯 VERSIÓN OPTIMIZADA PARA OPENAI ASSISTANT  
    Obtiene mensaje con vista previa corta - sin cuerpo completo
    """
    params = params or {}
    logger.info("Ejecutando email_get_message_preview (OPTIMIZADA) con params: %s", params)
    action_name = "email_get_message_preview"
    
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
    
    # CAMPOS OPTIMIZADOS PARA VISTA PREVIA
    preview_fields = "id,subject,sender,from,bodyPreview,receivedDateTime,isRead,importance,hasAttachments,webLink"
    
    query_api_params: Dict[str, Any] = {
        '$select': preview_fields
    }
    
    logger.info(f"{action_name}: OPTIMIZADO para OpenAI - Vista previa del mensaje '{message_id}'")
    
    try:
        response = client.get(url, scope=MAIL_READ_SCOPE, params=query_api_params)
        
        # OPTIMIZAR RESPUESTA
        if isinstance(response, dict):
            # Limitar bodyPreview si es muy largo
            if 'bodyPreview' in response and isinstance(response['bodyPreview'], str):
                if len(response['bodyPreview']) > 500:
                    response['bodyPreview'] = response['bodyPreview'][:500] + "... [CONTENIDO TRUNCADO PARA OPENAI]"
            
            result = {
                "status": "success", 
                "data": response,
                "optimization_info": {
                    "optimized_for": "OpenAI Assistant",
                    "fields_included": preview_fields.split(','),
                    "body_preview_truncated": len(response.get('bodyPreview', '')) > 500,
                    "estimated_size": f"{len(str(response))} characters"
                }
            }
            return result
        else:
            return {"status": "success", "data": response}
            
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)

def email_get_latest_messages(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    🎯 ACCIÓN ESPECÍFICA PARA OPENAI ASSISTANT
    Obtiene los últimos mensajes de forma optimizada
    """
    params = params or {}
    logger.info("Ejecutando email_get_latest_messages (ESPECÍFICA PARA OPENAI) con params: %s", params)
    action_name = "email_get_latest_messages"
    
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        # Intentar obtener el usuario actual
        user_identifier = "me"
    
    # CONFIGURACIÓN ULTRA OPTIMIZADA
    optimized_params = {
        'mailbox': user_identifier,
        'folder_id': params.get('folder_id', 'Inbox'),
        'top_per_page': min(int(params.get('count', 5)), 10),  # Máximo 10
        'max_items_total': min(int(params.get('count', 5)), 10),
        'order_by': 'receivedDateTime desc'
    }
    
    logger.info(f"{action_name}: Obteniendo últimos {optimized_params['top_per_page']} mensajes para OpenAI")
    
    return email_list_messages_summary(client, optimized_params)

def email_search_messages_optimized(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    🎯 BÚSQUEDA OPTIMIZADA PARA OPENAI ASSISTANT
    Busca mensajes con respuesta limitada
    """
    params = params or {}
    logger.info("Ejecutando email_search_messages_optimized (OPTIMIZADA) con params: %s", params)
    action_name = "email_search_messages_optimized"
    
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        user_identifier = "me"
    
    search_query: Optional[str] = params.get('query') or params.get('search')
    if not search_query:
        logger.error(f"{action_name}: El parámetro 'query' o 'search' es requerido.")
        return {"status": "error", "action": action_name, "message": "'query' o 'search' es requerido.", "http_status": 400}

    folder_id: str = params.get('folder_id', 'Inbox')
    # LÍMITES ESTRICTOS PARA BÚSQUEDA
    top_per_page: int = min(int(params.get('top_per_page', 5)), 8)
    max_items_total: int = min(int(params.get('max_items_total', 5)), 8)

    user_path = f"users/{user_identifier}"
    url_base = f"{settings.GRAPH_API_BASE_URL}/{user_path}/mailFolders/{folder_id}/messages"
    
    # CAMPOS MÍNIMOS PARA BÚSQUEDA
    search_fields = "id,receivedDateTime,subject,sender,from,isRead"
    
    query_api_params: Dict[str, Any] = {
        '$top': top_per_page,
        '$select': search_fields,
        '$search': f'"{search_query}"'
    }
    
    logger.info(f"{action_name}: Búsqueda optimizada '{search_query}' - Máximo {max_items_total} resultados")
    
    result = _email_paged_request(client, url_base, MAIL_READ_SCOPE, params, query_api_params, max_items_total, action_name)
    
    if result.get("status") == "success":
        result["optimization_info"] = {
            "optimized_for": "OpenAI Assistant",
            "search_query": search_query,
            "fields_included": search_fields.split(','),
            "max_results": max_items_total,
            "response_size_estimate": f"{len(str(result))} characters"
        }
    
    return result

def email_get_unread_count(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    🎯 CONTADOR OPTIMIZADO PARA OPENAI ASSISTANT
    Obtiene solo el conteo de mensajes no leídos
    """
    params = params or {}
    logger.info("Ejecutando email_get_unread_count (ULTRA OPTIMIZADA) con params: %s", params)
    action_name = "email_get_unread_count"
    
    user_identifier: Optional[str] = params.get('mailbox')
    if not user_identifier:
        user_identifier = "me"

    folder_id: str = params.get('folder_id', 'Inbox')
    user_path = f"users/{user_identifier}"
    url = f"{settings.GRAPH_API_BASE_URL}/{user_path}/mailFolders/{folder_id}/messages"
    
    # SOLO CONTEO - SIN DATOS ADICIONALES
    query_api_params: Dict[str, Any] = {
        '$filter': 'isRead eq false',
        '$select': 'id',
        '$top': 1000,  # Para conteo preciso
        '$count': True
    }
    
    logger.info(f"{action_name}: Contando mensajes no leídos para OpenAI - Solo metadata")
    
    try:
        response = client.get(url, scope=MAIL_READ_SCOPE, params=query_api_params)
        
        if isinstance(response, dict):
            unread_count = len(response.get('value', []))
            
            return {
                "status": "success",
                "data": {
                    "unread_count": unread_count,
                    "folder": folder_id,
                    "user": user_identifier
                },
                "optimization_info": {
                    "optimized_for": "OpenAI Assistant",
                    "response_type": "count_only",
                    "ultra_lightweight": True
                }
            }
        else:
            return {"status": "success", "data": {"unread_count": 0}}
            
    except Exception as e:
        return _handle_email_api_error(e, action_name, params)
