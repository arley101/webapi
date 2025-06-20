# app/actions/azuremgmt_actions.py
# -*- coding: utf-8 -*-
import logging
import requests # Para requests.exceptions.HTTPError
import json # Para el helper de error
from typing import Dict, List, Optional, Any

from app.core.config import settings # Para acceder a AZURE_MGMT_DEFAULT_SCOPE, AZURE_MGMT_API_BASE_URL
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# Helper para manejar errores de ARM API de forma centralizada
def _handle_azure_mgmt_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Azure Management action '{action_name}'"
    safe_params = {} # Inicializar
    if params_for_log:
        # Omitir campos potencialmente grandes o sensibles del log directo
        sensitive_keys = ['deployment_properties', 'template', 'parameters', 'properties']
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    arm_error_code = None # Específico para errores de ARM

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json()
            error_info = error_data.get("error", {}) # ARM errores suelen tener un objeto 'error'
            details_str = error_info.get("message", e.response.text)
            arm_error_code = error_info.get("code")
        except json.JSONDecodeError: 
            details_str = e.response.text[:500] if e.response.text else "No response body"
            
    return {
        "status": "error",
        "action": action_name,
        "message": f"Error ejecutando {action_name}: {details_str}",
        "http_status": status_code_int,
        "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
        "arm_error_code": arm_error_code
    }

# --- Implementación de Acciones de Azure Management ---

def list_resource_groups(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "azure_list_resource_groups"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    subscription_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    if not subscription_id:
        return {"status": "error", "action": action_name, "message": "'subscription_id' (en params o settings) es requerido.", "http_status": 400}

    api_version = params.get("api_version", "2021-04-01") 
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{subscription_id}/resourcegroups?api-version={api_version}"
    
    odata_params: Dict[str, Any] = {}
    if params.get("$top"): odata_params["$top"] = params["$top"]
    if params.get("$filter"): odata_params["$filter"] = params["$filter"]
    
    logger.info(f"Listando grupos de recursos para la suscripción '{subscription_id}' con OData params: {odata_params}")
    try:
        response = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE, params=odata_params)
        return {"status": "success", "data": response.json().get("value", [])}
    except Exception as e:
        return _handle_azure_mgmt_api_error(e, action_name, params)

def list_resources_in_rg(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "azure_list_resources_in_rg"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    subscription_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    resource_group_name = params.get("resource_group_name", settings.AZURE_RESOURCE_GROUP)

    if not subscription_id:
        return {"status": "error", "action": action_name, "message": "'subscription_id' (en params o settings) es requerido.", "http_status": 400}
    if not resource_group_name:
        return {"status": "error", "action": action_name, "message": "'resource_group_name' (en params o settings) es requerido.", "http_status": 400}

    api_version = params.get("api_version", "2021-04-01")
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/resources?api-version={api_version}"
    
    odata_params: Dict[str, Any] = {}
    if params.get("$top"): odata_params["$top"] = params["$top"]
    if params.get("$filter"): odata_params["$filter"] = params["$filter"] 
    
    logger.info(f"Listando recursos en RG '{resource_group_name}', suscripción '{subscription_id}'. Filtro: {odata_params.get('$filter')}")
    try:
        response = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE, params=odata_params)
        return {"status": "success", "data": response.json().get("value", [])}
    except Exception as e:
        return _handle_azure_mgmt_api_error(e, action_name, params)

def get_resource(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "azure_get_resource"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    resource_id = params.get("resource_id") 
    api_version = params.get("api_version") 

    if not resource_id:
        return {"status": "error", "action": action_name, "message": "'resource_id' (ID completo de ARM) es requerido.", "http_status": 400}
    if not api_version:
        return {"status": "error", "action": action_name, "message": "'api_version' específica para el tipo de recurso es requerida.", "http_status": 400}

    # resource_id ya debería empezar con "/", así que no es necesario añadirlo desde AZURE_MGMT_API_BASE_URL
    # Asegurar que no haya doble "/" si AZURE_MGMT_API_BASE_URL termina en "/" y resource_id empieza con "/"
    base_url_str = str(settings.AZURE_MGMT_API_BASE_URL).rstrip('/')
    resource_id_str = resource_id.lstrip('/')
    url = f"{base_url_str}/{resource_id_str}?api-version={api_version}"
    
    logger.info(f"Obteniendo detalles del recurso ARM ID: '{resource_id}' con api-version '{api_version}'")
    try:
        response = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE)
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_azure_mgmt_api_error(e, action_name, params)

