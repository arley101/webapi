"""
WhatsApp Business API (Cloud) Authentication Module
Módulo independiente para autenticación y cliente WhatsApp Business API
"""

import os
import json
import time
import logging
import requests
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class WhatsAppAuthError(Exception):
    """Errores específicos de autenticación WhatsApp"""
    pass

class WhatsAppClient:
    """Cliente para WhatsApp Business API (Cloud)"""
    
    def __init__(self):
        # Variables de entorno requeridas
        self.graph_api_version = os.getenv("GRAPH_API_VERSION", "v19.0")
        self.business_account_id = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.app_id = os.getenv("WHATSAPP_APP_ID")
        self.app_secret = os.getenv("WHATSAPP_APP_SECRET")
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
        self.webhook_baseurl = os.getenv("WHATSAPP_WEBHOOK_BASEURL", "https://elitedynamicsapi.azurewebsites.net")
        self.default_template_lang = os.getenv("WHATSAPP_DEFAULT_TEMPLATE_LANG", "es")
        self.rate_limit_safety_ms = int(os.getenv("WHATSAPP_RATE_LIMIT_SAFETY_MS", "500"))
        
        # Validar configuración crítica
        self._validate_config()
        
        # Base URL para Graph API
        self.base_url = f"https://graph.facebook.com/{self.graph_api_version}"
        
        # Configurar session con retry
        self.session = self._setup_session()
        
    def _validate_config(self):
        """Valida que todas las variables críticas estén configuradas"""
        required_vars = [
            ("WHATSAPP_BUSINESS_ACCOUNT_ID", self.business_account_id),
            ("WHATSAPP_PHONE_NUMBER_ID", self.phone_number_id),
            ("WHATSAPP_ACCESS_TOKEN", self.access_token)
        ]
        
        missing_vars = [var_name for var_name, var_value in required_vars if not var_value]
        
        if missing_vars:
            raise WhatsAppAuthError(
                f"Variables de entorno faltantes para WhatsApp: {', '.join(missing_vars)}"
            )
    
    def _setup_session(self) -> requests.Session:
        """Configura session con retry strategy para rate limits"""
        session = requests.Session()
        
        # Retry strategy para 429 (rate limit) y errores de servidor
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=self.rate_limit_safety_ms / 1000,
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def wa_endpoint(self, path: str) -> str:
        """Construye URL completa para endpoint de WhatsApp"""
        return f"{self.base_url}/{path}"
    
    def _get_headers(self) -> Dict[str, str]:
        """Headers estándar para peticiones a WhatsApp API"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _handle_response(self, response: requests.Response, action: str) -> Dict[str, Any]:
        """Maneja respuestas de la API con errores estándar"""
        try:
            response.raise_for_status()
            return {
                "status": "success",
                "action": action,
                "data": response.json()
            }
        except requests.exceptions.HTTPError as e:
            error_data = {}
            try:
                error_data = response.json()
            except:
                pass
            
            # Manejar rate limit específicamente
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", self.rate_limit_safety_ms / 1000)
                return {
                    "status": "error",
                    "action": action,
                    "message": f"Rate limit alcanzado. Reintentar en {retry_after}s",
                    "details": {"retry_after": retry_after, "error_data": error_data}
                }
            
            return {
                "status": "error",
                "action": action,
                "message": f"Error HTTP {response.status_code}: {str(e)}",
                "details": error_data
            }
        except Exception as e:
            return {
                "status": "error",
                "action": action,
                "message": f"Error inesperado: {str(e)}",
                "details": {}
            }
    
    def wa_post(self, path: str, json_data: Dict[str, Any], action: str = "wa_post") -> Dict[str, Any]:
        """POST request a WhatsApp API"""
        try:
            url = self.wa_endpoint(path)
            response = self.session.post(
                url=url,
                headers=self._get_headers(),
                json=json_data,
                timeout=30
            )
            return self._handle_response(response, action)
        except Exception as e:
            logger.error(f"Error en wa_post: {str(e)}")
            return {
                "status": "error",
                "action": action,
                "message": f"Error en petición POST: {str(e)}",
                "details": {}
            }
    
    def wa_get(self, path: str, params: Optional[Dict[str, Any]] = None, action: str = "wa_get") -> Dict[str, Any]:
        """GET request a WhatsApp API"""
        try:
            url = self.wa_endpoint(path)
            response = self.session.get(
                url=url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            return self._handle_response(response, action)
        except Exception as e:
            logger.error(f"Error en wa_get: {str(e)}")
            return {
                "status": "error",
                "action": action,
                "message": f"Error en petición GET: {str(e)}",
                "details": {}
            }
    
    def wa_delete(self, path: str, action: str = "wa_delete") -> Dict[str, Any]:
        """DELETE request a WhatsApp API"""
        try:
            url = self.wa_endpoint(path)
            response = self.session.delete(
                url=url,
                headers=self._get_headers(),
                timeout=30
            )
            return self._handle_response(response, action)
        except Exception as e:
            logger.error(f"Error en wa_delete: {str(e)}")
            return {
                "status": "error",
                "action": action,
                "message": f"Error en petición DELETE: {str(e)}",
                "details": {}
            }
    
    def wa_upload_media(self, file_data: bytes, file_name: str, mime_type: str, action: str = "wa_upload_media") -> Dict[str, Any]:
        """Upload media file a WhatsApp API"""
        try:
            url = self.wa_endpoint(f"{self.phone_number_id}/media")
            
            files = {
                'file': (file_name, file_data, mime_type),
                'messaging_product': (None, 'whatsapp'),
                'type': (None, mime_type.split('/')[0])  # image, video, audio, document
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}"
                # No incluir Content-Type para multipart
            }
            
            response = self.session.post(
                url=url,
                headers=headers,
                files=files,
                timeout=60  # Más tiempo para uploads
            )
            
            return self._handle_response(response, action)
            
        except Exception as e:
            logger.error(f"Error en wa_upload_media: {str(e)}")
            return {
                "status": "error",
                "action": action,
                "message": f"Error en upload de media: {str(e)}",
                "details": {}
            }

# Instancia global del cliente
_whatsapp_client = None

def get_whatsapp_client() -> WhatsAppClient:
    """Factory function para obtener instancia del cliente WhatsApp"""
    global _whatsapp_client
    if _whatsapp_client is None:
        _whatsapp_client = WhatsAppClient()
    return _whatsapp_client

def validate_phone_number(phone: str) -> str:
    """Valida y formatea número de teléfono para WhatsApp API"""
    # Remover caracteres no numéricos excepto +
    clean_phone = ''.join(char for char in phone if char.isdigit() or char == '+')
    
    # Remover + si existe
    if clean_phone.startswith('+'):
        clean_phone = clean_phone[1:]
    
    # Validar que sea un número válido (mínimo 10 dígitos)
    if len(clean_phone) < 10:
        raise ValueError(f"Número de teléfono inválido: {phone}")
    
    return clean_phone

def format_whatsapp_message(message_type: str, **kwargs) -> Dict[str, Any]:
    """Helper para formatear mensajes según tipo"""
    base_message = {
        "messaging_product": "whatsapp"
    }
    
    if message_type == "text":
        base_message.update({
            "type": "text",
            "text": {"body": kwargs.get("text", "")}
        })
    elif message_type == "template":
        base_message.update({
            "type": "template",
            "template": {
                "name": kwargs.get("template_name"),
                "language": {"code": kwargs.get("lang", "es")},
                "components": kwargs.get("components", [])
            }
        })
    elif message_type == "interactive":
        base_message.update({
            "type": "interactive",
            "interactive": kwargs.get("interactive", {})
        })
    elif message_type in ["image", "video", "audio", "document"]:
        media_object = {
            "type": message_type,
            message_type: {}
        }
        
        # URL o media_id
        if "link" in kwargs:
            media_object[message_type]["link"] = kwargs["link"]
        elif "id" in kwargs:
            media_object[message_type]["id"] = kwargs["id"]
        
        # Caption opcional
        if "caption" in kwargs and message_type in ["image", "video", "document"]:
            media_object[message_type]["caption"] = kwargs["caption"]
        
        base_message.update(media_object)
    
    return base_message
