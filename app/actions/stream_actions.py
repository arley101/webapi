# app/actions/stream_actions.py
import logging
import requests # Para requests.exceptions.HTTPError
import json # Para el helper de error
import urllib.parse # Para URL encoding en la búsqueda
from typing import Dict, List, Optional, Any

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient
# Importar helpers de sharepoint_actions para resolver site_id y drive_id si es necesario
logger = logging.getLogger(__name__)  # Define logger before usage

try:
    from app.actions.sharepoint_actions import _obtener_site_id_sp, _get_drive_id, _get_item_id_from_path_if_needed_sp
except ImportError:
    logger.error("CRÍTICO: Error al importar helpers de sharepoint_actions.py. Las funciones de Stream que dependen de ellos fallarán.")
    # Definir placeholders para que el módulo cargue, pero las funciones fallarán si se llaman.
    def _obtener_site_id_sp(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> str:
        raise NotImplementedError("Helper _obtener_site_id_sp no disponible/importado en stream_actions.")
    def _get_drive_id(client: AuthenticatedHttpClient, site_id: str, drive_id_or_name_input: Optional[str] = None) -> str:
        raise NotImplementedError("Helper _get_drive_id no disponible/importado en stream_actions.")
    def _get_item_id_from_path_if_needed_sp(client: AuthenticatedHttpClient, item_path_or_id: str, site_id: str, drive_id: str, params_for_metadata: Optional[Dict[str, Any]] = None) -> Any: # El tipo de retorno puede ser str o Dict de error
        raise NotImplementedError("Helper _get_item_id_from_path_if_needed_sp no disponible/importado en stream_actions.")


logger = logging.getLogger(__name__)

# Timeout más largo para búsquedas o descargas de video si es necesario
VIDEO_ACTION_TIMEOUT = max(settings.DEFAULT_API_TIMEOUT, 180) # Ej. 3 minutos

def _handle_stream_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Stream Action '{action_name}'"
    if params_for_log:
        log_message += f" con params: {params_for_log}" # Asumir que los params no son excesivamente grandes o sensibles aquí
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    graph_error_code = None # Específico para errores de Graph
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json()
            error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text)
            graph_error_code = error_info.get("code")
        except json.JSONDecodeError: 
            details_str = e.response.text[:500] if e.response.text else "No response body"
            
    return {
        "status": "error", 
        "action": action_name,
        "message": f"Error en {action_name}: {details_str}", 
        "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
        "http_status": status_code_int,
        "graph_error_code": graph_error_code
    }


