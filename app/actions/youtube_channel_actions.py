import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from app.core.config import settings

# Implementamos una función de validación local para evitar la dependencia externa
def validate_date_format(date_str):
    """Valida si una cadena tiene formato de fecha YYYY-MM-DD."""
    try:
        if date_str:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        return False
    except ValueError:
        return False

logger = logging.getLogger(__name__)

# --- CONSTANTES Y CONFIGURACIÓN ---
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
YOUTUBE_ANALYTICS_API_SERVICE_NAME = 'youtubeAnalytics'
YOUTUBE_ANALYTICS_API_VERSION = 'v2'

DEFAULT_MAX_RESULTS = 50
VALID_PRIVACY_STATUSES = ['private', 'public', 'unlisted']
VALID_MODERATION_STATUSES = ['heldForReview', 'published', 'rejected']

def _get_youtube_credentials(params: Dict[str, Any]) -> Credentials:
    """
    Construye las credenciales de OAuth 2.0 para la API de YouTube a partir de la configuración.
    En un entorno de producción, esto asume que se ha proporcionado un refresh_token válido.
    """
    # CORRECCIÓN: Usar variables específicas de YouTube en lugar de Google Ads
    client_id = params.get("client_id", settings.YOUTUBE_CLIENT_ID if hasattr(settings, 'YOUTUBE_CLIENT_ID') else settings.GOOGLE_ADS_CLIENT_ID)
    client_secret = params.get("client_secret", settings.YOUTUBE_CLIENT_SECRET if hasattr(settings, 'YOUTUBE_CLIENT_SECRET') else settings.GOOGLE_ADS_CLIENT_SECRET)
    refresh_token = params.get("refresh_token", settings.YOUTUBE_REFRESH_TOKEN if hasattr(settings, 'YOUTUBE_REFRESH_TOKEN') else settings.GOOGLE_ADS_REFRESH_TOKEN)

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Credenciales de YouTube (client_id, client_secret, refresh_token) no están configuradas.")

    # SOLUCIÓN CRÍTICA: Usar solo los scopes que están disponibles en tu refresh_token
    available_scopes = [
        "https://www.googleapis.com/auth/youtube.force-ssl",
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/youtubepartner-channel-audit",
        "https://www.googleapis.com/auth/youtube.third-party-link.creator"
    ]

    try:
        creds = Credentials.from_authorized_user_info(
            info={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token
            },
            scopes=available_scopes
        )
        
        # Forzar refresh del token para verificar validez
        if not creds.valid:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            
        return creds
    except Exception as e:
        logger.error(f"Error creando credenciales de YouTube: {e}")
        raise ValueError(f"Error en credenciales de YouTube: {str(e)}")

def _build_youtube_service(credentials: Credentials) -> Resource:
    """Construye y retorna el servicio de YouTube."""
    try:
        return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)
    except Exception as e:
        logger.error(f"Error construyendo servicio de YouTube: {e}")
        raise

def _build_youtube_analytics_service(credentials: Credentials) -> Resource:
    """Construye y retorna el servicio de YouTube Analytics."""
    try:
        # ADVERTENCIA: YouTube Analytics requiere scope específico no disponible
        logger.warning("YouTube Analytics requiere 'yt-analytics.readonly' scope que no está disponible en el token actual")
        return build(YOUTUBE_ANALYTICS_API_SERVICE_NAME, YOUTUBE_ANALYTICS_API_VERSION, credentials=credentials)
    except Exception as e:
        logger.error(f"Error construyendo servicio de YouTube Analytics: {e}")
        # SOLUCIÓN: Devolver None en lugar de fallar para funciones que no requieren Analytics
        raise ValueError("YouTube Analytics no está disponible. Regenera el refresh_token con scope 'yt-analytics.readonly'")

def _validate_date_params(params: Dict[str, Any]) -> None:
    """Valida los parámetros de fecha."""
    for date_param in ['start_date', 'end_date']:
        if date_param in params:
            if not validate_date_format(params[date_param]):
                raise ValueError(f"{date_param} debe tener formato YYYY-MM-DD")