def restart_function_app(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "azure_restart_function_app"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    subscription_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    resource_group_name = params.get("resource_group_name", settings.AZURE_RESOURCE_GROUP)
    function_app_name = params.get("function_app_name")

    if not subscription_id: 
        return {"status": "error", "action": action_name, "message": "'subscription_id' es requerido.", "http_status": 400}
    if not resource_group_name: 
        return {"status": "error", "action": action_name, "message": "'resource_group_name' es requerido.", "http_status": 400}
    if not function_app_name: 
        return {"status": "error", "action": action_name, "message": "'function_app_name' es requerido.", "http_status": 400}

    api_version = params.get("api_version", "2022-03-01") # API version para Microsoft.Web/sites
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Web/sites/{function_app_name}/restart?api-version={api_version}"
    
    logger.info(f"Reiniciando Function App '{function_app_name}' en RG '{resource_group_name}'")
    try:
        response = client.post(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE) # No necesita json_data
        if response.status_code == 204:
             return {"status": "success", "message": f"Function App '{function_app_name}' reiniciada exitosamente (204 No Content).", "http_status": response.status_code}
        elif response.status_code == 200: # A veces devuelve 200 OK
             return {"status": "success", "message": f"Solicitud de reinicio para Function App '{function_app_name}' enviada (200 OK).", "data": response.json() if response.content else None, "http_status": response.status_code}
        else: # Respuesta inesperada pero no error HTTP
            logger.warning(f"Respuesta inesperada {response.status_code} al reiniciar Function App: {response.text[:200]}")
            response.raise_for_status() # Forzar error si no fue 200 o 204
            return {} # No debería llegar aquí
    except Exception as e:
        return _handle_azure_mgmt_api_error(e, action_name, params)

def list_functions(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "azure_list_functions"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    subscription_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    resource_group_name = params.get("resource_group_name", settings.AZURE_RESOURCE_GROUP)
    function_app_name = params.get("function_app_name")

    if not all([subscription_id, resource_group_name, function_app_name]):
        return {"status": "error", "action": action_name, "message": "Se requieren 'subscription_id', 'resource_group_name', y 'function_app_name'.", "http_status": 400}

    api_version = params.get("api_version", "2022-03-01") 
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Web/sites/{function_app_name}/functions?api-version={api_version}"
    
    logger.info(f"Listando funciones para la Function App '{function_app_name}'")
    try:
        response = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE)
        return {"status": "success", "data": response.json().get("value", [])}
    except Exception as e:
        return _handle_azure_mgmt_api_error(e, action_name, params)

def get_function_status(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "azure_get_function_status"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    subscription_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    resource_group_name = params.get("resource_group_name", settings.AZURE_RESOURCE_GROUP)
    function_app_name = params.get("function_app_name")
    function_name = params.get("function_name")

    if not all([subscription_id, resource_group_name, function_app_name, function_name]):
        return {"status": "error", "action": action_name, "message": "Se requieren 'subscription_id', 'resource_group_name', 'function_app_name', y 'function_name'.", "http_status": 400}

    api_version = params.get("api_version", "2022-03-01")
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Web/sites/{function_app_name}/functions/{function_name}?api-version={api_version}"
    
    logger.info(f"Obteniendo estado de la función '{function_name}' en Function App '{function_app_name}'")
    try:
        response = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE)
        function_data = response.json()
        function_properties = function_data.get("properties", {})
        # El estado 'isDisabled' puede no estar siempre presente. Si no está, se asume habilitada.
        is_disabled = function_properties.get("isDisabled", False) 
        return {
            "status": "success", 
            "data": {
                "name": function_data.get("name", function_name), 
                "id": function_data.get("id"),
                "isDisabled": is_disabled, 
                "status_description": "Disabled" if is_disabled else "Enabled", 
                "properties": function_properties,
                "config": function_properties.get("config") # La configuración puede tener más detalles
            }
        }
    except Exception as e:
        return _handle_azure_mgmt_api_error(e, action_name, params)

def create_deployment(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> dict:
    params = params or {}
    action_name = "azure_create_deployment"
    logger.info(f"Ejecutando {action_name} con params (template/parameters omitidos del log): %s", {k:v for k,v in params.items() if k not in ['template', 'parameters', 'deployment_properties']})
    
    # Esta función es compleja y requiere muchos parámetros específicos.
    # Se mantiene como no implementada por ahora.
    subscription_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    resource_group_name = params.get("resource_group_name", settings.AZURE_RESOURCE_GROUP)
    deployment_name = params.get("deployment_name")
    deployment_properties = params.get("deployment_properties") # Esto debería contener 'template', 'parameters', 'mode'

    if not all([subscription_id, resource_group_name, deployment_name, deployment_properties]):
         return {"status": "error", "action": action_name, "message": "Faltan parámetros requeridos: 'subscription_id', 'resource_group_name', 'deployment_name', 'deployment_properties'.", "http_status": 400}
    if not isinstance(deployment_properties, dict) or "template" not in deployment_properties:
        return {"status": "error", "action": action_name, "message": "'deployment_properties' debe ser un dict y contener al menos 'template'.", "http_status": 400}

    api_version = params.get("api_version", "2021-04-01") # API para deployments
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{subscription_id}/resourcegroups/{resource_group_name}/providers/Microsoft.Resources/deployments/{deployment_name}?api-version={api_version}"
    
    payload = {"properties": deployment_properties} # El cuerpo de la solicitud PUT
    
    logger.warning(f"Acción '{action_name}' está siendo llamada. Esta es una operación compleja y potencialmente destructiva.")
    logger.info(f"Creando/Actualizando despliegue ARM '{deployment_name}' en RG '{resource_group_name}'. Modo: {deployment_properties.get('mode', 'Incremental')}")
    try:
        # create_deployment es una operación PUT
        response = client.put(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE, json_data=payload)
        # Puede devolver 200 OK o 201 Created. La respuesta contiene el estado del despliegue.
        return {"status": "success", "data": response.json(), "message": f"Despliegue ARM '{deployment_name}' iniciado/actualizado."}
    except Exception as e:
        # Los params pasados a _handle_azure_mgmt_api_error son los originales, no el payload.
        return _handle_azure_mgmt_api_error(e, action_name, params)


def list_logic_apps(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> dict:
    params = params or {}
    action_name = "azure_list_logic_apps"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    subscription_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    resource_group_name = params.get("resource_group_name") # Opcional, si se omite lista todas en la subscripción

    if not subscription_id:
        return {"status": "error", "action": action_name, "message": "'subscription_id' es requerido.", "http_status": 400}

    api_version = params.get("api_version", "2019-05-01") # Microsoft.Logic/workflows
    
    url_base: str
    log_context: str
    if resource_group_name:
        url_base = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Logic/workflows"
        log_context = f"RG '{resource_group_name}', suscripción '{subscription_id}'"
    else:
        url_base = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{subscription_id}/providers/Microsoft.Logic/workflows"
        log_context = f"suscripción '{subscription_id}' (todos los RGs)"
        
    url = f"{url_base}?api-version={api_version}"
    
    odata_params: Dict[str, Any] = {}
    if params.get("$top"): odata_params["$top"] = params["$top"]
    if params.get("$filter"): odata_params["$filter"] = params["$filter"]

    logger.info(f"Listando Logic Apps en {log_context}")
    try:
        response = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE, params=odata_params)
        return {"status": "success", "data": response.json().get("value", [])}
    except Exception as e:
        return _handle_azure_mgmt_api_error(e, action_name, params)


def trigger_logic_app(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> dict:
    params = params or {}
    action_name = "azure_trigger_logic_app"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    # Esta acción es un placeholder, ya que disparar una Logic App vía ARM es complejo.
    # Usualmente se usa la URL del trigger HTTP.
    # Si se quisiera implementar vía ARM:
    # 1. Obtener la URL del trigger: POST /.../triggers/{triggerName}/listCallbackUrl
    # 2. Hacer un POST a esa URL con el payload.
    # O para un 'run': POST /.../workflows/{workflowName}/runs/...
    
    logger.warning(f"Acción '{action_name}' requiere una implementación más específica o el uso de la URL del trigger HTTP del Logic App.")
    return {
        "status": "not_implemented", 
        "action": action_name,
        "message": f"Acción '{action_name}' no implementada vía ARM. Use la URL del trigger HTTP del Logic App directamente o especifique la operación ARM deseada.", 
        "service_module": __name__, 
        "http_status": 501
    }

def get_logic_app_run_history(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> dict:
    params = params or {}
    action_name = "azure_get_logic_app_run_history"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    subscription_id = params.get("subscription_id", settings.AZURE_SUBSCRIPTION_ID)
    resource_group_name = params.get("resource_group_name", settings.AZURE_RESOURCE_GROUP)
    workflow_name = params.get("workflow_name") # Nombre de la Logic App

    if not all([subscription_id, resource_group_name, workflow_name]):
        return {"status": "error", "action": action_name, "message": "Se requieren 'subscription_id', 'resource_group_name', y 'workflow_name'.", "http_status": 400}
    
    api_version = params.get("api_version", "2019-05-01")
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Logic/workflows/{workflow_name}/runs?api-version={api_version}"
    
    odata_params: Dict[str, Any] = {}
    if params.get("$top"): odata_params["$top"] = params["$top"]
    if params.get("$filter"): odata_params["$filter"] = params["$filter"] # Ej: "status eq 'Failed'"

    logger.info(f"Obteniendo historial de ejecuciones para Logic App '{workflow_name}' en RG '{resource_group_name}'")
    try:
        response = client.get(url, scope=settings.AZURE_MGMT_DEFAULT_SCOPE, params=odata_params)
        return {"status": "success", "data": response.json().get("value", [])}
    except Exception as e:
        return _handle_azure_mgmt_api_error(e, action_name, params)