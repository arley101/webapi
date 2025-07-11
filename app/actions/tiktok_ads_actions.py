# app/actions/tiktok_ads_actions.py
import logging
import requests
import json
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

TIKTOK_BUSINESS_API_BASE_URL = "https://business-api.tiktok.com/open_api"
TIKTOK_API_VERSION = "v1.3"

# --- HELPERS INTERNOS ROBUSTOS ---

def _get_tiktok_api_headers(params: Dict[str, Any]) -> Dict[str, str]:
    """Prepara los headers para las solicitudes a la TikTok Ads API."""
    access_token: Optional[str] = params.get("access_token", settings.TIKTOK_ADS.ACCESS_TOKEN)
    if not access_token:
        raise ValueError("Se requiere 'access_token' para TikTok Ads API.")
    
    headers = {"Access-Token": access_token, "Content-Type": "application/json"}
    return headers

def _handle_tiktok_api_error(e: Exception, action_name: str) -> Dict[str, Any]:
    """Maneja errores de la API de TikTok de forma estandarizada."""
    logger.error(f"Error en TikTok Action '{action_name}': {type(e).__name__} - {e}", exc_info=True)
    
    status_code = 500
    details = str(e)
    tiktok_error_code = None
    tiktok_request_id = None

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code = e.response.status_code
        tiktok_request_id = e.response.headers.get("X-Tt-Logid")
        try:
            error_data = e.response.json()
            details = error_data.get("message", e.response.text)
            tiktok_error_code = error_data.get("code")
        except json.JSONDecodeError:
            details = e.response.text
            
    return {
        "status": "error", "action": action_name,
        "message": f"Error interactuando con TikTok Ads API: {details}",
        "details": {
            "tiktok_error_code": tiktok_error_code,
            "tiktok_request_id": tiktok_request_id,
            "raw_response": details
        },
        "http_status": status_code
    }

# --- ACCIONES PRINCIPALES ---

def tiktok_get_ad_accounts(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene la lista de cuentas publicitarias a las que el token tiene acceso."""
    action_name = "tiktok_get_ad_accounts"
    logger.info(f"Ejecutando {action_name}...")

    app_id = params.get("app_id", settings.TIKTOK_ADS.APP_ID)
    app_secret = settings.TIKTOK_ADS.APP_SECRET
    if not app_id or not app_secret:
        return {"status": "error", "message": "Se requieren 'app_id' y 'app_secret' en la configuración.", "http_status": 400}

    try:
        headers = _get_tiktok_api_headers(params)
        url = f"{TIKTOK_BUSINESS_API_BASE_URL}/{TIKTOK_API_VERSION}/oauth2/advertiser/get/"
        
        query_params = {"app_id": app_id, "secret": app_secret}

        response = requests.get(url, headers=headers, params=query_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_tiktok_api_error(e, action_name)

def tiktok_get_campaigns(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene campañas para una cuenta publicitaria, con filtros opcionales."""
    action_name = "tiktok_get_campaigns"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    advertiser_id = params.get("advertiser_id", settings.TIKTOK_ADS.DEFAULT_ADVERTISER_ID)
    if not advertiser_id:
        return {"status": "error", "message": "Se requiere 'advertiser_id' en los params o en la configuración.", "http_status": 400}

    try:
        headers = _get_tiktok_api_headers(params)
        url = f"{TIKTOK_BUSINESS_API_BASE_URL}/{TIKTOK_API_VERSION}/campaign/get/"
        
        request_payload = {
            "advertiser_id": advertiser_id,
            "page": params.get("page", 1),
            "page_size": min(int(params.get("page_size", 50)), 1000),
            "fields": params.get("fields", ["campaign_id", "campaign_name", "objective", "status", "budget"])
        }
        
        if params.get("campaign_ids_filter"):
             request_payload["filtering"] = {"campaign_ids": params["campaign_ids_filter"]}

        logger.info(f"Listando campañas de TikTok para Advertiser ID '{advertiser_id}'. Payload: {request_payload}")
        response = requests.post(url, headers=headers, json=request_payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_tiktok_api_error(e, action_name)

def tiktok_get_analytics_report(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene un reporte analítico. Requiere un tipo de reporte y un nivel de datos."""
    action_name = "tiktok_get_analytics_report"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    advertiser_id = params.get("advertiser_id", settings.TIKTOK_ADS.DEFAULT_ADVERTISER_ID)
    if not advertiser_id:
        return {"status": "error", "message": "Se requiere 'advertiser_id' en los params o en la configuración.", "http_status": 400}

    required_params = ["report_type", "data_level", "dimensions", "start_date", "end_date"]
    if not all(params.get(p) for p in required_params):
        return {"status": "error", "message": f"Se requieren los parámetros: {required_params}", "http_status": 400}

    try:
        headers = _get_tiktok_api_headers(params)
        url = f"{TIKTOK_BUSINESS_API_BASE_URL}/{TIKTOK_API_VERSION}/report/integrated/get/"

        payload_report = {
            "advertiser_id": advertiser_id,
            "report_type": params.get("report_type"),
            "data_level": params.get("data_level"),
            "dimensions": params.get("dimensions"),
            "metrics": params.get("metrics", ["spend", "impressions", "clicks", "ctr", "cpc"]),
            "start_date": params.get("start_date"),
            "end_date": params.get("end_date"),
            "page": params.get("page", 1),
            "page_size": min(int(params.get("page_size", 100)), 1000),
        }

        if params.get("filtering"):
            payload_report["filtering"] = params.get("filtering")

        logger.info(f"Obteniendo reporte de TikTok para Advertiser ID '{advertiser_id}'. Payload: {payload_report}")
        response = requests.post(url, headers=headers, json=payload_report, timeout=max(settings.DEFAULT_API_TIMEOUT, 180))
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_tiktok_api_error(e, action_name)