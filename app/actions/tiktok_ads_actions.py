# app/actions/tiktok_ads_actions.py
import logging
import requests
import json
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# Asegúrate de que esta sea la URL base correcta y la versión más reciente de la API
TIKTOK_BUSINESS_API_BASE_URL = "https://business-api.tiktok.com/open_api"
TIKTOK_API_VERSION = "v1.3" # O la versión que estés utilizando

def _get_tiktok_api_headers(params: Dict[str, Any]) -> Dict[str, str]:
    """
    Prepara los headers para las solicitudes a la TikTok Ads API.
    Prioriza el access_token de params, luego de settings.
    """
    access_token: Optional[str] = params.get("access_token", settings.TIKTOK_ADS.ACCESS_TOKEN)

    if not access_token:
        raise ValueError("Se requiere 'access_token' para TikTok Ads API (ya sea en params o configurado en el backend).")
    
    headers = {
        "Access-Token": access_token,
        "Content-Type": "application/json"
    }
    # TikTok puede requerir otros headers para ciertos endpoints, ej. 'Advertiser-Id'
    # Se añadirán directamente en las funciones de acción si es necesario.
    return headers

def _handle_tiktok_api_error(
    e: Exception,
    action_name: str,
    params_for_log: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Helper para manejar errores de TikTok Ads API."""
    log_message = f"Error en TikTok Ads Action '{action_name}'"
    safe_params = {}
    if params_for_log:
        sensitive_keys = ['access_token', 'campaign_data', 'app_id'] # Ajusta según sea necesario
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    tiktok_error_code = None
    tiktok_request_id = None

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        tiktok_request_id = e.response.headers.get("X-Tt-Logid") # TikTok usa X-Tt-Logid para request ID
        try:
            error_data = e.response.json()
            # Estructura de error de TikTok: {"code": X, "message": "...", "request_id": "...", "data": {}}
            tiktok_error_code = error_data.get("code")
            details_str = error_data.get("message", e.response.text)
            if not tiktok_request_id: # A veces el request_id también está en el cuerpo
                tiktok_request_id = error_data.get("request_id")
        except json.JSONDecodeError:
            details_str = e.response.text[:500] if e.response.text else "No response body"
            
    return {
        "status": "error",
        "action": action_name,
        "message": f"Error interactuando con TikTok Ads API: {details_str}",
        "details": {
            "raw_exception_type": type(e).__name__,
            "raw_exception_message": str(e),
            "tiktok_api_error_code": tiktok_error_code,
            "tiktok_api_request_id": tiktok_request_id,
            "response_body": details_str if isinstance(e, requests.exceptions.HTTPError) else None
        },
        "http_status": status_code_int,
    }

# --- ACCIONES CRUD ---
# Nota: El parámetro 'client: AuthenticatedHttpClient' no se usa aquí.
# Se mantiene por consistencia con el action_mapper.

def tiktok_get_ad_accounts(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "tiktok_get_ad_accounts"
    logger.info(f"Ejecutando {action_name} con params (token/keys omitidos del log): %s", {k:v for k,v in params.items() if k not in ['access_token', 'app_id']})

    app_id: Optional[str] = params.get("app_id", settings.TIKTOK_ADS.APP_ID)
    if not app_id:
        return {"status": "error", "action": action_name, "message": "'app_id' es requerido (en params o configurado en el backend).", "http_status": 400}

    try:
        headers = _get_tiktok_api_headers(params)
        url = f"{TIKTOK_BUSINESS_API_BASE_URL}/{TIKTOK_API_VERSION}/oauth2/advertiser/get/"
        
        # Parámetros de la query para este endpoint
        query_api_params = {"app_id": app_id, "secret": settings.TIKTOK_ADS.APP_SECRET } # Asumiendo que tienes APP_SECRET para este endpoint
        # ¡CUIDADO! Si APP_SECRET se requiere, debe estar en settings.TIKTOK_ADS.APP_SECRET
        # Revisa la documentación de este endpoint específico. Si no requiere secret, quítalo.
        # Si el 'secret' se refiere al App Secret de la app de TikTok y no al token, debe cargarse de settings.
        # Es posible que 'secret' no sea necesario si el access_token ya encapsula la autorización de la app.
        # Voy a asumir que el `access_token` es suficiente por ahora, ya que es el método más común.
        # Si el endpoint /oauth2/advertiser/get/ *específicamente* requiere app_id Y secret en la query,
        # entonces settings.TIKTOK_ADS.APP_SECRET debe existir.

        # Simplificando la llamada si solo se necesita app_id con el token:
        query_api_params_for_request = {"app_id": app_id}
        if params.get("secret_for_endpoint"): # Permitir pasar un secret si es necesario para ciertos calls
            query_api_params_for_request["secret"] = params["secret_for_endpoint"]


        logger.info(f"Listando cuentas publicitarias de TikTok para App ID '{app_id}'.")
        response = requests.get(url, headers=headers, params=query_api_params_for_request, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve: # Error de _get_tiktok_api_headers
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_tiktok_api_error(e, action_name, params)

def tiktok_list_campaigns(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "tiktok_list_campaigns"
    logger.info(f"Ejecutando {action_name} con params (token/keys omitidos del log): %s", {k:v for k,v in params.items() if k not in ['access_token']})

    advertiser_id: Optional[str] = params.get("advertiser_id", settings.TIKTOK_ADS.DEFAULT_ADVERTISER_ID)
    if not advertiser_id:
        return {"status": "error", "action": action_name, "message": "'advertiser_id' es requerido (en params o configurado como default en el backend).", "http_status": 400}

    # Parámetros de filtrado y paginación para la API de TikTok
    # Consultar https://ads.tiktok.com/marketing_api/docs?id=1705080308396033
    filtering_payload: Optional[Dict[str, Any]] = params.get("filtering") # Objeto con filtros
    page: int = params.get("page", 1)
    page_size: int = min(params.get("page_size", 50), 100) # Max page_size suele ser 100
    fields: Optional[List[str]] = params.get("fields") 

    try:
        headers = _get_tiktok_api_headers(params)
        url = f"{TIKTOK_BUSINESS_API_BASE_URL}/{TIKTOK_API_VERSION}/campaign/get/"
        
        request_payload: Dict[str, Any] = {"advertiser_id": advertiser_id}
        if filtering_payload and isinstance(filtering_payload, dict):
            request_payload["filtering"] = filtering_payload
        request_payload["page"] = page
        request_payload["page_size"] = page_size
        if fields and isinstance(fields, list):
            request_payload["fields"] = fields
        else: # Campos por defecto si no se especifican
            request_payload["fields"] = ["campaign_id", "campaign_name", "objective_type", "budget_mode", "budget", "status", "create_time", "modify_time"]

        logger.info(f"Listando campañas de TikTok para Advertiser ID '{advertiser_id}'. Payload: {request_payload}")
        # La API de /campaign/get/ usa POST con el cuerpo JSON para los parámetros de filtrado/paginación
        response = requests.post(url, headers=headers, json=request_payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_tiktok_api_error(e, action_name, params)

def tiktok_create_campaign(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "tiktok_create_campaign"
    log_params = {k:v for k,v in params.items() if k not in ['access_token', 'campaign_data']}
    if 'campaign_data' in params: log_params['campaign_data_keys'] = list(params['campaign_data'].keys())
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    advertiser_id: Optional[str] = params.get("advertiser_id", settings.TIKTOK_ADS.DEFAULT_ADVERTISER_ID)
    campaign_data: Optional[Dict[str, Any]] = params.get("campaign_data")

    if not advertiser_id:
        return {"status": "error", "action": action_name, "message": "'advertiser_id' es requerido.", "http_status": 400}
    if not campaign_data or not isinstance(campaign_data, dict):
        return {"status": "error", "action": action_name, "message": "'campaign_data' (dict) es requerido.", "http_status": 400}
    
    # Asegurar que advertiser_id esté en el payload principal para la API
    final_payload = campaign_data.copy()
    final_payload["advertiser_id"] = advertiser_id

    # Validar campos mínimos en campaign_data según la API de TikTok (ej. campaign_name, objective_type, budget_mode)
    # Esto es solo un ejemplo, se deben verificar los campos requeridos reales
    required_fields_example = ["campaign_name", "objective_type", "budget_mode"]
    if not all(key in final_payload for key in required_fields_example):
        missing = [key for key in required_fields_example if key not in final_payload]
        return {"status": "error", "action": action_name, "message": f"Faltan campos requeridos en 'campaign_data': {missing}.", "http_status": 400}

    try:
        headers = _get_tiktok_api_headers(params)
        url = f"{TIKTOK_BUSINESS_API_BASE_URL}/{TIKTOK_API_VERSION}/campaign/create/"
        
        logger.info(f"Creando campaña de TikTok para Advertiser ID '{advertiser_id}'. Nombre: {final_payload.get('campaign_name')}")
        response = requests.post(url, headers=headers, json=final_payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_tiktok_api_error(e, action_name, params)

def tiktok_update_campaign(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "tiktok_update_campaign"
    log_params = {k:v for k,v in params.items() if k not in ['access_token', 'campaign_data']}
    if 'campaign_data' in params: log_params['campaign_data_keys'] = list(params['campaign_data'].keys())
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    advertiser_id: Optional[str] = params.get("advertiser_id", settings.TIKTOK_ADS.DEFAULT_ADVERTISER_ID)
    campaign_data: Optional[Dict[str, Any]] = params.get("campaign_data") # Debe incluir campaign_id

    if not advertiser_id:
        return {"status": "error", "action": action_name, "message": "'advertiser_id' es requerido.", "http_status": 400}
    if not campaign_data or not isinstance(campaign_data, dict) or not campaign_data.get("campaign_id"):
        return {"status": "error", "action": action_name, "message": "'campaign_data' (dict) con 'campaign_id' es requerido.", "http_status": 400}

    final_payload = campaign_data.copy()
    final_payload["advertiser_id"] = advertiser_id

    try:
        headers = _get_tiktok_api_headers(params)
        url = f"{TIKTOK_BUSINESS_API_BASE_URL}/{TIKTOK_API_VERSION}/campaign/update/"
        
        logger.info(f"Actualizando campaña de TikTok ID '{final_payload['campaign_id']}' para Advertiser ID '{advertiser_id}'.")
        response = requests.post(url, headers=headers, json=final_payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        # La API de update a menudo devuelve un cuerpo vacío o solo un indicador de éxito.
        # Consultar la documentación para la respuesta exacta.
        # Si devuelve datos, se pueden incluir en "data".
        response_data = response.json() if response.content else {"message": "Campaña actualizada exitosamente."}
        return {"status": "success", "action": action_name, "data": response_data, "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_tiktok_api_error(e, action_name, params)

def tiktok_get_basic_report(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "tiktok_get_basic_report"
    logger.info(f"Ejecutando {action_name} con params (token/keys omitidos del log): %s", {k:v for k,v in params.items() if k not in ['access_token']})

    advertiser_id: Optional[str] = params.get("advertiser_id", settings.TIKTOK_ADS.DEFAULT_ADVERTISER_ID)
    report_type: str = params.get("report_type", "BASIC") # Ej: BASIC, AUDIENCE, PLAYABLE_MATERIAL, CATALOG
    data_level: str = params.get("data_level", "AUCTION_CAMPAIGN") # Ej: AUCTION_AD, AUCTION_ADGROUP, AUCTION_CAMPAIGN
    dimensions: Optional[List[str]] = params.get("dimensions")
    metrics: Optional[List[str]] = params.get("metrics")
    start_date_str: Optional[str] = params.get("start_date") # YYYY-MM-DD
    end_date_str: Optional[str] = params.get("end_date") # YYYY-MM-DD
    filtering_payload: Optional[Dict[str, Any]] = params.get("filtering")
    order_field: Optional[str] = params.get("order_field")
    order_type: Optional[str] = params.get("order_type") # ASC, DESC
    page: int = params.get("page", 1)
    page_size: int = min(params.get("page_size", 50), 1000) # Max page_size puede ser 1000 para reportes

    if not advertiser_id:
        return {"status": "error", "action": action_name, "message": "'advertiser_id' es requerido.", "http_status": 400}
    if not dimensions or not isinstance(dimensions, list):
        return {"status": "error", "action": action_name, "message": "'dimensions' (lista de strings) es requerido.", "http_status": 400}
    if not metrics or not isinstance(metrics, list):
        return {"status": "error", "action": action_name, "message": "'metrics' (lista de strings) es requerido.", "http_status": 400}
    
    # Para reportes síncronos, la documentación menciona /report/integrated/get/
    # https://ads.tiktok.com/marketing_api/docs?id=1701890903410690
    
    try:
        headers = _get_tiktok_api_headers(params)
        url = f"{TIKTOK_BUSINESS_API_BASE_URL}/{TIKTOK_API_VERSION}/report/integrated/get/"
        
        payload_report: Dict[str, Any] = {
            "advertiser_id": advertiser_id,
            "report_type": report_type,
            "data_level": data_level,
            "dimensions": dimensions,
            "metrics": metrics,
            "page": page,
            "page_size": page_size
        }
        if start_date_str: payload_report["start_date"] = start_date_str
        if end_date_str: payload_report["end_date"] = end_date_str
        if filtering_payload and isinstance(filtering_payload, dict): payload_report["filtering"] = filtering_payload
        if order_field: payload_report["order_field"] = order_field
        if order_type: payload_report["order_type"] = order_type


        logger.info(f"Obteniendo reporte de TikTok para Advertiser ID '{advertiser_id}'. Payload: {payload_report}")
        # Esta API también usa POST con el cuerpo JSON
        response = requests.post(url, headers=headers, json=payload_report, timeout=max(settings.DEFAULT_API_TIMEOUT, 180)) # Timeout más largo para reportes
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_tiktok_api_error(e, action_name, params)

# --- FIN DEL MÓDULO actions/tiktok_ads_actions.py ---