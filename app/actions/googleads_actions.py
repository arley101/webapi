# app/actions/googleads_actions.py
import logging
from typing import Dict, List, Optional, Any
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import json_format

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# --- INICIALIZACIÓN DEL CLIENTE Y HELPERS ROBUSTOS ---
_google_ads_client_instance: Optional[GoogleAdsClient] = None

def get_google_ads_client() -> GoogleAdsClient:
    global _google_ads_client_instance
    if _google_ads_client_instance:
        return _google_ads_client_instance
    config = {
        "developer_token": settings.GOOGLE_ADS.DEVELOPER_TOKEN,
        "client_id": settings.GOOGLE_ADS.CLIENT_ID,
        "client_secret": settings.GOOGLE_ADS.CLIENT_SECRET,
        "refresh_token": settings.GOOGLE_ADS.REFRESH_TOKEN,
        "login_customer_id": str(settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID).replace("-", "") if settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID else None,
        "use_proto_plus": True,
    }
    if not all(config.get(k) for k in ["developer_token", "client_id", "client_secret", "refresh_token"]):
        raise ValueError("Faltan credenciales de Google Ads en la configuración.")
    logger.info("Inicializando cliente de Google Ads...")
    _google_ads_client_instance = GoogleAdsClient.load_from_dict(config)
    return _google_ads_client_instance

def _handle_google_ads_api_error(ex: GoogleAdsException, action_name: str) -> Dict[str, Any]:
    error_details = [{"message": error.message, "error_code": str(error.error_code)} for error in ex.failure.errors]
    logger.error(f"Google Ads API Exception en '{action_name}': {error_details}")
    return {"status": "error", "action": action_name, "message": "Error en la API de Google Ads.", "details": {"errors": error_details, "request_id": ex.request_id}, "http_status": 400}

def _execute_search_query(customer_id: str, query: str, action_name: str) -> Dict[str, Any]:
    try:
        gads_client = get_google_ads_client()
        ga_service = gads_client.get_service("GoogleAdsService")
        stream = ga_service.search_stream(customer_id=customer_id, query=query)
        results = [json_format.MessageToDict(row._pb) for batch in stream for row in batch.results]
        return {"status": "success", "data": results}
    except GoogleAdsException as ex:
        return _handle_google_ads_api_error(ex, action_name)
    except Exception as e:
        return {"status": "error", "message": str(e), "http_status": 500}

def _execute_mutate_operations(customer_id: str, operations: list, service_name: str, action_name: str) -> Dict[str, Any]:
    try:
        gads_client = get_google_ads_client()
        service = gads_client.get_service(service_name)
        response = service.mutate(customer_id=customer_id, operations=operations)
        return {"status": "success", "data": json_format.MessageToDict(response._pb)}
    except GoogleAdsException as ex:
        return _handle_google_ads_api_error(ex, action_name)
    except Exception as e:
        return {"status": "error", "message": str(e), "http_status": 500}

def _get_customer_id(params: Dict[str, Any]) -> Optional[str]:
    customer_id = params.get("customer_id", settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID)
    return str(customer_id).replace("-", "") if customer_id else None

