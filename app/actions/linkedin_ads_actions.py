# app/actions/linkedin_ads_actions.py
import logging
import requests
import json
from typing import Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE_URL = "https://api.linkedin.com/rest"
LINKEDIN_API_VERSION_HEADER = "202401" # Mantenerse actualizado con la versión recomendada

def _get_linkedin_api_headers(params: Dict[str, Any]) -> Dict[str, str]:
    access_token = params.get("access_token", settings.LINKEDIN_ACCESS_TOKEN)
    if not access_token: raise ValueError("Se requiere 'access_token' para la LinkedIn API (en params o en settings).")
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": LINKEDIN_API_VERSION_HEADER,
        "X-Restli-Protocol-Version": "2.0.0"
    }

def _handle_linkedin_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en LinkedIn Action '{action_name}': {type(e).__name__} - {e}"
    logger.error(log_message, exc_info=True)
    status_code, details, service_error_code = 500, str(e), None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code = e.response.status_code
        try:
            error_data = e.response.json()
            details = error_data.get("message", e.response.text)
            service_error_code = error_data.get("serviceErrorCode")
        except json.JSONDecodeError:
            details = e.response.text
    return {
        "status": "error", "action": action_name,
        "message": f"Error interactuando con LinkedIn API: {details}",
        "details": {"serviceErrorCode": service_error_code, "raw_response": details},
        "http_status": status_code
    }

def _get_ad_account_urn(account_id: Union[str, int]) -> str:
    if not account_id: raise ValueError("Se requiere 'ad_account_id'.")
    account_id_str = str(account_id).replace("urn:li:sponsoredAccount:", "").strip()
    if not account_id_str.isdigit(): raise ValueError(f"El 'ad_account_id' de LinkedIn ('{account_id_str}') debe ser numérico.")
    return f"urn:li:sponsoredAccount:{account_id_str}"

# --- ACCIONES CRUD COMPLETAS ---

