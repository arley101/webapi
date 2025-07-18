# app/actions/metaads_actions.py
import logging
from typing import Dict, Any

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.business import Business
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.page import Page
from facebook_business.exceptions import FacebookRequestError

from app.core.config import settings

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

def _handle_meta_ads_api_error(e: Exception, action_name: str) -> Dict[str, Any]:
    logger.error(f"Error en Meta Ads Action '{action_name}': {type(e).__name__} - {e}", exc_info=True)
    status_code, error_message, details = 500, str(e), {}

    if isinstance(e, FacebookRequestError):
        status_code = e.http_status() or 500
        error_body = e.body() if hasattr(e, 'body') and callable(e.body) else {}
        if error_body and 'error' in error_body:
            details = error_body['error']
            error_message = details.get('message', "Unknown Facebook API Error")
        else:
            details = {"raw_response": str(e)}
            error_message = e.api_error_message() or "Unknown Facebook API Error"
    
    return {"status": "error", "action": action_name, "message": error_message, "http_status": status_code, "details": details}

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
    action_name = "metaads_create_campaign"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = params.get("ad_account_id")
        campaign_payload = params.get("campaign_payload")
        if not ad_account_id or not campaign_payload:
            raise ValueError("'ad_account_id' y 'campaign_payload' son requeridos.")
        ad_account = AdAccount(f"act_{str(ad_account_id).replace('act_', '')}")
        campaign = ad_account.create_campaign(params=campaign_payload)
        return {"status": "success", "data": campaign.export_all_data()}
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