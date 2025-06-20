# app/actions/power_automate_actions.py
import logging
import os # No se usa directamente, pero podría serlo en el futuro.
import requests # Para ejecutar_flow (llamada directa a trigger) y tipos de excepción
import json # Para el helper de error
from typing import Dict, Optional, Any, List # Añadido List

# Importar la configuración y el cliente HTTP autenticado
from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient # Para llamadas ARM
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# API Version para Logic Apps (Power Automate flows son Logic Apps bajo el capó)
LOGIC_APPS_API_VERSION = "2019-05-01" # Esto podría ir a settings si varía.

def _handle_pa_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Power Automate action '{action_name}'"
    safe_params = {} # Inicializar
    if params_for_log:
        # Omitir payloads sensibles
        sensitive_keys = ['payload', 'trigger_headers']
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    error_source_api_code = None # Para códigos de error de ARM o del trigger HTTP

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        try:
            error_data = e.response.json()
            # Estructura de error de ARM
            if "error" in error_data and isinstance(error_data["error"], dict):
                error_info = error_data["error"]
                details_str = error_info.get("message", e.response.text)
                error_source_api_code = error_info.get("code")
            else: # Para errores de trigger HTTP que no son ARM
                details_str = e.response.text # o error_data si es JSON
        except json.JSONDecodeError: 
            details_str = e.response.text[:500] if e.response.text else "No response body"
            
    return {
        "status": "error", 
        "action": action_name,
        "message": f"Error en {action_name}: {details_str}", 
        "details": str(e) if not isinstance(e, requests.exceptions.HTTPError) else details_str,
        "http_status": status_code_int,
        "api_error_code": error_source_api_code # Código del error de la API subyacente
    }


# ---- FUNCIONES DE ACCIÓN PARA POWER AUTOMATE (Workflows/Logic Apps) ----

