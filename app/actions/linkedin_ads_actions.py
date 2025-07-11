# app/actions/linkedin_ads_actions.py
import logging
import requests
import json
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE_URL = "https://api.linkedin.com"
LINKEDIN_API_VERSION_HEADER = "202401" # Se recomienda usar una versión reciente
LINKEDIN_RESTLI_VERSION_HEADER = "2.0.0"

# --- HELPERS INTERNOS ROBUSTOS ---

def _get_linkedin_api_headers(params: Dict[str, Any]) -> Dict[str, str]:
    """Prepara los headers para las solicitudes a la LinkedIn API."""
    access_token: Optional[str] = params.get("access_token", settings.LINKEDIN_ACCESS_TOKEN)
    if not access_token:
        raise ValueError("Se requiere 'access_token' para LinkedIn API.")
    
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": LINKEDIN_API_VERSION_HEADER,
        "X-Restli-Protocol-Version": LINKEDIN_RESTLI_VERSION_HEADER
    }

def _handle_linkedin_api_error(e: Exception, action_name: str) -> Dict[str, Any]:
    """Maneja errores de la API de LinkedIn de forma estandarizada."""
    logger.error(f"Error en LinkedIn Action '{action_name}': {type(e).__name__} - {e}", exc_info=True)
    
    status_code = 500
    details = str(e)
    service_error_code = None

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

def _get_ad_account_urn(params: Dict[str, Any]) -> str:
    """Obtiene y formatea el URN de la cuenta publicitaria."""
    account_id = params.get("account_id", settings.DEFAULT_LINKEDIN_AD_ACCOUNT_ID)
    if not account_id:
        raise ValueError("Se requiere 'account_id' en los params o en la configuración.")
    
    account_id_str = str(account_id).replace("urn:li:sponsoredAccount:", "").strip()
    if not account_id_str.isdigit():
        raise ValueError(f"El 'account_id' de LinkedIn ('{account_id_str}') debe ser numérico.")
        
    return f"urn:li:sponsoredAccount:{account_id_str}"

# --- ACCIONES PRINCIPALES ---

def linkedin_find_ad_accounts(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Busca cuentas publicitarias a las que el token tiene acceso."""
    action_name = "linkedin_find_ad_accounts"
    logger.info(f"Ejecutando {action_name}...")
    
    try:
        headers = _get_linkedin_api_headers(params)
        url = f"{LINKEDIN_API_BASE_URL}/v2/adAccountsV2"
        
        # Búsqueda genérica para encontrar todas las cuentas asociadas
        query_params = {"q": "search"}
        
        response = requests.get(url, headers=headers, params=query_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name)

def linkedin_get_campaigns(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene campañas para una cuenta publicitaria, con filtros opcionales."""
    action_name = "linkedin_get_campaigns"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        account_urn = _get_ad_account_urn(params)
        headers = _get_linkedin_api_headers(params)
        
        url = f"{LINKEDIN_API_BASE_URL}/v2/adCampaignsV2"
        
        # El parámetro 'search.account.values[0]' es la forma correcta de filtrar por cuenta
        query_params: Dict[str, Any] = {
            "q": "search",
            "search.account.values[0]": account_urn
        }
        
        # Añadir filtros opcionales
        if params.get("status_filter"):
            query_params["search.status.values[0]"] = params["status_filter"].upper() # ej: ACTIVE, PAUSED, DRAFT

        logger.info(f"Listando campañas de LinkedIn para cuenta URN '{account_urn}' con filtros: {query_params}")
        response = requests.get(url, headers=headers, params=query_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name)

def linkedin_get_analytics(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene un reporte analítico. Requiere un rango de fechas."""
    action_name = "linkedin_get_analytics"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    try:
        account_urn = _get_ad_account_urn(params)
        headers = _get_linkedin_api_headers(params)

        url = f"{LINKEDIN_API_BASE_URL}/v2/adAnalyticsV2"
        
        required_params = ["start_day", "start_month", "start_year", "end_day", "end_month", "end_year"]
        if not all(params.get(p) for p in required_params):
            return {"status": "error", "message": f"Se requieren todos los parámetros de fecha: {required_params}", "http_status": 400}

        query_params = {
            "q": "analytics",
            "pivot": f"urn:li:sponsoredCampaign:{params.get('campaign_id')}" if params.get('campaign_id') else 'CAMPAIGN',
            "dateRange.start.day": params.get("start_day"),
            "dateRange.start.month": params.get("start_month"),
            "dateRange.start.year": params.get("start_year"),
            "dateRange.end.day": params.get("end_day"),
            "dateRange.end.month": params.get("end_month"),
            "dateRange.end.year": params.get("end_year"),
            "timeGranularity": params.get("time_granularity", "DAILY"),
            "accounts[0]": account_urn,
            "fields": params.get("fields", "impressions,clicks,costInLocalCurrency,dateRange")
        }

        query_params_cleaned = {k: v for k, v in query_params.items() if v is not None}

        logger.info(f"Obteniendo reporte analítico de LinkedIn para cuenta '{account_urn}' con params: {query_params_cleaned}")
        response = requests.get(url, headers=headers, params=query_params_cleaned, timeout=max(settings.DEFAULT_API_TIMEOUT, 180))
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name)