# app/actions/tiktok_ads_actions.py
import logging
import requests
import json
from typing import Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

TIKTOK_BUSINESS_API_BASE_URL = "https://business-api.tiktok.com/open_api"
TIKTOK_API_VERSION = "v1.3"

def _get_tiktok_api_headers(params: Dict[str, Any]) -> Dict[str, str]:
    access_token: Optional[str] = params.get("access_token", settings.TIKTOK_ADS.ACCESS_TOKEN)
    if not access_token: raise ValueError("Se requiere 'access_token' para TikTok Ads API.")
    return {"Access-Token": access_token, "Content-Type": "application/json"}

def _handle_tiktok_api_error(e: Exception, action_name: str) -> Dict[str, Any]:
    logger.error(f"Error en TikTok Action '{action_name}': {type(e).__name__} - {e}", exc_info=True)
    status_code, details, tiktok_error_code, tiktok_request_id = 500, str(e), None, None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code = e.response.status_code
        tiktok_request_id = e.response.headers.get("X-Tt-Logid")
        try:
            error_data = e.response.json()
            details = error_data.get("message", e.response.text)
            tiktok_error_code = error_data.get("code")
        except json.JSONDecodeError:
            details = e.response.text
    return {"status": "error", "action": action_name, "message": f"Error interactuando con TikTok Ads API: {details}", "details": {"tiktok_error_code": tiktok_error_code, "tiktok_request_id": tiktok_request_id, "raw_response": details}, "http_status": status_code}

def tiktok_get_ad_accounts(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "tiktok_get_ad_accounts"
    try:
        app_id = params.get("app_id", settings.TIKTOK_ADS.APP_ID)
        app_secret = settings.TIKTOK_ADS.APP_SECRET
        if not app_id or not app_secret: raise ValueError("Se requieren 'app_id' y 'app_secret' en la configuración.")
        headers = _get_tiktok_api_headers(params)
        url = f"{TIKTOK_BUSINESS_API_BASE_URL}/{TIKTOK_API_VERSION}/oauth2/advertiser/get/"
        query_params = {"app_id": app_id, "secret": app_secret}
        response = requests.get(url, headers=headers, params=query_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_tiktok_api_error(e, action_name)

def tiktok_get_campaigns(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "tiktok_get_campaigns"
    try:
        advertiser_id = params.get("advertiser_id", settings.TIKTOK_ADS.DEFAULT_ADVERTISER_ID)
        if not advertiser_id: raise ValueError("Se requiere 'advertiser_id' en los params o en la configuración.")
        headers = _get_tiktok_api_headers(params)
        url = f"{TIKTOK_BUSINESS_API_BASE_URL}/{TIKTOK_API_VERSION}/campaign/get/"
        request_payload = {
            "advertiser_id": advertiser_id,
            "page": params.get("page", 1),
            "page_size": min(int(params.get("page_size", 50)), 1000),
            "fields": params.get("fields", ["campaign_id", "campaign_name", "objective", "status", "budget"])
        }
        if params.get("campaign_ids_filter"): request_payload["filtering"] = {"campaign_ids": params["campaign_ids_filter"]}
        response = requests.get(url, headers=headers, json=request_payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_tiktok_api_error(e, action_name)

def tiktok_get_analytics_report(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "tiktok_get_analytics_report"
    try:
        advertiser_id = params.get("advertiser_id", settings.TIKTOK_ADS.DEFAULT_ADVERTISER_ID)
        if not advertiser_id: raise ValueError("Se requiere 'advertiser_id'.")
        required = ["report_type", "data_level", "dimensions", "start_date", "end_date"]
        if not all(params.get(p) for p in required): raise ValueError(f"Se requieren los parámetros: {required}")
        headers = _get_tiktok_api_headers(params)
        url = f"{TIKTOK_BUSINESS_API_BASE_URL}/{TIKTOK_API_VERSION}/report/integrated/get/"
        payload_report = {
            "advertiser_id": advertiser_id,
            "report_type": params["report_type"],
            "data_level": params["data_level"],
            "dimensions": params["dimensions"],
            "metrics": params.get("metrics", ["spend", "impressions", "clicks", "ctr", "cpc"]),
            "start_date": params["start_date"],
            "end_date": params["end_date"],
            "page": params.get("page", 1),
            "page_size": min(int(params.get("page_size", 100)), 1000),
        }
        if params.get("filtering"): payload_report["filtering"] = params.get("filtering")
        response = requests.get(url, headers=headers, json=payload_report, timeout=max(settings.DEFAULT_API_TIMEOUT, 180))
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_tiktok_api_error(e, action_name)