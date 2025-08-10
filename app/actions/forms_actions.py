# app/actions/forms_actions.py
import requests
import json
from typing import Dict, List, Optional, Any
import urllib.parse
import logging
from datetime import datetime

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

def _handle_forms_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Forms Action '{action_name}'"
    if params_for_log:
        log_message += f" con params: {params_for_log}"
    
    # Definir placeholders para que el módulo cargue, pero las funciones fallarán si se llaman.
    def _obtener_site_id_sp(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> str:
        raise NotImplementedError("Helper _obtener_site_id_sp no disponible desde forms_actions.")
    def _get_drive_id(client: AuthenticatedHttpClient, site_id: str, drive_id_or_name_input: Optional[str] = None) -> str:
        raise NotImplementedError("Helper _get_drive_id no disponible desde forms_actions.")

def _handle_forms_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Forms Action '{action_name}'"
    if params_for_log:
        log_message += f" con params: {params_for_log}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    graph_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json()
            error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text)
            graph_error_code = error_info.get("code")
        except json.JSONDecodeError: # Corregido
            details_str = e.response.text[:500] if e.response.text else "No response body"
            
    return {
        "status": "error", 
        "action": action_name,
        "message": f"Error en {action_name}: {details_str}", 
        "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
        "http_status": status_code_int,
        "graph_error_code": graph_error_code
    }


