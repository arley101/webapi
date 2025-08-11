# app/actions/linkedin_ads_actions.py
import logging
import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE_URL = "https://api.linkedin.com"
# Es importante verificar la última versión recomendada por LinkedIn para estos headers
LINKEDIN_API_VERSION_HEADER = "202401" # Ejemplo, ajusta a una versión reciente y válida
LINKEDIN_RESTLI_VERSION_HEADER = "2.0.0"

# Constantes adicionales para nuevas funciones
DEFAULT_CAMPAIGN_FIELDS = "id,name,status,type,objective,format,creativeSpec,targetingCriteria,budget,bidding"
DEFAULT_AD_FIELDS = "id,name,status,type,creatives,campaign,targeting,stats"
DEFAULT_ANALYTICS_FIELDS = "impressions,clicks,likes,shares,comments,costInLocalCurrency,conversionValue"

def _get_linkedin_api_headers(params: Dict[str, Any]) -> Dict[str, str]:
    """
    Prepara los headers para las solicitudes a la LinkedIn Ads API.
    Prioriza el access_token de params, luego de settings.
    """
    access_token: Optional[str] = params.get("access_token", settings.LINKEDIN_ACCESS_TOKEN)

    if not access_token:
        raise ValueError("Se requiere 'access_token' para LinkedIn Ads API (ya sea en params o configurado en el backend).")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": LINKEDIN_API_VERSION_HEADER,
        "X-Restli-Protocol-Version": LINKEDIN_RESTLI_VERSION_HEADER
    }
    return headers