def linkedin_find_ad_accounts(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_find_ad_accounts"
    try:
        headers = _get_linkedin_api_headers(params)
        url = f"{LINKEDIN_API_BASE_URL}/adAccounts"
        query_params = {"q": "search"}
        if params.get("search_name"):
            query_params["search.name.value"] = params["search_name"]
        
        logger.info(f"Buscando cuentas publicitarias de LinkedIn. Query: {params.get('search_name')}")
        response = requests.get(url, headers=headers, params=query_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_get_campaign_groups(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_get_campaign_groups"
    try:
        headers = _get_linkedin_api_headers(params)
        account_id = params.get("ad_account_id", settings.DEFAULT_LINKEDIN_AD_ACCOUNT_ID)
        if not account_id: raise ValueError("Se requiere 'ad_account_id'.")
        account_urn = _get_ad_account_urn(account_id)

        url = f"{LINKEDIN_API_BASE_URL}/adCampaignGroups"
        query_params = {"q": "search", "search.account": account_urn}
        
        logger.info(f"Obteniendo grupos de campañas para la cuenta '{account_urn}'")
        response = requests.get(url, headers=headers, params=query_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_get_campaigns(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_get_campaigns"
    try:
        headers = _get_linkedin_api_headers(params)
        account_id = params.get("ad_account_id", settings.DEFAULT_LINKEDIN_AD_ACCOUNT_ID)
        if not account_id: raise ValueError("Se requiere 'ad_account_id'.")
        account_urn = _get_ad_account_urn(account_id)

        url = f"{LINKEDIN_API_BASE_URL}/adCampaigns"
        query_params = {"q": "search", "search.account": account_urn}
        if params.get("campaign_group_id"):
            query_params["search.campaignGroup"] = f"urn:li:sponsoredCampaignGroup:{params['campaign_group_id']}"
        if params.get("status_filter"):
            query_params["search.status"] = params["status_filter"].upper()
            
        logger.info(f"Obteniendo campañas para la cuenta '{account_urn}'. Filtros: {query_params}")
        response = requests.get(url, headers=headers, params=query_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_create_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_create_campaign"
    try:
        headers = _get_linkedin_api_headers(params)
        campaign_payload = params.get("campaign_payload")
        if not campaign_payload: raise ValueError("El 'campaign_payload' es requerido.")

        url = f"{LINKEDIN_API_BASE_URL}/adCampaigns"
        
        logger.info(f"Creando nueva campaña en LinkedIn. Payload keys: {list(campaign_payload.keys())}")
        response = requests.post(url, headers=headers, json=campaign_payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        # La creación exitosa devuelve un status 201 y el ID en los headers
        created_campaign_id = response.headers.get("x-restli-id")
        return {"status": "success", "message": "Campaña creada exitosamente.", "data": {"id": created_campaign_id}, "http_status": 201}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_update_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_update_campaign"
    try:
        headers = _get_linkedin_api_headers(params)
        campaign_id = params.get("campaign_id")
        update_payload = params.get("update_payload")
        if not campaign_id or not update_payload: raise ValueError("'campaign_id' y 'update_payload' son requeridos.")

        # El update se hace con un payload de 'patch'
        payload = {"patch": {"$set": update_payload}}
        url = f"{LINKEDIN_API_BASE_URL}/adCampaigns/{campaign_id}"
        
        logger.info(f"Actualizando campaña de LinkedIn ID '{campaign_id}'.")
        response = requests.post(url, headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        # Un update exitoso devuelve 204 No Content
        return {"status": "success", "message": "Campaña actualizada exitosamente.", "http_status": 204}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_get_analytics(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_get_analytics"
    try:
        headers = _get_linkedin_api_headers(params)
        url = f"{LINKEDIN_API_BASE_URL}/adAnalytics"
        
        account_id = params.get("ad_account_id", settings.DEFAULT_LINKEDIN_AD_ACCOUNT_ID)
        if not account_id: raise ValueError("Se requiere 'ad_account_id'.")
        
        if not params.get("start_year") or not params.get("end_year"): raise ValueError("Se requieren parámetros de fecha (start_year, end_year, etc.).")
        
        payload = {
            "dateRange": {
                "start": {"year": params['start_year'], "month": params['start_month'], "day": params['start_day']},
                "end": {"year": params['end_year'], "month": params['end_month'], "day": params['end_day']}
            },
            "timeGranularity": params.get("time_granularity", "DAILY"),
            "accounts": [_get_ad_account_urn(account_id)],
            "pivot": f"urn:li:sponsoredAccount:{account_id}" # Pivot por cuenta
        }
        
        # Corrección: El endpoint adAnalytics espera un GET con los parámetros en la URL, no un POST.
        # La estructura del payload se convierte a parámetros de query.
        query_params = {
            "q": "analytics",
            "dateRange.start.day": params['start_day'],
            "dateRange.start.month": params['start_month'],
            "dateRange.start.year": params['start_year'],
            "dateRange.end.day": params['end_day'],
            "dateRange.end.month": params['end_month'],
            "dateRange.end.year": params['end_year'],
            "timeGranularity": params.get("time_granularity", "DAILY").upper(),
            "pivot": params.get("pivot", "MEMBER_COMPANY").upper(),
            "fields": params.get("fields", "impressions,clicks,costInLocalCurrency"),
            "campaigns[0]": f"urn:li:sponsoredCampaign:{params['campaign_ids'][0]}" # Ejemplo para un ID
        }

        # La construcción de la query para analytics puede ser compleja
        # Aquí se muestra un ejemplo básico. Se recomienda consultar la documentación para queries complejas.
        logger.info(f"Obteniendo analíticas de LinkedIn para la cuenta '{account_id}'.")
        response = requests.get(url, headers=headers, params=query_params, timeout=max(settings.DEFAULT_API_TIMEOUT, 180))
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)