def googleads_get_campaigns(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    customer_id = _get_customer_id(params)
    if not customer_id: return {"status": "error", "message": "Se requiere 'customer_id'."}
    status_filter = params.get("status")
    where_clause = f"WHERE campaign.status = '{status_filter}'" if status_filter else ""
    query = f"SELECT campaign.id, campaign.name, campaign.status FROM campaign {where_clause} ORDER BY campaign.name"
    return _execute_search_query(customer_id, query, "googleads_get_campaigns")

def googleads_create_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    customer_id = _get_customer_id(params)
    campaign_name = params.get("name")
    if not all([customer_id, campaign_name]):
        return {"status": "error", "message": "Se requieren 'customer_id' y 'name'."}
    gads_client = get_google_ads_client()
    operation = gads_client.get_type("CampaignOperation")
    campaign = operation.create
    campaign.name = campaign_name
    campaign.advertising_channel_type = gads_client.enums.AdvertisingChannelTypeEnum.SEARCH
    campaign.status = gads_client.enums.CampaignStatusEnum.PAUSED
    campaign.manual_cpc.enhanced_cpc_enabled = True
    campaign.network_settings.target_Google Search = True  # *** ESTA ES LA LÍNEA CORREGIDA ***
    budget_service = gads_client.get_service("CampaignBudgetService")
    budget_operation = gads_client.get_type("CampaignBudgetOperation")
    budget = budget_operation.create
    budget.name = f"Budget for {campaign_name}"
    budget.amount_micros = params.get("budget_micros", 500000)
    budget_response = budget_service.mutate_campaign_budgets(customer_id=customer_id, operations=[budget_operation])
    campaign.campaign_budget = budget_response.results[0].resource_name
    return _execute_mutate_operations(customer_id, [operation], "CampaignService", "googleads_create_campaign")

# ... (El resto de las funciones permanecen igual, ya que el error era solo en `create_campaign`)

def googleads_update_campaign_status(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    customer_id = _get_customer_id(params)
    campaign_id = params.get("campaign_id")
    status = params.get("status")
    if not all([customer_id, campaign_id, status]):
        return {"status": "error", "message": "Se requieren 'customer_id', 'campaign_id' y 'status'."}
    gads_client = get_google_ads_client()
    campaign_service = gads_client.get_service("CampaignService")
    operation = gads_client.get_type("CampaignOperation")
    campaign = operation.update
    campaign.resource_name = campaign_service.campaign_path(customer_id, campaign_id)
    campaign.status = gads_client.enums.CampaignStatusEnum[status].value
    operation.update_mask.paths.append("status")
    return _execute_mutate_operations(customer_id, [operation], "CampaignService", "googleads_update_campaign_status")

def googleads_get_ad_groups(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    customer_id = _get_customer_id(params)
    campaign_id = params.get("campaign_id")
    if not all([customer_id, campaign_id]):
        return {"status": "error", "message": "Se requieren 'customer_id' y 'campaign_id'."}
    query = f"SELECT ad_group.id, ad_group.name, ad_group.status FROM ad_group WHERE campaign.id = {campaign_id}"
    return _execute_search_query(customer_id, query, "googleads_get_ad_groups")

def googleads_create_ad_group(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    customer_id = _get_customer_id(params)
    campaign_id = params.get("campaign_id")
    ad_group_name = params.get("name")
    if not all([customer_id, campaign_id, ad_group_name]):
        return {"status": "error", "message": "Se requieren 'customer_id', 'campaign_id' y 'name'."}
    gads_client = get_google_ads_client()
    campaign_service = gads_client.get_service("CampaignService")
    operation = gads_client.get_type("AdGroupOperation")
    ad_group = operation.create
    ad_group.name = ad_group_name
    ad_group.status = gads_client.enums.AdGroupStatusEnum.ENABLED
    ad_group.campaign = campaign_service.campaign_path(customer_id, campaign_id)
    ad_group.type_ = gads_client.enums.AdGroupTypeEnum.SEARCH_STANDARD
    ad_group.cpc_bid_micros = params.get("cpc_bid_micros", 1000000)
    return _execute_mutate_operations(customer_id, [operation], "AdGroupService", "googleads_create_ad_group")

def googleads_get_ads(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    customer_id = _get_customer_id(params)
    ad_group_id = params.get("ad_group_id")
    if not all([customer_id, ad_group_id]):
        return {"status": "error", "message": "Se requieren 'customer_id' y 'ad_group_id'."}
    query = f"SELECT ad_group_ad.ad.id, ad_group_ad.ad.type, ad_group_ad.status FROM ad_group_ad WHERE ad_group.id = {ad_group_id}"
    return _execute_search_query(customer_id, query, "googleads_get_ads")

def googleads_create_responsive_search_ad(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    customer_id = _get_customer_id(params)
    ad_group_id = params.get("ad_group_id")
    headlines = params.get("headlines")
    descriptions = params.get("descriptions")
    final_urls = params.get("final_urls")
    if not all([customer_id, ad_group_id, headlines, descriptions, final_urls]):
        return {"status": "error", "message": "Faltan parámetros requeridos."}
    gads_client = get_google_ads_client()
    ad_group_service = gads_client.get_service("AdGroupService")
    operation = gads_client.get_type("AdGroupAdOperation")
    ad_group_ad = operation.create
    ad_group_ad.ad_group = ad_group_service.ad_group_path(customer_id, ad_group_id)
    ad_group_ad.status = gads_client.enums.AdGroupAdStatusEnum.ENABLED
    ad = ad_group_ad.ad
    ad.final_urls.extend(final_urls)
    ad.responsive_search_ad.headlines.extend([gads_client.get_type("AdTextAsset", text=h) for h in headlines])
    ad.responsive_search_ad.descriptions.extend([gads_client.get_type("AdTextAsset", text=d) for d in descriptions])
    return _execute_mutate_operations(customer_id, [operation], "AdGroupAdService", "googleads_create_responsive_search_ad")

def googleads_get_keywords(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    customer_id = _get_customer_id(params)
    ad_group_id = params.get("ad_group_id")
    if not all([customer_id, ad_group_id]):
        return {"status": "error", "message": "Se requieren 'customer_id' y 'ad_group_id'."}
    query = f"SELECT ad_group_criterion.criterion_id, ad_group_criterion.keyword.text FROM ad_group_criterion WHERE ad_group_criterion.type = 'KEYWORD' AND ad_group.id = {ad_group_id}"
    return _execute_search_query(customer_id, query, "googleads_get_keywords")

def googleads_add_keywords(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    customer_id = _get_customer_id(params)
    ad_group_id = params.get("ad_group_id")
    keywords = params.get("keywords")
    if not all([customer_id, ad_group_id, keywords]):
        return {"status": "error", "message": "Faltan parámetros requeridos."}
    gads_client = get_google_ads_client()
    ad_group_service = gads_client.get_service("AdGroupService")
    ad_group_resource_name = ad_group_service.ad_group_path(customer_id, ad_group_id)
    operations = []
    for keyword_text in keywords:
        operation = gads_client.get_type("AdGroupCriterionOperation")
        criterion = operation.create
        criterion.ad_group = ad_group_resource_name
        criterion.keyword.text = keyword_text
        operations.append(operation)
    return _execute_mutate_operations(customer_id, operations, "AdGroupCriterionService", "googleads_add_keywords")

def googleads_get_performance_report(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    customer_id = _get_customer_id(params)
    if not customer_id: return {"status": "error", "message": "Se requiere 'customer_id'."}
    date_range = params.get("date_range", "LAST_7_DAYS")
    query = f"SELECT campaign.id, campaign.name, metrics.impressions, metrics.clicks, metrics.cost_micros FROM campaign WHERE segments.date DURING {date_range}"
    return _execute_search_query(customer_id, query, "googleads_get_performance_report")