# app/actions/power_automate_actions.py
import logging
import requests 
import json 
from typing import Dict, Optional, Any, List 

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

LOGIC_APPS_API_VERSION = "2019-05-01" 

def _handle_pa_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Power Automate action '{action_name}'"
    safe_params = {k: (v if k not in ['payload', 'trigger_headers'] else f"[{type(v).__name__} OMITIDO]") for k, v in (params_for_log or {}).items()}
    log_message += f" con params: {safe_params}"
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    details_str = str(e); status_code_int = 500; error_code_api = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json()
            if "error" in error_data and isinstance(error_data["error"], dict):
                error_info = error_data["error"]
                details_str = error_info.get("message", e.response.text); error_code_api = error_info.get("code")
            else: details_str = e.response.text 
        except json.JSONDecodeError: details_str = e.response.text[:500] if e.response.text else "No response body"
    return {"status": "error", "action": action_name, "message": f"Error en {action_name}: {details_str}", 
            "details": str(e), "http_status": status_code_int, "api_error_code": error_code_api}

async async def listar_flows(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "pa_listar_flows"; logger.info(f"Ejecutando {action_name}: {params}")
    suscripcion_id = params.get('suscripcion_id', settings.AZURE_SUBSCRIPTION_ID)
    grupo_recurso = params.get('grupo_recurso', settings.AZURE_RESOURCE_GROUP)
    if not suscripcion_id: return {"status": "error", "action": action_name, "message": "'suscripcion_id' requerido.", "http_status": 400}
    api_version = params.get("api_version", LOGIC_APPS_API_VERSION)
    odata_params: Dict[str, Any] = {k:v for k,v in params.items() if k in ["$top", "$filter"]}
    url_base = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{suscripcion_id}/resourceGroups/{grupo_recurso}/providers/Microsoft.Logic/workflows" if grupo_recurso else f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{suscripcion_id}/providers/Microsoft.Logic/workflows"
    url = f"{url_base}?api-version={api_version}"
    try:
        mgmt_scope = settings.AZURE_MGMT_DEFAULT_SCOPE
        if not mgmt_scope: raise ValueError("AZURE_MGMT_DEFAULT_SCOPE no configurado.")
        response_data = client.get(url, scope=mgmt_scope, params=odata_params, timeout=settings.DEFAULT_API_TIMEOUT)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_pa_api_error(e, action_name, params)

async async def obtener_flow(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "pa_obtener_flow"; logger.info(f"Ejecutando {action_name}: {params}")
    nombre_flow: Optional[str] = params.get("nombre_flow")
    if not nombre_flow: return {"status": "error", "action": action_name, "message": "'nombre_flow' requerido.", "http_status": 400}
    suscripcion_id = params.get('suscripcion_id', settings.AZURE_SUBSCRIPTION_ID)
    grupo_recurso = params.get('grupo_recurso', settings.AZURE_RESOURCE_GROUP)
    if not suscripcion_id or not grupo_recurso: return {"status": "error", "action": action_name, "message": "'suscripcion_id' y 'grupo_recurso' requeridos.", "http_status": 400}
    api_version = params.get("api_version", LOGIC_APPS_API_VERSION)
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{suscripcion_id}/resourceGroups/{grupo_recurso}/providers/Microsoft.Logic/workflows/{nombre_flow}?api-version={api_version}"
    odata_params: Dict[str, Any] = {'$select': params['$select']} if params.get("$select") else {}
    try:
        mgmt_scope = settings.AZURE_MGMT_DEFAULT_SCOPE
        if not mgmt_scope: raise ValueError("AZURE_MGMT_DEFAULT_SCOPE no configurado.")
        response_data = client.get(url, scope=mgmt_scope, params=odata_params if odata_params else None, timeout=settings.DEFAULT_API_TIMEOUT)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data # Propagar error de http_client
        return {"status": "success", "data": response_data}
    except requests.exceptions.HTTPError as http_err:
        if http_err.response is not None and http_err.response.status_code == 404:
            return {"status": "error", "action": action_name, "message": f"Flow '{nombre_flow}' no encontrado.", "details": http_err.response.text, "http_status": 404}
        return _handle_pa_api_error(http_err, action_name, params)
    except Exception as e: return _handle_pa_api_error(e, action_name, params)

def ejecutar_flow(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "pa_ejecutar_flow"
    log_params = {k:v for k,v in params.items() if k not in ['payload', 'trigger_headers']}
    logger.info(f"Ejecutando {action_name} con params: {log_params}")
    flow_trigger_url: Optional[str] = params.get("flow_trigger_url")
    if not flow_trigger_url: return {"status": "error", "action": action_name, "message": "'flow_trigger_url' requerido.", "http_status": 400}
    payload: Optional[Dict[str, Any]] = params.get("payload")
    custom_headers = params.get("trigger_headers") or {}
    if payload and 'Content-Type' not in custom_headers: custom_headers.setdefault('Content-Type', 'application/json')
    try:
        response = requests.post(flow_trigger_url, headers=custom_headers, 
                                 json=payload if payload and custom_headers.get('Content-Type') == 'application/json' else None,
                                 data=json.dumps(payload) if payload and custom_headers.get('Content-Type') != 'application/json' else None, 
                                 timeout=max(settings.DEFAULT_API_TIMEOUT, 120))
        response.raise_for_status()
        response_body: Any = response.json() if response.content and 'application/json' in response.headers.get('Content-Type','') else (response.text if response.text else "Respuesta vacía.")
        status_msg = "Solicitud aceptada y en procesamiento." if response.status_code == 202 else "Respuesta del trigger del flujo."
        return {"status": "success" if response.ok else "accepted", "message": status_msg, "http_status": response.status_code,
                "response_body": response_body, "response_headers": dict(response.headers)}
    except requests.exceptions.RequestException as e:
        error_body = e.response.text[:500] if e.response is not None and e.response.text else str(e)
        status_code_err = e.response.status_code if e.response is not None else 503
        return {"status": "error", "action": action_name, "message": f"Error API/Red: {type(e).__name__}", "details": error_body, "http_status": status_code_err}
    except Exception as e: return {"status": "error", "action": action_name, "message": f"Error inesperado: {type(e).__name__}", "details": str(e), "http_status":500}

async async def obtener_estado_ejecucion_flow(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "pa_obtener_estado_ejecucion_flow"; logger.info(f"Ejecutando {action_name}: {params}")
    nombre_flow = params.get("nombre_flow"); run_id = params.get("run_id")
    if not nombre_flow or not run_id: return {"status": "error", "action": action_name, "message": "'nombre_flow' y 'run_id' requeridos.", "http_status": 400}
    suscripcion_id = params.get('suscripcion_id', settings.AZURE_SUBSCRIPTION_ID)
    grupo_recurso = params.get('grupo_recurso', settings.AZURE_RESOURCE_GROUP)
    if not suscripcion_id or not grupo_recurso: return {"status": "error", "action": action_name, "message": "'suscripcion_id' y 'grupo_recurso' requeridos.", "http_status": 400}
    api_version = params.get("api_version", LOGIC_APPS_API_VERSION)
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{suscripcion_id}/resourceGroups/{grupo_recurso}/providers/Microsoft.Logic/workflows/{nombre_flow}/runs/{run_id}?api-version={api_version}"
    odata_params: Dict[str, Any] = {'$select': params['$select']} if params.get("$select") else {}
    try:
        mgmt_scope = settings.AZURE_MGMT_DEFAULT_SCOPE
        if not mgmt_scope: raise ValueError("AZURE_MGMT_DEFAULT_SCOPE no configurado.")
        response_data = client.get(url, scope=mgmt_scope, params=odata_params if odata_params else None, timeout=settings.DEFAULT_API_TIMEOUT)
        if not isinstance(response_data, dict): raise Exception(f"Respuesta inesperada: {type(response_data)}")
        if response_data.get("status") == "error": return response_data
        return {"status": "success", "data": response_data}
    except requests.exceptions.HTTPError as http_err:
        if http_err.response is not None and http_err.response.status_code == 404:
            return {"status": "error", "action": action_name, "message": f"Ejecución de flow '{run_id}' no encontrada para '{nombre_flow}'.", "details": http_err.response.text, "http_status": 404}
        return _handle_pa_api_error(http_err, action_name, params)
    except Exception as e: return _handle_pa_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/power_automate_actions.py ---