# app/actions/linkedin_ads_actions.py
import logging
import requests
import json
from typing import Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE_URL = "https://api.linkedin.com/rest"
LINKEDIN_API_VERSION_HEADER = "202401"

def _get_linkedin_api_headers(params: Dict[str, Any]) -> Dict[str, str]:
    access_token = params.get("access_token", settings.LINKEDIN_ACCESS_TOKEN)
    if not access_token: raise ValueError("Se requiere 'access_token' para LinkedIn API.")
    return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "LinkedIn-Version": LINKEDIN_API_VERSION_HEADER, "X-Restli-Protocol-Version": "2.0.0"}

def _handle_linkedin_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    logger.error(f"Error en LinkedIn Action '{action_name}': {type(e).__name__} - {e}", exc_info=True)
    status_code, details, service_error_code = 500, str(e), None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code = e.response.status_code
        try:
            error_data = e.response.json()
            details = error_data.get("message", e.response.text)
            service_error_code = error_data.get("serviceErrorCode")
        except json.JSONDecodeError:
            details = e.response.text
    return {"status": "error", "action": action_name, "message": f"Error interactuando con LinkedIn API: {details}", "details": {"serviceErrorCode": service_error_code, "raw_response": details}, "http_status": status_code}

def _get_ad_account_urn(params: Dict[str, Any]) -> str:
    account_id = params.get("ad_account_id", settings.DEFAULT_LINKEDIN_AD_ACCOUNT_ID)
    if not account_id: raise ValueError("Se requiere 'ad_account_id' en los params o en la configuración.")
    account_id_str = str(account_id).replace("urn:li:sponsoredAccount:", "").strip()
    if not account_id_str.isdigit(): raise ValueError(f"El 'ad_account_id' de LinkedIn ('{account_id_str}') debe ser numérico.")
    return f"urn:li:sponsoredAccount:{account_id_str}"

def linkedin_find_ad_accounts(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_find_ad_accounts"
    try:
        headers = _get_linkedin_api_headers(params)
        url = f"{LINKEDIN_API_BASE_URL}/adAccounts"
        query_params = {"q": "search", "search.name": params.get("search_name", "")}
        response = requests.get(url, headers=headers, params=query_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_get_campaign_groups(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_get_campaign_groups"
    try:
        headers = _get_linkedin_api_headers(params)
        account_urn = _get_ad_account_urn(params)
        url = f"{LINKEDIN_API_BASE_URL}/adCampaignGroups"
        query_params = {"q": "search", "search.account": account_urn}
        response = requests.get(url, headers=headers, params=query_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_get_campaigns(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_get_campaigns"
    try:
        headers = _get_linkedin_api_headers(params)
        account_urn = _get_ad_account_urn(params)
        url = f"{LINKEDIN_API_BASE_URL}/adCampaigns"
        query_params = {"q": "search", "search.account": account_urn}
        if params.get("campaign_group_id"): query_params["search.campaignGroup"] = f"urn:li:sponsoredCampaignGroup:{params['campaign_group_id']}"
        if params.get("status_filter"): query_params["search.status"] = params["status_filter"].upper()
        response = requests.get(url, headers=headers, params=query_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_get_analytics(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_get_analytics"
    try:
        headers = _get_linkedin_api_headers(params)
        url = f"{LINKEDIN_API_BASE_URL}/adAnalytics"
        if not params.get("start_year") or not params.get("end_year"): raise ValueError("Se requieren parámetros de fecha (start_year, end_year, etc.).")
        payload = {
            "dateRange": {"start": {"year": params['start_year'], "month": params['start_month'], "day": params['start_day']}, "end": {"year": params['end_year'], "month": params['end_month'], "day": params['end_day']}},
            "timeGranularity": params.get("time_granularity", "DAILY"),
            "accounts": [_get_ad_account_urn(params)]
        }
        if params.get("pivot"): payload["pivot"] = params["pivot"].upper()
        if params.get("campaign_ids"): payload["campaigns"] = [f"urn:li:sponsoredCampaign:{c_id}" for c_id in params["campaign_ids"]]
        response = requests.post(url, headers=headers, json=payload, timeout=max(settings.DEFAULT_API_TIMEOUT, 180))
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)