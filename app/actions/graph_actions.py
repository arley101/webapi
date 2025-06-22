# app/actions/graph_actions.py
# -*- coding: utf-8 -*-
import logging
import requests # Para requests.exceptions.HTTPError
import json # Para el helper de error
from typing import Dict, List, Optional, Any

from app.core.config import settings # Para acceder a GRAPH_API_DEFAULT_SCOPE, GRAPH_API_BASE_URL
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

def _handle_generic_graph_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Helper para manejar errores genéricos de Graph API."""
    log_message = f"Error en Graph Action '{action_name}'"
    safe_params = {} # Inicializar safe_params
    if params_for_log:
        # Evitar loguear el payload si es muy grande o sensible
        sensitive_keys = ['payload', 'json_data', 'data']
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
            error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text)
            graph_error_code = error_info.get("code")
        except json.JSONDecodeError: # Corregido para usar json.JSONDecodeError
            details_str = e.response.text[:500] if e.response.text else "No response body"
            
    return {
        "status": "error",
        "action": action_name,
        "message": f"Error ejecutando acción genérica de Graph '{action_name}': {details_str}",
        "http_status": status_code_int,
        "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
        "graph_error_code": graph_error_code
    }

def generic_get(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "graph_generic_get" # Nombre de la acción pública
    # Loggear params de forma segura
    log_params = {k: v for k, v in params.items() if k not in ['custom_headers']} # Ejemplo de filtrado
    logger.info(f"Ejecutando {action_name} con params: %s", log_params)
    
    graph_path: Optional[str] = params.get("graph_path")
    
    if not graph_path:
        logger.error(f"{action_name}: El parámetro 'graph_path' es requerido en 'params'. Params recibidos: {params}")
        return {
            "status": "error", "action": action_name, 
            "message": "'graph_path' es requerido dentro de 'params' (ej. {'graph_path': 'organization'}).", 
            "http_status": 400, "details": f"Params recibidos: {params}"
        }

    base_url_override_str = params.get("base_url", str(settings.GRAPH_API_BASE_URL))
    
    # Permitir especificar beta endpoint o una versión diferente
    if params.get("api_version") == "beta":
        base_url_override_str = "https://graph.microsoft.com/beta"
    
    full_url = f"{base_url_override_str.rstrip('/')}/{graph_path.lstrip('/')}"
    
    query_api_params: Optional[Dict[str, Any]] = params.get("query_params")
    custom_scope_list: Optional[List[str]] = params.get("custom_scope")
    scope_to_use = custom_scope_list if custom_scope_list else settings.GRAPH_API_DEFAULT_SCOPE
    custom_headers: Optional[Dict[str, str]] = params.get("custom_headers")

    logger.info(f"{action_name}: Realizando GET a Graph API. Path: {graph_path}, URL: {full_url}, Scope: {scope_to_use}, QueryParams: {query_api_params}, Headers: {bool(custom_headers)}")
    try:
        response = client.get(full_url, scope=scope_to_use, params=query_api_params, headers=custom_headers)
        
        # --- CORRECCIÓN ---
        # `client.get` ya devuelve un dict (o str/bytes), no un objeto response.
        # Asumimos un estado 200 OK si no hay excepción, que es el comportamiento de `http_client`.
        data = response
        http_status = 200 # Asumir 200 OK en caso de éxito, ya que client.get no devuelve el status.
        
        if isinstance(data, str):
            logger.info(f"Respuesta GET genérica a Graph para {full_url} no es JSON, devolviendo texto.")
        
        return {"status": "success", "data": data, "http_status": http_status}
    except Exception as e:
        # Pasar los params originales (no log_params) al helper de error para contexto completo.
        return _handle_generic_graph_api_error(e, action_name, params)

def generic_post(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "generic_post" # Nombre de la acción pública
    log_params = {k: v for k, v in params.items() if k not in ['payload', 'json_data', 'data', 'custom_headers']}
    if 'payload' in params or 'json_data' in params or 'data' in params:
        log_params["payload_provided"] = True
    logger.info(f"Ejecutando {action_name} con params: %s", log_params)
    
    graph_path: Optional[str] = params.get("graph_path")
    payload: Optional[Dict[str, Any]] = params.get("payload") # El cuerpo JSON para el POST

    if not graph_path:
        logger.error(f"{action_name}: El parámetro 'graph_path' es requerido. Params recibidos: {params}")
        return {"status": "error", "action": action_name, "message": "'graph_path' es requerido.", "http_status": 400}
    # El payload es opcional para algunos POSTs que solo disparan una acción.

    base_url_override_str = params.get("base_url", str(settings.GRAPH_API_BASE_URL))
    if params.get("api_version") == "beta":
        base_url_override_str = "https://graph.microsoft.com/beta"
        
    full_url = f"{base_url_override_str.rstrip('/')}/{graph_path.lstrip('/')}"
    
    custom_scope_list: Optional[List[str]] = params.get("custom_scope")
    scope_to_use = custom_scope_list if custom_scope_list else settings.GRAPH_API_DEFAULT_SCOPE
    custom_headers: Optional[Dict[str, str]] = params.get("custom_headers")

    logger.info(f"{action_name}: Realizando POST a Graph API. Path: {graph_path}, URL: {full_url}, Scope: {scope_to_use}, Payload presente: {bool(payload)}, Headers: {bool(custom_headers)}")
    try:
        response = client.post(full_url, scope=scope_to_use, json_data=payload, headers=custom_headers)
        
        if response.status_code in [201, 200] and response.content:
            try:
                data = response.json()
                return {"status": "success", "data": data, "http_status": response.status_code}
            except requests.exceptions.JSONDecodeError:
                logger.info(f"Respuesta POST genérica a Graph para {full_url} no es JSON (status {response.status_code}), devolviendo texto.")
                return {"status": "success", "data": response.text, "http_status": response.status_code}
        elif response.status_code in [202, 204]: 
             logger.info(f"Solicitud POST genérica a Graph para {full_url} exitosa con status {response.status_code} (sin contenido de respuesta esperado).")
             return {"status": "success", "message": f"Operación POST completada con estado {response.status_code}.", "http_status": response.status_code, "data": None}
        else: 
            logger.info(f"Respuesta POST genérica a Graph para {full_url} con status {response.status_code}. Contenido: {response.text[:100]}...")
            return {"status": "success", "data": response.text, "http_status": response.status_code}
    except Exception as e:
        return _handle_generic_graph_api_error(e, action_name, params)

# --- Funciones de Compatibilidad para el Asistente GPT ---
# Estas funciones aceptan **kwargs y los reempaquetan en el diccionario 'params'
# que las funciones originales esperan.

def generic_get_compat(client: AuthenticatedHttpClient, **kwargs: Any) -> Dict[str, Any]:
    # No se usa 'params = params or {}' aquí porque kwargs es el que tiene los datos.
    action_name_log = "graph_generic_get_compat" # Para logging
    logger.info(f"Ejecutando {action_name_log} con kwargs: {kwargs}")
    # kwargs aquí contendrá las claves que el plugin desempaquetó, ej. {'graph_path': 'organization'}
    # o {'graph_path': 'users', 'query_params': {'$top': 2}}
    # Se pasan estos kwargs como el diccionario 'params' a generic_get.
    return generic_get(client, kwargs) 

def generic_post_compat(client: AuthenticatedHttpClient, **kwargs: Any) -> Dict[str, Any]:
    action_name_log = "graph_generic_post_compat"
    log_kwargs = {k:v for k,v in kwargs.items() if k not in ['payload']} # Omitir payload del log
    if 'payload' in kwargs: log_kwargs['payload_provided'] = True
    logger.info(f"Ejecutando {action_name_log} con kwargs: {log_kwargs}")
    # kwargs contendrá las claves desempaquetadas y el objeto 'payload' si el asistente lo envió correctamente anidado.
    # O, si el asistente envía 'payload' como un kwarg más (ej. payload={"key": "value"}), también funcionará.
    return generic_post(client, kwargs)

# --- FIN DEL MÓDULO actions/graph_actions.py ---