def listar_videos(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "stream_listar_videos"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    drive_scope: str = params.get('drive_scope', 'user').lower() # Cambiado default a 'user'
    search_folder_path: str = params.get('search_folder_path', '/') 
    user_query: Optional[str] = params.get('query') 
    top: int = min(int(params.get('top', 25)), 200) 

    # Query de búsqueda base para tipos comunes de video y la faceta 'video'
    # Usar la faceta 'video' es más directo si está disponible en la búsqueda de Drive.
    # `video ne null` o `video <> null` podrían funcionar en $filter, pero /search usa KQL-like.
    # Para /search, buscar por tipo de archivo o términos relacionados con video es más común.
    # O buscar items donde la propiedad `video` exista.
    video_file_types_kql = "(filetype:mp4 OR filetype:mov OR filetype:wmv OR filetype:avi OR filetype:mkv OR filetype:webm OR filetype:mpeg OR contentclass:STS_ListItem_DocumentLibrary AND (SecondaryFileExtension:mp4 OR SecondaryFileExtension:mov))"
    # O buscar por la faceta de video si el search de graph lo soporta bien: "video:*"
    # Por ahora, nos basaremos en tipos de archivo y query del usuario.

    final_search_kql_query = video_file_types_kql
    if user_query:
        final_search_kql_query = f"({user_query}) AND {final_search_kql_query}"
    
    api_query_odata_params = {
        '$top': top,
        '$select': params.get('select', 'id,name,webUrl,video,size,file,createdDateTime,lastModifiedDateTime,parentReference,@microsoft.graph.downloadUrl')
    }

    search_base_url_segment: str # Path del drive o carpeta donde buscar, ej /users/{id}/drive/root
    log_location_description: str
    
    user_identifier_for_drive: Optional[str] = params.get("user_id") # Para OneDrive de un usuario específico

    try:
        if drive_scope == 'user': # Cambiado de 'me' a 'user' para ser explícito
            if not user_identifier_for_drive:
                return {"status": "error", "action": action_name, "message": "Para 'drive_scope=user', se requiere 'user_id' (UPN o ID del usuario).", "http_status": 400}
            
            drive_id_param = params.get("drive_id") # ID específico del drive del usuario (ej. si tiene múltiples)
            user_path_segment = f"/users/{user_identifier_for_drive}"
            
            if drive_id_param:
                search_base_url_segment = f"{user_path_segment}/drives/{drive_id_param}"
                log_location_description = f"Drive específico '{drive_id_param}' del usuario '{user_identifier_for_drive}'"
            else: 
                search_base_url_segment = f"{user_path_segment}/drive" # Drive principal
                log_location_description = f"OneDrive principal del usuario '{user_identifier_for_drive}'"
            
            # Añadir path de la carpeta si se especifica
            clean_search_folder_path = search_folder_path.strip('/')
            if clean_search_folder_path:
                search_base_url_segment += f"/root:/{clean_search_folder_path}:" # Path relativo
            else:
                search_base_url_segment += "/root"


        elif drive_scope == 'site':
            site_identifier_param = params.get('site_identifier', params.get('site_id'))
            drive_identifier_param = params.get('drive_identifier', params.get('drive_id_or_name'))

            if not site_identifier_param: # drive_identifier puede ser opcional para usar el default del sitio
                return {"status": "error", "action": action_name, "message": "Si 'drive_scope' es 'site', se requiere 'site_identifier' (o 'site_id').", "http_status": 400}
            
            # Usar los helpers de sharepoint_actions para obtener site_id y drive_id
            # _obtener_site_id_sp necesita los params originales por si usa el default site_id de settings.
            effective_site_id = _obtener_site_id_sp(client, params) 
            effective_drive_id = _get_drive_id(client, effective_site_id, drive_identifier_param)

            search_base_url_segment = f"/sites/{effective_site_id}/drives/{effective_drive_id}"
            log_location_description = f"Drive '{effective_drive_id}' en sitio '{effective_site_id}'"
            
            clean_search_folder_path = search_folder_path.strip('/')
            if clean_search_folder_path:
                 search_base_url_segment += f"/root:/{clean_search_folder_path}:"
            else:
                search_base_url_segment += "/root"
        else:
            return {"status": "error", "action": action_name, "message": "'drive_scope' debe ser 'user' o 'site'.", "http_status": 400}
        
        # Endpoint de búsqueda: /{drive-base-path}/search(q='{queryText}')
        encoded_kql_query = urllib.parse.quote_plus(final_search_kql_query)
        search_api_url = f"{settings.GRAPH_API_BASE_URL}{search_base_url_segment}/search(q='{encoded_kql_query}')"

        logger.info(f"Buscando videos (KQL Query='{final_search_kql_query}') en {log_location_description}. URL: {search_api_url.split('?')[0]}... OData Params: {api_query_odata_params}")
        
        stream_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # Files.Read.All
        response = client.get(url=search_api_url, scope=stream_read_scope, params=api_query_odata_params, timeout=VIDEO_ACTION_TIMEOUT)
        
        # --- CORRECCIÓN ---
        search_results = response
        
        items_found: List[Dict[str, Any]] = []
        raw_value = search_results.get('value', [])
        if isinstance(raw_value, list):
            for hit_container_or_item in raw_value: # El formato de respuesta de /search puede variar
                resource_item = None
                if isinstance(hit_container_or_item, dict) and 'resource' in hit_container_or_item and isinstance(hit_container_or_item['resource'], dict):
                    resource_item = hit_container_or_item['resource'] # Formato de hits anidados
                elif isinstance(hit_container_or_item, dict) and 'id' in hit_container_or_item and 'name' in hit_container_or_item : # Formato directo de DriveItem
                    resource_item = hit_container_or_item
                
                if resource_item and resource_item.get("video"): # Filtrar solo los que tienen la faceta video explícita
                    items_found.append(resource_item)
        
        logger.info(f"Se encontraron {len(items_found)} archivos con faceta de video en {log_location_description} para la query dada.")
        # Aquí se podría implementar paginación si search_results contiene '@odata.nextLink'
        # pero la búsqueda de Drive no siempre pagina de forma estándar. El $top limita la primera página.
        return {"status": "success", "data": {"value": items_found, "@odata.count": len(items_found)}, "total_retrieved": len(items_found)}

    except ValueError as ve: 
         return {"status": "error", "action": action_name, "message": f"Error de configuración o parámetro para búsqueda de videos: {ve}", "http_status": 400}
    except NotImplementedError as nie: 
        return {"status": "error", "action": action_name, "message": f"Dependencia (helper de SharePoint) no implementada o no importada: {nie}", "http_status": 501}
    except Exception as e:
        return _handle_stream_api_error(e, action_name, params)


def obtener_metadatos_video(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "stream_obtener_metadatos_video"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    item_id_or_path: Optional[str] = params.get("item_id_or_path") # ID o path relativo al Drive/root del video
    drive_scope: str = params.get('drive_scope', 'user').lower()
    
    select_fields: str = params.get('select', "id,name,webUrl,size,createdDateTime,lastModifiedDateTime,file,video,parentReference,@microsoft.graph.downloadUrl")
    # Asegurar que 'video' y '@microsoft.graph.downloadUrl' estén en el select
    if "video" not in select_fields.lower(): select_fields += ",video"
    if "@microsoft.graph.downloadurl" not in select_fields.lower(): select_fields += ",@microsoft.graph.downloadUrl"

    if not item_id_or_path:
        return {"status": "error", "action": action_name, "message": "'item_id_or_path' (ID del video o path relativo a la raíz del Drive) es requerido.", "http_status": 400}

    item_url: str # URL completa al DriveItem
    log_item_description: str
    
    user_identifier_for_drive: Optional[str] = params.get("user_id")

    try:
        if drive_scope == 'user':
            if not user_identifier_for_drive:
                return {"status": "error", "action": action_name, "message": "Para 'drive_scope=user', se requiere 'user_id'.", "http_status": 400}
            drive_id_param = params.get("drive_id") # Opcional, si el usuario tiene múltiples drives
            
            user_drive_base = f"/users/{user_identifier_for_drive}/drives/{drive_id_param}" if drive_id_param else f"/users/{user_identifier_for_drive}/drive"
            
            # Determinar si es path o ID
            if "/" in item_id_or_path or ("." in item_id_or_path and not item_id_or_path.startswith("driveItem_") and len(item_id_or_path) < 70 and '!' not in item_id_or_path) :
                clean_path = item_id_or_path.strip('/')
                item_url = f"{settings.GRAPH_API_BASE_URL}{user_drive_base}/root:/{clean_path}"
            else: # Asumir ID
                item_url = f"{settings.GRAPH_API_BASE_URL}{user_drive_base}/items/{item_id_or_path}"
            log_item_description = f"video '{item_id_or_path}' en OneDrive de usuario '{user_identifier_for_drive}' (Drive ID: {drive_id_param or 'principal'})"

        elif drive_scope == 'site':
            site_identifier_param = params.get('site_identifier', params.get('site_id'))
            drive_identifier_param = params.get('drive_identifier', params.get('drive_id_or_name'))
            if not site_identifier_param:
                 return {"status": "error", "action": action_name, "message": "Si 'drive_scope' es 'site', 'site_identifier' es requerido.", "http_status": 400}

            effective_site_id = _obtener_site_id_sp(client, params) # Pasa params para el contexto de _obtener_site_id_sp
            effective_drive_id = _get_drive_id(client, effective_site_id, drive_identifier_param)
            
            # Para SP, es mejor resolver el path a ID si se pasa un path, usando el helper.
            item_actual_id_or_error = _get_item_id_from_path_if_needed_sp(client, item_id_or_path, effective_site_id, effective_drive_id, params)
            if isinstance(item_actual_id_or_error, dict) and item_actual_id_or_error.get("status") == "error":
                return item_actual_id_or_error # Propagar el error del helper

            item_url = f"{settings.GRAPH_API_BASE_URL}/sites/{effective_site_id}/drives/{effective_drive_id}/items/{item_actual_id_or_error}"
            log_item_description = f"video '{item_id_or_path}' (ID resuelto: {item_actual_id_or_error}) en SharePoint (Sitio: {effective_site_id}, Drive: {effective_drive_id})"
        else:
            return {"status": "error", "action": action_name, "message": "'drive_scope' debe ser 'user' o 'site'.", "http_status": 400}
        
        api_query_params = {"$select": select_fields}
        logger.info(f"Obteniendo metadatos de video para {log_item_description}. Select: {select_fields}")
        
        stream_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.get(url=item_url, scope=stream_read_scope, params=api_query_params, timeout=settings.DEFAULT_API_TIMEOUT)
        
        # --- CORRECCIÓN ---
        video_metadata = response
        
        if not video_metadata.get('video') and not video_metadata.get('file', {}).get('mimeType','').startswith('video/'):
             logger.warning(f"Metadatos obtenidos para '{log_item_description}', pero el item podría no ser un video (sin faceta 'video' o MIME type de video).")
             return {"status": "warning", "action": action_name, "data": video_metadata, "message": "Metadatos obtenidos, pero el item podría no ser un video reconocible por sus metadatos."}
        
        logger.info(f"Metadatos de video para '{log_item_description}' obtenidos exitosamente.")
        return {"status": "success", "data": video_metadata}
        
    except ValueError as ve: 
         return {"status": "error", "action": action_name, "message": f"Error de configuración o parámetro para obtener metadatos de video: {ve}", "http_status": 400}
    except NotImplementedError as nie: 
        return {"status": "error", "action": action_name, "message": f"Dependencia (helper de SharePoint) no implementada o no importada: {nie}", "http_status": 501}
    except Exception as e:
        return _handle_stream_api_error(e, action_name, params)


def get_video_playback_url(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "stream_get_video_playback_url"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    # Esta función simplemente llama a obtener_metadatos_video y extrae la downloadUrl.
    # Los parámetros necesarios son los mismos que para obtener_metadatos_video:
    # item_id_or_path, drive_scope, y opcionalmente user_id (para user scope),
    # site_identifier, drive_identifier (para site scope).
    
    logger.info(f"Intentando obtener URL de reproducción/descarga para video (llamando a 'obtener_metadatos_video'). Params: {params}")
    try:
        # Asegurarse que el select para obtener_metadatos_video incluya @microsoft.graph.downloadUrl
        params_for_metadata = params.copy() # No modificar params original
        current_select = params_for_metadata.get("select", "")
        if "@microsoft.graph.downloadurl" not in current_select.lower():
            params_for_metadata["select"] = f"{current_select},@microsoft.graph.downloadUrl" if current_select else "@microsoft.graph.downloadUrl,id,name,webUrl,video,file"
        
        metadata_response = obtener_metadatos_video(client, params_for_metadata)

        if metadata_response.get("status") != "success":
            # Propagar el error de obtener_metadatos_video, pero asegurar que la acción es la correcta.
            metadata_response["action"] = action_name 
            return metadata_response 
        
        item_data = metadata_response.get("data", {})
        download_url = item_data.get("@microsoft.graph.downloadUrl")
        
        if not download_url:
            item_id_desc = item_data.get("id", params.get("item_id_or_path", "ID no disponible"))
            logger.warning(f"No se encontró '@microsoft.graph.downloadUrl' para el video '{item_id_desc}'.")
            return {
                "status": "error", 
                "action": action_name,
                "message": "No se pudo obtener la URL de descarga/reproducción para el video.", 
                "details": "La propiedad @microsoft.graph.downloadUrl no está presente en los metadatos del item.", 
                "data_source_metadata": item_data, 
                "http_status": 404 
            }
        
        logger.info(f"URL de descarga/reproducción obtenida para video ID '{item_data.get('id')}'.")
        return {
            "status": "success", 
            "data": { # Devolver un subconjunto de información útil junto con la URL
                "id": item_data.get("id"), 
                "name": item_data.get("name"), 
                "webUrl": item_data.get("webUrl"), 
                "playback_url": download_url, 
                "video_info": item_data.get("video"), 
                "file_info": item_data.get("file") 
            }
        }
    except Exception as e: # Captura cualquier excepción no manejada por obtener_metadatos_video
        return _handle_stream_api_error(e, action_name, params)

def obtener_transcripcion_video(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "stream_obtener_transcripcion_video"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    video_item_id_desc = params.get("item_id_or_path", "ID de video no especificado")
    message = (
        f"La obtención o generación de transcripciones de video para '{video_item_id_desc}' no es una función "
        "directa y estándar de Microsoft Graph API para archivos de video genéricos en OneDrive/SharePoint."
    )
    details = (
        "Alternativas y Recomendaciones:\n"
        "1. Búsqueda de Archivo .vtt Asociado: Verifique si un archivo de transcripción (ej. con extensión .vtt o similar) "
        "existe junto al archivo de video en OneDrive/SharePoint. Si es así, puede descargarlo usando las acciones de archivo "
        "correspondientes (ej. 'onedrive_download_file' o 'sp_download_document').\n"
        "2. Stream (en SharePoint): Si el video fue subido y procesado a través de la nueva experiencia de Microsoft Stream "
        "(que almacena videos en SharePoint), la transcripción podría generarse automáticamente y estar disponible a través de "
        "la interfaz de Stream o como un archivo asociado al video. La API de Graph podría no exponer esto directamente para todas las versiones.\n"
        "3. Servicios de Terceros o Azure AI: Utilice servicios especializados como Azure AI Video Indexer. "
        "Suba el video a este servicio para procesarlo y obtener transcripciones, capítulos, información de oradores, etc. "
        "Luego, los resultados (ej. el texto de la transcripción) pueden ser enviados a esta API mediante una acción personalizada "
        "o almacenados donde su aplicación pueda acceder a ellos."
    )
    logger.warning(f"Acción '{action_name}' llamada para '{video_item_id_desc}'. {message}")
    return {
        "status": "not_supported", # O "info_only"
        "action": action_name,
        "message": message,
        "details": details,
        "http_status": 501 # Not Implemented (para una funcionalidad directa no existente)
    }

# --- FIN DEL MÓDULO actions/stream_actions.py ---