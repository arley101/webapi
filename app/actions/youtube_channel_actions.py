import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import os
import time
import requests
from io import BytesIO

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.services.auth.youtube_auth import get_youtube_client, format_video_metadata, validate_video_privacy

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
    Construye las credenciales de OAuth 2.0 para YouTube de forma dedicada y robusta.
    CORRECCIÓN: Se eliminó el fallback a credenciales de Google Ads para evitar conflictos.
    """
    # Ahora solo busca credenciales específicas de YouTube desde la configuración.
    client_id = params.get("client_id") or settings.YOUTUBE_CLIENT_ID
    client_secret = params.get("client_secret") or settings.YOUTUBE_CLIENT_SECRET
    refresh_token = params.get("refresh_token") or settings.YOUTUBE_REFRESH_TOKEN

    # Validación estricta: si falta alguna credencial de YouTube, la operación debe fallar.
    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Credenciales de YouTube (YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN) no están configuradas correctamente en el entorno.")

    try:
        creds = Credentials.from_authorized_user_info(
            info={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "token_uri": "https://oauth2.googleapis.com/token", # Añadido para mayor robustez
            },
            scopes=[
                "https://www.googleapis.com/auth/youtube",
                "https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube.force-ssl",
                "https://www.googleapis.com/auth/yt-analytics.readonly"
            ]
        )
        
        # Refresca el token si es necesario para asegurar su validez
        if not creds.valid and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            
        logger.info("🎥 YouTube: Credenciales dedicadas generadas exitosamente con refresh token.")
        return creds
    except Exception as e:
        logger.error(f"Error crítico generando credenciales dedicadas de YouTube: {e}")
        # Relanzar el error para que sea manejado por el decorador de errores de la acción.
        raise ValueError(f"Fallo al generar o refrescar las credenciales de YouTube: {e}")

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
        return build(YOUTUBE_ANALYTICS_API_SERVICE_NAME, YOUTUBE_ANALYTICS_API_VERSION, credentials=credentials)
    except Exception as e:
        logger.error(f"Error construyendo servicio de YouTube Analytics: {e}")
        raise ValueError(f"""
YouTube Analytics no disponible: {str(e)}

