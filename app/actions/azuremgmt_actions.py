# app/actions/azuremgmt_actions.py
# -*- coding: utf-8 -*-
import logging
import requests 
import json 
from typing import Dict, List, Optional, Any

from app.core.config import settings 
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

def _handle_azure_mgmt_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Azure Management action '{action_name}'"
    safe_params = {} 
    if params_for_log:
        sensitive_keys = ['deployment_properties', 'template', 'parameters', 'properties']
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    details_str = str(e); status_code_int = 500; arm_error_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json(); error_info = error_data.get("error", {})
            details_str = error_info.get("message", e.response.text); arm_error_code = error_info.get("code")
        except json.JSONDecodeError: details_str = e.response.text[:500] if e.response.text else "No response body"
    return {"status": "error", "action": action_name, "message": f"Error ejecutando {action_name}: {details_str}",
            "http_status": status_code_int, "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
            "arm_error_code": arm_error_code}

def list_resource_groups(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "azure_list_resource_groups"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    subscription_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    if not subscription_id:
        return {"status": "error", "action": action_name, "message": "'subscription_id' (en params o settings) es requerido.", "http_status": 400}
    api_version = params.get("api_version", "2021-04-01") 
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{subscription_id}/resourcegroups?api-version={api_version}"
    odata_params: Dict[str, Any] = {k:v for k,v in params.items() if k in ["$top", "$filter"]}
    try:
        response_data = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE, params=odata_params)
        if not isinstance(response_data, dict):
            custom_exception = Exception(f"Respuesta inesperada del cliente HTTP, se esperaba un diccionario. Tipo: {type(response_data).__name__}, Contenido: {str(response_data)[:200]}")
            return _handle_azure_mgmt_api_error(custom_exception, action_name, params)
        if response_data.get("status") == "error" and "http_status" in response_data: return response_data
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_azure_mgmt_api_error(e, action_name, params)

def list_resources_in_rg(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "azure_list_resources_in_rg"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    subscription_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    resource_group_name = params.get("resource_group_name", settings.AZURE_RESOURCE_GROUP)
    if not subscription_id or not resource_group_name: return {"status": "error", "action":action_name, "message": "'subscription_id' y 'resource_group_name' requeridos.", "http_status": 400}
    api_version = params.get("api_version", "2021-04-01")
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/resources?api-version={api_version}"
    odata_params: Dict[str, Any] = {k:v for k,v in params.items() if k in ["$top", "$filter"]}
    try:
        response_data = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE, params=odata_params)
        if not isinstance(response_data, dict):
            custom_exception = Exception(f"Respuesta inesperada del cliente HTTP. Tipo: {type(response_data).__name__}, Contenido: {str(response_data)[:200]}")
            return _handle_azure_mgmt_api_error(custom_exception, action_name, params)
        if response_data.get("status") == "error" and "http_status" in response_data: return response_data
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_azure_mgmt_api_error(e, action_name, params)

def get_resource(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "azure_get_resource"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    resource_id = params.get("resource_id"); api_version = params.get("api_version")
    if not resource_id or not api_version: return {"status": "error", "action":action_name, "message": "'resource_id' y 'api_version' requeridos.", "http_status": 400}
    base_url_str = str(settings.AZURE_MGMT_API_BASE_URL).rstrip('/'); resource_id_str = resource_id.lstrip('/')
    url = f"{base_url_str}/{resource_id_str}?api-version={api_version}"
    try:
        response_data = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE)
        if not isinstance(response_data, dict):
            custom_exception = Exception(f"Respuesta inesperada del cliente HTTP. Tipo: {type(response_data).__name__}, Contenido: {str(response_data)[:200]}")
            return _handle_azure_mgmt_api_error(custom_exception, action_name, params)
        if response_data.get("status") == "error" and "http_status" in response_data: return response_data
        return {"status": "success", "data": response_data}
    except Exception as e: return _handle_azure_mgmt_api_error(e, action_name, params)

