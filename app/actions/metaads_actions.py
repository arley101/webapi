# app/actions/metaads_actions.py
import logging
from typing import Dict, Any
from datetime import datetime
from app.core.config import settings
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.api import FacebookAdsApi

from facebook_business.adobjects.business import Business
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.page import Page
from facebook_business.exceptions import FacebookRequestError

logger = logging.getLogger(__name__)

# --- SDK INITIALIZATION AND HELPERS ---

def _get_meta_ads_api_client(params: Dict[str, Any]) -> FacebookAdsApi:
    access_token = settings.META_ADS.ACCESS_TOKEN
    app_id = settings.META_ADS.APP_ID
    app_secret = settings.META_ADS.APP_SECRET

    if not all([app_id, app_secret, access_token]):
        raise ValueError("Credenciales de Meta Ads (APP_ID, APP_SECRET, ACCESS_TOKEN) deben estar configuradas.")

    return FacebookAdsApi.init(
        app_id=str(app_id),
        app_secret=str(app_secret),
        access_token=str(access_token),
        api_version="v19.0"
    )

# Función helper para manejar errores (si no existe)
def _handle_meta_ads_api_error(error: Exception, action_name: str) -> Dict[str, Any]:
    """
    Maneja errores de la API de Meta Ads de manera consistente
    """
    error_message = str(error)
    error_code = getattr(error, 'api_error_code', 'UNKNOWN')
    
    logger.error(f"Meta Ads API Error in {action_name}: {error_message}")
    
    return {
        "status": "error",
        "message": f"Error en {action_name}: {error_message}",
        "error_code": error_code,
        "action": action_name
    }

def _get_ad_account_id(params: Dict[str, Any]) -> str:
    ad_account_id = params.get("ad_account_id")
    if not ad_account_id:
        raise ValueError("'ad_account_id' es requerido.")
    return f"act_{str(ad_account_id).replace('act_', '')}"

# --- ACCIONES FUNCIONALES ---