SOLUCIÓN:
Regenerar refresh_token con scope: 'https://www.googleapis.com/auth/yt-analytics.readonly'
""")

def _validate_privacy_status(privacy_status: str) -> str:
    """Valida y normaliza el estado de privacidad"""
    valid_statuses = ['private', 'unlisted', 'public']
    status_lower = privacy_status.lower()
    
    if status_lower not in valid_statuses:
        logger.warning(f"Invalid privacy status '{privacy_status}', defaulting to 'private'")
        return 'private'  # Ahora retorna correctamente
    
    return status_lower

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
        
        # Verificar que el archivo exista (NUEVO)
        file_path = params['file_path']
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"El archivo no existe: {file_path}")
            
        privacy_status = params.get('privacy_status', 'private')
        privacy_status = _validate_privacy_status(privacy_status)  # Asegurar que se use el valor retornado
        
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
            file_path, 
            chunksize=1024*1024,  # 1MB por chunk para mejor control
            resumable=True,
            mimetype='video/*'
        )
        
        request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media
        )
        
        # Procesar la subida con mejor manejo de progreso
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logger.info(f"Subida de video en progreso: {progress}%")
                # Reportar cada 20%
                if progress % 20 == 0:
                    print(f"Subida en progreso: {progress}%")
        
        # Registrar más información sobre el video subido
        video_id = response.get('id')
        logger.info(f"Video subido exitosamente. ID: {video_id}")
        
        return {
            "status": "success",
            "action": action_name,
            "data": response,
            "video_id": video_id,
            "video_url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
            "http_status": 200
        }
        
    except FileNotFoundError as fnf:
        logger.error(f"Error de archivo: {fnf}")
        return {
            "status": "error",
            "action": action_name,
            "message": str(fnf),
            "details": {"error_type": "file_not_found"},
            "http_status": 404
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
        # FUNCIONALIDAD COMPLETA sin restricciones
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
        
    except ValueError as config_error:
        # Error de configuración - devolver instrucciones claras
        return {
            "status": "error",
            "action": action_name,
            "message": "Configuración de YouTube requerida",
            "details": {
                "error_type": "configuration_required",
                "solution": str(config_error),
                "quick_fix": "Regenerar refresh_token con scopes de YouTube completos"
            },
            "http_status": 503
        }
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
    """Obtiene analíticas de video - FUNCIONALIDAD COMPLETA."""
    action_name = "youtube_get_video_analytics"
    try:
        credentials = _get_youtube_credentials(params)
        youtube_analytics = _build_youtube_analytics_service(credentials)

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
        
    except ValueError as config_error:
        return {
            "status": "error",
            "action": action_name,
            "message": "YouTube Analytics requiere configuración adicional",
            "details": {
                "error_type": "analytics_scope_required",
                "solution": str(config_error)
            },
            "http_status": 503
        }
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_get_channel_analytics(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene analíticas del canal - FUNCIONALIDAD COMPLETA."""
    action_name = "youtube_get_channel_analytics"
    try:
        credentials = _get_youtube_credentials(params)
        youtube_analytics = _build_youtube_analytics_service(credentials)
        
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
        
    except ValueError as config_error:
        return {
            "status": "error",
            "action": action_name,
            "message": "YouTube Analytics requiere configuración adicional",
            "details": {
                "error_type": "analytics_scope_required",
                "solution": str(config_error)
            },
            "http_status": 503
        }
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_get_audience_demographics(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene demografía de audiencia - FUNCIONALIDAD COMPLETA."""
    action_name = "youtube_get_audience_demographics"
    try:
        credentials = _get_youtube_credentials(params)
        youtube_analytics = _build_youtube_analytics_service(credentials)

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
        
    except ValueError as config_error:
        return {
            "status": "error",
            "action": action_name,
            "message": "YouTube Analytics requiere configuración adicional",
            "details": {
                "error_type": "analytics_scope_required",
                "solution": str(config_error)
            },
            "http_status": 503
        }
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_get_channel_info(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene información básica del canal - FUNCIONALIDAD COMPLETA."""
    action_name = "youtube_get_channel_info"
    try:
        credentials = _get_youtube_credentials(params)
        youtube = _build_youtube_service(credentials)
        
        # Usar TODAS las partes disponibles para información completa
        request = youtube.channels().list(
            part="snippet,statistics,brandingSettings,contentDetails,status",
            mine=True
        )
        response = request.execute()
        
        if not response.get("items"):
            return {
                "status": "error",
                "action": action_name,
                "message": "No se pudo acceder al canal",
                "details": {"reason": "Canal no encontrado o sin permisos"},
                "http_status": 404
            }
            
        return {"status": "success", "data": response}
        
    except ValueError as config_error:
        return {
            "status": "error",
            "action": action_name,
            "message": "Configuración de YouTube requerida",
            "details": {
                "error_type": "configuration_required",
                "solution": str(config_error)
            },
            "http_status": 503
        }
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_list_channel_videos(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Lista los videos del canal - FUNCIONALIDAD COMPLETA."""
    action_name = "youtube_list_channel_videos"
    try:
        credentials = _get_youtube_credentials(params)
        youtube = _build_youtube_service(credentials)
            
        # Método ROBUSTO con múltiples opciones
        try:
            # Opción 1: Search directo (más completo)
            search_request = youtube.search().list(
                part="snippet,id",
                forMine=True,
                type="video",
                maxResults=params.get("max_results", 50),
                order=params.get("order", "date")
            )
            videos_response = search_request.execute()
            
            return {"status": "success", "data": videos_response, "method": "search"}
            
        except Exception as search_error:
            logger.info(f"Search method failed, using playlist method: {search_error}")
            
            # Opción 2: Playlist de uploads (fallback)
            channel_request = youtube.channels().list(part="contentDetails", mine=True)
            channel_response = channel_request.execute()
            
            if not channel_response.get("items"):
                raise ValueError("No se pudo acceder al canal")
            
            uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            videos_request = youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=params.get("max_results", 50)
            )
            videos_response = videos_request.execute()
            
            return {"status": "success", "data": videos_response, "method": "playlist"}
            
    except ValueError as config_error:
        return {
            "status": "error",
            "action": action_name,
            "message": "Configuración de YouTube requerida",
            "details": {
                "error_type": "configuration_required",
                "solution": str(config_error)
            },
        }

# ============================================================================
# NUEVAS ACCIONES YOUTUBE - SEGÚN ESPECIFICACIONES DEL DOCUMENTO
# ============================================================================

async def youtube_upload_video(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sube video a YouTube con metadata completa
    Params: video_url, title, description, tags, playlist_id, privacy, schedule
    """
    try:
        video_url = params.get("video_url", "")
        video_path = params.get("video_path", "")
        title = params.get("title", "Video sin título")
        description = params.get("description", "")
        tags = params.get("tags", [])
        playlist_id = params.get("playlist_id", "")
        privacy = validate_video_privacy(params.get("privacy", "private"))
        scheduled_time = params.get("schedule", "")
        category_id = params.get("category_id", "22")
        
        if not video_url and not video_path:
            return {"status": "error", "message": "Se requiere 'video_url' o 'video_path'"}
        
        # Usar cliente YouTube mejorado
        yt_client = get_youtube_client()
        
        # Obtener datos del video
        if video_url:
            # Descargar de URL
            response = requests.get(video_url, timeout=300)  # 5 min timeout
            response.raise_for_status()
            video_data = response.content
        else:
            # Leer archivo local
            with open(video_path, 'rb') as f:
                video_data = f.read()
        
        # Formatear metadata
        metadata = format_video_metadata(
            title=title,
            description=description,
            tags=tags,
            category_id=category_id,
            privacy_status=privacy,
            scheduled_time=scheduled_time
        )
        
        # Upload usando cliente mejorado
        result = yt_client.upload_video_multipart(video_data, metadata, "youtube_upload_video")
        
        # Si upload exitoso y hay playlist, agregar a playlist
        if result.get("status") == "success" and playlist_id:
            video_id = result.get("data", {}).get("id")
            if video_id:
                playlist_result = await youtube_add_video_to_playlist(client, {
                    "playlist_id": playlist_id,
                    "video_id": video_id
                })
                result["playlist_addition"] = playlist_result
        
        # Persistencia
        if result.get("status") == "success":
            result["persist_suggestion"] = {
                "action": "save_memory",
                "params": {
                    "storage_type": "video",
                    "file_name": f"youtube_upload_{int(time.time())}.json",
                    "content": {
                        "video_id": result.get("data", {}).get("id"),
                        "title": title,
                        "description": description,
                        "tags": tags,
                        "privacy": privacy,
                        "source": video_url or video_path,
                        "upload_time": time.time(),
                        "youtube_url": f"https://youtube.com/watch?v={result.get('data', {}).get('id')}"
                    },
                    "tags": ["youtube", "upload", "video"]
                }
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error en youtube_upload_video: {str(e)}")
        return {
            "status": "error",
            "action": "youtube_upload_video",
            "message": f"Error subiendo video: {str(e)}",
            "details": {}
        }

async def youtube_update_video_metadata(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza metadata de video existente
    Params: video_id, title, description, tags, playlist_id
    """
    try:
        video_id = params.get("video_id", "")
        title = params.get("title", "")
        description = params.get("description", "")
        tags = params.get("tags", [])
        privacy = params.get("privacy", "")
        
        if not video_id:
            return {"status": "error", "message": "Parámetro 'video_id' requerido"}
        
        yt_client = get_youtube_client()
        
        # Preparar datos de actualización
        update_body = {
            "id": video_id,
            "snippet": {}
        }
        
        if title:
            update_body["snippet"]["title"] = title
        if description:
            update_body["snippet"]["description"] = description
        if tags:
            update_body["snippet"]["tags"] = tags
        
        # Agregar status si se especifica privacy
        if privacy:
            privacy = validate_video_privacy(privacy)
            update_body["status"] = {"privacyStatus": privacy}
        
        # Determinar parts según qué se está actualizando
        parts = []
        if update_body["snippet"]:
            parts.append("snippet")
        if "status" in update_body:
            parts.append("status")
        
        if not parts:
            return {"status": "error", "message": "No hay datos para actualizar"}
        
        # Ejecutar actualización
        request = yt_client.service.videos().update(
            part=",".join(parts),
            body=update_body
        )
        
        result = yt_client.execute_request(request, "youtube_update_video_metadata")
        
        return result
        
    except Exception as e:
        logger.error(f"Error en youtube_update_video_metadata: {str(e)}")
        return {
            "status": "error",
            "action": "youtube_update_video_metadata",
            "message": f"Error actualizando metadata: {str(e)}",
            "details": {}
        }

async def youtube_get_analytics(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtiene analytics de video/canal por rango de fechas
    Params: video_id (opcional), start_date, end_date, metrics
    """
    try:
        video_id = params.get("video_id", "")
        start_date = params.get("start_date", "")
        end_date = params.get("end_date", "")
        metrics = params.get("metrics", ["views", "watchTime", "subscribersGained"])
        
        if not start_date or not end_date:
            return {"status": "error", "message": "Se requieren 'start_date' y 'end_date' (formato: YYYY-MM-DD)"}
        
        yt_client = get_youtube_client()
        
        # Construir query de analytics
        if video_id:
            # Analytics específicos de video
            filters = f"video=={video_id}"
            dimensions = "day"
        else:
            # Analytics del canal
            filters = ""
            dimensions = "day"
        
        # Construir servicio de YouTube Analytics
        try:
            analytics_service = build('youtubeAnalytics', 'v2', credentials=yt_client._get_oauth_credentials())
        except:
            return {"status": "error", "message": "No se pudo acceder a YouTube Analytics API"}
        
        # Ejecutar query
        request = analytics_service.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics=",".join(metrics),
            dimensions=dimensions,
            filters=filters if filters else None,
            sort="day"
        )
        
        result = yt_client.execute_request(request, "youtube_get_analytics")
        
        # Persistencia
        if result.get("status") == "success":
            result["persist_suggestion"] = {
                "action": "save_memory",
                "params": {
                    "storage_type": "analytics",
                    "file_name": f"youtube_analytics_{int(time.time())}.json",
                    "content": {
                        "video_id": video_id or "channel",
                        "start_date": start_date,
                        "end_date": end_date,
                        "metrics": metrics,
                        "analytics_data": result.get("data", {}),
                        "generated_at": time.time()
                    },
                    "tags": ["youtube", "analytics", "metrics"]
                }
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error en youtube_get_analytics: {str(e)}")
        return {
            "status": "error",
            "action": "youtube_get_analytics",
            "message": f"Error obteniendo analytics: {str(e)}",
            "details": {}
        }

async def youtube_schedule_video(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Programa publicación de video
    Params: video_id, scheduled_time (ISO format)
    """
    try:
        video_id = params.get("video_id", "")
        scheduled_time = params.get("scheduled_time", "")
        
        if not video_id or not scheduled_time:
            return {"status": "error", "message": "Se requieren 'video_id' y 'scheduled_time'"}
        
        yt_client = get_youtube_client()
        
        # Actualizar status del video para scheduling
        update_body = {
            "id": video_id,
            "status": {
                "privacyStatus": "private",  # Debe ser private para scheduled
                "publishAt": scheduled_time
            }
        }
        
        request = yt_client.service.videos().update(
            part="status",
            body=update_body
        )
        
        result = yt_client.execute_request(request, "youtube_schedule_video")
        
        return result
        
    except Exception as e:
        logger.error(f"Error en youtube_schedule_video: {str(e)}")
        return {
            "status": "error",
            "action": "youtube_schedule_video",
            "message": f"Error programando video: {str(e)}",
            "details": {}
        }

async def youtube_bulk_upload_from_folder(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sube múltiples videos desde una carpeta usando STORAGE_RULES
    Params: folder_path, default_title_template, default_description, playlist_id
    """
    try:
        folder_path = params.get("folder_path", "")
        title_template = params.get("default_title_template", "Video {index} - {filename}")
        default_description = params.get("default_description", "")
        playlist_id = params.get("playlist_id", "")
        privacy = validate_video_privacy(params.get("privacy", "private"))
        
        if not folder_path:
            return {"status": "error", "message": "Parámetro 'folder_path' requerido"}
        
        if not os.path.exists(folder_path):
            return {"status": "error", "message": f"Carpeta no existe: {folder_path}"}
        
        # Buscar archivos de video
        video_extensions = [".mp4", ".mov", ".avi", ".mkv", ".wmv"]
        video_files = []
        
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            if os.path.isfile(file_path) and any(file.lower().endswith(ext) for ext in video_extensions):
                video_files.append(file_path)
        
        if not video_files:
            return {"status": "error", "message": "No se encontraron archivos de video en la carpeta"}
        
        # Subir cada video
        results = []
        successful_uploads = 0
        failed_uploads = 0
        
        for i, video_path in enumerate(video_files, 1):
            try:
                filename = os.path.basename(video_path)
                title = title_template.format(index=i, filename=filename)
                
                upload_result = await youtube_upload_video(client, {
                    "video_path": video_path,
                    "title": title,
                    "description": default_description,
                    "privacy": privacy,
                    "playlist_id": playlist_id
                })
                
                if upload_result.get("status") == "success":
                    successful_uploads += 1
                else:
                    failed_uploads += 1
                
                results.append({
                    "file": filename,
                    "status": upload_result.get("status"),
                    "video_id": upload_result.get("data", {}).get("id"),
                    "title": title
                })
                
                # Delay entre uploads para evitar rate limits
                time.sleep(2)
                
            except Exception as e:
                failed_uploads += 1
                results.append({
                    "file": os.path.basename(video_path),
                    "status": "error",
                    "error": str(e)
                })
        
        final_result = {
            "status": "success",
            "action": "youtube_bulk_upload_from_folder",
            "data": {
                "total_files": len(video_files),
                "successful_uploads": successful_uploads,
                "failed_uploads": failed_uploads,
                "results": results
            }
        }
        
        # Persistencia del bulk upload
        final_result["persist_suggestion"] = {
            "action": "save_memory",
            "params": {
                "storage_type": "analytics",
                "file_name": f"youtube_bulk_upload_{int(time.time())}.json",
                "content": final_result["data"],
                "tags": ["youtube", "bulk_upload", "batch"]
            }
        }
        
        return final_result
        
    except Exception as e:
        logger.error(f"Error en youtube_bulk_upload_from_folder: {str(e)}")
        return {
            "status": "error",
            "action": "youtube_bulk_upload_from_folder",
            "message": f"Error en bulk upload: {str(e)}",
            "details": {}
        }

async def youtube_manage_comments(client, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gestiona comentarios: listar, responder, fijar, ocultar
    Params: video_id, action (list|reply|pin|hide), comment_id, reply_text
    """
    try:
        video_id = params.get("video_id", "")
        action = params.get("action", "list")  # list|reply|pin|hide
        comment_id = params.get("comment_id", "")
        reply_text = params.get("reply_text", "")
        
        if not video_id:
            return {"status": "error", "message": "Parámetro 'video_id' requerido"}
        
        yt_client = get_youtube_client()
        
        if action == "list":
            # Listar comentarios
            request = yt_client.service.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=params.get("max_results", 20),
                order=params.get("order", "time")
            )
            
            result = yt_client.execute_request(request, "youtube_manage_comments_list")
            
        elif action == "reply":
            # Responder comentario
            if not comment_id or not reply_text:
                return {"status": "error", "message": "Para responder se requieren 'comment_id' y 'reply_text'"}
            
            # Obtener el comment thread
            thread_request = yt_client.service.commentThreads().list(
                part="snippet",
                id=comment_id
            )
            thread_result = yt_client.execute_request(thread_request, "get_comment_thread")
            
            if thread_result.get("status") != "success":
                return thread_result
            
            # Crear respuesta
            reply_body = {
                "snippet": {
                    "parentId": comment_id,
                    "textOriginal": reply_text
                }
            }
            
            request = yt_client.service.comments().insert(
                part="snippet",
                body=reply_body
            )
            
            result = yt_client.execute_request(request, "youtube_manage_comments_reply")
            
        elif action == "pin":
            # Fijar comentario (requiere ser el propietario del video)
            if not comment_id:
                return {"status": "error", "message": "Para fijar se requiere 'comment_id'"}
            
            # Esta funcionalidad puede requerir API específicas adicionales
            return {"status": "error", "message": "Funcionalidad de fijar comentarios no disponible en API actual"}
            
        elif action == "hide":
            # Ocultar/moderar comentario
            if not comment_id:
                return {"status": "error", "message": "Para ocultar se requiere 'comment_id'"}
            
            # Actualizar status del comentario
            update_body = {
                "id": comment_id,
                "snippet": {
                    "moderationStatus": "rejected"
                }
            }
            
            request = yt_client.service.comments().update(
                part="snippet",
                body=update_body
            )
            
            result = yt_client.execute_request(request, "youtube_manage_comments_hide")
            
        else:
            return {"status": "error", "message": f"Acción no válida: {action}. Usar: list|reply|pin|hide"}
        
        return result
        
    except Exception as e:
        logger.error(f"Error en youtube_manage_comments: {str(e)}")
        return {
            "status": "error",
            "action": "youtube_manage_comments",
            "message": f"Error gestionando comentarios: {str(e)}",
            "details": {}
        }