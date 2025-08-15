"""
YouTube Data API v3 Authentication Module
Módulo independiente para autenticación y cliente YouTube separado de Google core
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class YouTubeAuthError(Exception):
    """Errores específicos de autenticación YouTube"""
    pass

class YouTubeClient:
    """Cliente para YouTube Data API v3"""
    
    def __init__(self):
        # Variables de entorno específicas para YouTube
        self.client_id = os.getenv("YOUTUBE_CLIENT_ID")
        self.client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
        self.refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")
        self.api_key = os.getenv("YOUTUBE_API_KEY")  # Para lecturas públicas
        
        # Validar configuración
        self._validate_config()
        
        # Scopes para YouTube
        self.scopes = [
            'https://www.googleapis.com/auth/youtube.upload',
            'https://www.googleapis.com/auth/youtube.readonly',
            'https://www.googleapis.com/auth/youtube.force-ssl'
        ]
        
        # Cliente YouTube
        self.service = None
        self._setup_service()
    
    def _validate_config(self):
        """Valida configuración mínima"""
        if not self.refresh_token and not self.api_key:
            raise YouTubeAuthError(
                "Se requiere YOUTUBE_REFRESH_TOKEN para operaciones autenticadas o "
                "YOUTUBE_API_KEY para lecturas públicas"
            )
    
    def _setup_service(self):
        """Configura el servicio de YouTube API"""
        try:
            if self.refresh_token and self.client_id and self.client_secret:
                # Autenticación OAuth para operaciones completas
                credentials = self._get_oauth_credentials()
                self.service = build('youtube', 'v3', credentials=credentials)
            elif self.api_key:
                # Solo API key para lecturas públicas
                self.service = build('youtube', 'v3', developerKey=self.api_key)
            else:
                raise YouTubeAuthError("No se pudo configurar servicio YouTube")
                
        except Exception as e:
            logger.error(f"Error configurando servicio YouTube: {str(e)}")
            raise YouTubeAuthError(f"Error en configuración YouTube: {str(e)}")
    
    def _get_oauth_credentials(self) -> Credentials:
        """Obtiene credenciales OAuth actualizadas"""
        credentials = Credentials(
            token=None,
            refresh_token=self.refresh_token,
            id_token=None,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.scopes
        )
        
        # Refrescar token
        credentials.refresh(Request())
        return credentials
    
    def execute_request(self, request, action: str = "youtube_request") -> Dict[str, Any]:
        """Ejecuta request a YouTube API con manejo de errores"""
        try:
            result = request.execute()
            return {
                "status": "success",
                "action": action,
                "data": result
            }
        except HttpError as e:
            error_details = json.loads(e.content.decode('utf-8'))
            return {
                "status": "error",
                "action": action,
                "message": f"YouTube API Error: {e.resp.status}",
                "details": error_details
            }
        except Exception as e:
            return {
                "status": "error",
                "action": action,
                "message": f"Error inesperado: {str(e)}",
                "details": {}
            }
    
    def upload_video_multipart(self, video_data: bytes, metadata: Dict[str, Any], action: str = "upload_video") -> Dict[str, Any]:
        """Upload de video usando multipart upload"""
        try:
            from googleapiclient.http import MediaIoBaseUpload
            import io
            
            # Crear media upload
            video_stream = io.BytesIO(video_data)
            media = MediaIoBaseUpload(
                video_stream,
                mimetype='video/*',
                resumable=True,
                chunksize=1024*1024  # 1MB chunks
            )
            
            # Request de inserción
            request = self.service.videos().insert(
                part="snippet,status",
                body=metadata,
                media_body=media
            )
            
            return self.execute_request(request, action)
            
        except Exception as e:
            return {
                "status": "error",
                "action": action,
                "message": f"Error en upload: {str(e)}",
                "details": {}
            }

# Instancia global
_youtube_client = None

def get_youtube_client() -> YouTubeClient:
    """Factory function para obtener instancia del cliente YouTube"""
    global _youtube_client
    if _youtube_client is None:
        _youtube_client = YouTubeClient()
    return _youtube_client

def format_video_metadata(title: str, description: str = "", tags: List[str] = None, 
                         category_id: str = "22", privacy_status: str = "private", 
                         **kwargs) -> Dict[str, Any]:
    """Helper para formatear metadata de video"""
    metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": category_id
        },
        "status": {
            "privacyStatus": privacy_status,
            "embeddable": kwargs.get("embeddable", True),
            "license": kwargs.get("license", "youtube"),
            "publicStatsViewable": kwargs.get("public_stats", True)
        }
    }
    
    if tags:
        metadata["snippet"]["tags"] = tags
    
    if "scheduled_time" in kwargs:
        metadata["status"]["publishAt"] = kwargs["scheduled_time"]
        metadata["status"]["privacyStatus"] = "private"  # Debe ser private para scheduled
    
    return metadata

def validate_video_privacy(privacy: str) -> str:
    """Valida y normaliza privacy status"""
    valid_privacy = ["private", "public", "unlisted"]
    privacy_lower = privacy.lower()
    
    if privacy_lower not in valid_privacy:
        return "private"  # Default seguro
    
    return privacy_lower
