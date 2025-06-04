# app/actions/youtube_ads_actions.py
# Renombrado conceptualmente a youtube_data_actions.py si solo se usa Data API.
# Por ahora, mantenemos el nombre del archivo original.

import logging
import requests
import json
from typing import Dict, Any, Optional

# Importar la configuración (aunque no se use directamente para el token en esta versión, es buena práctica)
from app.core.config import settings 
from app.shared.helpers.http_client import AuthenticatedHttpClient
# AuthenticatedHttpClient no se usa aquí porque YouTube Data API usa su propio Bearer token
# o API Key, no DefaultAzureCredential.
# from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

YOUTUBE_API_V3_BASE_URL = "https://www.googleapis.com/youtube/v3"

def _get_youtube_api_headers(access_token: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, str]:
    """
    Prepara los headers para las solicitudes a la YouTube Data API.
    Prioriza el access_token si se proporciona.
    """
    headers = {"Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    elif api_key:
        # El API Key se pasa como parámetro de URL 'key', no en header generalmente para YouTube Data API
        # Pero si se necesitara en header para algún caso, aquí se manejaría.
        # Por ahora, el API Key se añadirá a los params de la solicitud GET.
        pass
    else:
        raise ValueError("Se requiere un 'access_token' o un 'api_key' para las solicitudes a YouTube Data API.")
    return headers

def _handle_youtube_api_error(
    e: Exception,
    action_name: str,
    params_for_log: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Helper para manejar errores de YouTube Data API."""
    log_message = f"Error en YouTube Data API Action '{action_name}'"
    if params_for_log:
        # Omitir campos sensibles si es necesario
        safe_params = {k:v for k,v in params_for_log.items() if k not in ['access_token', 'api_key']}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    api_error_info = None

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json()
            # La estructura de error de Google APIs suele ser: {"error": {"code": XXX, "message": "...", "errors": [...]}}
            api_error_info = error_data.get("error", error_data) 
            details_str = api_error_info.get("message", e.response.text)
        except json.JSONDecodeError:
            details_str = e.response.text[:500] if e.response.text else "No response body"
            
    return {
        "status": "error",
        "action": action_name,
        "message": f"Error interactuando con YouTube Data API: {details_str}",
        "details": {
            "raw_exception_type": type(e).__name__,
            "raw_exception_message": str(e),
            "youtube_api_error": api_error_info # Contiene la estructura del error de la API de Google
        },
        "http_status": status_code_int,
    }

# Acción para obtener estadísticas de un canal de YouTube
# Nota: El parámetro 'client: AuthenticatedHttpClient' no se usa aquí
def youtube_get_channel_stats(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "youtube_get_channel_stats"
    logger.info(f"Ejecutando {action_name} con params (token/key omitidos del log): %s", {k:v for k,v in params.items() if k not in ['access_token', 'api_key']})

    access_token: Optional[str] = params.get("access_token")
    api_key: Optional[str] = params.get("api_key") # Alternativa si solo se necesitan datos públicos
    channel_id: Optional[str] = params.get("channel_id")
    part: str = params.get("part", "snippet,statistics,brandingSettings,contentDetails") # Campos a solicitar

    if not channel_id:
        return {"status": "error", "action": action_name, "message": "'channel_id' es requerido.", "http_status": 400}
    if not access_token and not api_key:
        return {"status": "error", "action": action_name, "message": "Se requiere 'access_token' o 'api_key' para esta acción.", "http_status": 401}

    try:
        headers = _get_youtube_api_headers(access_token=access_token, api_key=api_key)
        
        url_params: Dict[str, Any] = {
            "part": part,
            "id": channel_id
        }
        if api_key and not access_token: # Si se usa API Key, se añade como parámetro de URL
            url_params["key"] = api_key
            
        url = f"{YOUTUBE_API_V3_BASE_URL}/channels"
        
        logger.info(f"Solicitando estadísticas de canal de YouTube ID '{channel_id}'. Part: '{part}'")
        response = requests.get(url, headers=headers, params=url_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status() # Lanza HTTPError para 4xx/5xx
        
        response_data = response.json()
        # La respuesta para canales suele ser una lista de items, incluso si solo se pide un ID.
        if response_data.get("items") and isinstance(response_data["items"], list) and len(response_data["items"]) > 0:
            channel_data = response_data["items"][0] # Tomar el primer (y único esperado) item
            return {"status": "success", "action": action_name, "data": channel_data, "http_status": response.status_code}
        else:
            logger.warning(f"No se encontraron 'items' en la respuesta de YouTube para channel_id '{channel_id}'. Respuesta: {response_data}")
            return {"status": "error", "action": action_name, "message": f"No se encontró información para el canal ID '{channel_id}'.", "details": response_data, "http_status": 404}

    except ValueError as ve: # Por ejemplo, de _get_youtube_api_headers
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 400}
    except Exception as e:
        return _handle_youtube_api_error(e, action_name, params)

# --- Aquí podrías añadir más funciones para YouTube Data API ---
# Ejemplos:
# def Youtube_videos(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
#     # params: q (query), maxResults, order, videoCategoryId, etc.
#     pass

# def youtube_get_video_details(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
#     # params: video_id, part (snippet,statistics,contentDetails,player)
#     pass

# --- FIN DEL MÓDULO actions/youtube_data_actions.py (nombre conceptual) ---