def _handle_linkedin_api_error(
    e: Exception,
    action_name: str,
    params_for_log: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Helper para manejar errores de LinkedIn Ads API."""
    log_message = f"Error en LinkedIn Ads Action '{action_name}'"
    safe_params = {}
    if params_for_log:
        sensitive_keys = ['access_token'] # Ajusta según sea necesario
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    details_str = str(e)
    status_code_int = 500
    linkedin_error_code = None
    linkedin_service_error_code = None
    linkedin_request_id = None

    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code_int = e.response.status_code
        linkedin_request_id = e.response.headers.get("x-li-uuid") or e.response.headers.get("x-linkedin-tracking-id")
        try:
            error_data = e.response.json()
            # Estructura de error de LinkedIn: {"serviceErrorCode": X, "message": "...", "status": Y}
            linkedin_service_error_code = error_data.get("serviceErrorCode")
            linkedin_error_code = error_data.get("code") # A veces 'code' existe
            details_str = error_data.get("message", e.response.text)
        except json.JSONDecodeError:
            details_str = e.response.text[:500] if e.response.text else "No response body"
            
    return {
        "status": "error",
        "action": action_name,
        "message": f"Error interactuando con LinkedIn Ads API: {details_str}",
        "details": {
            "raw_exception_type": type(e).__name__,
            "raw_exception_message": str(e),
            "linkedin_api_status": status_code_int, # 'status' suele estar en el cuerpo del error también
            "linkedin_api_error_code": linkedin_error_code,
            "linkedin_api_service_error_code": linkedin_service_error_code,
            "linkedin_api_request_id": linkedin_request_id,
            "response_body": details_str if isinstance(e, requests.exceptions.HTTPError) else None
        },
        "http_status": status_code_int,
    }

def _get_linkedin_ad_account_urn(params: Dict[str, Any]) -> str:
    """
    Obtiene el URN de la cuenta publicitaria de LinkedIn.
    Prioriza account_id de params, luego de settings.DEFAULT_LINKEDIN_AD_ACCOUNT_ID.
    Espera el ID numérico y lo formatea como URN.
    """
    numeric_account_id_str: Optional[str] = params.get("account_id", settings.DEFAULT_LINKEDIN_AD_ACCOUNT_ID)
    
    if not numeric_account_id_str:
        raise ValueError("Se requiere 'account_id' (numérico) en params o DEFAULT_LINKEDIN_AD_ACCOUNT_ID configurado.")
    
    # Limpiar por si se pasa el URN completo o "urn:li:sponsoredAccount:"
    numeric_id_cleaned = str(numeric_account_id_str).replace("urn:li:sponsoredAccount:", "").strip()
    
    if not numeric_id_cleaned.isdigit():
        raise ValueError(f"El 'account_id' de LinkedIn ('{numeric_id_cleaned}') debe ser numérico.")
        
    return f"urn:li:sponsoredAccount:{numeric_id_cleaned}"


# --- ACCIONES ---
# Nota: El parámetro 'client: AuthenticatedHttpClient' no se usa aquí.
# Se mantiene por consistencia con el action_mapper.

def linkedin_get_ad_accounts(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "linkedin_get_ad_accounts"
    logger.info(f"Ejecutando {action_name} con params (token omitido del log): %s", {k:v for k,v in params.items() if k not in ['access_token']})

    # Documentación: https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-accounts?view=li-lms-2024-01&tabs=http#search-for-ad-accounts
    # Endpoint para buscar cuentas a las que el token tiene acceso
    url = f"{LINKEDIN_API_BASE_URL}/v2/adAccountsV2"
    
    # Parámetros de búsqueda
    # q=search es un buscador general. Se puede filtrar por 'reference' (URN del owner) o 'id' (URN de la cuenta)
    # Para listar las cuentas asociadas al token, q=search&search=(type:(values:List(BUSINESS,ENTERPRISE_PROFILE)))
    # O según el ejemplo del usuario: q=search
    
    query_api_params: Dict[str, Any] = {"q": params.get("q_search_type", "search")} # "search" como default
    
    # Se pueden añadir filtros más específicos si se conocen, ej:
    # search_filter_reference_urn = params.get("search_filter_owner_urn") # ej. urn:li:organization:12345
    # if search_filter_reference_urn:
    #    query_api_params["search.reference.values[0]"] = search_filter_reference_reference_urn

    logger.info(f"Listando cuentas publicitarias de LinkedIn. Tipo de búsqueda: {query_api_params['q']}")
    try:
        headers = _get_linkedin_api_headers(params)
        response = requests.get(url, headers=headers, params=query_api_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 401}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)


def linkedin_list_campaigns(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "linkedin_list_campaigns"
    logger.info(f"Ejecutando {action_name} con params (token omitido del log): %s", {k:v for k,v in params.items() if k not in ['access_token']})

    try:
        account_urn = _get_linkedin_ad_account_urn(params)
        headers = _get_linkedin_api_headers(params)
        
        # Documentación: https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/campaign-management/create-and-manage-campaign-groups?view=li-lms-2024-01&tabs=http#search-for-campaigns
        # El formato del filtro de búsqueda es `search=(account:(values:List(urn%3Ali%3AsponsoredAccount%3A1234567)))`
        # El SDK de Python lo maneja, pero con requests directos hay que construirlo bien.
        # Tu borrador usaba: search.account.values[0]={account_id} lo cual puede no ser correcto.
        
        url = f"{LINKEDIN_API_BASE_URL}/v2/adCampaignsV2"
        query_api_params: Dict[str, Any] = {
            "q": "search",
            "search.account.values[0]": account_urn # LinkedIn espera el URN completo aquí
        }
        
        # Parámetros adicionales de la API de LinkedIn
        if params.get("fields"): # Ej: "id,name,status,versionTag,account"
            query_api_params["fields"] = params["fields"]
        if params.get("count"): # Para paginación
            query_api_params["count"] = params["count"]
        if params.get("start"): # Para paginación
            query_api_params["start"] = params["start"]
        # Otros filtros como `search.status.values[0]=ACTIVE` pueden añadirse.

        logger.info(f"Listando campañas de LinkedIn para cuenta URN '{account_urn}'. Params: {query_api_params}")
        response = requests.get(url, headers=headers, params=query_api_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 400 if "account_id" in str(ve) else 401}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)


def linkedin_get_basic_report(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "linkedin_get_basic_report"
    logger.info(f"Ejecutando {action_name} con params (token omitido del log): %s", {k:v for k,v in params.items() if k not in ['access_token']})

    try:
        account_urn = _get_linkedin_ad_account_urn(params)
        headers = _get_linkedin_api_headers(params)

        # Documentación AdAnalyticsV2: https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads-reporting/ads-reporting?view=li-lms-2024-01&tabs=http
        # Endpoint: /v2/adAnalyticsV2
        url = f"{LINKEDIN_API_BASE_URL}/v2/adAnalyticsV2"
        
        # Parámetros de la query. Tu borrador tenía: ?q=analytics&pivot=CAMPAIGN&accounts[0]={account_id}
        # El formato correcto es con `dateRange`, `timeGranularity`, `pivot`, `fields`, etc.
        # Y el account se especifica como un filtro.
        
        query_api_params: Dict[str, Any] = {
            "q": "analytics",
            "pivot": params.get("pivot", "CAMPAIGN"), # CAMPAIGN, CREATIVE, COMPANY, ACCOUNT, etc.
            "dateRange.start.day": params.get("start_day"), # Ejemplo: 1
            "dateRange.start.month": params.get("start_month"), # Ejemplo: 1
            "dateRange.start.year": params.get("start_year"), # Ejemplo: 2023
            "dateRange.end.day": params.get("end_day"),
            "dateRange.end.month": params.get("end_month"),
            "dateRange.end.year": params.get("end_year"),
            "timeGranularity": params.get("time_granularity", "DAILY"), # DAILY, MONTHLY, ALL
            "accounts[0]": account_urn # Especificar la cuenta para el reporte
        }
        
        # Validar que las fechas sean proveídas (al menos año, mes, día)
        if not all([query_api_params["dateRange.start.day"], query_api_params["dateRange.start.month"], query_api_params["dateRange.start.year"],
                    query_api_params["dateRange.end.day"], query_api_params["dateRange.end.month"], query_api_params["dateRange.end.year"]]):
            return {"status": "error", "action": action_name, "message": "Se requieren 'start_day', 'start_month', 'start_year', 'end_day', 'end_month', 'end_year' para el rango de fechas.", "http_status": 400}

        # Campos (métricas e IDs de dimensiones)
        # Ejemplo de campos: impressions,clicks,spend,costPerImpression,campaign,creative
        fields_report_param: Optional[str] = params.get("fields_report") # String separado por comas
        if fields_report_param:
            query_api_params["fields"] = fields_report_param
        else: # Unos campos por defecto
            query_api_params["fields"] = "impressions,clicks,spend,externalWebsiteConversions,dateRange,pivotValues"


        # Remover claves None para no enviarlas
        query_api_params_cleaned = {k: v for k, v in query_api_params.items() if v is not None}

        logger.info(f"Obteniendo reporte básico de LinkedIn para cuenta URN '{account_urn}'. Params: {query_api_params_cleaned}")
        response = requests.get(url, headers=headers, params=query_api_params_cleaned, timeout=max(settings.DEFAULT_API_TIMEOUT, 180)) # Reportes pueden tardar
        response.raise_for_status()
        return {"status": "success", "action": action_name, "data": response.json(), "http_status": response.status_code}
    except ValueError as ve:
        return {"status": "error", "action": action_name, "message": str(ve), "http_status": 400 if "account_id" in str(ve) else 401}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_create_campaign_group(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_create_campaign_group"
    try:
        headers = _get_linkedin_api_headers(params)
        account_urn = _get_linkedin_ad_account_urn(params)
        name = params.get("name")
        status = params.get("status", "ACTIVE")
        if not name: 
            raise ValueError("Se requiere 'name'.")
        
        url = f"{LINKEDIN_API_BASE_URL}/rest/adCampaignGroupsV2"
        payload = {
            "name": name, 
            "account": account_urn, 
            "status": status
        }
        response = requests.post(url, headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": {"id": response.headers.get("x-restli-id")}}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name)

def linkedin_update_campaign_group_status(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_update_campaign_group_status"
    try:
        headers = _get_linkedin_api_headers(params)
        group_id = params.get("group_id")
        new_status = params.get("new_status") # ACTIVE, DRAFT, ARCHIVED
        if not group_id or not new_status:
            raise ValueError("Se requieren 'group_id' y 'new_status'.")

        url = f"{LINKEDIN_API_BASE_URL}/rest/adCampaignGroupsV2/{group_id}"
        payload = {"patch": {"$set": {"status": new_status}}}
        response = requests.post(url, headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "message": f"Estado del grupo {group_id} actualizado a {new_status}."}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name)

def linkedin_get_campaign_analytics_by_day(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_get_campaign_analytics_by_day"
    try:
        headers = _get_linkedin_api_headers(params)
        campaign_urn = f"urn:li:sponsoredCampaign:{params['campaign_id']}"
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        
        if not all([campaign_urn, start_date, end_date]):
            raise ValueError("Se requieren 'campaign_id', 'start_date' y 'end_date'.")

        url = f"{LINKEDIN_API_BASE_URL}/rest/adAnalytics"
        payload = {
            "dateRange": {"start": start_date, "end": end_date},
            "timeGranularity": "DAILY",
            "campaigns": [campaign_urn],
            "fields": ["impressions", "clicks", "costInLocalCurrency"]
        }
        response = requests.post(url, headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name)

def linkedin_get_account_analytics_by_company(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_get_account_analytics_by_company"
    try:
        headers = _get_linkedin_api_headers(params)
        account_urn = _get_linkedin_ad_account_urn(params)
        time_range = params.get("time_range")
        
        if not time_range:
            raise ValueError("Se requiere 'time_range'.")

        url = f"{LINKEDIN_API_BASE_URL}/rest/adAnalytics"
        payload = {
            "dateRange": time_range,
            "timeGranularity": "ALL",
            "accounts": [account_urn],
            "pivot": "COMPANY"
        }
        response = requests.post(url, headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name)

# Funciones CRUD para Campañas
def linkedin_create_campaign(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_create_campaign"
    try:
        headers = _get_linkedin_api_headers(params)
        account_urn = _get_linkedin_ad_account_urn(params)
        
        required_fields = ['name', 'objective', 'budget', 'bidding']
        if not all(params.get(field) for field in required_fields):
            raise ValueError(f"Se requieren los campos: {', '.join(required_fields)}")

        payload = {
            "account": account_urn,
            "name": params["name"],
            "objective": params["objective"],
            "status": params.get("status", "DRAFT"),
            "budget": params["budget"],
            "bidding": params["bidding"],
            "targetingCriteria": params.get("targeting", {}),
            "creativeSpec": params.get("creative_spec", {})
        }

        url = f"{LINKEDIN_API_BASE_URL}/v2/adCampaignsV2"
        response = requests.post(url, headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        return {
            "status": "success",
            "action": action_name,
            "data": response.json(),
            "campaign_id": response.headers.get("x-restli-id")
        }
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_update_campaign(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_update_campaign"
    try:
        headers = _get_linkedin_api_headers(params)
        campaign_id = params.get("campaign_id")
        if not campaign_id:
            raise ValueError("Se requiere campaign_id")

        update_fields = {k: v for k, v in params.items() 
                        if k in ["name", "status", "budget", "bidding", "targetingCriteria", "creativeSpec"]}
        
        if not update_fields:
            raise ValueError("Se requiere al menos un campo para actualizar")

        url = f"{LINKEDIN_API_BASE_URL}/v2/adCampaignsV2/{campaign_id}"
        payload = {"patch": {"$set": update_fields}}
        
        response = requests.post(url, headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        return {
            "status": "success",
            "action": action_name,
            "message": f"Campaña {campaign_id} actualizada exitosamente"
        }
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_delete_campaign(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_delete_campaign"
    try:
        headers = _get_linkedin_api_headers(params)
        campaign_id = params.get("campaign_id")
        if not campaign_id:
            raise ValueError("Se requiere campaign_id")

        url = f"{LINKEDIN_API_BASE_URL}/v2/adCampaignsV2/{campaign_id}"
        response = requests.delete(url, headers=headers, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        return {
            "status": "success",
            "action": action_name,
            "message": f"Campaña {campaign_id} eliminada exitosamente"
        }
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

# Funciones CRUD para Anuncios
def linkedin_create_ad(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_create_ad"
    try:
        headers = _get_linkedin_api_headers(params)
        campaign_id = params.get("campaign_id")
        if not campaign_id:
            raise ValueError("Se requiere campaign_id")

        required_fields = ['name', 'type', 'creatives']
        if not all(params.get(field) for field in required_fields):
            raise ValueError(f"Se requieren los campos: {', '.join(required_fields)}")

        payload = {
            "campaign": f"urn:li:sponsoredCampaign:{campaign_id}",
            "name": params["name"],
            "type": params["type"],
            "status": params.get("status", "DRAFT"),
            "creatives": params["creatives"]
        }

        url = f"{LINKEDIN_API_BASE_URL}/v2/ads"
        response = requests.post(url, headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        return {
            "status": "success",
            "action": action_name,
            "data": response.json(),
            "ad_id": response.headers.get("x-restli-id")
        }
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_update_ad(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_update_ad"
    try:
        headers = _get_linkedin_api_headers(params)
        ad_id = params.get("ad_id")
        if not ad_id:
            raise ValueError("Se requiere ad_id")

        update_fields = {k: v for k, v in params.items() 
                        if k in ["name", "status", "creatives"]}
        
        if not update_fields:
            raise ValueError("Se requiere al menos un campo para actualizar")

        url = f"{LINKEDIN_API_BASE_URL}/v2/ads/{ad_id}"
        payload = {"patch": {"$set": update_fields}}
        
        response = requests.post(url, headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        return {
            "status": "success",
            "action": action_name,
            "message": f"Anuncio {ad_id} actualizado exitosamente"
        }
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_delete_ad(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_delete_ad"
    try:
        headers = _get_linkedin_api_headers(params)
        ad_id = params.get("ad_id")
        if not ad_id:
            raise ValueError("Se requiere ad_id")

        url = f"{LINKEDIN_API_BASE_URL}/v2/ads/{ad_id}"
        response = requests.delete(url, headers=headers, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        return {
            "status": "success",
            "action": action_name,
            "message": f"Anuncio {ad_id} eliminado exitosamente"
        }
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

# Funciones de Análisis y Reportes
def linkedin_get_creative_analytics(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_get_creative_analytics"
    try:
        headers = _get_linkedin_api_headers(params)
        account_urn = _get_linkedin_ad_account_urn(params)
        
        if not all(params.get(f) for f in ["start_date", "end_date"]):
            raise ValueError("Se requieren start_date y end_date")

        url = f"{LINKEDIN_API_BASE_URL}/v2/adAnalyticsV2"
        payload = {
            "dateRange": {
                "start": params["start_date"],
                "end": params["end_date"]
            },
            "timeGranularity": params.get("time_granularity", "DAILY"),
            "accounts": [account_urn],
            "pivot": "CREATIVE",
            "fields": params.get("fields", DEFAULT_ANALYTICS_FIELDS)
        }

        response = requests.post(url, headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        return {
            "status": "success",
            "action": action_name,
            "data": response.json()
        }
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_get_conversion_report(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_get_conversion_report"
    try:
        headers = _get_linkedin_api_headers(params)
        account_urn = _get_linkedin_ad_account_urn(params)
        
        if not all(params.get(f) for f in ["start_date", "end_date"]):
            raise ValueError("Se requieren start_date y end_date")

        url = f"{LINKEDIN_API_BASE_URL}/v2/adAnalyticsV2"
        payload = {
            "dateRange": {
                "start": params["start_date"],
                "end": params["end_date"]
            },
            "timeGranularity": params.get("time_granularity", "DAILY"),
            "accounts": [account_urn],
            "pivot": "CONVERSION",
            "fields": "conversionValue,costInLocalCurrency,conversions,postClickConversions,postViewConversions"
        }

        response = requests.post(url, headers=headers, json=payload, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        return {
            "status": "success",
            "action": action_name,
            "data": response.json()
        }
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_get_budget_usage(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_get_budget_usage"
    try:
        headers = _get_linkedin_api_headers(params)
        account_urn = _get_linkedin_ad_account_urn(params)

        url = f"{LINKEDIN_API_BASE_URL}/v2/adAccounts/{account_urn}/budgetStatus"
        response = requests.get(url, headers=headers, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        return {
            "status": "success",
            "action": action_name,
            "data": response.json()
        }
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

def linkedin_get_audience_insights(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "linkedin_get_audience_insights"
    try:
        headers = _get_linkedin_api_headers(params)
        account_urn = _get_linkedin_ad_account_urn(params)
        campaign_id = params.get("campaign_id")
        
        if not campaign_id:
            raise ValueError("Se requiere campaign_id")

        url = f"{LINKEDIN_API_BASE_URL}/v2/campaignInsights"
        query_params = {
            "campaign": f"urn:li:sponsoredCampaign:{campaign_id}",
            "fields": "audienceSize,demographicDistribution,industryDistribution,jobFunctionDistribution"
        }

        response = requests.get(url, headers=headers, params=query_params, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        return {
            "status": "success",
            "action": action_name,
            "data": response.json()
        }
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

# ============================================================================
# FUNCIONES ADICIONALES RESTAURADAS
# ============================================================================

def linkedin_get_campaign_demographics(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtener datos demográficos de audiencia de campañas de LinkedIn."""
    action_name = "linkedin_get_campaign_demographics"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    try:
        campaign_id = params.get("campaign_id")
        if not campaign_id:
            return {"status": "error", "error": "campaign_id es requerido"}
        
        headers = _get_linkedin_api_headers(params)
        
        # Construir parámetros para analytics de demografía
        start_date = params.get("start_date", "2024-01-01")
        end_date = params.get("end_date", "2024-12-31")
        
        # Llamada a la API de analytics con breakdown por demografía
        url = f"{LINKEDIN_API_BASE_URL}/v2/adAnalyticsV2"
        analytics_params = {
            "q": "analytics",
            "pivot": "MEMBER_COMPANY_SIZE,MEMBER_INDUSTRY,MEMBER_JOB_FUNCTION,MEMBER_SENIORITY",
            "campaigns": f"urn:li:sponsoredCampaign:{campaign_id}",
            "dateRange.start.day": int(start_date.split('-')[2]),
            "dateRange.start.month": int(start_date.split('-')[1]),
            "dateRange.start.year": int(start_date.split('-')[0]),
            "dateRange.end.day": int(end_date.split('-')[2]),
            "dateRange.end.month": int(end_date.split('-')[1]),
            "dateRange.end.year": int(end_date.split('-')[0]),
            "fields": "externalWebsiteConversions,clicks,impressions,costInUsd,dateRange,pivot,pivotValue"
        }
        
        response = requests.get(url, headers=headers, params=analytics_params)
        response.raise_for_status()
        
        data = response.json()
        
        # Procesar los datos demográficos
        demographics_data = {
            "campaign_id": campaign_id,
            "date_range": f"{start_date} to {end_date}",
            "company_size": [],
            "industry": [],
            "job_function": [],
            "seniority": []
        }
        
        if "elements" in data:
            for element in data["elements"]:
                pivot_value = element.get("pivotValue")
                metrics = {
                    "impressions": element.get("impressions", 0),
                    "clicks": element.get("clicks", 0),
                    "cost_usd": element.get("costInUsd", 0),
                    "conversions": element.get("externalWebsiteConversions", 0)
                }
                
                # Categorizar por tipo de demografía
                if "MEMBER_COMPANY_SIZE" in pivot_value:
                    demographics_data["company_size"].append({
                        "size": pivot_value, 
                        "metrics": metrics
                    })
                elif "MEMBER_INDUSTRY" in pivot_value:
                    demographics_data["industry"].append({
                        "industry": pivot_value,
                        "metrics": metrics
                    })
                elif "MEMBER_JOB_FUNCTION" in pivot_value:
                    demographics_data["job_function"].append({
                        "function": pivot_value,
                        "metrics": metrics
                    })
                elif "MEMBER_SENIORITY" in pivot_value:
                    demographics_data["seniority"].append({
                        "level": pivot_value,
                        "metrics": metrics
                    })
        
        logger.info(f"Obtenidas demografías para campaña {campaign_id}")
        return {"status": "success", "data": demographics_data}
        
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)


