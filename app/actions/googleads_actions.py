# app/actions/googleads_actions.py
import logging
from typing import Dict, List, Optional, Any
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import json_format

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- INICIALIZACIÓN DEL CLIENTE Y HELPERS ROBUSTOS ---
_google_ads_client_instance: Optional[GoogleAdsClient] = None

def get_google_ads_client() -> GoogleAdsClient:
    global _google_ads_client_instance
    if _google_ads_client_instance:
        return _google_ads_client_instance
    
    # Cargar credenciales desde la configuración centralizada
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

def _get_customer_id(params: Dict[str, Any]) -> str:
    customer_id = params.get("customer_id", settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID)
    if not customer_id: raise ValueError("Se requiere 'customer_id'.")
    return str(customer_id).replace("-", "")

# --- ACCIONES COMPLETAS Y FUNCIONALES ---

def googleads_get_campaigns(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    customer_id = _get_customer_id(params)
    status_filter = params.get("status")
    where_clause = f"WHERE campaign.status = '{status_filter.upper()}'" if status_filter else ""
    query = f"SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type FROM campaign {where_clause} ORDER BY campaign.name"
    return _execute_search_query(customer_id, query, "googleads_get_campaigns")

def googleads_create_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    customer_id = _get_customer_id(params)
    campaign_name = params.get("name")
    if not campaign_name: raise ValueError("Se requiere el parámetro 'name' para la campaña.")
    
    gads_client = get_google_ads_client()
    
    # Crear presupuesto primero
    budget_operation = gads_client.get_type("CampaignBudgetOperation")
    budget = budget_operation.create
    budget.name = f"Budget for {campaign_name} - {id(campaign_name)}"
    budget.amount_micros = params.get("budget_micros", 500000)
    budget.delivery_method = gads_client.enums.BudgetDeliveryMethodEnum.STANDARD
    budget_service = gads_client.get_service("CampaignBudgetService")
    budget_response = budget_service.mutate_campaign_budgets(customer_id=customer_id, operations=[budget_operation])
    budget_resource_name = budget_response.results[0].resource_name

    # Crear campaña y asignarle el presupuesto
    operation = gads_client.get_type("CampaignOperation")
    campaign = operation.create
    campaign.name = campaign_name
    campaign.campaign_budget = budget_resource_name
    campaign.status = gads_client.enums.CampaignStatusEnum.PAUSED
    
    campaign_type = params.get("type", "SEARCH").upper()
    if campaign_type == "PERFORMANCE_MAX":
        campaign.advertising_channel_type = gads_client.enums.AdvertisingChannelTypeEnum.PERFORMANCE_MAX
        campaign.bidding_strategy_type = gads_client.enums.BiddingStrategyTypeEnum.MAXIMIZE_CONVERSION_VALUE
        campaign.maximize_conversion_value.target_roas = params.get("target_roas", 0.0)
    else: # Default a Search
        campaign.advertising_channel_type = gads_client.enums.AdvertisingChannelTypeEnum.SEARCH
        campaign.bidding_strategy_type = gads_client.enums.BiddingStrategyTypeEnum.MANUAL_CPC
        campaign.network_settings.target_google_search = True
    
    return _execute_mutate_operations(customer_id, [operation], "CampaignService", "googleads_create_campaign")

def googleads_get_ad_groups(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    customer_id = _get_customer_id(params)
    campaign_id = params.get("campaign_id")
    if not campaign_id: raise ValueError("Se requiere 'campaign_id'.")
    query = f"SELECT ad_group.id, ad_group.name, ad_group.status FROM ad_group WHERE campaign.id = {campaign_id}"
    return _execute_search_query(customer_id, query, "googleads_get_ad_groups")

# --- NUEVAS FUNCIONES INTEGRADAS ---

def googleads_get_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene detalles específicos de una campaña."""
    customer_id = _get_customer_id(params)
    campaign_id = params.get("campaign_id")
    if not campaign_id:
        raise ValueError("Se requiere 'campaign_id'.")
    query = """
        SELECT 
            campaign.id, 
            campaign.name, 
            campaign.status, 
            campaign.bidding_strategy_type, 
            campaign.campaign_budget 
        FROM campaign 
        WHERE campaign.id = %s
    """ % campaign_id
    return _execute_search_query(customer_id, query, "googleads_get_campaign")

def googleads_update_campaign_status(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza el estado de una campaña específica."""
    customer_id = _get_customer_id(params)
    campaign_id = params.get("campaign_id")
    status = params.get("status")
    if not campaign_id or not status:
        raise ValueError("Se requieren 'campaign_id' y 'status'.")

    try:
        gads_client = get_google_ads_client()
        campaign_service = gads_client.get_service("CampaignService")
        operation = gads_client.get_type("CampaignOperation")
        
        campaign = operation.update
        campaign.resource_name = campaign_service.campaign_path(customer_id, campaign_id)
        campaign.status = gads_client.enums.CampaignStatusEnum[status.upper()]
        
        field_mask = gads_client.get_type("FieldMask")
        field_mask.paths.append("status")
        operation.update_mask.CopyFrom(field_mask)
        
        return _execute_mutate_operations(
            customer_id, 
            [operation], 
            "CampaignService", 
            "googleads_update_campaign_status"
        )
    except Exception as e:
        logger.error(f"Error al actualizar estado de campaña: {str(e)}")
        return {"status": "error", "message": str(e), "http_status": 500}

def googleads_create_performance_max_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea una campaña Performance Max con configuraciones optimizadas."""
    params['type'] = 'PERFORMANCE_MAX'
    return googleads_create_campaign(client, params)

def googleads_create_remarketing_list(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea una nueva lista de remarketing."""
    customer_id = _get_customer_id(params)
    name = params.get("name")
    description = params.get("description")
    membership_days = params.get("membership_days", 365)
    
    if not name:
        raise ValueError("Se requiere 'name' para la lista.")

    try:
        gads_client = get_google_ads_client()
        operation = gads_client.get_type("UserListOperation")
        user_list = operation.create
        user_list.name = name
        user_list.description = description or f"Lista creada automáticamente - {name}"
        user_list.membership_life_span = membership_days
        user_list.crm_based_user_list.upload_key_type = (
            gads_client.enums.CustomerMatchUploadKeyTypeEnum.CONTACT_INFO
        )

        return _execute_mutate_operations(
            customer_id,
            [operation],
            "UserListService",
            "googleads_create_remarketing_list"
        )
    except Exception as e:
        logger.error(f"Error al crear lista de remarketing: {str(e)}")
        return {"status": "error", "message": str(e), "http_status": 500}

# --- FUNCIONES DE REPORTE Y ANÁLISIS ---

def googleads_get_campaign_performance(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene métricas de rendimiento de campaña."""
    customer_id = _get_customer_id(params)
    campaign_id = params.get("campaign_id")
    date_range = params.get("date_range", "LAST_30_DAYS")
    
    query = f"""
        SELECT 
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions
        FROM campaign
        WHERE campaign.id = {campaign_id}
        AND segments.date DURING {date_range}
    """
    
    return _execute_search_query(customer_id, query, "googleads_get_campaign_performance")

# Puedes agregar más funciones según necesites...