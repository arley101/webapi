"""
Google Services Authentication Module
Gmail, Calendar, Drive, Sheets - Separado de YouTube
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional, List
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GoogleAuthError(Exception):
    """Errores específicos de autenticación Google"""
    pass

class GoogleServicesClient:
    """Cliente para Google Services (Gmail, Calendar, Drive, Sheets)"""
    
    def __init__(self):
        # Variables de entorno para OAuth usuario
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET") 
        self.refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
        
        # Variable opcional para Service Account
        self.service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        
        # Validar configuración
        self._validate_config()
        
        # Scopes por servicio
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        
        # Servicios
        self.gmail_service = None
        self.calendar_service = None
        self.drive_service = None
        self.sheets_service = None
        
        self._setup_services()
    
    def _validate_config(self):
        """Valida configuración mínima"""
        if not self.refresh_token and not self.service_account_json:
            raise GoogleAuthError(
                "Se requiere GOOGLE_REFRESH_TOKEN para OAuth usuario o "
                "GOOGLE_SERVICE_ACCOUNT_JSON para Service Account"
            )
    
    def _get_oauth_credentials(self) -> Credentials:
        """Obtiene credenciales OAuth de usuario"""
        credentials = Credentials(
            token=None,
            refresh_token=self.refresh_token,
            id_token=None,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.scopes
        )
        
        credentials.refresh(Request())
        return credentials
    
    def _get_service_account_credentials(self) -> ServiceAccountCredentials:
        """Obtiene credenciales de Service Account"""
        service_account_info = json.loads(self.service_account_json)
        credentials = ServiceAccountCredentials.from_service_account_info(
            service_account_info,
            scopes=self.scopes
        )
        return credentials
    
    def _setup_services(self):
        """Configura todos los servicios Google"""
        try:
            # Determinar tipo de credenciales
            if self.refresh_token and self.client_id and self.client_secret:
                credentials = self._get_oauth_credentials()
            elif self.service_account_json:
                credentials = self._get_service_account_credentials()
            else:
                raise GoogleAuthError("No se pudo obtener credenciales")
            
            # Construir servicios
            self.gmail_service = build('gmail', 'v1', credentials=credentials)
            self.calendar_service = build('calendar', 'v3', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
            self.sheets_service = build('sheets', 'v4', credentials=credentials)
            
        except Exception as e:
            logger.error(f"Error configurando servicios Google: {str(e)}")
            raise GoogleAuthError(f"Error en configuración Google: {str(e)}")
    
    def execute_request(self, service_name: str, request, action: str = "google_request") -> Dict[str, Any]:
        """Ejecuta request a Google API con manejo de errores"""
        try:
            result = request.execute()
            return {
                "status": "success",
                "action": action,
                "service": service_name,
                "data": result
            }
        except HttpError as e:
            error_details = json.loads(e.content.decode('utf-8'))
            return {
                "status": "error",
                "action": action,
                "service": service_name,
                "message": f"Google {service_name} API Error: {e.resp.status}",
                "details": error_details
            }
        except Exception as e:
            return {
                "status": "error",
                "action": action,
                "service": service_name,
                "message": f"Error inesperado: {str(e)}",
                "details": {}
            }

# Instancia global
_google_client = None

def get_google_client() -> GoogleServicesClient:
    """Factory function para obtener instancia del cliente Google"""
    global _google_client
    if _google_client is None:
        _google_client = GoogleServicesClient()
    return _google_client

def format_gmail_message(to: str, subject: str, body: str, 
                        html_body: str = None, cc: List[str] = None, 
                        bcc: List[str] = None, attachments: List[Dict] = None) -> Dict[str, Any]:
    """Helper para formatear mensaje de Gmail"""
    import base64
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email import encoders
    
    # Crear mensaje
    if html_body or attachments:
        message = MIMEMultipart('alternative')
    else:
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        if cc:
            message['cc'] = ', '.join(cc)
        return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
    
    # Mensaje multipart
    message['to'] = to
    message['subject'] = subject
    if cc:
        message['cc'] = ', '.join(cc)
    if bcc:
        message['bcc'] = ', '.join(bcc)
    
    # Agregar contenido
    if body:
        message.attach(MIMEText(body, 'plain'))
    if html_body:
        message.attach(MIMEText(html_body, 'html'))
    
    # Agregar attachments
    if attachments:
        for attachment in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['data'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f"attachment; filename= {attachment['filename']}"
            )
            message.attach(part)
    
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

def format_calendar_event(title: str, start_time: str, end_time: str,
                         description: str = "", location: str = "", 
                         attendees: List[str] = None, timezone: str = "UTC") -> Dict[str, Any]:
    """Helper para formatear evento de Calendar"""
    event = {
        'summary': title,
        'description': description,
        'start': {
            'dateTime': start_time,
            'timeZone': timezone,
        },
        'end': {
            'dateTime': end_time,
            'timeZone': timezone,
        },
    }
    
    if location:
        event['location'] = location
    
    if attendees:
        event['attendees'] = [{'email': email} for email in attendees]
        event['conferenceData'] = {
            'createRequest': {
                'requestId': f"meet-{int(time.time())}",
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
    
    return event
