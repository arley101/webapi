# app/actions/metaads_actions.py
import logging
import json
from typing import Dict, List, Optional, Any

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.business import Business
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.page import Page
from facebook_business.exceptions import FacebookRequestError

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# --- SDK INITIALIZATION AND HELPERS ---

_meta_ads_api_instance: Optional[FacebookAdsApi] = None

def _get_meta_ads_api_client(params: Dict[str, Any]) -> FacebookAdsApi:
    """Initializes and returns a FacebookAdsApi instance, ensuring credentials are used correctly."""
    global _meta_ads_api_instance

    access_token = settings.META_ADS.ACCESS_TOKEN
    app_id = settings.META_ADS.APP_ID
    app_secret = settings.META_ADS.APP_SECRET
    
    access_token = params.get("system_user_token_override", access_token)

    if not all([app_id, app_secret, access_token]):
        raise ValueError("Meta Ads credentials (META_ADS_APP_ID, META_ADS_APP_SECRET, META_ADS_ACCESS_TOKEN) must be configured in your environment.")

    if _meta_ads_api_instance and not params.get("system_user_token_override"):
         return _meta_ads_api_instance

    logger.info("Initializing Facebook Marketing API client...")
    FacebookAdsApi.init(app_id=str(app_id), app_secret=str(app_secret), access_token=str(access_token), api_version="v19.0")
    
    current_api = FacebookAdsApi.get_default_api()
    if not current_api:
        raise ConnectionError("Failed to get default API instance from FacebookAdsApi.")
    
    if not params.get("system_user_token_override"):
        _meta_ads_api_instance = current_api
        
    return current_api

def _handle_meta_ads_api_error(e: Exception, action_name: str) -> Dict[str, Any]:
    """Formats a FacebookRequestError into a standard error response."""
    logger.error(f"Error in Meta Ads Action '{action_name}': {type(e).__name__} - {e}", exc_info=True)
    status_code, error_message = 500, str(e)
    details = {}
    user_title = None
    user_message = None

    if isinstance(e, FacebookRequestError):
        status_code = e.http_status() or 500
        error_message = e.api_error_message() or "Unknown Facebook API Error"
        
        if hasattr(e, 'api_error_user_title'):
            user_title = e.api_error_user_title()
        if hasattr(e, 'api_error_user_message'):
            user_message = e.api_error_user_message()
            
        # ***** CORRECCIÓN FINAL Y DEFINITIVA #2 *****
        # El método correcto para obtener el cuerpo del error es .body()
        error_body = e.body() if hasattr(e, 'body') else str(e)
        # ***** FIN DE LA CORRECCIÓN *****

        details = {
            "api_error_code": e.api_error_code(),
            "api_error_subcode": e.api_error_subcode(),
            "api_error_message": e.api_error_message(),
            "api_error_user_title": user_title,
            "api_error_user_msg": user_message,
            "raw_response": error_body
        }
    return {"status": "error", "action": action_name, "message": user_message or error_message, "http_status": status_code, "details": details}

# --- ACTIONS ---

def metaads_get_business_details(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_business_details"
    try:
        _get_meta_ads_api_client(params)
        business_id = params.get("business_id")
        if not business_id: raise ValueError("'business_id' is required.")
        business = Business(business_id)
        business_info = business.api_get(fields=params.get("fields", ["id", "name", "verification_status"]))
        return {"status": "success", "data": business_info.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_list_owned_pages(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_list_owned_pages"
    try:
        _get_meta_ads_api_client(params)
        business_id = params.get("business_id")
        if not business_id: raise ValueError("'business_id' is required.")
        business = Business(business_id)
        owned_pages = business.get_owned_pages(fields=params.get("fields", ["id", "name", "access_token"]))
        return {"status": "success", "data": [page.export_all_data() for page in owned_pages]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_page_engagement(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_get_page_engagement"
    original_api_instance = FacebookAdsApi.get_default_api()
    try:
        page_id = params.get("page_id")
        page_access_token = params.get("page_access_token")
        if not page_id or not page_access_token: raise ValueError("'page_id' and 'page_access_token' are required.")
        
        temp_api_instance = FacebookAdsApi.init(access_token=page_access_token, api_version="v19.0")
        page = Page(page_id, api=temp_api_instance)
        page_info = page.api_get(fields=params.get("fields", ["id", "name", "engagement"]))
        
        return {"status": "success", "data": page_info.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)
    finally:
        if original_api_instance: FacebookAdsApi.set_default_api(original_api_instance)

def metaads_list_campaigns(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_list_campaigns"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = params.get("ad_account_id")
        if not ad_account_id: raise ValueError("'ad_account_id' is required.")
        ad_account = AdAccount(f"act_{str(ad_account_id).replace('act_', '')}")
        campaigns = ad_account.get_campaigns(fields=params.get("fields", ["id", "name", "status", "objective"]))
        return {"status": "success", "data": [campaign.export_all_data() for campaign in campaigns]}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_create_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_create_campaign"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = params.get("ad_account_id")
        campaign_payload = params.get("campaign_payload")
        if not ad_account_id or not campaign_payload: raise ValueError("'ad_account_id' and 'campaign_payload' are required.")
        ad_account = AdAccount(f"act_{str(ad_account_id).replace('act_', '')}")
        created_campaign = ad_account.create_campaign(params=campaign_payload)
        return {"status": "success", "data": created_campaign.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)