def list_forms(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "forms_list_forms"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    drive_scope: str = params.get('drive_scope', 'me').lower()
    search_text: Optional[str] = params.get('search_query') 
    top: int = min(int(params.get('top', 25)), 200) # Límite para búsqueda Graph

    # Query para buscar archivos que son Forms.
    # El tipo de paquete 'Form' o 'FormPackage' puede ser un buen indicador.
    # `file:contentType:FormPackage` o buscar por nombre.
    base_form_query = 'package/type eq \'Form\' OR file/mimeType eq \'application/vnd.ms-form\''
    if search_text:
        effective_search_query = f"({search_text}) AND ({base_form_query})"
    else:
        effective_search_query = base_form_query
    
    # Nota: El endpoint de búsqueda de Drive es /search(q='...'). 
    # $filter no se usa con /search. Los OData params como $select, $top se aplican a la URL de /search.
    
    api_query_odata_params = {
        '$top': top,
        '$select': params.get('select', 'id,name,webUrl,createdDateTime,lastModifiedDateTime,size,parentReference,file,package')
    }

    search_url_path_base: str 
    log_location_description: str
    user_identifier_for_me_drive = params.get("user_id") # Para OneDrive de otro usuario

    try:
        if drive_scope == 'me':
            drive_id_param = params.get("drive_id") 
            user_path_segment = f"users/{user_identifier_for_me_drive}" if user_identifier_for_me_drive else "me"
            
            if drive_id_param:
                search_url_path_base = f"/{user_path_segment}/drives/{drive_id_param}/root"
                log_location_description = f"OneDrive (drive ID: {drive_id_param}) de '{user_path_segment}'"
            else: 
                search_url_path_base = f"/{user_path_segment}/drive/root"
                log_location_description = f"OneDrive principal de '{user_path_segment}'"
        elif drive_scope == 'site':
            site_identifier = params.get('site_identifier', params.get('site_id'))
            drive_identifier = params.get('drive_identifier', params.get('drive_id_or_name'))

            if not site_identifier: # drive_identifier puede ser opcional si se usa el default del sitio
                return {"status": "error", "action": action_name, "message": "Si 'drive_scope' es 'site', se requiere 'site_identifier' (o 'site_id').", "http_status": 400}
            
            site_id = _obtener_site_id_sp(client, {"site_identifier": site_identifier, **params}) # Pasa params para que _obtener_site_id_sp tenga contexto si necesita default
            drive_id = _get_drive_id(client, site_id, drive_identifier) # drive_identifier puede ser None para usar default
            search_url_path_base = f"/sites/{site_id}/drives/{drive_id}/root"
            log_location_description = f"Drive '{drive_id}' en sitio '{site_id}'"
        else:
            return {"status": "error", "action": action_name, "message": "'drive_scope' debe ser 'me' o 'site'.", "http_status": 400}

        encoded_query = urllib.parse.quote_plus(effective_search_query)
        url = f"{settings.GRAPH_API_BASE_URL}{search_url_path_base}/search(q='{encoded_query}')"

        logger.info(f"Buscando Formularios (Query Graph: '{effective_search_query}') en {log_location_description}")
        
        forms_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response = client.get(url=url, scope=forms_read_scope, params=api_query_odata_params) 
        
        # --- CORRECCIÓN ---
        search_results_data = response
        
        items_found: List[Dict[str, Any]] = []
        raw_value = search_results_data.get('value', [])
        if isinstance(raw_value, list):
            for hit_or_container in raw_value:
                resource_item = None
                # El resultado de /search puede ser una lista de DriveItems o una estructura más anidada
                if isinstance(hit_or_container, dict) and 'resource' in hit_or_container and isinstance(hit_or_container['resource'], dict):
                    resource_item = hit_or_container['resource']
                elif isinstance(hit_or_container, dict) and 'id' in hit_or_container and 'name' in hit_or_container : 
                    resource_item = hit_or_container 
                
                if resource_item:
                    # Confirmar si es un Form revisando el tipo de paquete o MIME type
                    is_form_package = resource_item.get("package", {}).get("type", "").lower() == "form"
                    is_form_mimetype = resource_item.get("file", {}).get("mimeType") == "application/vnd.ms-form"
                    # A veces los forms son solo .xlsx que contienen el form, no se detectan así.
                    # La búsqueda por 'contentType:FormPackage' es más directa si el indexador de Graph lo soporta bien.
                    if is_form_package or is_form_mimetype or ".form" in resource_item.get("name", "").lower():
                        items_found.append(resource_item)
        
        logger.info(f"Se encontraron {len(items_found)} archivos que podrían ser Formularios en {log_location_description}.")
        return {"status": "success", "data": items_found, "total_retrieved": len(items_found)}

    except ValueError as ve: 
         return {"status": "error", "action": action_name, "message": f"Error de configuración o parámetro para búsqueda de Forms: {ve}", "http_status": 400}
    except NotImplementedError as nie:
        return {"status": "error", "action": action_name, "message": f"Dependencia no implementada: {nie}", "http_status": 501}
    except Exception as e:
        return _handle_forms_api_error(e, action_name, params)


def get_form(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "forms_get_form"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    form_item_id: Optional[str] = params.get("form_item_id") # ID del DriveItem del Form
    drive_id: Optional[str] = params.get("drive_id")
    site_id: Optional[str] = params.get("site_id") # ID del sitio de SharePoint si el Form está en un drive de sitio
    user_id_for_me_drive: Optional[str] = params.get("user_id") # Si el Form está en el OneDrive de otro usuario

    select_fields: str = params.get("select", "id,name,webUrl,createdDateTime,lastModifiedDateTime,size,parentReference,file,package,@microsoft.graph.downloadUrl")

    if not form_item_id: # drive_id y site_id/user_id pueden ser opcionales si el form_item_id es globalmente único y el contexto lo permite
        return {"status": "error", "action": action_name, "message": "'form_item_id' es requerido.", "http_status": 400}

    url_base_item: str
    log_target: str

    if site_id and drive_id: # Form en un drive de SharePoint
        url_base_item = f"{settings.GRAPH_API_BASE_URL}/sites/{site_id}/drives/{drive_id}/items/{form_item_id}"
        log_target = f"item Form (DriveItem) ID '{form_item_id}' en drive '{drive_id}' del sitio '{site_id}'"
    elif drive_id: # Form en un drive de usuario (propio o de otro)
        user_path_segment = f"users/{user_id_for_me_drive}" if user_id_for_me_drive else "me"
        url_base_item = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/drives/{drive_id}/items/{form_item_id}"
        log_target = f"item Form (DriveItem) ID '{form_item_id}' en drive '{drive_id}' de '{user_path_segment}'"
    else: # Si solo se tiene form_item_id, es ambiguo sin drive/sitio.
          # Podríamos intentar /me/drive/items/{form_item_id} como un fallback muy genérico si no hay más info.
          # Pero es mejor requerir el contexto del drive.
        logger.warning(f"{action_name}: Se recomienda proveer 'drive_id' y ('site_id' o 'user_id') para precisión.")
        user_path_segment = f"users/{user_id_for_me_drive}" if user_id_for_me_drive else "me"
        url_base_item = f"{settings.GRAPH_API_BASE_URL}/{user_path_segment}/drive/items/{form_item_id}" # Asume drive principal
        log_target = f"item Form (DriveItem) ID '{form_item_id}' en drive principal de '{user_path_segment}' (contexto de drive no especificado explícitamente)"

    api_query_odata_params = {"$select": select_fields}

    logger.info(f"Obteniendo metadatos del archivo de Formulario: {log_target}")
    forms_read_scope = getattr(settings, 'GRAPH_SCOPE_FILES_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
    try:
        response = client.get(url=url_base_item, scope=forms_read_scope, params=api_query_odata_params)
        
        # --- CORRECCIÓN ---
        form_file_metadata = response
        
        is_confirmed_form_file = False
        if form_file_metadata.get("package", {}).get("type", "").lower() == "form":
            is_confirmed_form_file = True
        elif ".form" in form_file_metadata.get("name", "").lower():
            is_confirmed_form_file = True
        elif form_file_metadata.get("file", {}).get("mimeType") == "application/vnd.ms-form":
            is_confirmed_form_file = True
        
        message = "Metadatos del archivo obtenidos."
        if is_confirmed_form_file:
            message += " El item parece ser un archivo de Microsoft Form."
            logger.info(f"Metadatos del Formulario '{form_item_id}' obtenidos. Confirmado como archivo de Form.")
        else:
            message += " El item podría no ser un archivo de Microsoft Form reconocible por sus metadatos."
            logger.warning(f"Item '{form_item_id}' obtenido, pero no se pudo confirmar como archivo de Form por 'package.type' o 'name'.")

        return {"status": "success", "data": form_file_metadata, "is_confirmed_form_file": is_confirmed_form_file, "message": message}
    except Exception as e:
        return _handle_forms_api_error(e, action_name, params)


def get_form_responses(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "forms_get_form_responses"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    form_id_param: Optional[str] = params.get("form_id") # Este es el ID del Form en el servicio Forms, no el DriveItem ID.
    
    message = (
        f"La obtención de respuestas para Microsoft Forms (ID de Form servicio: {form_id_param or 'desconocido'}) "
        "directamente a través de Microsoft Graph API no está soportada de forma estándar y fiable para aplicaciones."
    )
    details = (
        "Solución Recomendada: Utilizar Power Automate (o Logic Apps).\n"
        "1. Crear un flujo en Power Automate que se active con 'Cuando se envía una respuesta nueva' (desde el conector de Microsoft Forms).\n"
        "2. En el flujo, usar la acción 'Obtener los detalles de la respuesta' (del conector de Microsoft Forms), pasando el ID de la respuesta del trigger.\n"
        "3. Enviar los detalles de la respuesta (como un objeto JSON) mediante una acción 'HTTP POST' a esta API (EliteDynamicsAPI), "
        "invocando una acción personalizada que esté diseñada para recibir y procesar dichos datos (ej. una acción como 'procesar_form_respuesta_powerautomate').\n"
        "Esta función actual ('forms_get_form_responses') es un placeholder y no puede recuperar respuestas de Forms vía Graph API."
    )
    logger.warning(f"Acción '{action_name}' llamada para Form ID de servicio '{form_id_param}'. {message}")
    return {
        "status": "not_supported",
        "action": action_name,
        "message": message,
        "details": details,
        "http_status": 501 # Not Implemented
    }

def _obtener_site_id_sp(graph_client) -> str:
    """Obtiene el site ID de SharePoint"""
    try:
        site_url = "https://graph.microsoft.com/v1.0/sites/root"
        response = graph_client.get(site_url)
        response.raise_for_status()
        return response.json().get('id')
    except Exception as e:
        logger.error(f"Error obteniendo site ID: {str(e)}")
        return None

def _get_drive_id(graph_client, site_id: str) -> str:
    """Obtiene el drive ID del sitio"""
    try:
        drive_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"
        response = graph_client.get(drive_url)
        response.raise_for_status()
        return response.json().get('id')
    except Exception as e:
        logger.error(f"Error obteniendo drive ID: {str(e)}")
        return None

# --- FIN DEL MÓDULO actions/forms_actions.py ---