def listar_flows(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "pa_listar_flows" # Corregido para coincidir con ACTION_MAP (si es el caso)
    logger.info(f"Ejecutando {action_name} con params: {params}")

    suscripcion_id = params.get('suscripcion_id', settings.AZURE_SUBSCRIPTION_ID)
    grupo_recurso = params.get('grupo_recurso', settings.AZURE_RESOURCE_GROUP)

    if not suscripcion_id: # grupo_recurso puede ser opcional si se quiere listar todos en sub
        msg = "Parámetro 'suscripcion_id' (o AZURE_SUBSCRIPTION_ID en settings) es requerido."
        logger.error(f"{action_name}: {msg}")
        return {"status": "error", "action": action_name, "message": msg, "http_status": 400}

    api_version = params.get("api_version", LOGIC_APPS_API_VERSION)
    odata_params: Dict[str, Any] = {}
    if params.get("$top"): odata_params["$top"] = params["$top"]
    if params.get("$filter"): odata_params["$filter"] = params["$filter"]
    
    url_base: str
    log_context: str

    if grupo_recurso:
        url_base = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{suscripcion_id}/resourceGroups/{grupo_recurso}/providers/Microsoft.Logic/workflows"
        log_context = f"Suscripción '{suscripcion_id}', GrupoRecursos '{grupo_recurso}'"
    else:
        url_base = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{suscripcion_id}/providers/Microsoft.Logic/workflows"
        log_context = f"Suscripción '{suscripcion_id}' (todos los grupos de recursos)"
        logger.warning(f"{action_name}: Listando flujos para toda la suscripción ya que 'grupo_recurso' no fue provisto.")
        
    url = f"{url_base}?api-version={api_version}"

    logger.info(f"Listando flujos (Logic Apps) en {log_context}. API Version: {api_version}, OData: {odata_params}")
    try:
        # El scope para Azure Management API
        mgmt_scope = settings.AZURE_MGMT_DEFAULT_SCOPE
        if not mgmt_scope: raise ValueError("AZURE_MGMT_DEFAULT_SCOPE no está configurado.")

        response = client.get(url, scope=mgmt_scope, params=odata_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response_data = response.json()
        return {"status": "success", "data": response_data.get("value", [])}
    except Exception as e:
        return _handle_pa_api_error(e, action_name, params)


def obtener_flow(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "pa_obtener_flow" # Corregido para coincidir con ACTION_MAP
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    nombre_flow: Optional[str] = params.get("nombre_flow")
    if not nombre_flow:
        return {"status": "error", "action": action_name, "message": "'nombre_flow' es requerido.", "http_status": 400}

    suscripcion_id = params.get('suscripcion_id', settings.AZURE_SUBSCRIPTION_ID)
    grupo_recurso = params.get('grupo_recurso', settings.AZURE_RESOURCE_GROUP)
    if not suscripcion_id or not grupo_recurso:
        msg = "Parámetros 'suscripcion_id' y 'grupo_recurso' (o sus equivalentes en settings) son requeridos."
        logger.error(f"{action_name}: {msg}")
        return {"status": "error", "action": action_name, "message": msg, "http_status": 400}

    api_version = params.get("api_version", LOGIC_APPS_API_VERSION)
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{suscripcion_id}/resourceGroups/{grupo_recurso}/providers/Microsoft.Logic/workflows/{nombre_flow}?api-version={api_version}"
    
    odata_params: Dict[str, Any] = {}
    if params.get("$select"): odata_params["$select"] = params["$select"] # Si se quieren campos específicos

    logger.info(f"Obteniendo flow '{nombre_flow}' en RG '{grupo_recurso}', Suscripción '{suscripcion_id}'. Select: {odata_params.get('$select')}")
    try:
        mgmt_scope = settings.AZURE_MGMT_DEFAULT_SCOPE
        if not mgmt_scope: raise ValueError("AZURE_MGMT_DEFAULT_SCOPE no está configurado.")
        
        response = client.get(url, scope=mgmt_scope, params=odata_params if odata_params else None, timeout=settings.DEFAULT_API_TIMEOUT)
        flow_data = response.json()
        return {"status": "success", "data": flow_data}
    except requests.exceptions.HTTPError as http_err:
        if http_err.response is not None and http_err.response.status_code == 404:
            return {"status": "error", "action": action_name, "message": f"Flow (Logic App) '{nombre_flow}' no encontrado.", "details": http_err.response.text, "http_status": 404}
        return _handle_pa_api_error(http_err, action_name, params)
    except Exception as e:
        return _handle_pa_api_error(e, action_name, params)


def ejecutar_flow(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    # El `client: AuthenticatedHttpClient` no se usa aquí porque es una llamada HTTP directa al trigger del flow.
    # Se mantiene en la firma por consistencia con el action_mapper.
    params = params or {}
    action_name = "pa_ejecutar_flow" # Corregido para coincidir con ACTION_MAP
    log_params = {k:v for k,v in params.items() if k not in ['payload', 'trigger_headers']}
    if 'payload' in params: log_params['payload_provided'] = True
    if 'trigger_headers' in params: log_params['custom_headers_provided'] = True
    logger.info(f"Ejecutando {action_name} con params: {log_params}")
    
    flow_trigger_url: Optional[str] = params.get("flow_trigger_url")
    payload: Optional[Dict[str, Any]] = params.get("payload") # Cuerpo JSON para el trigger
    custom_headers_for_trigger: Optional[Dict[str, str]] = params.get("trigger_headers") # Ej. para API Keys

    if not flow_trigger_url:
        return {"status": "error", "action": action_name, "message": "Parámetro 'flow_trigger_url' (URL del trigger HTTP del flujo) es requerido.", "http_status": 400}

    request_headers = custom_headers_for_trigger or {}
    # Si hay payload y no se especificó Content-Type, asumir application/json
    if payload and 'Content-Type' not in request_headers:
        request_headers.setdefault('Content-Type', 'application/json')

    logger.info(f"Ejecutando trigger de Power Automate flow (Logic App): POST a {flow_trigger_url.split('?')[0]}... (Query params en URL omitidos del log)")
    try:
        # Usar requests.post directamente, no el client autenticado para Graph/ARM
        response = requests.post(
            flow_trigger_url,
            headers=request_headers,
            json=payload if payload and request_headers.get('Content-Type') == 'application/json' else None,
            data=json.dumps(payload) if payload and request_headers.get('Content-Type') != 'application/json' else None, 
            timeout=max(settings.DEFAULT_API_TIMEOUT, 120) # Timeout más largo para triggers de flow
        )
        response.raise_for_status() # Lanza HTTPError para 4xx/5xx

        logger.info(f"Trigger de flow invocado. URL (base): {flow_trigger_url.split('?')[0]}, Status: {response.status_code}, Reason: {response.reason}")
        
        response_body: Any
        try:
            response_body = response.json()
        except json.JSONDecodeError:
            response_body = response.text if response.text else "Respuesta vacía del trigger del flow."

        # POST a un trigger de flow puede devolver 200 OK, 202 Accepted (si el flujo es largo), u otros.
        status_message = "Respuesta del trigger del flujo."
        if response.status_code == 202:
            status_message = "Solicitud al flujo aceptada y en procesamiento (asíncrono)."
        
        return {
            "status": "success" if response.ok else "accepted", # "accepted" para 202
            "message": status_message,
            "http_status": response.status_code,
            "response_body": response_body,
            "response_headers": dict(response.headers) 
        }
    except requests.exceptions.RequestException as e: # Incluye HTTPError, ConnectionError, Timeout
        # _handle_pa_api_error está más orientado a errores ARM JSON, así que aquí un manejo más directo
        error_body = e.response.text[:500] if e.response is not None and e.response.text else str(e)
        status_code_err = e.response.status_code if e.response is not None else 503 # 503 para ConnectionError/Timeout
        logger.error(f"Error de red/HTTP ejecutando trigger de flow '{flow_trigger_url.split('?')[0]}...': {status_code_err} - {e}. Respuesta: {error_body}", exc_info=True)
        return {"status": "error", "action": action_name, "message": f"Error API/Red ejecutando trigger de flow: {type(e).__name__}", "details": error_body, "http_status": status_code_err}
    except Exception as e: # Otros errores inesperados
        logger.error(f"Error inesperado ejecutando trigger de flow '{flow_trigger_url.split('?')[0]}...': {e}", exc_info=True)
        return {"status": "error", "action": action_name, "message": f"Error inesperado al ejecutar trigger de flow: {type(e).__name__}", "details": str(e), "http_status":500}


def obtener_estado_ejecucion_flow(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "pa_obtener_estado_ejecucion_flow" # Corregido para coincidir con ACTION_MAP
    logger.info(f"Ejecutando {action_name} con params: {params}")

    nombre_flow: Optional[str] = params.get("nombre_flow")
    run_id: Optional[str] = params.get("run_id") # ID de la ejecución (workflow run)
    if not nombre_flow or not run_id:
        return {"status": "error", "action": action_name, "message": "Parámetros 'nombre_flow' y 'run_id' son requeridos.", "http_status": 400}

    suscripcion_id = params.get('suscripcion_id', settings.AZURE_SUBSCRIPTION_ID)
    grupo_recurso = params.get('grupo_recurso', settings.AZURE_RESOURCE_GROUP)
    if not suscripcion_id or not grupo_recurso:
        msg = "Parámetros 'suscripcion_id' y 'grupo_recurso' (o sus equivalentes en settings) son requeridos."
        logger.error(f"{action_name}: {msg}")
        return {"status": "error", "action": action_name, "message": msg, "http_status": 400}

    api_version = params.get("api_version", LOGIC_APPS_API_VERSION)
    # Endpoint para obtener una ejecución específica de un workflow
    url = f"{settings.AZURE_MGMT_API_BASE_URL}/subscriptions/{suscripcion_id}/resourceGroups/{grupo_recurso}/providers/Microsoft.Logic/workflows/{nombre_flow}/runs/{run_id}?api-version={api_version}"
    
    odata_params: Dict[str, Any] = {}
    if params.get("$select"): odata_params["$select"] = params["$select"] # Ej: "name,status,startTime,endTime,outputs,error"
    
    logger.info(f"Obteniendo estado de ejecución '{run_id}' del flow (Logic App) '{nombre_flow}' en RG '{grupo_recurso}'. Select: {odata_params.get('$select')}")
    try:
        mgmt_scope = settings.AZURE_MGMT_DEFAULT_SCOPE
        if not mgmt_scope: raise ValueError("AZURE_MGMT_DEFAULT_SCOPE no está configurado.")
        
        response = client.get(url, scope=mgmt_scope, params=odata_params if odata_params else None, timeout=settings.DEFAULT_API_TIMEOUT)
        run_data = response.json()
        return {"status": "success", "data": run_data}
    except requests.exceptions.HTTPError as http_err:
        if http_err.response is not None and http_err.response.status_code == 404:
            return {"status": "error", "action": action_name, "message": f"Ejecución de flow (Logic App run) '{run_id}' no encontrada para workflow '{nombre_flow}'.", "details": http_err.response.text, "http_status": 404}
        return _handle_pa_api_error(http_err, action_name, params)
    except Exception as e:
        return _handle_pa_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/power_automate_actions.py ---