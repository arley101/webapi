# app/actions/powerbi_actions.py
import logging
import requests # Usado directamente para las llamadas a Power BI API
import json
import time # Podría usarse para monitorear exportaciones, aunque no implementado actualmente
from typing import Dict, List, Optional, Any

from azure.identity import ClientSecretCredential, CredentialUnavailableError # Para la autenticación de PBI

from app.core.config import settings
# AuthenticatedHttpClient no se usa aquí, pero se mantiene en la firma por consistencia con action_mapper
from app.shared.helpers.http_client import AuthenticatedHttpClient 

logger = logging.getLogger(__name__)

# --- Constantes y Configuración Específica para Power BI API ---
PBI_API_BASE_URL_MYORG = "https://api.powerbi.com/v1.0/myorg"
# Scope específico para la API REST de Power BI, definido en settings
PBI_API_DEFAULT_SCOPE = settings.POWER_BI_DEFAULT_SCOPE 
# Timeout para llamadas a Power BI API
PBI_API_CALL_TIMEOUT = max(settings.DEFAULT_API_TIMEOUT, 120) # Default más largo para PBI

# --- Helper de Autenticación (Específico para Power BI API con Client Credentials) ---
_pbi_credential_instance: Optional[ClientSecretCredential] = None

def _get_powerbi_api_token(params_from_action: Optional[Dict[str, Any]] = None) -> str:
    global _pbi_credential_instance

    auth_override_params = params_from_action.get("auth_override") if params_from_action else {}
    
    # Leer credenciales desde settings (que a su vez las lee de variables de entorno)
    # o desde el override si se proporciona.
    tenant_id = auth_override_params.get("pbi_tenant_id", settings.PBI_TENANT_ID)
    client_id = auth_override_params.get("pbi_client_id", settings.PBI_CLIENT_ID)
    client_secret = auth_override_params.get("pbi_client_secret", settings.PBI_CLIENT_SECRET)

    if not all([tenant_id, client_id, client_secret]):
        missing = []
        if not tenant_id: missing.append("PBI_TENANT_ID")
        if not client_id: missing.append("PBI_CLIENT_ID")
        if not client_secret: missing.append("PBI_CLIENT_SECRET (o sus equivalentes en auth_override)")
        
        msg = f"Faltan configuraciones de autenticación para Power BI API: {', '.join(missing)}. Verifique settings o el parámetro 'auth_override'."
        logger.critical(msg)
        raise ValueError(msg) # Este error debería ser capturado por _handle_pbi_api_error

    # Recrear instancia si no existe o si los IDs han cambiado (improbable en este flujo si no hay override, pero robusto)
    # Si hay auth_override, siempre se crea una nueva instancia para esas credenciales específicas.
    current_credential_instance: ClientSecretCredential
    if auth_override_params:
        logger.info("Creando instancia de ClientSecretCredential para Power BI con credenciales de 'auth_override'.")
        current_credential_instance = ClientSecretCredential(
            tenant_id=str(tenant_id), client_id=str(client_id), client_secret=str(client_secret)
        )
    else: # Usar instancia global si no hay override
        if _pbi_credential_instance is None or \
           (_pbi_credential_instance._tenant_id != tenant_id or _pbi_credential_instance._client_id != client_id): # type: ignore
            logger.info("Creando/Recreando instancia ClientSecretCredential global para Power BI API.")
            _pbi_credential_instance = ClientSecretCredential(
                tenant_id=str(tenant_id), client_id=str(client_id), client_secret=str(client_secret)
            )
        current_credential_instance = _pbi_credential_instance
    
    if not PBI_API_DEFAULT_SCOPE or not PBI_API_DEFAULT_SCOPE[0]: # Scope debe estar definido
        raise ValueError("POWER_BI_DEFAULT_SCOPE no está configurado correctamente en settings.")

    try:
        logger.info(f"Solicitando token para Power BI API con scope: {PBI_API_DEFAULT_SCOPE[0]}")
        token_credential = current_credential_instance.get_token(PBI_API_DEFAULT_SCOPE[0])
        logger.info("Token para Power BI API obtenido exitosamente.")
        return token_credential.token
    except CredentialUnavailableError as cred_unavailable_err:
        logger.critical(f"Credencial no disponible para obtener token Power BI: {cred_unavailable_err}", exc_info=True)
        raise ConnectionAbortedError(f"Credencial para Power BI no disponible: {cred_unavailable_err}") from cred_unavailable_err
    except Exception as token_err: # Captura cualquier otra excepción de get_token
        logger.error(f"Error inesperado obteniendo token Power BI: {type(token_err).__name__} - {token_err}", exc_info=True)
        raise ConnectionRefusedError(f"Error obteniendo token para Power BI: {token_err}") from token_err