def _validate_privacy_status(privacy_status: str) -> None:
    """Valida el estado de privacidad."""
    if privacy_status not in VALID_PRIVACY_STATUSES:
        raise ValueError(f"privacy_status debe ser uno de: {', '.join(VALID_PRIVACY_STATUSES)}")

def _handle_youtube_api_error(e: Exception, action_name: str) -> Dict[str, Any]:
    """Maneja errores de la API de Google de forma estandarizada."""
    logger.error(f"Error en YouTube Action '{action_name}': {e}", exc_info=True)
    status_code = 500
    message = str(e)
    details = {}

    if isinstance(e, HttpError):
        status_code = e.resp.status
        try:
            error_details = e.error_details[0] if e.error_details else {}
            message = error_details.get('message', e.reason)
            details = error_details
        except Exception:
            message = e.reason
            details = {"raw_response": e.content.decode('utf-8', 'ignore')}

    return {"status": "error", "action": action_name, "message": message, "details": details, "http_status": status_code}

# --- ACCIONES PRINCIPALES ---

def youtube_upload_video(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sube un video a YouTube.
    
    Args:
        client: Cliente HTTP autenticado (no usado, mantenido por consistencia)
        params: Diccionario con los parámetros necesarios
            - file_path (str): Ruta al archivo de video
            - title (str): Título del video
            - description (str, opcional): Descripción del video
            - privacy_status (str, opcional): Estado de privacidad ('private', 'public', 'unlisted')
            - tags (List[str], opcional): Lista de etiquetas
            - category_id (str, opcional): ID de categoría de YouTube
            
    Returns:
        Dict con el resultado de la operación
    """
    action_name = "youtube_upload_video"
    try:
        # Validaciones
        required_params = ['file_path', 'title']
        if not all(params.get(p) for p in required_params):
            raise ValueError(f"Parámetros requeridos: {', '.join(required_params)}")
        
        privacy_status = params.get('privacy_status', 'private')
        _validate_privacy_status(privacy_status)
        
        # Inicialización
        credentials = _get_youtube_credentials(params)
        youtube = _build_youtube_service(credentials)
        
        # Preparar el body de la solicitud
        request_body = {
            "snippet": {
                "title": params['title'],
                "description": params.get('description', ''),
                "tags": params.get('tags', []),
                "categoryId": params.get('category_id', '22')
            },
            "status": {"privacyStatus": privacy_status}
        }

        # Subir el video
        media = MediaFileUpload(
            params['file_path'], 
            chunksize=-1, 
            resumable=True,
            mimetype='video/*'
        )
        
        request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media
        )
        
        # Procesar la subida
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logger.info(f"Subida de video en progreso: {progress}%")
        
        return {
            "status": "success",
            "action": action_name,
            "data": response,
            "video_id": response.get('id'),
            "http_status": 200
        }
        
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_update_video_metadata(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "youtube_update_video_metadata"
    try:
        credentials = _get_youtube_credentials(params)
        youtube = _build_youtube_service(credentials)

        video_id = params.get('video_id')
        new_title = params.get('new_title')
        new_description = params.get('new_description')

        if not video_id:
            raise ValueError("'video_id' es requerido.")

        # Obtener el video actual para no sobreescribir otros metadatos
        video_response = youtube.videos().list(part="snippet,status", id=video_id).execute()
        if not video_response.get("items"):
            return {"status": "error", "message": f"Video con ID '{video_id}' no encontrado.", "http_status": 404}
        
        video_resource = video_response["items"][0]
        if new_title is not None:
            video_resource["snippet"]["title"] = new_title
        if new_description is not None:
            video_resource["snippet"]["description"] = new_description
        
        request = youtube.videos().update(part="snippet", body=video_resource)
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_set_video_thumbnail(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "youtube_set_video_thumbnail"
    try:
        credentials = _get_youtube_credentials(params)
        youtube = _build_youtube_service(credentials)

        video_id = params.get('video_id')
        image_path = params.get('image_path')

        if not video_id or not image_path:
            raise ValueError("'video_id' y 'image_path' son requeridos.")

        request = youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(image_path)
        )
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_delete_video(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "youtube_delete_video"
    try:
        credentials = _get_youtube_credentials(params)
        youtube = _build_youtube_service(credentials)

        video_id = params.get('video_id')
        if not video_id:
            raise ValueError("'video_id' es requerido.")
        
        request = youtube.videos().delete(id=video_id)
        request.execute() # Devuelve 204 No Content
        return {"status": "success", "message": f"Video '{video_id}' eliminado exitosamente.", "http_status": 204}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_create_playlist(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "youtube_create_playlist"
    try:
        credentials = _get_youtube_credentials(params)
        youtube = _build_youtube_service(credentials)

        title = params.get('title')
        if not title:
            raise ValueError("'title' es requerido.")
            
        body = {
            "snippet": {
                "title": title,
                "description": params.get("description", ""),
            },
            "status": {"privacyStatus": params.get("privacy_status", "private")}
        }

        request = youtube.playlists().insert(part="snippet,status", body=body)
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_add_video_to_playlist(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "youtube_add_video_to_playlist"
    try:
        credentials = _get_youtube_credentials(params)
        youtube = _build_youtube_service(credentials)

        playlist_id = params.get('playlist_id')
        video_id = params.get('video_id')
        if not playlist_id or not video_id:
            raise ValueError("'playlist_id' y 'video_id' son requeridos.")

        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id}
            }
        }
        request = youtube.playlistItems().insert(part="snippet", body=body)
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_list_videos_in_playlist(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "youtube_list_videos_in_playlist"
    try:
        credentials = _get_youtube_credentials(params)
        youtube = _build_youtube_service(credentials)
        playlist_id = params.get('playlist_id')
        if not playlist_id:
            raise ValueError("'playlist_id' es requerido.")
            
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=params.get("max_results", 50)
        )
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_get_video_comments(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "youtube_get_video_comments"
    try:
        credentials = _get_youtube_credentials(params)
        youtube = _build_youtube_service(credentials)
        video_id = params.get('video_id')
        if not video_id:
            raise ValueError("'video_id' es requerido.")
        
        request = youtube.commentThreads().list(
            part="snippet,replies",
            videoId=video_id
        )
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_reply_to_comment(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "youtube_reply_to_comment"
    try:
        credentials = _get_youtube_credentials(params)
        youtube = _build_youtube_service(credentials)
        
        parent_comment_id = params.get('parent_comment_id')
        text = params.get('text')
        if not parent_comment_id or not text:
            raise ValueError("'parent_comment_id' y 'text' son requeridos.")
            
        request = youtube.comments().insert(
            part="snippet",
            body={
                "snippet": {
                    "parentId": parent_comment_id,
                    "textOriginal": text
                }
            }
        )
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_moderate_comment(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "youtube_moderate_comment"
    try:
        credentials = _get_youtube_credentials(params)
        youtube = _build_youtube_service(credentials)

        comment_id = params.get('comment_id')
        moderation_status = params.get('moderation_status') # 'heldForReview', 'published', 'rejected'
        if not comment_id or not moderation_status:
            raise ValueError("'comment_id' y 'moderation_status' son requeridos.")
            
        request = youtube.comments().setModerationStatus(
            id=comment_id,
            moderationStatus=moderation_status,
            banAuthor=params.get('ban_author', False)
        )
        request.execute()
        return {"status": "success", "message": f"Estado de moderación del comentario '{comment_id}' actualizado a '{moderation_status}'.", "http_status": 204}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

# --- ACCIONES DE ANALÍTICAS (YouTube Analytics API v2) ---

def youtube_get_video_analytics(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene analíticas de video (requiere scope adicional)."""
    action_name = "youtube_get_video_analytics"
    try:
        # CORRECCIÓN: Verificar disponibilidad de Analytics
        try:
            credentials = _get_youtube_credentials(params)
            youtube_analytics = _build_youtube_analytics_service(credentials)
        except ValueError as e:
            return {
                "status": "error",
                "action": action_name,
                "message": "YouTube Analytics no disponible. Scopes insuficientes.",
                "details": {"required_scope": "https://www.googleapis.com/auth/yt-analytics.readonly"},
                "http_status": 403
            }

        video_id = params.get('video_id')
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        if not all([video_id, start_date, end_date]):
            raise ValueError("'video_id', 'start_date', y 'end_date' son requeridos.")

        request = youtube_analytics.reports().query(
            dimensions="day",
            endDate=end_date,
            ids="channel==MINE",
            metrics=params.get("metrics", "views,likes,comments,estimatedMinutesWatched,averageViewDuration"),
            startDate=start_date,
            filters=f"video=={video_id}"
        )
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_get_channel_analytics(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene analíticas del canal (requiere scope adicional)."""
    action_name = "youtube_get_channel_analytics"
    try:
        # CORRECCIÓN: Verificar disponibilidad de Analytics
        try:
            credentials = _get_youtube_credentials(params)
            youtube_analytics = _build_youtube_analytics_service(credentials)
        except ValueError as e:
            return {
                "status": "error",
                "action": action_name,
                "message": "YouTube Analytics no disponible. Scopes insuficientes.",
                "details": {"required_scope": "https://www.googleapis.com/auth/yt-analytics.readonly"},
                "http_status": 403
            }
        
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        if not all([start_date, end_date]):
            raise ValueError("'start_date' y 'end_date' son requeridos.")
            
        request = youtube_analytics.reports().query(
            endDate=end_date,
            ids="channel==MINE",
            metrics=params.get("metrics", "views,likes,comments,subscribersGained,subscribersLost,estimatedMinutesWatched"),
            startDate=start_date,
            dimensions=params.get("dimensions", "day")
        )
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_get_audience_demographics(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene demografía de audiencia (requiere scope adicional)."""
    action_name = "youtube_get_audience_demographics"
    try:
        # CORRECCIÓN: Verificar disponibilidad de Analytics
        try:
            credentials = _get_youtube_credentials(params)
            youtube_analytics = _build_youtube_analytics_service(credentials)
        except ValueError as e:
            return {
                "status": "error",
                "action": action_name,
                "message": "YouTube Analytics no disponible. Scopes insuficientes.",
                "details": {"required_scope": "https://www.googleapis.com/auth/yt-analytics.readonly"},
                "http_status": 403
            }

        start_date = params.get('start_date')
        end_date = params.get('end_date')
        if not all([start_date, end_date]):
            raise ValueError("'start_date' y 'end_date' son requeridos.")
            
        request = youtube_analytics.reports().query(
            dimensions="ageGroup",
            endDate=end_date,
            ids="channel==MINE",
            metrics=params.get("metrics", "viewerPercentage"),
            startDate=start_date
        )
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

# NUEVA FUNCIÓN: Obtener información básica del canal sin Analytics
def youtube_get_channel_info(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene información básica del canal (no requiere Analytics)."""
    action_name = "youtube_get_channel_info"
    try:
        credentials = _get_youtube_credentials(params)
        youtube = _build_youtube_service(credentials)
        
        request = youtube.channels().list(
            part="snippet,statistics,brandingSettings",
            mine=True
        )
        response = request.execute()
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

# NUEVA FUNCIÓN: Listar videos del canal
def youtube_list_channel_videos(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Lista los videos del canal."""
    action_name = "youtube_list_channel_videos"
    try:
        credentials = _get_youtube_credentials(params)
        youtube = _build_youtube_service(credentials)
        
        # Primero obtener el canal para conseguir el uploads playlist ID
        channel_request = youtube.channels().list(part="contentDetails", mine=True)
        channel_response = channel_request.execute()
        
        if not channel_response.get("items"):
            return {"status": "error", "message": "No se pudo acceder al canal", "http_status": 404}
        
        uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # Obtener videos del playlist de uploads
        videos_request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=params.get("max_results", 50)
        )
        videos_response = videos_request.execute()
        
        return {"status": "success", "data": videos_response}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)