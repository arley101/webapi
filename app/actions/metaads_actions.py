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

    if isinstance(e, FacebookRequestError):
        status_code = e.http_status() or 500
        error_message = e.api_error_message() or "Unknown Facebook API Error"
        details = {
            "api_error_code": e.api_error_code(),
            "api_error_subcode": e.api_error_subcode(),
            "api_error_message": e.api_error_message(),
            "api_error_user_title": e.api_error_user_title(),
            "api_error_user_msg": e.api_error_user_message(),
            "raw_response": e.get_response(as_dict=True)
        }
    return {"status": "error", "action": action_name, "message": error_message, "http_status": status_code, "details": details}

# --- ACTIONS FOR PERMISSION DEMONSTRATION ---

def metaads_get_business_details(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Demonstrates 'business_management' by fetching business details."""
    action_name = "metaads_get_business_details"
    logger.info(f"Executing {action_name} for business_id: {params.get('business_id')}")
    try:
        _get_meta_ads_api_client(params)
        business_id = params.get("business_id")
        if not business_id:
            raise ValueError("'business_id' is required.")

        business = Business(business_id)
        fields_to_get = params.get("fields", ["id", "name", "verification_status"])
        business_info = business.api_get(fields=fields_to_get)
        
        return {"status": "success", "data": business_info.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_list_owned_pages(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Demonstrates 'pages_show_list' by listing pages owned by a business to retrieve a Page Token."""
    action_name = "metaads_list_owned_pages"
    logger.info(f"Executing {action_name} for business_id: {params.get('business_id')}")
    try:
        _get_meta_ads_api_client(params)
        business_id = params.get("business_id")
        if not business_id:
            raise ValueError("'business_id' is required.")
        
        business = Business(business_id)
        fields_to_get = params.get("fields", ["id", "name", "access_token"]) # access_token is crucial here
        owned_pages = business.get_owned_pages(fields=fields_to_get)
        
        pages_list = [page.export_all_data() for page in owned_pages]
        return {"status": "success", "data": pages_list}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_page_engagement(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Demonstrates 'pages_read_engagement' using a specific Page Access Token."""
    action_name = "metaads_get_page_engagement"
    logger.info(f"Executing {action_name} for page_id: {params.get('page_id')}")
    
    original_api_instance = FacebookAdsApi.get_default_api()
    try:
        page_id = params.get("page_id")
        page_access_token = params.get("page_access_token")
        if not page_id or not page_access_token:
            raise ValueError("'page_id' and 'page_access_token' are required.")

        temp_api_instance = FacebookAdsApi.init(access_token=page_access_token, api_version="v19.0")
        
        # ***** CORRECCIÓN FINAL Y DEFINITIVA *****
        # El ID se pasa como el primer argumento posicional, sin palabra clave.
        page = Page(page_id, api=temp_api_instance)
        # ***** FIN DE LA CORRECCIÓN *****

        fields_to_get = params.get("fields", ["id", "name", "engagement"])
        page_info = page.api_get(fields=fields_to_get)
        
        return {"status": "success", "data": page_info.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)
    finally:
        if original_api_instance:
            FacebookAdsApi.set_default_api(original_api_instance)
            logger.info("Facebook API client reverted to default System User instance.")

# --- OTHER ACTIONS ---

def metaads_list_campaigns(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_list_campaigns"
    logger.info(f"Executing {action_name} for ad_account_id: {params.get('ad_account_id')}")
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = params.get("ad_account_id")
        if not ad_account_id:
            raise ValueError("'ad_account_id' is required.")
        
        ad_account = AdAccount(f"act_{str(ad_account_id).replace('act_', '')}")
        fields_to_get = params.get("fields", ["id", "name", "status", "objective"])
        campaigns = ad_account.get_campaigns(fields=fields_to_get)

        campaigns_list = [campaign.export_all_data() for campaign in campaigns]
        return {"status": "success", "data": campaigns_list}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_create_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "metaads_create_campaign"
    logger.info(f"Executing {action_name} for ad_account_id: {params.get('ad_account_id')}")
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = params.get("ad_account_id")
        campaign_payload = params.get("campaign_payload")
        if not ad_account_id or not campaign_payload:
            raise ValueError("'ad_account_id' and 'campaign_payload' are required.")

        ad_account = AdAccount(f"act_{str(ad_account_id).replace('act_', '')}")
        created_campaign = ad_account.create_campaign(params=campaign_payload)

        return {"status": "success", "data": created_campaign.export_all_data()}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_update_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "metaads_update_campaign"
    try:
        _get_meta_ads_api_client(params)
        campaign_id = params.get("campaign_id")
        update_payload = params.get("update_payload")
        if not campaign_id or not update_payload:
            raise ValueError("'campaign_id' and 'update_payload' are required.")
        
        campaign = Campaign(campaign_id)
        campaign.api_update(params=update_payload)
        return {"status": "success", "data": {"id": campaign_id, "success": True}}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_delete_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "metaads_delete_campaign"
    try:
        _get_meta_ads_api_client(params)
        campaign_id = params.get("campaign_id")
        if not campaign_id:
            raise ValueError("'campaign_id' is required.")
        
        campaign = Campaign(campaign_id)
        campaign.api_delete()
        return {"status": "success", "message": f"Campaign '{campaign_id}' deleted."}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)

def metaads_get_insights(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "metaads_get_insights"
    try:
        _get_meta_ads_api_client(params)
        ad_account_id = params.get("ad_account_id")
        insights_params = params.get("insights_params")
        if not ad_account_id or not insights_params:
            raise ValueError("'ad_account_id' and 'insights_params' are required.")
            
        ad_account = AdAccount(f"act_{str(ad_account_id).replace('act_', '')}")
        insights = ad_account.get_insights(params=insights_params)
        insights_list = [insight.export_all_data() for insight in insights]
        return {"status": "success", "data": insights_list}
    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name)