def _get_pbi_auth_headers(params_from_action: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    try:
        token = _get_powerbi_api_token(params_from_action)
        return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    except Exception as e: # Propaga errores de _get_powerbi_api_token
        raise e 

def _handle_pbi_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Power BI action '{action_name}'"
    safe_params = {} # Inicializar
    if params_for_log:
        sensitive_keys = ['auth_override'] # payload no es común en PBI GETs
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
        
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    pbi_error_code = None # Power BI errores pueden tener una estructura diferente

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json() 
            # Power BI errores anidan en 'error': {"error": {"code": "...", "message": "..."}}
            error_info = error_data.get("error", error_data) # Tomar error_data si 'error' no está
            details_str = error_info.get("message", e.response.text)
            pbi_error_code = error_info.get("code")
        except json.JSONDecodeError:
            details_str = e.response.text[:500] if e.response.text else "No response body"
    elif isinstance(e, (ValueError, ConnectionError, ConnectionAbortedError, ConnectionRefusedError)):
        # Errores de configuración de credenciales o de obtención de token
        status_code_int = 401 # Asumir error de autenticación/configuración no autorizado
        details_str = str(e) # El mensaje de la excepción ya es descriptivo
    
    return {
        "status": "error", 
        "action": action_name,
        "message": f"Error en {action_name}: {details_str}", 
        "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str, # Detalles técnicos
        "http_status": status_code_int,
        "powerbi_error_code": pbi_error_code
    }

# ---- FUNCIONES DE ACCIÓN PARA POWER BI ----
# El parámetro 'client: AuthenticatedHttpClient' se ignora aquí ya que PBI usa su propio flujo de auth.

def list_reports(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "powerbi_list_reports"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    workspace_id: Optional[str] = params.get("workspace_id") # ID del workspace (grupo)
    
    try:
        pbi_headers = _get_pbi_auth_headers(params) # Pasar params por si hay auth_override
    except Exception as auth_err:
        return _handle_pbi_api_error(auth_err, action_name, params)

    log_owner_context: str
    if workspace_id:
        url = f"{PBI_API_BASE_URL_MYORG}/groups/{workspace_id}/reports"
        log_owner_context = f"workspace '{workspace_id}'"
    else: # Listar en "My Workspace" o todos los accesibles por la App Principal.
        url = f"{PBI_API_BASE_URL_MYORG}/reports"
        log_owner_context = "la organización (accesibles por la App Principal, o 'My Workspace')"
        logger.warning(f"{action_name}: Listando informes sin workspace_id específico. El alcance dependerá de los permisos de la App Principal de Power BI.")
    
    odata_params: Dict[str, Any] = {}
    if params.get("$filter"): odata_params["$filter"] = params["$filter"]
    if params.get("$top"): odata_params["$top"] = params["$top"]
    if params.get("$skip"): odata_params["$skip"] = params["$skip"]

    logger.info(f"Listando informes Power BI en {log_owner_context}. Filtro: {odata_params.get('$filter')}, Top: {odata_params.get('$top')}")
    try:
        response = requests.get(url, headers=pbi_headers, params=odata_params, timeout=PBI_API_CALL_TIMEOUT)
        response.raise_for_status()
        response_data = response.json()
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e:
        return _handle_pbi_api_error(e, f"{action_name} en {log_owner_context}", params)

def export_report(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "powerbi_export_report"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    report_id: Optional[str] = params.get("report_id")
    workspace_id: Optional[str] = params.get("workspace_id") # Opcional, si el reporte no está en "My Workspace"
    export_format: str = params.get("format", "PDF").upper()
    
    if not report_id:
        return {"status": "error", "action": action_name, "message": "Parámetro 'report_id' es requerido.", "http_status": 400}
    if export_format not in ["PDF", "PPTX", "PNG"]: # Otros formatos pueden existir, verificar docs.
        return {"status": "error", "action": action_name, "message": "Parámetro 'format' debe ser PDF, PPTX, o PNG.", "http_status": 400}
    
    try:
        pbi_headers = _get_pbi_auth_headers(params)
    except Exception as auth_err:
        return _handle_pbi_api_error(auth_err, action_name, params)

    log_report_context: str
    if workspace_id:
        url = f"{PBI_API_BASE_URL_MYORG}/groups/{workspace_id}/reports/{report_id}/ExportToFile"
        log_report_context = f"reporte '{report_id}' en workspace '{workspace_id}'"
    else:
        url = f"{PBI_API_BASE_URL_MYORG}/reports/{report_id}/ExportToFile" # Para reportes en "My Workspace"
        log_report_context = f"reporte '{report_id}' (asumiendo 'My Workspace')"
        logger.warning(f"{action_name}: Exportando reporte '{report_id}' sin workspace_id. Se asume que está en 'My Workspace' del usuario efectivo de la App Principal.")

    # Payload para la API de ExportToFile
    # https://learn.microsoft.com/en-us/rest/api/power-bi/reports/export-to-file
    payload_export: Dict[str, Any] = {"format": export_format}
    # Se pueden añadir configuraciones adicionales al payload, ej. para reportLevelFilters, specificPages, etc.
    # page_name = params.get("page_name") # Para exportar una página específica
    # if page_name: payload_export["powerBIReportConfiguration"] = {"pages": [{"pageName": page_name}]}
    # visual_name = params.get("visual_name") # Para exportar un visual específico (más complejo)
    # report_level_filters = params.get("report_level_filters") # Lista de filtros
    # dataset_bindings = params.get("dataset_bindings") # Para cambiar la conexión del dataset

    if params.get("powerbi_report_configuration") and isinstance(params["powerbi_report_configuration"], dict):
        payload_export["powerBIReportConfiguration"] = params["powerbi_report_configuration"]
        logger.info(f"Aplicando 'powerbi_report_configuration' personalizado a la exportación.")
    
    logger.info(f"Iniciando exportación de {log_report_context} a formato {export_format}. Payload keys: {list(payload_export.keys())}")
    try:
        response = requests.post(url, headers=pbi_headers, json=payload_export, timeout=PBI_API_CALL_TIMEOUT)
        
        # La exportación es asíncrona, devuelve 202 Accepted si se inicia.
        if response.status_code == 202: # Accepted
            export_job_details = response.json()
            export_id = export_job_details.get("id") # ID del trabajo de exportación
            logger.info(f"Exportación iniciada para {log_report_context}. Export Job ID: {export_id}. Estado actual: {export_job_details.get('status')}")
            return {
                "status": "pending", # Indicar que es una operación asíncrona
                "message": "Exportación de reporte iniciada. Use 'export_id' para verificar el estado.",
                "export_id": export_id, 
                "report_id": report_id,
                "current_status": export_job_details.get('status'), # Ej. "Running"
                "details": export_job_details, 
                "http_status": 202
            }
        else: # Si no es 202, es un error o una respuesta inesperada
            response.raise_for_status() # Forzar HTTPError para otros códigos 4xx/5xx
            # Si no lanza error pero no es 202, es raro.
            logger.warning(f"Respuesta inesperada {response.status_code} al iniciar exportación de {log_report_context}. Respuesta: {response.text[:200]}")
            return {"status": "warning", "message": f"Respuesta inesperada {response.status_code} del servidor al iniciar exportación.", "details": response.text, "http_status": response.status_code}
    except Exception as e:
        return _handle_pbi_api_error(e, f"export_report para {log_report_context}", params)


# Funciones para dashboards y datasets (siguiendo el mismo patrón)
def list_dashboards(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "powerbi_list_dashboards"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    workspace_id: Optional[str] = params.get("workspace_id")
    try:
        pbi_headers = _get_pbi_auth_headers(params)
    except Exception as auth_err:
        return _handle_pbi_api_error(auth_err, action_name, params)

    log_owner: str
    if workspace_id:
        url = f"{PBI_API_BASE_URL_MYORG}/groups/{workspace_id}/dashboards"
        log_owner = f"workspace '{workspace_id}'"
    else:
        url = f"{PBI_API_BASE_URL_MYORG}/dashboards"
        log_owner = "la organización (o 'My Workspace')"
        logger.warning(f"{action_name}: Listando dashboards sin workspace_id.")
        
    odata_params: Dict[str, Any] = {}
    if params.get("$filter"): odata_params["$filter"] = params["$filter"]
    if params.get("$top"): odata_params["$top"] = params["$top"]

    logger.info(f"Listando dashboards Power BI en {log_owner}. Filtro: {odata_params.get('$filter')}")
    try:
        response = requests.get(url, headers=pbi_headers, params=odata_params, timeout=PBI_API_CALL_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json().get("value", [])}
    except Exception as e:
        return _handle_pbi_api_error(e, f"{action_name} en {log_owner}", params)

def list_datasets(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "powerbi_list_datasets"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    workspace_id: Optional[str] = params.get("workspace_id")
    try:
        pbi_headers = _get_pbi_auth_headers(params)
    except Exception as auth_err:
        return _handle_pbi_api_error(auth_err, action_name, params)

    log_owner: str
    if workspace_id:
        url = f"{PBI_API_BASE_URL_MYORG}/groups/{workspace_id}/datasets"
        log_owner = f"workspace '{workspace_id}'"
    else:
        url = f"{PBI_API_BASE_URL_MYORG}/datasets"
        log_owner = "la organización (o 'My Workspace')"
        logger.warning(f"{action_name}: Listando datasets sin workspace_id.")
        
    odata_params: Dict[str, Any] = {}
    if params.get("$filter"): odata_params["$filter"] = params["$filter"]
    if params.get("$top"): odata_params["$top"] = params["$top"]

    logger.info(f"Listando datasets Power BI en {log_owner}. Filtro: {odata_params.get('$filter')}")
    try:
        response = requests.get(url, headers=pbi_headers, params=odata_params, timeout=PBI_API_CALL_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json().get("value", [])}
    except Exception as e:
        return _handle_pbi_api_error(e, f"{action_name} en {log_owner}", params)

def refresh_dataset(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "powerbi_refresh_dataset"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    dataset_id: Optional[str] = params.get("dataset_id")
    workspace_id: Optional[str] = params.get("workspace_id") # ID del workspace donde reside el dataset
    notify_option: Optional[str] = params.get("notify_option") # Ej: "MailOnCompletion", "MailOnFailure", "NoNotification"

    if not dataset_id:
        return {"status": "error", "action": action_name, "message": "Parámetro 'dataset_id' es requerido.", "http_status": 400}
    
    try:
        pbi_headers = _get_pbi_auth_headers(params)
    except Exception as auth_err:
        return _handle_pbi_api_error(auth_err, action_name, params)

    log_dataset_context: str
    if workspace_id:
        url = f"{PBI_API_BASE_URL_MYORG}/groups/{workspace_id}/datasets/{dataset_id}/refreshes"
        log_dataset_context = f"dataset '{dataset_id}' en workspace '{workspace_id}'"
    else:
        url = f"{PBI_API_BASE_URL_MYORG}/datasets/{dataset_id}/refreshes"
        log_dataset_context = f"dataset '{dataset_id}' (asumiendo 'My Workspace')"
        logger.warning(f"{action_name}: Iniciando refresco para dataset '{dataset_id}' sin workspace_id.")

    payload_refresh: Dict[str, Any] = {}
    if notify_option and notify_option in ["MailOnCompletion", "MailOnFailure", "NoNotification"]:
        payload_refresh["notifyOption"] = notify_option
    
    logger.info(f"Iniciando refresco para {log_dataset_context}. NotifyOption: {notify_option or 'Default API'}")
    try:
        # La API de refresco es un POST
        response = requests.post(url, headers=pbi_headers, json=payload_refresh if payload_refresh else None, timeout=PBI_API_CALL_TIMEOUT)
        
        # Un refresco exitoso devuelve 202 Accepted.
        if response.status_code == 202:
            # La respuesta de 202 no suele tener cuerpo JSON, pero puede tener headers útiles.
            request_id_pbi_header = response.headers.get("RequestId") # RequestId es útil para seguimiento con Soporte PBI
            logger.info(f"Solicitud de refresco para {log_dataset_context} aceptada (202). Power BI RequestId (header): {request_id_pbi_header}")
            return {
                "status": "pending", # Es una operación asíncrona
                "message": "Solicitud de refresco de dataset aceptada y en progreso.", 
                "dataset_id": dataset_id, 
                "pbi_request_id": request_id_pbi_header, 
                "http_status": 202
            }
        else:
            response.raise_for_status() # Forzar error para otros códigos 4xx/5xx
            logger.warning(f"Respuesta inesperada {response.status_code} al iniciar refresco de {log_dataset_context}. Respuesta: {response.text[:200]}")
            return {"status": "warning", "message": f"Respuesta inesperada {response.status_code} del servidor al iniciar refresco.", "details": response.text, "http_status": response.status_code}
    except Exception as e:
        return _handle_pbi_api_error(e, f"refresh_dataset para {log_dataset_context}", params)

# Las funciones "powerbi_listar_workspaces" y "powerbi_obtener_estado_refresco_dataset"
# estaban comentadas en el action_mapper original. Si se necesitan, se pueden implementar:
# - Listar Workspaces (Grupos): GET /groups
# - Obtener Estado de Refresco: GET /groups/{groupId}/datasets/{datasetId}/refreshes (para ver historial y estado)
#   o GET /groups/{groupId}/datasets/{datasetId}/refreshes/{refreshId} (para un refresco específico)
# - Obtener estado de exportación: GET /groups/{groupId}/reports/{reportId}/exports/{exportId}

# --- FIN DEL MÓDULO actions/powerbi_actions.py ---