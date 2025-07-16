# app/actions/youtube_channel_actions.py
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os
import pickle
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- YOUTUBE DATA API V3 CONSTANTS ---
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
# Nota: La gestión de canal (subir, borrar, etc.) requiere OAuth 2.0, no solo una API Key.
# Este módulo asumirá un flujo para obtener credenciales de un token almacenado.

def _get_youtube_credentials():
    """Gets valid OAuth2.0 credentials for the YouTube Data API."""
    creds = None
    # El archivo token.pickle almacena los tokens de acceso y refresco del usuario.
    # Se crea automáticamente cuando el flujo de autorización se completa por primera vez.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # Si no hay credenciales (válidas), el usuario necesitará ejecutar un flujo de autenticación local.
    # Esta parte no puede ser ejecutada por el backend en la nube y es un prerrequisito.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Este es un placeholder. En un entorno de producción real, el refresh token
            # debe ser gestionado de forma segura.
            raise Exception("Credenciales de YouTube no encontradas o expiradas. Se requiere re-autenticación.")
    return creds

def _handle_youtube_api_error(e: Exception, action_name: str) -> dict:
    logger.error(f"Error en YouTube Action '{action_name}': {e}", exc_info=True)
    return {"status": "error", "action": action_name, "message": str(e), "http_status": 500}

def youtube_upload_video(client: Any, params: dict) -> dict:
    action_name = "youtube_upload_video"
    try:
        credentials = _get_youtube_credentials()
        youtube = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

        request_body = {
            "snippet": {
                "title": params['title'],
                "description": params.get('description', ''),
                "tags": params.get('tags', []),
                "categoryId": params.get('categoryId', '22') # Default a "People & Blogs"
            },
            "status": {
                "privacyStatus": params.get('privacyStatus', 'private') # 'private', 'public', or 'unlisted'
            }
        }

        media = MediaFileUpload(params['file_path'], chunksize=-1, resumable=True)

        request = youtube.videos().insert(
            part=",".join(request_body.keys()),
            body=request_body,
            media_body=media
        )
        
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_update_video_details(client: Any, params: dict) -> dict:
    action_name = "youtube_update_video_details"
    try:
        credentials = _get_youtube_credentials()
        youtube = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

        video_id = params['video_id']
        update_payload = params['update_payload'] # ej. {"snippet": {"title": "New Title"}}

        request = youtube.videos().update(
            part="snippet,status",
            body={
                "id": video_id,
                **update_payload
            }
        )
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_list_comments(client: Any, params: dict) -> dict:
    action_name = "youtube_list_comments"
    try:
        credentials = _get_youtube_credentials()
        youtube = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
        
        request = youtube.commentThreads().list(
            part="snippet,replies",
            videoId=params['video_id']
        )
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_reply_to_comment(client: Any, params: dict) -> dict:
    action_name = "youtube_reply_to_comment"
    try:
        credentials = _get_youtube_credentials()
        youtube = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
        
        request = youtube.comments().insert(
            part="snippet",
            body={
                "snippet": {
                    "parentId": params['parent_comment_id'],
                    "textOriginal": params['comment_text']
                }
            }
        )
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)