# app/actions/power_automate_actions.py
import logging
import requests
import json
from typing import Dict, Optional, Any, List

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# La API de Power Automate (Workflows) es parte de Azure Management
LOGIC_APPS_API_VERSION = "2019-05-01"

# --- HELPERS INTERNOS ROBUSTOS ---

def _handle_pa_api_error(e: Exception, action_name: str) -> Dict[str, Any]:
    """Maneja errores de la API de Power Automate/Logic Apps de forma estandarizada."""
    logger.error(f"Error en Power Automate Action '{action_name}': {type(e).__name__} - {e}", exc_info=True)
    
    status_code = 500
    details = str(e)
    api_error_code = None

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code = e.response.status_code
        try:
            error_data = e.response.json()
            error_info = error_data.get("error", {})
            details = error_info.get("message", e.response.text)
            api_error_code = error_info.get("code")
        except json.JSONDecodeError:
            details = e.response.text
            
    return {
        "status": "error", "action": action_name,
        "message": f"Error interactuando con Power Automate API: {details}",
        "details": {"api_error_code": api_error_code, "raw_response": details},
        "http_status": status_code
    }

def _get_common_arm_params(params: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Obtiene los parámetros comunes de ARM desde los params o la configuración."""
    return {
        "subscription_id": params.get('suscripcion_id', settings.AZURE_SUBSCRIPTION_ID),
        "resource_group": params.get('grupo_recurso', settings.AZURE_RESOURCE_GROUP),
    }

# --- ACCIONES PRINCIPALES ---

def pa_listar_flows(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Lista los flujos (Logic Apps) en una suscripción y, opcionalmente, en un grupo de recursos."""
    action_name = "pa_listar_flows"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    arm_params = _get_common_arm_params(params)
    if not arm_params["subscription_id"]:
        return {"status": "error", "message": "Se requiere 'suscripcion_id'."}

    api_version = params.get("api_version", LOGIC_APPS_API_VERSION)
    
    if arm_params["resource_group"]:
        url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{arm_params['subscription_id']}/resourceGroups/{arm_params['resource_group']}/providers/Microsoft.Logic/workflows?api-version={api_version}"
    else:
        url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{arm_params['subscription_id']}/providers/Microsoft.Logic/workflows?api-version={api_version}"

    try:
        response = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE)
        return {"status": "success", "data": response.get("value", [])}
    except Exception as e:
        return _handle_pa_api_error(e, action_name)

def pa_obtener_flow(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene los detalles de un flujo (Logic App) específico."""
    action_name = "pa_obtener_flow"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    arm_params = _get_common_arm_params(params)
    nombre_flow = params.get("nombre_flow")
    if not all([arm_params["subscription_id"], arm_params["resource_group"], nombre_flow]):
        return {"status": "error", "message": "Se requieren 'suscripcion_id', 'grupo_recurso' y 'nombre_flow'."}

    api_version = params.get("api_version", LOGIC_APPS_API_VERSION)
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{arm_params['subscription_id']}/resourceGroups/{arm_params['resource_group']}/providers/Microsoft.Logic/workflows/{nombre_flow}?api-version={api_version}"

    try:
        response = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_pa_api_error(e, action_name)

def pa_ejecutar_flow(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta un flujo mediante su URL de trigger HTTP (método recomendado)."""
    action_name = "pa_ejecutar_flow"
    logger.info(f"Ejecutando {action_name} con params (payload omitido del log)")
    
    trigger_url = params.get("flow_trigger_url")
    payload = params.get("payload", {})
    if not trigger_url:
        return {
            "status": "error", 
            "message": "Para ejecutar un flujo, se requiere el parámetro 'flow_trigger_url'. Esta es la URL del trigger 'Cuando se recibe una solicitud HTTP' que se encuentra en la configuración del flujo en Power Automate.",
            "http_status": 400
        }

    try:
        # Esta es una llamada HTTP directa, no usa el AuthenticatedHttpClient de Graph/ARM
        response = requests.post(trigger_url, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        # El status 202 (Accepted) es común si el flujo se ejecuta de forma asíncrona
        status_code = response.status_code
        status_msg = "Solicitud al flujo aceptada." if status_code == 202 else "Flujo ejecutado."
        
        return {"status": "success", "message": status_msg, "http_status": status_code}
    except Exception as e:
        return _handle_pa_api_error(e, action_name)

def pa_obtener_estado_ejecucion_flow(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene el estado de una ejecución específica de un flujo (Logic App)."""
    action_name = "pa_obtener_estado_ejecucion_flow"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    arm_params = _get_common_arm_params(params)
    nombre_flow = params.get("nombre_flow")
    run_id = params.get("run_id")
    if not all([arm_params["subscription_id"], arm_params["resource_group"], nombre_flow, run_id]):
        return {"status": "error", "message": "Se requieren 'suscripcion_id', 'grupo_recurso', 'nombre_flow' y 'run_id'."}

    api_version = params.get("api_version", LOGIC_APPS_API_VERSION)
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{arm_params['subscription_id']}/resourceGroups/{arm_params['resource_group']}/providers/Microsoft.Logic/workflows/{nombre_flow}/runs/{run_id}?api-version={api_version}"

    try:
        response = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_pa_api_error(e, action_name)