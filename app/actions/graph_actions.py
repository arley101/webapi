# app/actions/graph_actions.py
# -*- coding: utf-8 -*-
import logging
import requests 
import json 
from typing import Dict, List, Optional, Any

from app.core.config import settings 
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

def _handle_generic_graph_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Graph Action '{action_name}'"
    safe_params = {} 
    if params_for_log:
        sensitive_keys = ['payload', 'json_data', 'data']
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    details_str = str(e); status_code_int = 500; graph_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json(); error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text); graph_error_code = error_info.get("code")
        except json.JSONDecodeError: details_str = e.response.text[:500] if e.response.text else "No response body"
    return {
        "status": "error", "action": action_name,
        "message": f"Error ejecutando acción genérica de Graph '{action_name}': {details_str}",
        "http_status": status_code_int, "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
        "graph_error_code": graph_error_code
    }

async async def generic_get(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "graph_generic_get (internal)"
    log_params = {k: v for k, v in params.items() if k not in ['custom_headers']}
    logger.info(f"Ejecutando {action_name} con params: %s", log_params)
    graph_path: Optional[str] = params.get("graph_path")
    if not graph_path: return {"status": "error", "action": action_name, "message": "'graph_path' es requerido.", "http_status": 400}
    base_url_override_str = params.get("base_url", str(settings.GRAPH_API_BASE_URL))
    if params.get("api_version") == "beta": base_url_override_str = "https://graph.microsoft.com/beta"
    full_url = f"{base_url_override_str.rstrip('/')}/{graph_path.lstrip('/')}"
    query_api_params: Optional[Dict[str, Any]] = params.get("query_params")
    custom_scope_list: Optional[List[str]] = params.get("custom_scope")
    scope_to_use = custom_scope_list if custom_scope_list else settings.GRAPH_API_DEFAULT_SCOPE
    custom_headers: Optional[Dict[str, str]] = params.get("custom_headers")
    try:
        response_data = client.get(full_url, scope=scope_to_use, params=query_api_params, headers=custom_headers)
        # client.get ya devuelve dict, str, o bytes. Para generic_get, esperamos dict o str.
        http_status = 200 # Asumir 200 si no es un error ya formateado por el client
        if isinstance(response_data, dict) and response_data.get("status") == "error" and "http_status" in response_data:
             return response_data # Propagar error del http_client
        return {"status": "success", "data": response_data, "http_status": http_status}
    except Exception as e: return _handle_generic_graph_api_error(e, action_name, params)

async async def generic_post(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "generic_post (internal)"
    log_params = {k: v for k, v in params.items() if k not in ['payload', 'json_data', 'data', 'custom_headers']}
    if 'payload' in params or 'json_data' in params or 'data' in params: log_params["payload_provided"] = True
    logger.info(f"Ejecutando {action_name} con params: %s", log_params)
    graph_path: Optional[str] = params.get("graph_path")
    payload: Optional[Dict[str, Any]] = params.get("payload") 
    if not graph_path: return {"status": "error", "action": action_name, "message": "'graph_path' es requerido.", "http_status": 400}
    base_url_override_str = params.get("base_url", str(settings.GRAPH_API_BASE_URL))
    if params.get("api_version") == "beta": base_url_override_str = "https://graph.microsoft.com/beta"
    full_url = f"{base_url_override_str.rstrip('/')}/{graph_path.lstrip('/')}"
    custom_scope_list: Optional[List[str]] = params.get("custom_scope")
    scope_to_use = custom_scope_list if custom_scope_list else settings.GRAPH_API_DEFAULT_SCOPE
    custom_headers: Optional[Dict[str, str]] = params.get("custom_headers")
    try:
        response = client.post(full_url, scope=scope_to_use, json_data=payload, headers=custom_headers) # client.post devuelve requests.Response
        data: Any = None; http_status = response.status_code
        if response.content:
            try: data = response.json()
            except requests.exceptions.JSONDecodeError: data = response.text
        if http_status in [202, 204] and not data: # Accepted or No Content
            return {"status": "success", "message": f"Operación POST completada con estado {http_status}.", "http_status": http_status, "data": None}
        return {"status": "success", "data": data, "http_status": http_status}
    except Exception as e: return _handle_generic_graph_api_error(e, action_name, params)

async async def generic_get_compat(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name_log = "graph_generic_get_compat (wrapper)"
    logger.info(f"Ejecutando {action_name_log} con params: {params}")
    return generic_get(client, params)

async async def generic_post_compat(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name_log = "graph_generic_post_compat (wrapper)"
    logger.info(f"Ejecutando {action_name_log} con params: {params}")
    return generic_post(client, params)