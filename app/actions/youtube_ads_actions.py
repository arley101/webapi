# app/actions/youtube_ads_actions.py
import logging
import requests
import json
from typing import Dict, Any, Optional

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

YOUTUBE_API_V3_BASE_URL = "https://www.googleapis.com/youtube/v3"

# --- HELPERS INTERNOS ROBUSTOS ---

def _get_youtube_auth_params(params: Dict[str, Any]) -> Dict[str, str]:
    """Prepara los parámetros de autenticación para la API de YouTube."""
    api_key = params.get("api_key", settings.YOUTUBE_API_KEY)
    access_token = params.get("access_token", settings.YOUTUBE_ACCESS_TOKEN)
    
    if api_key:
        return {"key": api_key}
    if access_token:
        # El token de acceso se pasa en el header, no como parámetro de URL
        return {}
    
    raise ValueError("Se requiere 'api_key' o 'access_token' para las acciones de YouTube.")

def _get_youtube_headers(params: Dict[str, Any]) -> Dict[str, str]:
    """Prepara los headers, incluyendo el token de acceso si se proporciona."""
    headers = {"Accept": "application/json"}
    access_token = params.get("access_token", settings.YOUTUBE_ACCESS_TOKEN)
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers

def _handle_youtube_api_error(e: Exception, action_name: str) -> Dict[str, Any]:
    """Maneja errores de la API de YouTube de forma estandarizada."""
    logger.error(f"Error en YouTube Action '{action_name}': {type(e).__name__} - {e}", exc_info=True)
    
    status_code = 500
    details = str(e)
    api_error_info = None

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code = e.response.status_code
        try:
            error_data = e.response.json()
            api_error_info = error_data.get("error", error_data)
            details = api_error_info.get("message", e.response.text)
        except json.JSONDecodeError:
            details = e.response.text
            
    return {
        "status": "error", "action": action_name,
        "message": f"Error interactuando con YouTube Data API: {details}",
        "details": {"youtube_api_error": api_error_info, "raw_response": details},
        "http_status": status_code
    }

# --- ACCIONES PRINCIPALES (YOUTUBE DATA API) ---

def youtube_data_get_channel_details(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene detalles y estadísticas de uno o más canales por su ID."""
    action_name = "youtube_data_get_channel_details"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    channel_ids = params.get("channel_ids") # Puede ser una lista de IDs o un solo ID string
    if not channel_ids:
        return {"status": "error", "message": "'channel_ids' (lista o string) es requerido.", "http_status": 400}
    
    # Asegurar que sea un string separado por comas
    id_string = ",".join(channel_ids) if isinstance(channel_ids, list) else channel_ids

    try:
        auth_params = _get_youtube_auth_params(params)
        headers = _get_youtube_headers(params)
        
        url_params = {
            "part": params.get("part", "snippet,statistics,contentDetails"),
            "id": id_string,
            **auth_params
        }
        
        url = f"{YOUTUBE_API_V3_BASE_URL}/channels"
        
        response = requests.get(url, headers=headers, params=url_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_data_search_videos(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Busca videos basados en una consulta de texto y otros filtros."""
    action_name = "youtube_data_search_videos"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    query_text = params.get("query")
    if not query_text:
        return {"status": "error", "message": "'query' de búsqueda es requerido.", "http_status": 400}
    
    try:
        auth_params = _get_youtube_auth_params(params)
        headers = _get_youtube_headers(params)

        url_params = {
            "part": "snippet",
            "q": query_text,
            "type": "video",
            "maxResults": min(int(params.get("max_results", 25)), 50),
            **auth_params
        }
        
        # Añadir filtros opcionales
        if params.get("channel_id"):
            url_params["channelId"] = params.get("channel_id")
        if params.get("order"): # relevance, date, rating, title, viewCount
            url_params["order"] = params.get("order")

        url = f"{YOUTUBE_API_V3_BASE_URL}/search"
        
        response = requests.get(url, headers=headers, params=url_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)

def youtube_data_get_video_details(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene detalles y estadísticas de uno o más videos por su ID."""
    action_name = "youtube_data_get_video_details"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    video_ids = params.get("video_ids")
    if not video_ids:
        return {"status": "error", "message": "'video_ids' (lista o string) es requerido.", "http_status": 400}
        
    id_string = ",".join(video_ids) if isinstance(video_ids, list) else video_ids

    try:
        auth_params = _get_youtube_auth_params(params)
        headers = _get_youtube_headers(params)

        url_params = {
            "part": params.get("part", "snippet,statistics,contentDetails,player"),
            "id": id_string,
            **auth_params
        }
        
        url = f"{YOUTUBE_API_V3_BASE_URL}/videos"
        
        response = requests.get(url, headers=headers, params=url_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name)