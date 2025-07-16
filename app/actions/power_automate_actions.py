# app/actions/power_automate_actions.py
import logging
import requests
import json
from typing import Dict, Optional, Any, List

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

POWER_AUTOMATE_API_BASE_URL = "https://management.azure.com"
DEFAULT_API_VERSION = "2019-05-01" 

def _handle_pa_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Power Automate Action '{action_name}'"
    if params_for_log:
        safe_params = {k: v for k, v in params_for_log.items() if k not in ['flow_definition', 'trigger_url', 'payload']}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
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
    subscription_id = params.get('subscription_id', settings.AZURE_SUBSCRIPTION_ID)
    resource_group = params.get('resource_group', settings.AZURE_RESOURCE_GROUP)
    
    if not subscription_id:
        raise ValueError("Se requiere 'subscription_id' en los parámetros o en la configuración del entorno.")
    if not resource_group:
         raise ValueError("Se requiere 'resource_group' en los parámetros o en la configuración del entorno.")

    return { "subscription_id": subscription_id, "resource_group": resource_group }

def pa_list_flows(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "pa_list_flows"
    try:
        arm_params = _get_common_arm_params(params)
        api_version = params.get("api_version", DEFAULT_API_VERSION)
        url = f"{POWER_AUTOMATE_API_BASE_URL}/subscriptions/{arm_params['subscription_id']}/resourceGroups/{arm_params['resource_group']}/providers/Microsoft.Logic/workflows?api-version={api_version}"
        odata_params = {key: params[key] for key in ['$top', '$filter'] if key in params}
        response = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE, params=odata_params)
        return {"status": "success", "data": response.get("value", [])}
    except Exception as e:
        return _handle_pa_api_error(e, action_name, params)

def pa_get_flow(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "pa_get_flow"
    try:
        arm_params = _get_common_arm_params(params)
        flow_name = params.get("flow_name")
        if not flow_name: raise ValueError("Se requiere 'flow_name'.")
        api_version = params.get("api_version", DEFAULT_API_VERSION)
        url = f"{POWER_AUTOMATE_API_BASE_URL}/subscriptions/{arm_params['subscription_id']}/resourceGroups/{arm_params['resource_group']}/providers/Microsoft.Logic/workflows/{flow_name}?api-version={api_version}"
        response = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_pa_api_error(e, action_name, params)

def pa_create_or_update_flow(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "pa_create_or_update_flow"
    try:
        arm_params = _get_common_arm_params(params)
        flow_name = params.get("flow_name")
        flow_definition = params.get("flow_definition")
        location = params.get("location", "eastus") 

        if not flow_name or not flow_definition or not isinstance(flow_definition, dict):
            raise ValueError("Se requieren 'flow_name' y una 'flow_definition' (dict) válida.")

        api_version = params.get("api_version", DEFAULT_API_VERSION)
        url = f"{POWER_AUTOMATE_API_BASE_URL}/subscriptions/{arm_params['subscription_id']}/resourceGroups/{arm_params['resource_group']}/providers/Microsoft.Logic/workflows/{flow_name}?api-version={api_version}"
        
        payload = {
            "location": location,
            "properties": { "definition": flow_definition, "state": params.get("state", "Enabled") }
        }
        if params.get("tags"): payload["tags"] = params.get("tags")
        
        response = client.put(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE, json_data=payload)
        return {"status": "success", "data": response.json(), "http_status": response.status_code}
    except Exception as e:
        return _handle_pa_api_error(e, action_name, params)

def pa_delete_flow(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "pa_delete_flow"
    try:
        arm_params = _get_common_arm_params(params)
        flow_name = params.get("flow_name")
        if not flow_name: raise ValueError("Se requiere 'flow_name'.")
        api_version = params.get("api_version", DEFAULT_API_VERSION)
        url = f"{POWER_AUTOMATE_API_BASE_URL}/subscriptions/{arm_params['subscription_id']}/resourceGroups/{arm_params['resource_group']}/providers/Microsoft.Logic/workflows/{flow_name}?api-version={api_version}"
        response = client.delete(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE)
        return {"status": "success", "message": f"Flujo '{flow_name}' eliminado.", "http_status": response.status_code}
    except Exception as e:
        return _handle_pa_api_error(e, action_name, params)
        
def pa_run_flow_trigger(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "pa_run_flow_trigger"
    try:
        trigger_url = params.get("flow_trigger_url")
        payload = params.get("payload", {})
        if not trigger_url: raise ValueError("Se requiere el parámetro 'flow_trigger_url'.")

        response = requests.post(trigger_url, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        response_data = response.json() if response.content else {}
        return {"status": "success", "message": "Solicitud al flujo aceptada.", "data": response_data, "http_status": response.status_code}
    except Exception as e:
        return _handle_pa_api_error(e, action_name, params)

def pa_get_flow_run_history(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "pa_get_flow_run_history"
    try:
        arm_params = _get_common_arm_params(params)
        flow_name = params.get("flow_name")
        if not flow_name: raise ValueError("Se requiere 'flow_name'.")
        api_version = params.get("api_version", DEFAULT_API_VERSION)
        url = f"{POWER_AUTOMATE_API_BASE_URL}/subscriptions/{arm_params['subscription_id']}/resourceGroups/{arm_params['resource_group']}/providers/Microsoft.Logic/workflows/{flow_name}/runs?api-version={api_version}"
        odata_params = {key: params[key] for key in ['$top', '$filter'] if key in params}
        response = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE, params=odata_params)
        return {"status": "success", "data": response.get("value", [])}
    except Exception as e:
        return _handle_pa_api_error(e, action_name, params)

def pa_get_flow_run_details(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "pa_get_flow_run_details"
    try:
        arm_params = _get_common_arm_params(params)
        flow_name, run_id = params.get("flow_name"), params.get("run_id")
        if not all([flow_name, run_id]): raise ValueError("Se requieren 'flow_name' y 'run_id'.")
        api_version = params.get("api_version", DEFAULT_API_VERSION)
        url = f"{POWER_AUTOMATE_API_BASE_URL}/subscriptions/{arm_params['subscription_id']}/resourceGroups/{arm_params['resource_group']}/providers/Microsoft.Logic/workflows/{flow_name}/runs/{run_id}?api-version={api_version}"
        response = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE)
        return {"status": "success", "data": response}
    except Exception as e:
        return _handle_pa_api_error(e, action_name, params)