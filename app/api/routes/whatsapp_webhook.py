"""
WhatsApp Webhook Router
Maneja eventos entrantes de WhatsApp Business API
"""

import os
import json
import hmac
import hashlib
import logging
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.services.auth.whatsapp_auth import get_whatsapp_client
from app.actions.whatsapp_actions import whatsapp_send_text, whatsapp_send_interactive

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

# ============================================================================
# WEBHOOK VERIFICATION (GET)
# ============================================================================

@router.get("/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"), 
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Verificación del webhook WhatsApp
    Meta envía GET con hub.mode, hub.challenge, hub.verify_token
    """
    try:
        verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
        
        logger.info(f"Webhook verification attempt: mode={hub_mode}, token_match={hub_verify_token == verify_token}")
        
        if hub_mode == "subscribe" and hub_verify_token == verify_token:
            logger.info("Webhook verification successful")
            return PlainTextResponse(content=hub_challenge)
        else:
            logger.warning(f"Webhook verification failed: incorrect token or mode")
            raise HTTPException(status_code=403, detail="Forbidden")
            
    except Exception as e:
        logger.error(f"Error in webhook verification: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ============================================================================
# WEBHOOK EVENTS (POST)
# ============================================================================

@router.post("/whatsapp")
async def handle_whatsapp_webhook(request: Request):
    """
    Maneja eventos entrantes de WhatsApp
    Procesa mensajes, delivery receipts, read receipts, etc.
    """
    try:
        # Obtener datos del webhook
        body = await request.body()
        
        # Validar firma si está habilitada
        if os.getenv("WHATSAPP_VALIDATE_SIGNATURE", "false").lower() == "true":
            signature = request.headers.get("X-Hub-Signature-256", "")
            if not _validate_signature(body, signature):
                logger.warning("Invalid webhook signature")
                raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Parsear JSON
        try:
            webhook_data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Procesar eventos
        await _process_webhook_events(webhook_data)
        
        # WhatsApp espera respuesta 200
        return {"status": "success", "message": "Webhook processed"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _validate_signature(payload: bytes, signature: str) -> bool:
    """Valida firma del webhook usando App Secret"""
    try:
        app_secret = os.getenv("WHATSAPP_APP_SECRET", "")
        if not app_secret:
            return True  # Si no hay secret configurado, no validar
        
        expected_signature = hmac.new(
            app_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Remover prefijo "sha256=" si existe
        if signature.startswith("sha256="):
            signature = signature[7:]
        
        return hmac.compare_digest(expected_signature, signature)
        
    except Exception as e:
        logger.error(f"Error validating signature: {str(e)}")
        return False

async def _process_webhook_events(webhook_data: Dict[str, Any]):
    """Procesa eventos del webhook de WhatsApp"""
    try:
        # Estructura típica: entry[0].changes[0].value
        entries = webhook_data.get("entry", [])
        
        for entry in entries:
            changes = entry.get("changes", [])
            
            for change in changes:
                field = change.get("field", "")
                value = change.get("value", {})
                
                if field == "messages":
                    await _handle_messages(value)
                elif field == "message_statuses":
                    await _handle_message_statuses(value)
                
    except Exception as e:
        logger.error(f"Error processing webhook events: {str(e)}")

async def _handle_messages(message_data: Dict[str, Any]):
    """Maneja mensajes entrantes"""
    try:
        messages = message_data.get("messages", [])
        contacts = message_data.get("contacts", [])
        
        # Crear mapa de contactos para lookup rápido
        contact_map = {contact["wa_id"]: contact for contact in contacts}
        
        for message in messages:
            sender_phone = message.get("from", "")
            message_type = message.get("type", "")
            message_id = message.get("id", "")
            timestamp = message.get("timestamp", "")
            
            # Obtener info del contacto
            contact_info = contact_map.get(sender_phone, {})
            sender_name = contact_info.get("profile", {}).get("name", "Usuario")
            
            logger.info(f"Received {message_type} message from {sender_phone} ({sender_name})")
            
            # Persistir mensaje entrante
            await _persist_incoming_message(message, contact_info)
            
            # Procesar según tipo de mensaje
            if message_type == "text":
                await _handle_text_message(message, contact_info)
            elif message_type == "interactive":
                await _handle_interactive_response(message, contact_info)
            elif message_type in ["image", "video", "audio", "document"]:
                await _handle_media_message(message, contact_info)
            elif message_type == "location":
                await _handle_location_message(message, contact_info)
            
    except Exception as e:
        logger.error(f"Error handling messages: {str(e)}")

async def _handle_message_statuses(status_data: Dict[str, Any]):
    """Maneja delivery/read receipts"""
    try:
        statuses = status_data.get("statuses", [])
        
        for status in statuses:
            message_id = status.get("id", "")
            recipient_id = status.get("recipient_id", "")
            status_type = status.get("status", "")
            timestamp = status.get("timestamp", "")
            
            logger.info(f"Message {message_id} to {recipient_id}: {status_type}")
            
            # Persistir status update
            await _persist_message_status(status)
            
    except Exception as e:
        logger.error(f"Error handling message statuses: {str(e)}")

async def _handle_text_message(message: Dict[str, Any], contact_info: Dict[str, Any]):
    """Procesa mensaje de texto entrante"""
    try:
        sender_phone = message.get("from", "")
        text_body = message.get("text", {}).get("body", "")
        
        # Lógica básica de respuesta automática
        response_text = await _generate_auto_response(text_body, sender_phone, contact_info)
        
        if response_text:
            # Enviar respuesta automática
            from app.core.auth_manager import get_auth_client
            client = get_auth_client()
            
            await whatsapp_send_text(client, {
                "to": sender_phone,
                "text": response_text
            })
            
    except Exception as e:
        logger.error(f"Error handling text message: {str(e)}")

async def _handle_interactive_response(message: Dict[str, Any], contact_info: Dict[str, Any]):
    """Procesa respuesta a mensaje interactivo"""
    try:
        sender_phone = message.get("from", "")
        interactive = message.get("interactive", {})
        
        if interactive.get("type") == "button_reply":
            button_id = interactive.get("button_reply", {}).get("id", "")
            logger.info(f"Button clicked: {button_id} by {sender_phone}")
            
            # Procesar respuesta según botón
            await _process_button_response(button_id, sender_phone, contact_info)
            
        elif interactive.get("type") == "list_reply":
            list_id = interactive.get("list_reply", {}).get("id", "")
            logger.info(f"List option selected: {list_id} by {sender_phone}")
            
            # Procesar respuesta de lista
            await _process_list_response(list_id, sender_phone, contact_info)
            
    except Exception as e:
        logger.error(f"Error handling interactive response: {str(e)}")

async def _handle_media_message(message: Dict[str, Any], contact_info: Dict[str, Any]):
    """Procesa mensaje de media entrante"""
    try:
        sender_phone = message.get("from", "")
        message_type = message.get("type", "")
        
        media_data = message.get(message_type, {})
        media_id = media_data.get("id", "")
        caption = media_data.get("caption", "")
        
        logger.info(f"Received {message_type} from {sender_phone}: {media_id}")
        
        # Aquí podrías descargar y procesar el media
        # Por ahora solo enviamos confirmación
        from app.core.auth_manager import get_auth_client
        client = get_auth_client()
        
        await whatsapp_send_text(client, {
            "to": sender_phone,
            "text": f"✅ Recibido tu {message_type}. Gracias por compartir."
        })
        
    except Exception as e:
        logger.error(f"Error handling media message: {str(e)}")

async def _handle_location_message(message: Dict[str, Any], contact_info: Dict[str, Any]):
    """Procesa mensaje de ubicación"""
    try:
        sender_phone = message.get("from", "")
        location = message.get("location", {})
        
        latitude = location.get("latitude", "")
        longitude = location.get("longitude", "")
        name = location.get("name", "")
        address = location.get("address", "")
        
        logger.info(f"Received location from {sender_phone}: {latitude}, {longitude}")
        
        # Respuesta básica
        from app.core.auth_manager import get_auth_client
        client = get_auth_client()
        
        await whatsapp_send_text(client, {
            "to": sender_phone,
            "text": f"📍 Ubicación recibida. Gracias por compartir tu localización."
        })
        
    except Exception as e:
        logger.error(f"Error handling location message: {str(e)}")

async def _generate_auto_response(text: str, sender_phone: str, contact_info: Dict[str, Any]) -> Optional[str]:
    """Genera respuesta automática básica"""
    try:
        text_lower = text.lower()
        sender_name = contact_info.get("profile", {}).get("name", "")
        
        # Respuestas automáticas básicas
        if any(keyword in text_lower for keyword in ["hola", "hello", "hi", "buenos días", "buenas tardes"]):
            return f"¡Hola {sender_name}! 👋 Gracias por contactarnos. ¿En qué podemos ayudarte?"
        
        elif any(keyword in text_lower for keyword in ["info", "información", "ayuda", "help"]):
            return "📋 Estamos aquí para ayudarte. ¿Sobre qué necesitas información?"
        
        elif any(keyword in text_lower for keyword in ["precio", "costo", "cotización", "presupuesto"]):
            return "💰 Para información sobre precios y cotizaciones, un asesor se pondrá en contacto contigo pronto."
        
        elif any(keyword in text_lower for keyword in ["gracias", "thanks", "thank you"]):
            return "😊 ¡De nada! Si necesitas algo más, no dudes en escribirnos."
        
        else:
            # Respuesta genérica para otros mensajes
            return "📝 Hemos recibido tu mensaje. Un miembro de nuestro equipo te responderá pronto."
            
    except Exception as e:
        logger.error(f"Error generating auto response: {str(e)}")
        return None

async def _process_button_response(button_id: str, sender_phone: str, contact_info: Dict[str, Any]):
    """Procesa respuesta de botón"""
    try:
        from app.core.auth_manager import get_auth_client
        client = get_auth_client()
        
        if button_id == "confirmar":
            await whatsapp_send_text(client, {
                "to": sender_phone,
                "text": "✅ Confirmado. Procederemos con tu solicitud."
            })
        elif button_id == "reprogramar":
            await whatsapp_send_text(client, {
                "to": sender_phone, 
                "text": "📅 Perfecto. Te contactaremos para reprogramar."
            })
        elif button_id == "cancelar":
            await whatsapp_send_text(client, {
                "to": sender_phone,
                "text": "❌ Entendido. Hemos cancelado tu solicitud."
            })
        
    except Exception as e:
        logger.error(f"Error processing button response: {str(e)}")

async def _process_list_response(list_id: str, sender_phone: str, contact_info: Dict[str, Any]):
    """Procesa respuesta de lista"""
    try:
        from app.core.auth_manager import get_auth_client
        client = get_auth_client()
        
        # Respuesta genérica para selección de lista
        await whatsapp_send_text(client, {
            "to": sender_phone,
            "text": f"✅ Has seleccionado: {list_id}. Procesaremos tu selección."
        })
        
    except Exception as e:
        logger.error(f"Error processing list response: {str(e)}")

async def _persist_incoming_message(message: Dict[str, Any], contact_info: Dict[str, Any]):
    """Persiste mensaje entrante usando STORAGE_RULES"""
    try:
        # Usar el sistema de memoria persistente para guardar mensajes
        from app.memory.memory_functions import save_memory
        from app.core.auth_manager import get_auth_client
        
        client = get_auth_client()
        
        await save_memory(client, {
            "storage_type": "document",
            "file_name": f"whatsapp_incoming_{message.get('id', int(time.time()))}.json",
            "content": {
                "type": "incoming_message",
                "message_data": message,
                "contact_info": contact_info,
                "received_at": time.time(),
                "processed": True
            },
            "tags": ["whatsapp", "incoming", message.get("type", "unknown")]
        })
        
    except Exception as e:
        logger.error(f"Error persisting incoming message: {str(e)}")

async def _persist_message_status(status: Dict[str, Any]):
    """Persiste status de mensaje"""
    try:
        from app.memory.memory_functions import save_memory
        from app.core.auth_manager import get_auth_client
        
        client = get_auth_client()
        
        await save_memory(client, {
            "storage_type": "analytics",
            "file_name": f"whatsapp_status_{status.get('id', int(time.time()))}.json",
            "content": {
                "type": "message_status",
                "status_data": status,
                "recorded_at": time.time()
            },
            "tags": ["whatsapp", "status", status.get("status", "unknown")]
        })
        
    except Exception as e:
        logger.error(f"Error persisting message status: {str(e)}")
