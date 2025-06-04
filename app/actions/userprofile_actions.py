# app/actions/userprofile_actions.py
import logging
import requests # Para requests.exceptions.HTTPError y otros usos si fueran necesarios
import json # Para el helper de error
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

def _handle_userprofile_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en UserProfile action '{action_name}'"
    safe_params = {}
    if params_for_log:
        sensitive_keys = ['update_payload', 'passwordProfile'] 
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    details_str = str(e); status_code_int = 500; graph_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json(); error_info = error_data.get("error", error_data)
            details_str = error_info.get("message", e.response.text); graph_error_code = error_info.get("code")
        except json.JSONDecodeError: 
            details_str = e.response.text[:500] if e.response.text else "No response body"
    return {
        "status": "error", "action": action_name,
        "message": f"Error en {action_name}: {details_str}", 
        "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
        "http_status": status_code_int, "graph_error_code": graph_error_code
    }

def profile_get_my_profile(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "profile_get_my_profile"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    user_id: Optional[str] = params.get("user_id") 
    if not user_id:
        return _handle_userprofile_api_error(ValueError("'user_id' es requerido."), action_name, params)
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id}" 
    default_select = "id,displayName,givenName,surname,userPrincipalName,jobTitle,mail,mobilePhone,officeLocation,businessPhones,aboutMe,birthday,hireDate,interests,mySite,pastProjects,preferredLanguage,responsibilities,schools,skills"
    select_fields = params.get("select", default_select)
    query_api_params = {"$select": select_fields}
    try:
        profile_scope = getattr(settings, 'GRAPH_SCOPE_USER_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
        response_data = client.get(url, scope=profile_scope, params=query_api_params)
        if not isinstance(response_data, dict):
            raise Exception(f"Respuesta inesperada de client.get (se esperaba dict): {type(response_data)}. Contenido: {str(response_data)[:200]}")
        if response_data.get("status") == "error" and "http_status" in response_data: return response_data # Propagar error de http_client
        return {"status": "success", "data": response_data}
    except ValueError as ve: return _handle_userprofile_api_error(ve, action_name, params)
    except Exception as e: return _handle_userprofile_api_error(e, action_name, params)

def profile_get_my_manager(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "profile_get_my_manager"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    user_id: Optional[str] = params.get("user_id")
    if not user_id: return _handle_userprofile_api_error(ValueError("'user_id' es requerido."), action_name, params)
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/manager"
    default_select = "id,displayName,userPrincipalName,jobTitle,mail"
    select_fields = params.get("select", default_select)
    query_api_params = {"$select": select_fields}
    try:
        manager_scope = getattr(settings, 'GRAPH_SCOPE_USER_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
        response_data = client.get(url, scope=manager_scope, params=query_api_params)
        if not isinstance(response_data, dict):
            raise Exception(f"Respuesta inesperada de client.get para manager: {type(response_data)}")
        if response_data.get("status") == "error" and "http_status" in response_data: return response_data
        return {"status": "success", "data": response_data}
    except requests.exceptions.HTTPError as http_err:
        if http_err.response is not None and http_err.response.status_code == 404:
            return {"status": "success", "data": None, "message": "Manager no encontrado."} 
        return _handle_userprofile_api_error(http_err, action_name, params)
    except ValueError as ve: return _handle_userprofile_api_error(ve, action_name, params)
    except Exception as e: return _handle_userprofile_api_error(e, action_name, params)

def profile_get_my_direct_reports(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "profile_get_my_direct_reports"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    user_id: Optional[str] = params.get("user_id")
    if not user_id: return _handle_userprofile_api_error(ValueError("'user_id' es requerido."), action_name, params)
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/directReports"
    default_select = "id,displayName,userPrincipalName,jobTitle,mail"
    select_fields = params.get("select", default_select)
    query_api_params: Dict[str,Any] = {"$select": select_fields}
    if params.get("$top"): query_api_params["$top"] = params["$top"] 
    try:
        reports_scope = getattr(settings, 'GRAPH_SCOPE_USER_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
        response_data = client.get(url, scope=reports_scope, params=query_api_params)
        if not isinstance(response_data, dict):
            raise Exception(f"Respuesta inesperada de client.get para direct reports: {type(response_data)}")
        if response_data.get("status") == "error" and "http_status" in response_data: return response_data
        return {"status": "success", "data": response_data.get("value", [])} # Graph devuelve una colección bajo "value"
    except ValueError as ve: return _handle_userprofile_api_error(ve, action_name, params)
    except Exception as e: return _handle_userprofile_api_error(e, action_name, params)

def profile_get_my_photo(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Any: 
    params = params or {}; action_name = "profile_get_my_photo"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    user_id: Optional[str] = params.get("user_id")
    if not user_id: return _handle_userprofile_api_error(ValueError("'user_id' es requerido."), action_name, params)
    photo_size: Optional[str] = params.get("size") 
    url_photo_segment = f"photos/{photo_size}" if photo_size else "photo"
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id}/{url_photo_segment}/$value"
    try:
        photo_scope = getattr(settings, 'GRAPH_SCOPE_USER_READ_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
        response_content = client.get(url, scope=photo_scope, stream=True) # client.get devuelve bytes si stream=True y es exitoso
        if isinstance(response_content, bytes):
            return response_content 
        elif isinstance(response_content, dict) and response_content.get("status") == "error":
            return response_content 
        else:
            return _handle_userprofile_api_error(Exception(f"Respuesta inesperada al obtener foto: {type(response_content)}"), action_name, params)
    except requests.exceptions.HTTPError as http_err:
        if http_err.response is not None and http_err.response.status_code == 404:
            return {"status": "error", "action": action_name, "message": "Foto de perfil no encontrada.", "http_status": 404, "details": "Usuario sin foto o tamaño no existe."}
        return _handle_userprofile_api_error(http_err, action_name, params)
    except ValueError as ve: return _handle_userprofile_api_error(ve, action_name, params)
    except Exception as e: return _handle_userprofile_api_error(e, action_name, params)

def profile_update_my_profile(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "profile_update_my_profile"
    log_params = {k:v for k,v in params.items() if k != 'update_payload'}
    logger.info(f"Ejecutando {action_name} con params: {log_params}")
    user_id: Optional[str] = params.get("user_id"); update_payload: Optional[Dict[str, Any]] = params.get("update_payload")
    if not user_id: return _handle_userprofile_api_error(ValueError("'user_id' es requerido."), action_name, params)
    if not update_payload or not isinstance(update_payload, dict) or not update_payload: 
        return _handle_userprofile_api_error(ValueError("'update_payload' (dict no vacío) es requerido."), action_name, params)
    url = f"{settings.GRAPH_API_BASE_URL}/users/{user_id}"
    try:
        update_scope = getattr(settings, 'GRAPH_SCOPE_USER_READWRITE_ALL', settings.GRAPH_API_DEFAULT_SCOPE) # type: ignore
        response_obj = client.patch(url, scope=update_scope, json_data=update_payload) # client.patch devuelve requests.Response
        if response_obj.status_code == 204:
            get_params = {"user_id": user_id}
            if params.get("select_after_update"): get_params["select"] = params["select_after_update"] # type: ignore
            else: get_params["select"] = "id,displayName,givenName,surname,userPrincipalName,jobTitle,mail,mobilePhone,officeLocation,businessPhones,aboutMe,birthday,hireDate,interests,mySite,pastProjects,preferredLanguage,responsibilities,schools,skills"
            updated_profile_response = profile_get_my_profile(client, get_params)
            if updated_profile_response.get("status") == "success":
                return {"status": "success", "data": updated_profile_response.get("data"), "message": "Perfil actualizado."}
            else: return {"status": "success", "message": "Perfil actualizado (204), falló re-obtención.", "http_status": 204, "details_get_failed": updated_profile_response}
        else: 
            response_data = response_obj.json() if response_obj.content else {}
            return {"status": "warning", "data": response_data, "message": f"Actualización de perfil devolvió {response_obj.status_code}.", "http_status": response_obj.status_code}
    except Exception as e: return _handle_userprofile_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/userprofile_actions.py ---