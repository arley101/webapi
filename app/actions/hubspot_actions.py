# app/actions/hubspot_actions.py
import logging
import requests
import json
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

HUBSPOT_API_BASE_URL = "https://api.hubapi.com"

def _get_hubspot_api_headers(params: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Prepara los headers para las solicitudes a la HubSpot API.
    Prioriza el token de params, luego de settings.
    """
    params = params or {}
    # Permitir override del token desde params, si no, usar el de settings
    # Renombrar para mayor claridad, HubSpot usa "Private App Token"
    token: Optional[str] = params.get("hubspot_token_override", settings.HUBSPOT_PRIVATE_APP_TOKEN) 

    if not token:
        raise ValueError("Se requiere el Token de Aplicación Privada de HubSpot (en params como 'hubspot_token_override' o configurado como HUBSPOT_PRIVATE_APP_TOKEN en el backend).")
    
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def _handle_hubspot_api_error(
    e: Exception,
    action_name: str,
    params_for_log: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Helper para manejar errores de HubSpot API."""
    log_message = f"Error en HubSpot API Action '{action_name}'"
    safe_params = {}
    if params_for_log:
        # Omitir el token y payloads grandes/sensibles
        sensitive_keys = ['hubspot_token_override', 'data', 'properties_payload']
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    hubspot_error_category = None
    hubspot_correlation_id = None
    hubspot_message = str(e) # Fallback

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        hubspot_correlation_id = e.response.headers.get("x-hubspot-correlation-id") or \
                                 e.response.headers.get("x-correlationid") # A veces usan otros nombres
        try:
            error_data = e.response.json()
            # Estructura de error común de HubSpot: {"status": "error", "message": "...", "correlationId": "...", "category": "..."}
            # A veces puede tener "errors": [{"message": ..., "in": ...}]
            hubspot_message = error_data.get("message", e.response.text)
            hubspot_error_category = error_data.get("category")
            if error_data.get("errors") and isinstance(error_data["errors"], list) and error_data["errors"]:
                hubspot_message = error_data["errors"][0].get("message", hubspot_message) # Tomar el primer error específico
            details_str = json.dumps(error_data)
        except json.JSONDecodeError:
            details_str = e.response.text[:500] if e.response.text else "No response body"
            hubspot_message = details_str
            
    return {
        "status": "error",
        "action": action_name,
        "message": f"Error interactuando con HubSpot API: {hubspot_message}",
        "details": {
            "raw_exception_type": type(e).__name__,
            "raw_exception_message": str(e),
            "hubspot_api_category": hubspot_error_category,
            "hubspot_api_correlation_id": hubspot_correlation_id,
            "response_body_preview": details_str[:500] if isinstance(details_str, str) else details_str
        },
        "http_status": status_code_int,
    }

# --- ACCIONES CRUD PARA CONTACTOS ---
# Nota: El parámetro 'client: AuthenticatedHttpClient' no se usa.

def hubspot_get_contacts(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "hubspot_get_contacts"
    logger.info(f"Ejecutando {action_name} con params: %s", {k:v for k,v in params.items() if k not in ['hubspot_token_override']})

    url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/contacts"
    
    # Parámetros de consulta para la API de HubSpot v3
    # Ej: limit, after, properties, propertiesWithHistory, associations, archived
    query_api_params: Dict[str, Any] = {}
    if params.get("limit"): query_api_params["limit"] = min(int(params["limit"]), 100) # Max limit es 100
    if params.get("after"): query_api_params["after"] = params["after"] # Para paginación
    if params.get("properties"): # string separado por comas, o lista de strings
        props = params["properties"]
        query_api_params["properties"] = ",".join(props) if isinstance(props, list) else props
    if params.get("associations"): # string separado por comas (ej. "deals,tickets")
        query_api_params["associations"] = params["associations"]
    if params.get("archived") is not None: # boolean
        query_api_params["archived"] = str(params["archived"]).lower()

    logger.info(f"Listando contactos de HubSpot. Query Params: {query_api_params}")
    try:
        headers = _get_hubspot_api_headers(params)
        response = requests.get(url, headers=headers, params=query_api_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve: # Error de _get_hubspot_api_headers
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name, params)

def hubspot_create_contact(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "hubspot_create_contact"
    log_params = {k:v for k,v in params.items() if k not in ['hubspot_token_override', 'properties_payload']}
    if 'properties_payload' in params: log_params['properties_payload_keys'] = list(params['properties_payload'].keys())
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    properties_payload: Optional[Dict[str, Any]] = params.get("properties_payload")
    if not properties_payload or not isinstance(properties_payload, dict):
        return {"status": "error", "action": action_name, "message": "'properties_payload' (dict con propiedades del contacto) es requerido.", "http_status": 400}

    # El payload para crear un contacto es {"properties": { "firstname": "...", "email": "..."}}
    request_body = {"properties": properties_payload}
    
    url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/contacts"
    logger.info(f"Creando contacto en HubSpot. Properties: {list(properties_payload.keys())}")
    try:
        headers = _get_hubspot_api_headers(params)
        response = requests.post(url, headers=headers, json=request_body, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name, params)

def hubspot_update_contact(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "hubspot_update_contact"
    log_params = {k:v for k,v in params.items() if k not in ['hubspot_token_override', 'properties_payload']}
    if 'properties_payload' in params: log_params['properties_payload_keys'] = list(params['properties_payload'].keys())
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    contact_id: Optional[str] = params.get("contact_id")
    properties_payload: Optional[Dict[str, Any]] = params.get("properties_payload")

    if not contact_id:
        return {"status": "error", "action": action_name, "message": "'contact_id' es requerido.", "http_status": 400}
    if not properties_payload or not isinstance(properties_payload, dict):
        return {"status": "error", "action": action_name, "message": "'properties_payload' (dict con propiedades a actualizar) es requerido.", "http_status": 400}

    request_body = {"properties": properties_payload}
    url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/contacts/{contact_id}"
    logger.info(f"Actualizando contacto de HubSpot ID '{contact_id}'. Properties: {list(properties_payload.keys())}")
    try:
        headers = _get_hubspot_api_headers(params)
        response = requests.patch(url, headers=headers, json=request_body, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name, params)

def hubspot_delete_contact(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "hubspot_delete_contact"
    logger.info(f"Ejecutando {action_name} con params: %s", {k:v for k,v in params.items() if k not in ['hubspot_token_override']})

    contact_id: Optional[str] = params.get("contact_id")
    if not contact_id:
        return {"status": "error", "action": action_name, "message": "'contact_id' es requerido.", "http_status": 400}

    url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/contacts/{contact_id}"
    logger.info(f"Eliminando contacto de HubSpot ID '{contact_id}'")
    try:
        headers = _get_hubspot_api_headers(params)
        response = requests.delete(url, headers=headers, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status() # HubSpot devuelve 204 No Content en delete exitoso
        return {"status": "success", "action": action_name, "message": f"Contacto '{contact_id}' eliminado.", "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name, params)

# --- ACCIONES CRUD PARA DEALS (NEGOCIOS) ---

def hubspot_get_deals(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "hubspot_get_deals"
    logger.info(f"Ejecutando {action_name} con params: %s", {k:v for k,v in params.items() if k not in ['hubspot_token_override']})

    url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/deals"
    query_api_params: Dict[str, Any] = {}
    if params.get("limit"): query_api_params["limit"] = min(int(params["limit"]), 100)
    if params.get("after"): query_api_params["after"] = params["after"]
    if params.get("properties"): 
        props = params["properties"]
        query_api_params["properties"] = ",".join(props) if isinstance(props, list) else props
    if params.get("associations"): 
        query_api_params["associations"] = params["associations"]
    if params.get("archived") is not None: 
        query_api_params["archived"] = str(params["archived"]).lower()

    logger.info(f"Listando negocios (deals) de HubSpot. Query Params: {query_api_params}")
    try:
        headers = _get_hubspot_api_headers(params)
        response = requests.get(url, headers=headers, params=query_api_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name, params)

def hubspot_create_deal(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "hubspot_create_deal"
    log_params = {k:v for k,v in params.items() if k not in ['hubspot_token_override', 'properties_payload']}
    if 'properties_payload' in params: log_params['properties_payload_keys'] = list(params['properties_payload'].keys())
    logger.info(f"Ejecutando {action_name} con params: {log_params}")
    
    properties_payload: Optional[Dict[str, Any]] = params.get("properties_payload")
    if not properties_payload or not isinstance(properties_payload, dict):
        return {"status": "error", "action": action_name, "message": "'properties_payload' (dict con propiedades del deal) es requerido.", "http_status": 400}

    # Ejemplo de campos requeridos/comunes para un deal: dealname, dealstage, pipeline, amount, closedate
    # El usuario debe proveerlos en properties_payload
    request_body = {"properties": properties_payload}
    url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/deals"
    logger.info(f"Creando negocio (deal) en HubSpot. Properties: {list(properties_payload.keys())}")
    try:
        headers = _get_hubspot_api_headers(params)
        response = requests.post(url, headers=headers, json=request_body, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name, params)

def hubspot_update_deal(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "hubspot_update_deal"
    log_params = {k:v for k,v in params.items() if k not in ['hubspot_token_override', 'properties_payload']}
    if 'properties_payload' in params: log_params['properties_payload_keys'] = list(params['properties_payload'].keys())
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    deal_id: Optional[str] = params.get("deal_id")
    properties_payload: Optional[Dict[str, Any]] = params.get("properties_payload")

    if not deal_id:
        return {"status": "error", "action": action_name, "message": "'deal_id' es requerido.", "http_status": 400}
    if not properties_payload or not isinstance(properties_payload, dict):
        return {"status": "error", "action": action_name, "message": "'properties_payload' (dict con propiedades a actualizar) es requerido.", "http_status": 400}

    request_body = {"properties": properties_payload}
    url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/deals/{deal_id}"
    logger.info(f"Actualizando negocio (deal) de HubSpot ID '{deal_id}'. Properties: {list(properties_payload.keys())}")
    try:
        headers = _get_hubspot_api_headers(params)
        response = requests.patch(url, headers=headers, json=request_body, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name, params)

def hubspot_delete_deal(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "hubspot_delete_deal"
    logger.info(f"Ejecutando {action_name} con params: %s", {k:v for k,v in params.items() if k not in ['hubspot_token_override']})

    deal_id: Optional[str] = params.get("deal_id")
    if not deal_id:
        return {"status": "error", "action": action_name, "message": "'deal_id' es requerido.", "http_status": 400}

    url = f"{HUBSPOT_API_BASE_URL}/crm/v3/objects/deals/{deal_id}"
    logger.info(f"Eliminando negocio (deal) de HubSpot ID '{deal_id}'")
    try:
        headers = _get_hubspot_api_headers(params)
        response = requests.delete(url, headers=headers, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status() # HubSpot devuelve 204 No Content
        return {"status": "success", "action": action_name, "message": f"Negocio (deal) '{deal_id}' eliminado.", "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_hubspot_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/hubspot_actions.py ---