def metaads_get_business_details(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_business_details"
    try:
        _get_meta_ads_api_client(params)
        business_id = params.get("business_id", settings.META_ADS.BUSINESS_ACCOUNT_ID)
        if not business_id:
            raise ValueError("'business_id' es requerido.")
        business = Business(business_id)
        info = business.api_get(fields=params.get("fields", ["id", "name", "verification_status"]))
        return {"status": "success", "data": info.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_list_owned_pages(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_list_owned_pages"
    try:
        _get_meta_ads_api_client(params)
        business_id = params.get("business_id", settings.META_ADS.BUSINESS_ACCOUNT_ID)
        if not business_id:
            raise ValueError("'business_id' es requerido.")
        business = Business(business_id)
        pages = business.get_owned_pages(fields=params.get("fields", ["id", "name", "access_token"]))
        return {"status": "success", "data": [page.export_all_data() for page in pages]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_page_engagement(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_page_engagement"
    try:
        page_id = params.get("page_id")
        if not page_id:
            raise ValueError("'page_id' es requerido.")
        api = _get_meta_ads_api_client(params)
        page = Page(page_id, api=api)
        info = page.api_get(fields=params.get("fields", ["id", "name", "engagement", "fan_count"]))
        return {"status": "success", "data": info.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_list_campaigns(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_list_campaigns"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = params.get("ad_account_id")
        if not ad_account_id:
            raise ValueError("'ad_account_id' es requerido.")
        ad_account = AdAccount(f"act_{str(ad_account_id).replace('act_', '')}")
        campaigns = ad_account.get_campaigns(fields=params.get("fields", ["id", "name", "status", "objective"]))
        return {"status": "success", "data": [c.export_all_data() for c in campaigns]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_create_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea una nueva campaña en Meta Ads
    """
    action_name = "metaads_create_campaign"
    try:
        # Extraer parámetros correctamente
        account_id = params.get('account_id') or settings.META_ADS.BUSINESS_ACCOUNT_ID
        name = params.get('name', f'Campaign_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        objective = params.get('objective', 'OUTCOME_TRAFFIC')
        status = params.get('status', 'PAUSED')
        special_ad_categories = params.get('special_ad_categories', [])
        
        if not account_id:
            return {
                "status": "error",
                "message": "account_id es requerido"
            }
        
        # Configurar parámetros de la campaña
        campaign_params = {
            'name': name,
            'objective': objective,
            'status': status,
            'special_ad_categories': special_ad_categories
        }
        
        # Crear la campaña usando el SDK de Facebook
        ad_account = AdAccount(f'act_{account_id}')
        campaign = ad_account.create_campaign(params=campaign_params)
        
        # Obtener los datos de la campaña creada
        campaign_data = campaign.export_all_data()
        
        return {
            "status": "success",
            "message": f"Campaña '{name}' creada exitosamente",
            "data": {
                "id": campaign_data.get('id'),
                "name": campaign_data.get('name'),
                "status": campaign_data.get('status'),
                "objective": campaign_data.get('objective'),
                "account_id": account_id,
                "created_time": campaign_data.get('created_time')
            }
        }
        
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_update_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_update_campaign"
    try:
        _get_meta_ads_api_client(params)
        campaign_id = params.get("campaign_id")
        update_payload = params.get("update_payload")
        if not campaign_id or not update_payload:
            raise ValueError("'campaign_id' y 'update_payload' son requeridos.")
        campaign = Campaign(campaign_id)
        campaign.api_update(params=update_payload)
        updated = campaign.api_get(fields=["id", "name", "status"])
        return {"status": "success", "data": updated.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_delete_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_delete_campaign"
    try:
        _get_meta_ads_api_client(params)
        campaign_id = params.get("campaign_id")
        if not campaign_id:
            raise ValueError("'campaign_id' es requerido.")
        Campaign(campaign_id).api_delete()
        return {"status": "success", "message": f"Campaña '{campaign_id}' eliminada."}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def get_insights(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_insights"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = params.get("ad_account_id")
        insights_params = params.get("insights_params")
        if not ad_account_id or not insights_params:
            raise ValueError("'ad_account_id' y 'insights_params' son requeridos.")
        ad_account = AdAccount(f"act_{str(ad_account_id).replace('act_', '')}")
        insights = ad_account.get_insights(params=insights_params)
        return {"status": "success", "data": [i.export_all_data() for i in insights]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_campaign_details(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_campaign_details"
    try:
        _get_meta_ads_api_client(params)
        campaign_id = params.get("campaign_id")
        fields = params.get("fields", ["id", "name", "status", "objective", "daily_budget", "lifetime_budget"])
        if not campaign_id:
            raise ValueError("'campaign_id' es requerido.")
        
        campaign = Campaign(campaign_id)
        details = campaign.api_get(fields=fields)
        return {"status": "success", "data": details.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_create_ad_set(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_create_ad_set"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = params.get("ad_account_id")
        ad_set_payload = params.get("ad_set_payload")
        if not ad_account_id or not ad_set_payload:
            raise ValueError("'ad_account_id' y 'ad_set_payload' son requeridos.")
        
        ad_account = AdAccount(f"act_{str(ad_account_id).replace('act_', '')}")
        ad_set = ad_account.create_ad_set(params=ad_set_payload)
        return {"status": "success", "data": ad_set.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_ad_set_details(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_ad_set_details"
    try:
        _get_meta_ads_api_client(params)
        ad_set_id = params.get("ad_set_id")
        fields = params.get("fields", ["id", "name", "status", "campaign_id", "targeting", "daily_budget"])
        if not ad_set_id:
            raise ValueError("'ad_set_id' es requerido.")

        ad_set = AdSet(ad_set_id)
        details = ad_set.api_get(fields=fields)
        return {"status": "success", "data": details.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_account_insights(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    # Reemplaza la función existente get_insights con esta versión actualizada
    action_name = "metaads_get_account_insights"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = params.get("ad_account_id")
        insights_params = params.get("insights_params", {})
        if not ad_account_id:
            raise ValueError("'ad_account_id' es requerido.")
        
        ad_account = AdAccount(f"act_{str(ad_account_id).replace('act_', '')}")
        insights = ad_account.get_insights(params=insights_params)
        return {"status": "success", "data": [i.export_all_data() for i in insights]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_create_ad(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_create_ad"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = _get_ad_account_id(params)
        payload = params.get("ad_payload")
        if not payload:
            raise ValueError("'ad_payload' es requerido.")
        ad_account = AdAccount(ad_account_id)
        ad = ad_account.create_ad(params=payload)
        return {"status": "success", "data": ad.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_ad_preview(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_ad_preview"
    try:
        _get_meta_ads_api_client(params)
        ad_id = params.get("ad_id")
        ad_format = params.get("ad_format", "DESKTOP_FEED_STANDARD")
        if not ad_id:
            raise ValueError("'ad_id' es requerido.")
        ad = Ad(ad_id)
        previews = ad.get_previews(params={'ad_format': ad_format})
        return {"status": "success", "data": [p.export_all_data() for p in previews]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_update_ad(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_update_ad"
    try:
        _get_meta_ads_api_client(params)
        ad_id = params.get("ad_id")
        update_payload = params.get("update_payload")
        if not ad_id or not update_payload:
            raise ValueError("'ad_id' y 'update_payload' son requeridos.")
        ad = Ad(ad_id)
        ad.api_update(params=update_payload)
        updated = ad.api_get(fields=["id", "name", "status", "creative"])
        return {"status": "success", "data": updated.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_delete_ad(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_delete_ad"
    try:
        _get_meta_ads_api_client(params)
        ad_id = params.get("ad_id")
        if not ad_id:
            raise ValueError("'ad_id' es requerido.")
        Ad(ad_id).api_delete()
        return {"status": "success", "message": f"Anuncio '{ad_id}' eliminado."}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_update_ad_set(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_update_ad_set"
    try:
        _get_meta_ads_api_client(params)
        ad_set_id = params.get("ad_set_id")
        update_payload = params.get("update_payload")
        if not ad_set_id or not update_payload:
            raise ValueError("'ad_set_id' y 'update_payload' son requeridos.")
        ad_set = AdSet(ad_set_id)
        ad_set.api_update(params=update_payload)
        updated = ad_set.api_get(fields=["id", "name", "status", "targeting", "budget_remaining"])
        return {"status": "success", "data": updated.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_delete_ad_set(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_delete_ad_set"
    try:
        _get_meta_ads_api_client(params)
        ad_set_id = params.get("ad_set_id")
        if not ad_set_id:
            raise ValueError("'ad_set_id' es requerido.")
        AdSet(ad_set_id).api_delete()
        return {"status": "success", "message": f"Conjunto de anuncios '{ad_set_id}' eliminado."}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_update_page_settings(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_update_page_settings"
    try:
        _get_meta_ads_api_client(params)
        page_id = params.get("page_id")
        settings_payload = params.get("settings_payload")
        if not page_id or not settings_payload:
            raise ValueError("'page_id' y 'settings_payload' son requeridos.")
        page = Page(page_id)
        page.api_update(params=settings_payload)
        updated = page.api_get(fields=["id", "name", "settings"])
        return {"status": "success", "data": updated.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_create_custom_audience(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_create_custom_audience"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = _get_ad_account_id(params)
        audience_payload = params.get("audience_payload")
        if not audience_payload:
            raise ValueError("'audience_payload' es requerido.")
        ad_account = AdAccount(ad_account_id)
        audience = ad_account.create_custom_audience(params=audience_payload)
        return {"status": "success", "data": audience.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_list_custom_audiences(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_list_custom_audiences"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = _get_ad_account_id(params)
        ad_account = AdAccount(ad_account_id)
        audiences = ad_account.get_custom_audiences(fields=["id", "name", "subtype", "approximate_count"])
        return {"status": "success", "data": [a.export_all_data() for a in audiences]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_create_ad_creative(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_create_ad_creative"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = _get_ad_account_id(params)
        creative_payload = params.get("creative_payload")
        if not creative_payload:
            raise ValueError("'creative_payload' es requerido.")
        ad_account = AdAccount(ad_account_id)
        creative = ad_account.create_ad_creative(params=creative_payload)
        return {"status": "success", "data": creative.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_ad_details(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_ad_details"
    try:
        _get_meta_ads_api_client(params)
        ad_id = params.get("ad_id")
        if not ad_id:
            raise ValueError("'ad_id' es requerido.")
        ad = Ad(ad_id)
        details = ad.api_get(fields=["id", "name", "status", "creative", "tracking_specs", "conversion_specs"])
        return {"status": "success", "data": details.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_ad_set_insights(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_ad_set_insights"
    try:
        _get_meta_ads_api_client(params)
        ad_set_id = params.get("ad_set_id")
        if not ad_set_id:
            raise ValueError("'ad_set_id' es requerido.")
        ad_set = AdSet(ad_set_id)
        insights = ad_set.get_insights(params=params.get("insights_params", {}))
        return {"status": "success", "data": [i.export_all_data() for i in insights]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_campaign_insights(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_campaign_insights"
    try:
        _get_meta_ads_api_client(params)
        campaign_id = params.get("campaign_id")
        if not campaign_id:
            raise ValueError("'campaign_id' es requerido.")
        campaign = Campaign(campaign_id)
        insights = campaign.get_insights(params=params.get("insights_params", {}))
        return {"status": "success", "data": [i.export_all_data() for i in insights]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_pause_entity(client: Any, params: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
    action_name = f"metaads_pause_{entity_type}"
    try:
        _get_meta_ads_api_client(params)
        entity_id = params.get(f"{entity_type}_id")
        if not entity_id:
            raise ValueError(f"'{entity_type}_id' es requerido.")
        
        entity_map = {
            "campaign": Campaign,
            "ad": Ad,
            "ad_set": AdSet
        }
        
        EntityClass = entity_map.get(entity_type)
        if not EntityClass:
            raise ValueError(f"Tipo de entidad no válido: {entity_type}")
            
        entity = EntityClass(entity_id)
        entity.api_update(params={"status": "PAUSED"})
        updated = entity.api_get(fields=["id", "name", "status"])
        return {"status": "success", "data": updated.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_pause_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    return metaads_pause_entity(client, params, "campaign")

def metaads_pause_ad(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    return metaads_pause_entity(client, params, "ad")

def metaads_pause_ad_set(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    return metaads_pause_entity(client, params, "ad_set")

def metaads_get_pixel_events(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_pixel_events"
    try:
        _get_meta_ads_api_client(params)
        pixel_id = params.get("pixel_id")
        if not pixel_id:
            raise ValueError("'pixel_id' es requerido.")
        
        ad_account_id = _get_ad_account_id(params)
        ad_account = AdAccount(ad_account_id)
        events = ad_account.get_pixels(fields=["id", "name", "code", "last_fired_time"])
        return {"status": "success", "data": [e.export_all_data() for e in events]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)