def restart_function_app(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "azure_restart_function_app"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    sub_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    rg_name = params.get("resource_group_name", settings.AZURE_RESOURCE_GROUP)
    app_name = params.get("function_app_name")
    if not all([sub_id, rg_name, app_name]): return {"status": "error", "action":action_name, "message": "'subscription_id', 'resource_group_name', 'function_app_name' requeridos.", "http_status": 400}
    api_version = params.get("api_version", "2022-03-01")
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{sub_id}/resourceGroups/{rg_name}/providers/Microsoft.Web/sites/{app_name}/restart?api-version={api_version}"
    try:
        response_obj = client.post(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE) 
        if response_obj.status_code == 204: return {"status": "success", "message": f"Function App '{app_name}' reiniciada (204).", "http_status": 204}
        if response_obj.status_code == 200: return {"status": "success", "message": f"Reinicio de Function App '{app_name}' enviado (200).", "data": response_obj.json() if response_obj.content else None, "http_status": 200}
        response_obj.raise_for_status() 
        return {} 
    except Exception as e: return _handle_azure_mgmt_api_error(e, action_name, params)

def list_functions(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "azure_list_functions"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    sub_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    rg_name = params.get("resource_group_name", settings.AZURE_RESOURCE_GROUP)
    app_name = params.get("function_app_name")
    if not all([sub_id, rg_name, app_name]): return {"status": "error", "action":action_name, "message": "Se requieren 'subscription_id', 'resource_group_name', 'function_app_name'.", "http_status": 400}
    api_version = params.get("api_version", "2022-03-01") 
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{sub_id}/resourceGroups/{rg_name}/providers/Microsoft.Web/sites/{app_name}/functions?api-version={api_version}"
    try:
        response_data = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE)
        if not isinstance(response_data, dict):
            custom_exception = Exception(f"Respuesta inesperada del cliente HTTP. Tipo: {type(response_data).__name__}, Contenido: {str(response_data)[:200]}")
            return _handle_azure_mgmt_api_error(custom_exception, action_name, params)
        if response_data.get("status") == "error" and "http_status" in response_data: return response_data
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_azure_mgmt_api_error(e, action_name, params)

def get_function_status(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "azure_get_function_status"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    sub_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    rg_name = params.get("resource_group_name", settings.AZURE_RESOURCE_GROUP)
    app_name = params.get("function_app_name"); func_name = params.get("function_name")
    if not all([sub_id, rg_name, app_name, func_name]): return {"status": "error", "action":action_name, "message": "Se requieren 'subscription_id', 'resource_group_name', 'function_app_name', 'function_name'.", "http_status": 400}
    api_version = params.get("api_version", "2022-03-01")
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{sub_id}/resourceGroups/{rg_name}/providers/Microsoft.Web/sites/{app_name}/functions/{func_name}?api-version={api_version}"
    try:
        response_data = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE)
        if not isinstance(response_data, dict):
            custom_exception = Exception(f"Respuesta inesperada del cliente HTTP. Tipo: {type(response_data).__name__}, Contenido: {str(response_data)[:200]}")
            return _handle_azure_mgmt_api_error(custom_exception, action_name, params)
        if response_data.get("status") == "error" and "http_status" in response_data: return response_data
        props = response_data.get("properties", {}); isDisabled = props.get("isDisabled", False)
        return {"status": "success", "data": {"name": response_data.get("name", func_name), "id": response_data.get("id"), "isDisabled": isDisabled, 
                                                "status_description": "Disabled" if isDisabled else "Enabled", "properties": props}}
    except Exception as e: return _handle_azure_mgmt_api_error(e, action_name, params)

def create_deployment(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> dict:
    params = params or {}; action_name = "azure_create_deployment"
    log_params_safe = {k:v for k,v in params.items() if k not in ['template', 'parameters', 'deployment_properties']}
    logger.info(f"Ejecutando {action_name} con params (template/parameters omitidos del log): %s", log_params_safe)
    sub_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    rg_name = params.get("resource_group_name", settings.AZURE_RESOURCE_GROUP)
    dep_name = params.get("deployment_name"); dep_props = params.get("deployment_properties")
    if not all([sub_id, rg_name, dep_name, dep_props]): return {"status": "error", "action":action_name, "message": "Faltan parámetros requeridos.", "http_status": 400}
    if not isinstance(dep_props, dict) or "template" not in dep_props: return {"status": "error", "action":action_name, "message": "'deployment_properties' debe ser dict con 'template'.", "http_status": 400}
    api_version = params.get("api_version", "2021-04-01")
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{sub_id}/resourcegroups/{rg_name}/providers/Microsoft.Resources/deployments/{dep_name}?api-version={api_version}"
    payload = {"properties": dep_props}
    try:
        response_obj = client.put(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE, json_data=payload)
        return {"status": "success", "data": response_obj.json(), "message": f"Despliegue ARM '{dep_name}' iniciado/actualizado."}
    except Exception as e: return _handle_azure_mgmt_api_error(e, action_name, params)

def list_logic_apps(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> dict:
    params = params or {}; action_name = "azure_list_logic_apps"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    sub_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    rg_name = params.get("resource_group_name")
    if not sub_id: return {"status": "error", "action":action_name, "message": "'subscription_id' requerido.", "http_status": 400}
    api_version = params.get("api_version", "2019-05-01")
    url_base = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{sub_id}/resourceGroups/{rg_name}/providers/Microsoft.Logic/workflows" if rg_name else f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{sub_id}/providers/Microsoft.Logic/workflows"
    url = f"{url_base}?api-version={api_version}"
    odata_params: Dict[str, Any] = {k:v for k,v in params.items() if k in ["$top", "$filter"]}
    try:
        response_data = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE, params=odata_params)
        if not isinstance(response_data, dict):
            custom_exception = Exception(f"Respuesta inesperada del cliente HTTP. Tipo: {type(response_data).__name__}, Contenido: {str(response_data)[:200]}")
            return _handle_azure_mgmt_api_error(custom_exception, action_name, params)
        if response_data.get("status") == "error" and "http_status" in response_data: return response_data
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_azure_mgmt_api_error(e, action_name, params)

def trigger_logic_app(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> dict:
    params = params or {}; action_name = "azure_trigger_logic_app"
    logger.warning(f"Acción '{action_name}' requiere una implementación más específica o el uso de la URL del trigger HTTP del Logic App.")
    return {"status": "not_implemented", "action": action_name, "message": "Acción no implementada vía ARM.", "http_status": 501}

def get_logic_app_run_history(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> dict:
    params = params or {}; action_name = "azure_get_logic_app_run_history"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    sub_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    rg_name = params.get("resource_group_name", settings.AZURE_RESOURCE_GROUP)
    workflow_name = params.get("workflow_name")
    if not all([sub_id, rg_name, workflow_name]): return {"status": "error", "action":action_name, "message": "Se requieren 'subscription_id', 'resource_group_name', 'workflow_name'.", "http_status": 400}
    api_version = params.get("api_version", "2019-05-01")
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{sub_id}/resourceGroups/{rg_name}/providers/Microsoft.Logic/workflows/{workflow_name}/runs?api-version={api_version}"
    odata_params: Dict[str, Any] = {k:v for k,v in params.items() if k in ["$top", "$filter"]}
    try:
        response_data = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE, params=odata_params)
        if not isinstance(response_data, dict):
            custom_exception = Exception(f"Respuesta inesperada del cliente HTTP. Tipo: {type(response_data).__name__}, Contenido: {str(response_data)[:200]}")
            return _handle_azure_mgmt_api_error(custom_exception, action_name, params)
        if response_data.get("status") == "error" and "http_status" in response_data: return response_data
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e: return _handle_azure_mgmt_api_error(e, action_name, params)