def linkedin_create_lead_gen_form(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    """Crear un formulario de generación de leads en LinkedIn."""
    action_name = "linkedin_create_lead_gen_form"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    try:
        account_id = params.get("account_id")
        if not account_id:
            return {"status": "error", "error": "account_id es requerido"}
        
        form_name = params.get("form_name")
        if not form_name:
            return {"status": "error", "error": "form_name es requerido"}
        
        headers = _get_linkedin_api_headers(params)
        
        # Construir el payload del formulario
        form_payload = {
            "account": f"urn:li:sponsoredAccount:{account_id}",
            "name": form_name,
            "description": params.get("description", ""),
            "privacyPolicyUrl": params.get("privacy_policy_url", ""),
            "thankYouMessage": params.get("thank_you_message", "Gracias por tu interés."),
            "locale": {
                "country": params.get("country", "US"),
                "language": params.get("language", "en")
            },
            "questions": []
        }
        
        # Agregar preguntas predefinidas
        default_questions = params.get("questions", [
            {"fieldType": "FIRST_NAME", "required": True},
            {"fieldType": "LAST_NAME", "required": True},
            {"fieldType": "EMAIL", "required": True},
            {"fieldType": "COMPANY", "required": False},
            {"fieldType": "JOB_TITLE", "required": False}
        ])
        
        for question in default_questions:
            question_obj = {
                "fieldType": question.get("fieldType"),
                "required": question.get("required", False)
            }
            
            # Agregar opciones para preguntas personalizadas
            if question.get("custom_question"):
                question_obj["customQuestionText"] = question.get("custom_question")
                if question.get("options"):
                    question_obj["predefinedOptions"] = question.get("options")
            
            form_payload["questions"].append(question_obj)
        
        # Configuraciones adicionales
        if params.get("webhook_url"):
            form_payload["actions"] = [{
                "type": "WEBHOOK",
                "url": params.get("webhook_url")
            }]
        
        # Crear el formulario
        url = f"{LINKEDIN_API_BASE_URL}/v2/leadGenForms"
        response = requests.post(url, headers=headers, json=form_payload)
        response.raise_for_status()
        
        data = response.json()
        
        # Extraer ID del formulario de la respuesta
        form_id = None
        if "id" in data:
            form_id = data["id"]
        elif "elements" in data and len(data["elements"]) > 0:
            form_id = data["elements"][0].get("id")
        
        logger.info(f"Formulario de lead gen creado exitosamente: {form_id}")
        return {
            "status": "success", 
            "data": {
                "form_id": form_id,
                "form_name": form_name,
                "account_id": account_id,
                "response": data
            }
        }
        
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)


