# app/actions/linkedin_ads_actions.py
import logging
import requests
import json
from typing import Dict, Any, Optional, List

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

# Aquí se podrían añadir funciones para crear/actualizar campañas, ad sets, ads, etc.
# Ejemplo placeholder:
# def linkedin_create_campaign(client: Optional[Any], params: Dict[str, Any]) -> Dict[str, Any]:
#     params = params or {}
#     action_name = "linkedin_create_campaign"
#     logger.info(f"Ejecutando {action_name} con params (payload omitido): ...")
#     # ... lógica para construir payload y llamar a POST /v2/adCampaignsV2 ...
#     return {"status": "not_implemented", "message": "Función no implementada."}

# --- FIN DEL MÓDULO actions/linkedin_ads_actions.py ---