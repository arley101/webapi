"""
WhatsApp Business API Actions
Implementación completa de todas las acciones WhatsApp Business Cloud API
"""

import os
import json
import logging
import requests
import time
from typing import Dict, Any, Optional, List
from app.services.auth.whatsapp_auth import (
    get_whatsapp_client, 
    validate_phone_number, 
    format_whatsapp_message,
    WhatsAppAuthError
)

logger = logging.getLogger(__name__)

# ============================================================================
# ENVÍO DE MENSAJES
# ============================================================================

async def whatsapp_send_text(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Envía mensaje de texto simple"""
    try:
        to = validate_phone_number(params.get("to", ""))
        text = params.get("text", "")
        
        if not text:
            return {"status": "error", "message": "Parámetro 'text' requerido"}
        
        wa_client = get_whatsapp_client()
        
        # Formatear mensaje
        message_data = format_whatsapp_message("text", text=text)
        message_data["to"] = to
        
        # Enviar
        path = f"{wa_client.phone_number_id}/messages"
        result = wa_client.wa_post(path, message_data, "whatsapp_send_text")
        
        # Agregar persistencia opcional
        if result.get("status") == "success":
            result["persist_suggestion"] = {
                "action": "save_memory",
                "params": {
                    "storage_type": "document",
                    "file_name": f"whatsapp_message_{int(time.time())}.json",
                    "content": {
                        "type": "text_message",
                        "to": to,
                        "text": text,
                        "message_id": result.get("data", {}).get("messages", [{}])[0].get("id"),
                        "timestamp": time.time()
                    },
                    "tags": ["whatsapp", "outbound", "text"]
                }
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error en whatsapp_send_text: {str(e)}")
        return {
            "status": "error",
            "action": "whatsapp_send_text",
            "message": f"Error enviando texto: {str(e)}",
            "details": {}
        }

async def whatsapp_send_template(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Envía mensaje template para conversaciones fuera de 24h"""
    try:
        to = validate_phone_number(params.get("to", ""))
        template_name = params.get("template_name", "")
        lang = params.get("lang", os.getenv("WHATSAPP_DEFAULT_TEMPLATE_LANG", "es"))
        components = params.get("components", [])
        
        if not template_name:
            return {"status": "error", "message": "Parámetro 'template_name' requerido"}
        
        wa_client = get_whatsapp_client()
        
        # Formatear mensaje template
        message_data = format_whatsapp_message(
            "template", 
            template_name=template_name,
            lang=lang,
            components=components
        )
        message_data["to"] = to
        
        # Enviar
        path = f"{wa_client.phone_number_id}/messages"
        result = wa_client.wa_post(path, message_data, "whatsapp_send_template")
        
        # Persistencia
        if result.get("status") == "success":
            result["persist_suggestion"] = {
                "action": "save_memory",
                "params": {
                    "storage_type": "document",
                    "file_name": f"whatsapp_template_{int(time.time())}.json",
                    "content": {
                        "type": "template_message",
                        "to": to,
                        "template_name": template_name,
                        "language": lang,
                        "components": components,
                        "message_id": result.get("data", {}).get("messages", [{}])[0].get("id"),
                        "timestamp": time.time()
                    },
                    "tags": ["whatsapp", "outbound", "template"]
                }
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error en whatsapp_send_template: {str(e)}")
        return {
            "status": "error",
            "action": "whatsapp_send_template",
            "message": f"Error enviando template: {str(e)}",
            "details": {}
        }

async def whatsapp_send_media(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Envía media (imagen, video, audio, documento)"""
    try:
        to = validate_phone_number(params.get("to", ""))
        media_type = params.get("media_type", "image")  # image|video|audio|document
        link = params.get("link", "")
        media_id = params.get("media_id", "")
        caption = params.get("caption", "")
        
        if not link and not media_id:
            return {"status": "error", "message": "Se requiere 'link' o 'media_id'"}
        
        if media_type not in ["image", "video", "audio", "document"]:
            return {"status": "error", "message": "media_type debe ser: image|video|audio|document"}
        
        wa_client = get_whatsapp_client()
        
        # Formatear mensaje media
        if link:
            message_data = format_whatsapp_message(media_type, link=link, caption=caption)
        else:
            message_data = format_whatsapp_message(media_type, id=media_id, caption=caption)
        
        message_data["to"] = to
        
        # Enviar
        path = f"{wa_client.phone_number_id}/messages"
        result = wa_client.wa_post(path, message_data, "whatsapp_send_media")
        
        # Persistencia
        if result.get("status") == "success":
            result["persist_suggestion"] = {
                "action": "save_memory",
                "params": {
                    "storage_type": "image" if media_type == "image" else "video" if media_type == "video" else "document",
                    "file_name": f"whatsapp_{media_type}_{int(time.time())}.json",
                    "content": {
                        "type": f"{media_type}_message",
                        "to": to,
                        "media_type": media_type,
                        "source_url": link or f"media_id:{media_id}",
                        "caption": caption,
                        "message_id": result.get("data", {}).get("messages", [{}])[0].get("id"),
                        "timestamp": time.time()
                    },
                    "tags": ["whatsapp", "outbound", media_type]
                }
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error en whatsapp_send_media: {str(e)}")
        return {
            "status": "error",
            "action": "whatsapp_send_media",
            "message": f"Error enviando media: {str(e)}",
            "details": {}
        }

async def whatsapp_send_interactive(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Envía mensaje interactivo (botones o lista)"""
    try:
        to = validate_phone_number(params.get("to", ""))
        interactive = params.get("interactive", {})
        
        if not interactive:
            return {"status": "error", "message": "Parámetro 'interactive' requerido"}
        
        wa_client = get_whatsapp_client()
        
        # Formatear mensaje interactivo
        message_data = format_whatsapp_message("interactive", interactive=interactive)
        message_data["to"] = to
        
        # Enviar
        path = f"{wa_client.phone_number_id}/messages"
        result = wa_client.wa_post(path, message_data, "whatsapp_send_interactive")
        
        # Persistencia
        if result.get("status") == "success":
            result["persist_suggestion"] = {
                "action": "save_memory",
                "params": {
                    "storage_type": "document",
                    "file_name": f"whatsapp_interactive_{int(time.time())}.json",
                    "content": {
                        "type": "interactive_message",
                        "to": to,
                        "interactive_type": interactive.get("type"),
                        "interactive_data": interactive,
                        "message_id": result.get("data", {}).get("messages", [{}])[0].get("id"),
                        "timestamp": time.time()
                    },
                    "tags": ["whatsapp", "outbound", "interactive"]
                }
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error en whatsapp_send_interactive: {str(e)}")
        return {
            "status": "error",
            "action": "whatsapp_send_interactive",
            "message": f"Error enviando interactivo: {str(e)}",
            "details": {}
        }

async def whatsapp_mark_read(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Marca mensaje como leído"""
    try:
        message_id = params.get("message_id", "")
        
        if not message_id:
            return {"status": "error", "message": "Parámetro 'message_id' requerido"}
        
        wa_client = get_whatsapp_client()
        
        # Formatear request
        read_data = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        # Enviar
        path = f"{wa_client.phone_number_id}/messages"
        result = wa_client.wa_post(path, read_data, "whatsapp_mark_read")
        
        return result
        
    except Exception as e:
        logger.error(f"Error en whatsapp_mark_read: {str(e)}")
        return {
            "status": "error",
            "action": "whatsapp_mark_read",
            "message": f"Error marcando como leído: {str(e)}",
            "details": {}
        }

# ============================================================================
# GESTIÓN DE MEDIA
# ============================================================================

async def whatsapp_upload_media(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Sube archivo media y devuelve media_id"""
    try:
        file_url = params.get("file_url", "")
        file_path = params.get("file_path", "")
        mime_type = params.get("mime_type", "")
        
        if not file_url and not file_path:
            return {"status": "error", "message": "Se requiere 'file_url' o 'file_path'"}
        
        wa_client = get_whatsapp_client()
        
        # Obtener datos del archivo
        if file_url:
            # Descargar de URL
            response = requests.get(file_url, timeout=30)
            response.raise_for_status()
            file_data = response.content
            file_name = file_url.split("/")[-1]
            if not mime_type:
                mime_type = response.headers.get("content-type", "application/octet-stream")
        else:
            # Leer archivo local
            with open(file_path, 'rb') as f:
                file_data = f.read()
            file_name = os.path.basename(file_path)
            if not mime_type:
                # Inferir mime type básico
                ext = file_name.split(".")[-1].lower()
                mime_map = {
                    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                    "mp4": "video/mp4", "mov": "video/quicktime",
                    "mp3": "audio/mpeg", "wav": "audio/wav",
                    "pdf": "application/pdf", "doc": "application/msword"
                }
                mime_type = mime_map.get(ext, "application/octet-stream")
        
        # Upload
        result = wa_client.wa_upload_media(file_data, file_name, mime_type, "whatsapp_upload_media")
        
        # Persistencia
        if result.get("status") == "success":
            media_id = result.get("data", {}).get("id")
            result["persist_suggestion"] = {
                "action": "save_memory",
                "params": {
                    "storage_type": "document",
                    "file_name": f"whatsapp_media_{int(time.time())}.json",
                    "content": {
                        "type": "media_upload",
                        "media_id": media_id,
                        "file_name": file_name,
                        "mime_type": mime_type,
                        "source": file_url or file_path,
                        "timestamp": time.time()
                    },
                    "tags": ["whatsapp", "media", "upload"]
                }
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error en whatsapp_upload_media: {str(e)}")
        return {
            "status": "error",
            "action": "whatsapp_upload_media",
            "message": f"Error subiendo media: {str(e)}",
            "details": {}
        }

async def whatsapp_get_media(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene información de media por media_id"""
    try:
        media_id = params.get("media_id", "")
        
        if not media_id:
            return {"status": "error", "message": "Parámetro 'media_id' requerido"}
        
        wa_client = get_whatsapp_client()
        
        # Obtener info del media
        path = f"{media_id}"
        result = wa_client.wa_get(path, None, "whatsapp_get_media")
        
        return result
        
    except Exception as e:
        logger.error(f"Error en whatsapp_get_media: {str(e)}")
        return {
            "status": "error",
            "action": "whatsapp_get_media",
            "message": f"Error obteniendo media: {str(e)}",
            "details": {}
        }

async def whatsapp_download_media(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Descarga media y opcionalmente lo persiste"""
    try:
        media_id = params.get("media_id", "")
        persist = params.get("persist", False)
        
        if not media_id:
            return {"status": "error", "message": "Parámetro 'media_id' requerido"}
        
        wa_client = get_whatsapp_client()
        
        # Primero obtener URL de descarga
        media_info_result = await whatsapp_get_media(client, {"media_id": media_id})
        if media_info_result.get("status") != "success":
            return media_info_result
        
        download_url = media_info_result.get("data", {}).get("url", "")
        if not download_url:
            return {"status": "error", "message": "No se pudo obtener URL de descarga"}
        
        # Descargar archivo
        headers = {"Authorization": f"Bearer {wa_client.access_token}"}
        response = requests.get(download_url, headers=headers, timeout=60)
        response.raise_for_status()
        
        file_data = response.content
        mime_type = response.headers.get("content-type", "application/octet-stream")
        file_name = f"whatsapp_media_{media_id}"
        
        result = {
            "status": "success",
            "action": "whatsapp_download_media",
            "data": {
                "media_id": media_id,
                "file_size": len(file_data),
                "mime_type": mime_type,
                "file_name": file_name
            }
        }
        
        # Persistencia opcional
        if persist:
            # Determinar storage_type
            if mime_type.startswith("image/"):
                storage_type = "image"
            elif mime_type.startswith("video/"):
                storage_type = "video"
            else:
                storage_type = "document"
            
            result["persist_suggestion"] = {
                "action": "save_memory",
                "params": {
                    "storage_type": storage_type,
                    "file_name": file_name,
                    "content": {
                        "media_id": media_id,
                        "download_url": download_url,
                        "file_data": file_data.hex(),  # Hex para JSON
                        "mime_type": mime_type,
                        "timestamp": time.time()
                    },
                    "tags": ["whatsapp", "media", "download"]
                }
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error en whatsapp_download_media: {str(e)}")
        return {
            "status": "error",
            "action": "whatsapp_download_media",
            "message": f"Error descargando media: {str(e)}",
            "details": {}
        }

# ============================================================================
# GESTIÓN DE TEMPLATES
# ============================================================================

async def whatsapp_list_templates(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Lista templates aprobados en la WABA"""
    try:
        wa_client = get_whatsapp_client()
        
        # Obtener templates
        path = f"{wa_client.business_account_id}/message_templates"
        result = wa_client.wa_get(path, {"fields": "name,status,category,language"}, "whatsapp_list_templates")
        
        # Filtrar solo templates aprobados
        if result.get("status") == "success":
            all_templates = result.get("data", {}).get("data", [])
            approved_templates = [t for t in all_templates if t.get("status") == "APPROVED"]
            result["data"]["approved_templates"] = approved_templates
            result["data"]["approved_count"] = len(approved_templates)
        
        return result
        
    except Exception as e:
        logger.error(f"Error en whatsapp_list_templates: {str(e)}")
        return {
            "status": "error",
            "action": "whatsapp_list_templates",
            "message": f"Error listando templates: {str(e)}",
            "details": {}
        }

async def whatsapp_create_template(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea template para aprobación (opcional, programático)"""
    try:
        template_name = params.get("name", "")
        category = params.get("category", "MARKETING")
        language = params.get("language", "es")
        components = params.get("components", [])
        
        if not template_name:
            return {"status": "error", "message": "Parámetro 'name' requerido"}
        
        wa_client = get_whatsapp_client()
        
        # Formatear template data
        template_data = {
            "name": template_name,
            "category": category,
            "language": language,
            "components": components
        }
        
        # Crear template
        path = f"{wa_client.business_account_id}/message_templates"
        result = wa_client.wa_post(path, template_data, "whatsapp_create_template")
        
        return result
        
    except Exception as e:
        logger.error(f"Error en whatsapp_create_template: {str(e)}")
        return {
            "status": "error",
            "action": "whatsapp_create_template",
            "message": f"Error creando template: {str(e)}",
            "details": {}
        }

# ============================================================================
# GESTIÓN DE CONVERSACIÓN
# ============================================================================

async def whatsapp_get_message_status(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Consulta delivery/read status de un mensaje"""
    try:
        message_id = params.get("message_id", "")
        
        if not message_id:
            return {"status": "error", "message": "Parámetro 'message_id' requerido"}
        
        wa_client = get_whatsapp_client()
        
        # Consultar status (nota: esto puede requerir webhook data en producción)
        path = f"{message_id}"
        result = wa_client.wa_get(path, None, "whatsapp_get_message_status")
        
        return result
        
    except Exception as e:
        logger.error(f"Error en whatsapp_get_message_status: {str(e)}")
        return {
            "status": "error",
            "action": "whatsapp_get_message_status",
            "message": f"Error consultando status: {str(e)}",
            "details": {}
        }

async def whatsapp_broadcast_segment(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Envía template a lista de contactos con throttling"""
    try:
        to_list = params.get("to_list", [])
        template_name = params.get("template_name", "")
        lang = params.get("lang", os.getenv("WHATSAPP_DEFAULT_TEMPLATE_LANG", "es"))
        components = params.get("components", [])
        batch_size = params.get("batch_size", 50)
        delay_between_batches = params.get("delay_seconds", 5)
        
        if not to_list:
            return {"status": "error", "message": "Parámetro 'to_list' requerido"}
        if not template_name:
            return {"status": "error", "message": "Parámetro 'template_name' requerido"}
        
        wa_client = get_whatsapp_client()
        
        results = []
        total_contacts = len(to_list)
        successful_sends = 0
        failed_sends = 0
        
        # Procesar en lotes
        for i in range(0, total_contacts, batch_size):
            batch = to_list[i:i + batch_size]
            
            for phone in batch:
                try:
                    # Enviar template individual
                    send_result = await whatsapp_send_template(client, {
                        "to": phone,
                        "template_name": template_name,
                        "lang": lang,
                        "components": components
                    })
                    
                    if send_result.get("status") == "success":
                        successful_sends += 1
                    else:
                        failed_sends += 1
                    
                    results.append({
                        "phone": phone,
                        "status": send_result.get("status"),
                        "message_id": send_result.get("data", {}).get("messages", [{}])[0].get("id")
                    })
                    
                    # Pequeño delay entre mensajes individuales
                    time.sleep(0.1)
                    
                except Exception as e:
                    failed_sends += 1
                    results.append({
                        "phone": phone,
                        "status": "error",
                        "error": str(e)
                    })
            
            # Delay entre lotes
            if i + batch_size < total_contacts:
                time.sleep(delay_between_batches)
        
        final_result = {
            "status": "success",
            "action": "whatsapp_broadcast_segment",
            "data": {
                "total_contacts": total_contacts,
                "successful_sends": successful_sends,
                "failed_sends": failed_sends,
                "results": results,
                "template_used": template_name
            }
        }
        
        # Persistencia del broadcast
        final_result["persist_suggestion"] = {
            "action": "save_memory",
            "params": {
                "storage_type": "analytics",
                "file_name": f"whatsapp_broadcast_{int(time.time())}.json",
                "content": final_result["data"],
                "tags": ["whatsapp", "broadcast", "template", template_name]
            }
        }
        
        return final_result
        
    except Exception as e:
        logger.error(f"Error en whatsapp_broadcast_segment: {str(e)}")
        return {
            "status": "error",
            "action": "whatsapp_broadcast_segment",
            "message": f"Error en broadcast: {str(e)}",
            "details": {}
        }

# ============================================================================
# HANDOVER Y TICKETS
# ============================================================================

async def whatsapp_handover_to_human(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Señaliza handover a humano (lógica interna)"""
    try:
        phone = validate_phone_number(params.get("phone", ""))
        reason = params.get("reason", "user_request")
        context = params.get("context", {})
        
        if not phone:
            return {"status": "error", "message": "Parámetro 'phone' requerido"}
        
        # Esta es lógica interna - marcar conversación para handover
        handover_data = {
            "phone": phone,
            "status": "handed_over",
            "reason": reason,
            "context": context,
            "timestamp": time.time(),
            "requires_human_attention": True
        }
        
        result = {
            "status": "success",
            "action": "whatsapp_handover_to_human",
            "data": handover_data
        }
        
        # Persistir handover
        result["persist_suggestion"] = {
            "action": "save_memory",
            "params": {
                "storage_type": "document",
                "file_name": f"whatsapp_handover_{phone}_{int(time.time())}.json",
                "content": handover_data,
                "tags": ["whatsapp", "handover", "human_required"]
            }
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error en whatsapp_handover_to_human: {str(e)}")
        return {
            "status": "error",
            "action": "whatsapp_handover_to_human",
            "message": f"Error en handover: {str(e)}",
            "details": {}
        }

async def whatsapp_close_ticket(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """Cierra ticket/conversación (lógica interna)"""
    try:
        phone = validate_phone_number(params.get("phone", ""))
        resolution = params.get("resolution", "resolved")
        notes = params.get("notes", "")
        
        if not phone:
            return {"status": "error", "message": "Parámetro 'phone' requerido"}
        
        # Lógica interna de cierre
        close_data = {
            "phone": phone,
            "status": "closed",
            "resolution": resolution,
            "notes": notes,
            "closed_at": time.time(),
            "requires_human_attention": False
        }
        
        result = {
            "status": "success",
            "action": "whatsapp_close_ticket",
            "data": close_data
        }
        
        # Persistir cierre
        result["persist_suggestion"] = {
            "action": "save_memory",
            "params": {
                "storage_type": "document",
                "file_name": f"whatsapp_close_{phone}_{int(time.time())}.json",
                "content": close_data,
                "tags": ["whatsapp", "ticket_closed", resolution]
            }
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error en whatsapp_close_ticket: {str(e)}")
        return {
            "status": "error",
            "action": "whatsapp_close_ticket",
            "message": f"Error cerrando ticket: {str(e)}",
            "details": {}
        }