def linkedin_ads_get_demographics(params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtener análisis demográfico de audiencias de LinkedIn Ads."""
    action_name = "linkedin_ads_get_demographics"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    try:
        headers = _get_linkedin_api_headers(params)
        account_urn = _get_linkedin_ad_account_urn(params)
        
        # Configurar parámetros de fecha
        start_date = params.get("start_date", "2024-01-01")
        end_date = params.get("end_date", "2024-12-31")
        
        # Obtener analytics demográficos por edad, género, y localización
        demographics_data = {}
        
        # 1. Analytics por edad
        age_url = f"{LINKEDIN_API_BASE_URL}/v2/adAnalyticsV2"
        age_params = {
            "q": "analytics",
            "pivot": "MEMBER_AGE",
            "dateRange.start.day": start_date.split("-")[2],
            "dateRange.start.month": start_date.split("-")[1],
            "dateRange.start.year": start_date.split("-")[0],
            "dateRange.end.day": end_date.split("-")[2],
            "dateRange.end.month": end_date.split("-")[1],
            "dateRange.end.year": end_date.split("-")[0],
            "accounts": account_urn,
            "fields": "impressions,clicks,clicks,costInUsd,externalWebsiteConversions"
        }
        
        age_response = requests.get(age_url, headers=headers, params=age_params, timeout=settings.DEFAULT_API_TIMEOUT)
        age_response.raise_for_status()
        demographics_data["age_breakdown"] = age_response.json()
        
        # 2. Analytics por género
        gender_params = age_params.copy()
        gender_params["pivot"] = "MEMBER_GENDER"
        
        gender_response = requests.get(age_url, headers=headers, params=gender_params, timeout=settings.DEFAULT_API_TIMEOUT)
        gender_response.raise_for_status()
        demographics_data["gender_breakdown"] = gender_response.json()
        
        # 3. Analytics por ubicación geográfica
        location_params = age_params.copy()
        location_params["pivot"] = "MEMBER_COUNTRY"
        
        location_response = requests.get(age_url, headers=headers, params=location_params, timeout=settings.DEFAULT_API_TIMEOUT)
        location_response.raise_for_status()
        demographics_data["location_breakdown"] = location_response.json()
        
        # 4. Analytics por experiencia laboral
        experience_params = age_params.copy()
        experience_params["pivot"] = "MEMBER_SENIORITY"
        
        experience_response = requests.get(age_url, headers=headers, params=experience_params, timeout=settings.DEFAULT_API_TIMEOUT)
        experience_response.raise_for_status()
        demographics_data["seniority_breakdown"] = experience_response.json()
        
        # Procesar y resumir datos
        total_impressions = 0
        total_clicks = 0
        total_cost = 0
        
        for breakdown_type, data in demographics_data.items():
            if "elements" in data:
                for element in data["elements"]:
                    if "impressions" in element:
                        total_impressions += element["impressions"]
                    if "clicks" in element:
                        total_clicks += element["clicks"]
                    if "costInUsd" in element:
                        total_cost += element["costInUsd"]
        
        # Calcular métricas agregadas
        ctr = (total_clicks / total_impressions) * 100 if total_impressions > 0 else 0
        cpc = total_cost / total_clicks if total_clicks > 0 else 0
        cpm = (total_cost / total_impressions) * 1000 if total_impressions > 0 else 0
        
        logger.info(f"Analytics demográficos obtenidos para {account_urn}")
        
        return {
            "status": "success",
            "action": action_name,
            "data": demographics_data,
            "summary": {
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "total_cost_usd": total_cost,
                "ctr_percentage": round(ctr, 2),
                "cpc_usd": round(cpc, 2),
                "cpm_usd": round(cpm, 2),
                "date_range": f"{start_date} to {end_date}",
                "account_urn": account_urn
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)


def linkedin_ads_generate_leads(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generar y gestionar leads a través de LinkedIn Ads."""
    action_name = "linkedin_ads_generate_leads"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    try:
        headers = _get_linkedin_api_headers(params)
        account_urn = _get_linkedin_ad_account_urn(params)
        
        operation = params.get("operation", "get_leads")  # get_leads, create_form, get_forms
        
        if operation == "get_leads":
            # Obtener leads generados por formularios
            form_id = params.get("form_id")
            if not form_id:
                return {"status": "error", "message": "form_id es requerido para obtener leads"}
            
            leads_url = f"{LINKEDIN_API_BASE_URL}/v2/leadFormResponses"
            leads_params = {
                "q": "leadForm",
                "leadForm": f"urn:li:leadGenForm:{form_id}",
                "fields": "id,submittedAt,formResponse,leadGenForm,associatedCampaign"
            }
            
            response = requests.get(leads_url, headers=headers, params=leads_params, timeout=settings.DEFAULT_API_TIMEOUT)
            response.raise_for_status()
            leads_data = response.json()
            
            # Procesar leads
            processed_leads = []
            if "elements" in leads_data:
                for lead in leads_data["elements"]:
                    processed_lead = {
                        "id": lead.get("id"),
                        "submitted_at": lead.get("submittedAt"),
                        "campaign": lead.get("associatedCampaign"),
                        "form_responses": []
                    }
                    
                    if "formResponse" in lead:
                        for field in lead["formResponse"]:
                            processed_lead["form_responses"].append({
                                "field_name": field.get("fieldName"),
                                "field_value": field.get("fieldValue")
                            })
                    
                    processed_leads.append(processed_lead)
            
            return {
                "status": "success",
                "action": action_name,
                "data": {
                    "leads": processed_leads,
                    "total_leads": len(processed_leads),
                    "form_id": form_id,
                    "account_urn": account_urn
                },
                "timestamp": datetime.now().isoformat()
            }
            
        elif operation == "get_forms":
            # Obtener formularios de lead generation
            forms_url = f"{LINKEDIN_API_BASE_URL}/v2/leadGenForms"
            forms_params = {
                "q": "account",
                "account": account_urn,
                "fields": "id,name,description,status,formType,thankYouMessage,privacyPolicyUrl"
            }
            
            response = requests.get(forms_url, headers=headers, params=forms_params, timeout=settings.DEFAULT_API_TIMEOUT)
            response.raise_for_status()
            forms_data = response.json()
            
            processed_forms = []
            if "elements" in forms_data:
                for form in forms_data["elements"]:
                    processed_forms.append({
                        "id": form.get("id"),
                        "name": form.get("name"),
                        "description": form.get("description"),
                        "status": form.get("status"),
                        "form_type": form.get("formType"),
                        "thank_you_message": form.get("thankYouMessage"),
                        "privacy_policy_url": form.get("privacyPolicyUrl")
                    })
            
            return {
                "status": "success",
                "action": action_name,
                "data": {
                    "forms": processed_forms,
                    "total_forms": len(processed_forms),
                    "account_urn": account_urn
                },
                "timestamp": datetime.now().isoformat()
            }
            
        elif operation == "create_campaign":
            # Crear campaña optimizada para lead generation
            campaign_name = params.get("campaign_name")
            if not campaign_name:
                return {"status": "error", "message": "campaign_name es requerido"}
            
            campaign_payload = {
                "name": campaign_name,
                "type": "SPONSORED_CONTENT",
                "account": account_urn,
                "status": "PAUSED",  # Crear en pausa para configuración
                "targetingCriteria": {
                    "include": {
                        "and": [
                            {
                                "or": {
                                    "urn:li:adTargetingFacet:locations": params.get("target_locations", ["urn:li:geo:103644278"])  # US por defecto
                                }
                            }
                        ]
                    }
                },
                "objectiveType": "LEAD_GENERATION",
                "costType": "CPC",
                "dailyBudget": {
                    "amount": str(params.get("daily_budget", 100)),
                    "currencyCode": "USD"
                }
            }
            
            # Si se proporciona una audiencia específica
            if "target_job_titles" in params:
                campaign_payload["targetingCriteria"]["include"]["and"].append({
                    "or": {
                        "urn:li:adTargetingFacet:titles": params["target_job_titles"]
                    }
                })
            
            campaign_url = f"{LINKEDIN_API_BASE_URL}/v2/adCampaignsV2"
            response = requests.post(campaign_url, headers=headers, json=campaign_payload, timeout=settings.DEFAULT_API_TIMEOUT)
            response.raise_for_status()
            campaign_data = response.json()
            
            return {
                "status": "success",
                "action": action_name,
                "data": {
                    "campaign_id": campaign_data.get("id"),
                    "campaign_name": campaign_name,
                    "status": "CREATED_PAUSED",
                    "account_urn": account_urn,
                    "objective": "LEAD_GENERATION"
                },
                "timestamp": datetime.now().isoformat()
            }
            
        else:
            return {
                "status": "error",
                "message": f"Operación no válida: {operation}. Use: get_leads, get_forms, create_campaign"
            }
            
    except Exception as e:
        return _handle_linkedin_api_error(e, action_name, params)

# Aquí se podrían añadir funciones para crear/actualizar campañas, ad sets, ads, etc.
# Ejemplo placeholder:
# def linkedin_create_campaign(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
#     params = params or {}
#     action_name = "linkedin_create_campaign"
#     logger.info(f"Ejecutando {action_name} con params (payload omitido): ...")
#     # ... lógica para construir payload y llamar a POST /v2/adCampaignsV2 ...
#     return {"status": "not_implemented", "message": "Función no implementada."}

# --- FIN DEL MÓDULO actions/linkedin_ads_actions.py ---