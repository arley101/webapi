# app/actions/googleads_actions.py
import logging
import base64
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
    if (_google_ads_client_instance):
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

# --- NUEVAS FUNCIONES AVANZADAS ---

def googleads_list_accessible_customers(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "googleads_list_accessible_customers"
    try:
        gads_client = get_google_ads_client()
        customer_service = gads_client.get_service("CustomerService")
        accessible_customers = customer_service.list_accessible_customers()
        return {"status": "success", "data": {"resource_names": accessible_customers.resource_names}}
    except GoogleAdsException as ex:
        return _handle_google_ads_api_error(ex, action_name)
    except Exception as e:
        return {"status": "error", "action": action_name, "message": str(e), "http_status": 500}

def googleads_get_campaign_by_name(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "googleads_get_campaign_by_name"
    customer_id = _get_customer_id(params)
    campaign_name = params.get("name")
    if not campaign_name:
        return {"status": "error", "action": action_name, "message": "El parámetro 'name' es requerido.", "http_status": 400}
    
    sanitized_name = campaign_name.replace("'", "\\'")
    query = f"SELECT campaign.id, campaign.name, campaign.status, campaign.resource_name FROM campaign WHERE campaign.name = '{sanitized_name}' LIMIT 1"
    response = _execute_search_query(customer_id, query, action_name)
    
    if response["status"] == "success":
        if not response["data"]:
            return {"status": "error", "action": action_name, "message": f"No se encontró campaña con nombre '{campaign_name}'.", "http_status": 404}
        return {"status": "success", "data": response["data"][0]['campaign']}
    return response

def googleads_upload_click_conversion(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "googleads_upload_click_conversion"
    try:
        customer_id = _get_customer_id(params)
        gclid = params.get("gclid")
        conversion_action_id = params.get("conversion_action_id")
        conversion_datetime = params.get("conversion_datetime")
        conversion_value = params.get("conversion_value")

        if not all([gclid, conversion_action_id, conversion_datetime, conversion_value is not None]):
            raise ValueError("Se requieren 'gclid', 'conversion_action_id', 'conversion_datetime' y 'conversion_value'.")

        gads_client = get_google_ads_client()
        conversion_upload_service = gads_client.get_service("ConversionUploadService")
        
        click_conversion = gads_client.get_type("ClickConversion")
        click_conversion.gclid = gclid
        click_conversion.conversion_action = f"customers/{customer_id}/conversionActions/{conversion_action_id}"
        click_conversion.conversion_date_time = conversion_datetime
        click_conversion.conversion_value = float(conversion_value)
        click_conversion.currency_code = params.get("currency_code", "USD")

        request = gads_client.get_type("UploadClickConversionsRequest")
        request.customer_id = customer_id
        request.conversions.append(click_conversion)
        request.partial_failure = True

        response = conversion_upload_service.upload_click_conversions(request=request)
        
        response_dict = json_format.MessageToDict(response._pb)
        if "partialFailureError" in response_dict:
            return {"status": "partial_error", "message": "La carga de conversiones tuvo fallos parciales.", "data": response_dict}

        return {"status": "success", "data": response_dict}
    except GoogleAdsException as ex:
        return _handle_google_ads_api_error(ex, action_name)
    except Exception as e:
        return {"status": "error", "action": action_name, "message": str(e), "http_status": 500}

def googleads_upload_image_asset(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "googleads_upload_image_asset"
    try:
        customer_id = _get_customer_id(params)
        image_base64 = params.get("image_base64_data")
        asset_name = params.get("asset_name")

        if not image_base64 or not asset_name:
            raise ValueError("Se requieren 'image_base64_data' y 'asset_name'.")

        gads_client = get_google_ads_client()
        asset_operation = gads_client.get_type("AssetOperation")
        asset = asset_operation.create
        asset.name = asset_name
        asset.type_ = gads_client.enums.AssetTypeEnum.IMAGE
        asset.image_asset.data = base64.b64decode(image_base64)
        
        return _execute_mutate_operations(customer_id, [asset_operation], "AssetService", action_name)
    except Exception as e:
        return {"status": "error", "action": action_name, "message": str(e), "http_status": 500}

def googleads_get_keyword_performance_report(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "googleads_get_keyword_performance_report"
    customer_id = _get_customer_id(params)
    date_range = params.get("date_range", "LAST_7_DAYS")
    
    query = f"""
        SELECT
            ad_group.name,
            ad_group_criterion.criterion_id,
            ad_group_criterion.keyword.text,
            metrics.clicks,
            metrics.impressions,
            metrics.ctr,
            metrics.average_cpc,
            metrics.cost_micros
        FROM keyword_view
        WHERE segments.date DURING {date_range}
        AND campaign.status = 'ENABLED'
        AND ad_group.status = 'ENABLED'
        ORDER BY metrics.clicks DESC
        LIMIT 50
    """
    return _execute_search_query(customer_id, query, action_name)

def googleads_get_campaign_performance_by_device(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "googleads_get_campaign_performance_by_device"
    customer_id = _get_customer_id(params)
    campaign_id = params.get("campaign_id")
    date_range = params.get("date_range", "LAST_30_DAYS")

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            segments.device,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr
        FROM campaign
        WHERE campaign.id = {campaign_id}
        AND segments.date DURING {date_range}
        ORDER BY metrics.clicks DESC
    """
    return _execute_search_query(customer_id, query, action_name)

def googleads_add_keywords_to_ad_group(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Agrega palabras clave a un grupo de anuncios."""
    action_name = "googleads_add_keywords_to_ad_group"
    try:
        customer_id = _get_customer_id(params)
        ad_group_id = params.get("ad_group_id")
        keywords = params.get("keywords", [])

        if not ad_group_id or not keywords:
            raise ValueError("Se requieren 'ad_group_id' y 'keywords'")

        gads_client = get_google_ads_client()
        operations = []

        for keyword in keywords:
            operation = gads_client.get_type("AdGroupCriterionOperation")
            criterion = operation.create
            criterion.ad_group = gads_client.get_service("AdGroupService").ad_group_path(
                customer_id, ad_group_id
            )
            criterion.status = gads_client.enums.AdGroupCriterionStatusEnum.ENABLED
            criterion.keyword.text = keyword
            criterion.keyword.match_type = gads_client.enums.KeywordMatchTypeEnum.EXACT
            operations.append(operation)

        return _execute_mutate_operations(
            customer_id, 
            operations, 
            "AdGroupCriterionService", 
            action_name
        )
    except Exception as e:
        return {"status": "error", "action": action_name, "message": str(e), "http_status": 500}

def googleads_apply_audience_to_ad_group(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Aplica una audiencia a un grupo de anuncios."""
    action_name = "googleads_apply_audience_to_ad_group"
    try:
        customer_id = _get_customer_id(params)
        ad_group_id = params.get("ad_group_id")
        audience_id = params.get("audience_id")

        if not ad_group_id or not audience_id:
            raise ValueError("Se requieren 'ad_group_id' y 'audience_id'")

        gads_client = get_google_ads_client()
        operation = gads_client.get_type("AdGroupCriterionOperation")
        criterion = operation.create
        criterion.ad_group = gads_client.get_service("AdGroupService").ad_group_path(
            customer_id, ad_group_id
        )
        criterion.user_list.user_list = gads_client.get_service("UserListService").user_list_path(
            customer_id, audience_id
        )

        return _execute_mutate_operations(
            customer_id,
            [operation],
            "AdGroupCriterionService",
            action_name
        )
    except Exception as e:
        return {"status": "error", "action": action_name, "message": str(e), "http_status": 500}

def googleads_create_responsive_search_ad(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Crea un anuncio de búsqueda responsive."""
    action_name = "googleads_create_responsive_search_ad"
    try:
        customer_id = _get_customer_id(params)
        ad_group_id = params.get("ad_group_id")
        headlines = params.get("headlines", [])
        descriptions = params.get("descriptions", [])

        if not ad_group_id or not headlines or not descriptions:
            raise ValueError("Se requieren 'ad_group_id', 'headlines' y 'descriptions'")

        gads_client = get_google_ads_client()
        operation = gads_client.get_type("AdGroupAdOperation")
        ad_group_ad = operation.create
        ad_group_ad.ad_group = gads_client.get_service("AdGroupService").ad_group_path(
            customer_id, ad_group_id
        )
        ad_group_ad.status = gads_client.enums.AdGroupAdStatusEnum.PAUSED

        # Configurar el anuncio responsive
        ad = ad_group_ad.ad
        ad.responsive_search_ad.headlines = [
            {"text": headline} for headline in headlines[:15]  # Máximo 15 títulos
        ]
        ad.responsive_search_ad.descriptions = [
            {"text": description} for description in descriptions[:4]  # Máximo 4 descripciones
        ]

        return _execute_mutate_operations(
            customer_id,
            [operation],
            "AdGroupAdService",
            action_name
        )
    except Exception as e:
        return {"status": "error", "action": action_name, "message": str(e), "http_status": 500}

def googleads_get_ad_performance(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Obtiene el rendimiento de los anuncios."""
    action_name = "googleads_get_ad_performance"
    customer_id = _get_customer_id(params)
    ad_group_id = params.get("ad_group_id")
    date_range = params.get("date_range", "LAST_30_DAYS")

    where_clause = f"AND ad_group.id = {ad_group_id}" if ad_group_id else ""
    
    query = f"""
        SELECT
            ad_group_ad.ad.id,
            ad_group_ad.ad.responsive_search_ad.headlines,
            ad_group_ad.ad.responsive_search_ad.descriptions,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr
        FROM ad_group_ad
        WHERE segments.date DURING {date_range}
        {where_clause}
        ORDER BY metrics.clicks DESC
    """
    
    return _execute_search_query(customer_id, query, action_name)

def googleads_upload_offline_conversion(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Carga conversiones offline."""
    action_name = "googleads_upload_offline_conversion"
    try:
        customer_id = _get_customer_id(params)
        conversion_action_id = params.get("conversion_action_id")
        conversion_data = params.get("conversion_data", [])

        if not conversion_action_id or not conversion_data:
            raise ValueError("Se requieren 'conversion_action_id' y 'conversion_data'")

        gads_client = get_google_ads_client()
        operations = []

        for data in conversion_data:
            operation = gads_client.get_type("OfflineUserDataJobOperation")
            job = operation.create
            job.type_ = gads_client.enums.OfflineUserDataJobTypeEnum.STORE_SALES_UPLOAD_FIRST_PARTY
            job.store_sales_metadata.loyalty_fraction = 1.0
            job.store_sales_metadata.transaction_upload_fraction = 1.0

            user_data = job.user_data.add()
            user_data.transaction_attribute.conversion_action = (
                f"customers/{customer_id}/conversionActions/{conversion_action_id}"
            )
            user_data.transaction_attribute.currency_code = data.get("currency_code", "USD")
            user_data.transaction_attribute.transaction_amount_micros = int(
                float(data.get("transaction_amount", 0)) * 1_000_000
            )
            user_data.transaction_attribute.transaction_date_time = data.get(
                "transaction_date_time"
            )

        return _execute_mutate_operations(
            customer_id,
            operations,
            "OfflineUserDataJobService",
            action_name
        )
    except Exception as e:
        return {"status": "error", "action": action_name, "message": str(e), "http_status": 500}

# Puedes agregar más funciones según necesites...