# app/actions/userprofile_actions.py
import logging
import requests # Para requests.exceptions.HTTPError y otros usos si fueran necesarios
import json # Para el helper de error
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# Helper de error específico para este módulo o reutilizar uno genérico de Graph si se prefiere
def _handle_userprofile_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en UserProfile action '{action_name}'"
    safe_params = {}
    if params_for_log:
        # Especificar claves sensibles si las hay en los payloads de userprofile
        sensitive_keys = ['update_payload', 'passwordProfile'] 
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    graph_error_code = None

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json()
            error_info = error_data.get("error", error_data) # Tomar el objeto 'error' o el cuerpo completo
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

# --- Funciones de Acción para UserProfile ---

def profile_get_my_profile(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "profile_get_my_profile"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    user_id: Optional[str] = params.get("user_id") 
    if not user_id:
        return _handle_userprofile_api_error(ValueError("'user_id' es requerido en params para obtener el perfil de un usuario específico."), action_name, params)

    # Para obtener el perfil de un usuario específico (no el de la app 'me')
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id}" 
    
    # Propiedades comunes del perfil. Ajustar según necesidad.
    default_select = "id,displayName,givenName,surname,userPrincipalName,jobTitle,mail,mobilePhone,officeLocation,businessPhones,aboutMe,birthday,hireDate,interests,mySite,pastProjects,preferredLanguage,responsibilities,schools,skills"
    select_fields = params.get("select", default_select)
    query_api_params = {"$select": select_fields}

    logger.info(f"Obteniendo perfil para user_id: '{user_id}' con select: '{select_fields}'")
    
    try:
        # User.Read.All es necesario para leer el perfil completo de cualquier usuario con permisos de aplicación.
        profile_scope = getattr(settings, 'GRAPH_SCOPE_USER_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        # El método http_client.get ahora puede devolver dict, str, o bytes.
        # Para esta llamada, esperamos un dict (JSON).
        response_data = client.get(url, scope=profile_scope, params=query_api_params)
        
        if isinstance(response_data, dict):
            # Si get devolvió un dict de error ya formateado por el client, propagarlo.
            if response_data.get("status") == "error":
                return response_data
            return {"status": "success", "data": response_data}
        else: # Si devolvió string o bytes, es inesperado para este endpoint.
            logger.error(f"Respuesta inesperada de client.get para perfil (se esperaba dict): {type(response_data)}. Contenido: {str(response_data)[:200]}")
            return _handle_userprofile_api_error(Exception(f"Tipo de respuesta inesperado del cliente HTTP: {type(response_data)}"), action_name, params)

    except ValueError as ve: # Errores de parámetros o de token no obtenido en client.get
        return _handle_userprofile_api_error(ve, action_name, params)
    except Exception as e: # Errores de red o HTTP que client.get pudo haber relanzado
        return _handle_userprofile_api_error(e, action_name, params)

def profile_get_my_manager(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "profile_get_my_manager"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    user_id: Optional[str] = params.get("user_id")
    if not user_id:
        return _handle_userprofile_api_error(ValueError("'user_id' es requerido."), action_name, params)

    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/manager"
    default_select = "id,displayName,userPrincipalName,jobTitle,mail"
    select_fields = params.get("select", default_select)
    query_api_params = {"$select": select_fields}
    
    logger.info(f"Obteniendo manager para user_id: '{user_id}'")
    try:
        manager_scope = getattr(settings, 'GRAPH_SCOPE_USER_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_data = client.get(url, scope=manager_scope, params=query_api_params)
        
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data # Error del client
            return {"status": "success", "data": response_data}
        else:
            logger.error(f"Respuesta inesperada de client.get para manager: {type(response_data)}")
            return _handle_userprofile_api_error(Exception(f"Tipo de respuesta inesperado: {type(response_data)}"), action_name, params)

    except requests.exceptions.HTTPError as http_err:
        if http_err.response is not None and http_err.response.status_code == 404:
            logger.info(f"Manager no encontrado (404) para user_id '{user_id}'.")
            # Devolver un éxito con data=None para indicar que no tiene manager, no que la API falló.
            return {"status": "success", "data": None, "message": "Manager no encontrado."} 
        return _handle_userprofile_api_error(http_err, action_name, params) # Otros errores HTTP
    except ValueError as ve:
        return _handle_userprofile_api_error(ve, action_name, params)
    except Exception as e:
        return _handle_userprofile_api_error(e, action_name, params)

def profile_get_my_direct_reports(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "profile_get_my_direct_reports"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    user_id: Optional[str] = params.get("user_id")
    if not user_id:
        return _handle_userprofile_api_error(ValueError("'user_id' es requerido."), action_name, params)

    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/directReports"
    default_select = "id,displayName,userPrincipalName,jobTitle,mail"
    select_fields = params.get("select", default_select)
    
    query_api_params: Dict[str,Any] = {"$select": select_fields}
    if params.get("$top"): query_api_params["$top"] = params["$top"] 
    # $skip y paginación completa podrían añadirse si es necesario
    
    logger.info(f"Obteniendo reportes directos para user_id: '{user_id}'")
    try:
        reports_scope = getattr(settings, 'GRAPH_SCOPE_USER_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_data = client.get(url, scope=reports_scope, params=query_api_params)
        
        if isinstance(response_data, dict):
            if response_data.get("status") == "error": return response_data
            # Graph devuelve una colección bajo "value"
            return {"status": "success", "data": response_data.get("value", [])}
        elif isinstance(response_data, list): # Por si Graph devuelve directamente la lista
            return {"status": "success", "data": response_data}
        else:
            logger.error(f"Respuesta inesperada de client.get para direct reports: {type(response_data)}")
            return _handle_userprofile_api_error(Exception(f"Tipo de respuesta inesperado: {type(response_data)}"), action_name, params)
            
    except ValueError as ve:
        return _handle_userprofile_api_error(ve, action_name, params)
    except Exception as e:
        return _handle_userprofile_api_error(e, action_name, params)

def profile_get_my_photo(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Any: 
    params = params or {}
    action_name = "profile_get_my_photo"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    user_id: Optional[str] = params.get("user_id")
    if not user_id:
        return _handle_userprofile_api_error(ValueError("'user_id' es requerido."), action_name, params)
        
    photo_size: Optional[str] = params.get("size") 
    
    url_photo_segment = "photo"
    if photo_size:
        # Validar que photo_size sea uno de los formatos soportados si es necesario
        # Ej: "48x48", "64x64", "96x96", "120x120", "240x240", "360x360", "432x432", "504x504", "648x648"
        url_photo_segment = f"photos/{photo_size}"

    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/{url_photo_segment}/$value"
    logger.info(f"Obteniendo foto de perfil (tamaño: {photo_size or 'default'}) para user_id: '{user_id}'")
    
    try:
        photo_scope = getattr(settings, 'GRAPH_SCOPE_USER_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        # Pasar stream=True para que el http_client.get sepa que puede ser binario
        response_content = client.get(url, scope=photo_scope, stream=True) 
        
        if isinstance(response_content, bytes):
            return response_content # Devolver los bytes directamente, el router los manejará
        elif isinstance(response_content, dict) and response_content.get("status") == "error":
            # Si http_client.get ya devolvió un error formateado (ej. por 404), propagarlo.
            return response_content 
        else:
            # Si no son bytes ni un error formateado del client, es inesperado.
            logger.error(f"Se esperaban bytes de la foto pero se recibió tipo {type(response_content)}: {str(response_content)[:200]}")
            return _handle_userprofile_api_error(Exception("Respuesta inesperada al obtener la foto."), action_name, params)

    except requests.exceptions.HTTPError as http_err:
        # Este bloque se activaría si client.get relanza el error HTTP en lugar de manejarlo.
        # Con la nueva implementación de get en http_client.py, debería manejar 404 y devolver texto/json de error.
        # Pero por si acaso, o si otro tipo de HTTPError ocurre.
        if http_err.response is not None and http_err.response.status_code == 404:
            logger.warning(f"Foto de perfil no encontrada (404) para user_id '{user_id}' vía HTTPError.")
            return {"status": "error", "action": action_name, "message": "Foto de perfil no encontrada.", "http_status": 404, "details": "El usuario podría no tener una foto o el tamaño solicitado no existe."}
        return _handle_userprofile_api_error(http_err, action_name, params)
    except ValueError as ve: # Para errores de scope/token desde client.get
        return _handle_userprofile_api_error(ve, action_name, params)
    except Exception as e: # Otros errores
        return _handle_userprofile_api_error(e, action_name, params)

def profile_update_my_profile(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "profile_update_my_profile"
    log_params = {k:v for k,v in params.items() if k != 'update_payload'}
    if 'update_payload' in params : log_params['update_payload_keys'] = list(params['update_payload'].keys())
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    user_id: Optional[str] = params.get("user_id")
    update_payload: Optional[Dict[str, Any]] = params.get("update_payload")

    if not user_id:
        return _handle_userprofile_api_error(ValueError("'user_id' es requerido."), action_name, params)
    if not update_payload or not isinstance(update_payload, dict) or not update_payload: # Payload no puede ser vacío
        return _handle_userprofile_api_error(ValueError("'update_payload' (dict no vacío con propiedades a actualizar) es requerido."), action_name, params)

    # Las propiedades del perfil de usuario (aboutMe, skills, etc.) se actualizan en el objeto /users/{id}.
    # El recurso /profile es de solo lectura.
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id}"
    
    logger.info(f"Actualizando propiedades de usuario para user_id: '{user_id}'. Payload keys: {list(update_payload.keys())}")
    try:
        # User.ReadWrite.All es necesario para actualizar propiedades de otros usuarios.
        update_scope = getattr(settings, 'GRAPH_SCOPE_USER_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE)
        response_obj = client.patch(url, scope=update_scope, json_data=update_payload) # client.patch devuelve requests.Response
        
        # PATCH a /users/{id} devuelve 204 No Content si tiene éxito.
        if response_obj.status_code == 204:
            logger.info(f"Propiedades de usuario para user_id '{user_id}' actualizadas exitosamente (204).")
            # Opcional: re-obtener el perfil para devolverlo
            get_params = {"user_id": user_id}
            # Si el usuario quiere un select específico después de actualizar
            if params.get("select_after_update"): 
                get_params["select"] = params["select_after_update"]
            else: # Usar el mismo select que se usaría en profile_get_my_profile por defecto
                get_params["select"] = "id,displayName,givenName,surname,userPrincipalName,jobTitle,mail,mobilePhone,officeLocation,businessPhones,aboutMe,birthday,hireDate,interests,mySite,pastProjects,preferredLanguage,responsibilities,schools,skills"

            updated_profile_response = profile_get_my_profile(client, get_params) # Llamar a la acción de este módulo
            
            if updated_profile_response.get("status") == "success":
                return {"status": "success", "data": updated_profile_response.get("data"), "message": "Perfil de usuario actualizado."}
            else:
                logger.warning(f"Propiedades de usuario para '{user_id}' actualizadas (204), pero falló la re-obtención. Error: {updated_profile_response.get('message')}")
                return {"status": "success", "message": "Perfil de usuario actualizado (204), pero falló la re-obtención de datos.", "http_status": 204, "details_get_failed": updated_profile_response}
        else: 
            # Si no es 204 pero la librería no lanzó una excepción HTTPError (ej. un 200 OK con cuerpo),
            # lo cual sería inusual para un PATCH a /users/{id}.
            logger.warning(f"Respuesta inesperada {response_obj.status_code} al actualizar perfil de user_id '{user_id}'. Respuesta: {response_obj.text[:200]}")
            response_data = {}
            if response_obj.content:
                try: response_data = response_obj.json()
                except json.JSONDecodeError: response_data = {"raw_response": response_obj.text}
            return {"status": "warning", "data": response_data, "message": f"Actualización de perfil devolvió estado {response_obj.status_code}.", "http_status": response_obj.status_code}
            
    except Exception as e:
        return _handle_userprofile_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/userprofile_actions.py ---