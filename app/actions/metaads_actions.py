# app/actions/metaads_actions.py
import logging
from typing import Dict, List, Optional, Any
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.exceptions import FacebookRequestError
import json
import time

from app.core.config import settings 
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)
_meta_ads_api_instance: Optional[FacebookAdsApi] = None

def get_meta_ads_api_client(client_config_override: Optional[Dict[str, str]] = None) -> FacebookAdsApi:
    global _meta_ads_api_instance
    if _meta_ads_api_instance and not client_config_override: return _meta_ads_api_instance
    config_to_use = client_config_override or {
        "app_id": settings.META_ADS.APP_ID, "app_secret": settings.META_ADS.APP_SECRET,
        "access_token": settings.META_ADS.ACCESS_TOKEN,
    }
    if not all(config_to_use.get(k) for k in ["app_id", "app_secret", "access_token"]):
        raise ValueError("Faltan credenciales de Meta Ads (APP_ID, APP_SECRET, ACCESS_TOKEN).")
    try:
        api_version = "v19.0" # O la versión más reciente que estés usando
        FacebookAdsApi.init(app_id=str(config_to_use["app_id"]), app_secret=str(config_to_use["app_secret"]), 
                            access_token=str(config_to_use["access_token"]), api_version=api_version)
        current_api_instance = FacebookAdsApi.get_default_api()
        if not current_api_instance: raise ConnectionError("FacebookAdsApi.get_default_api() devolvió None.")
        if not client_config_override: _meta_ads_api_instance = current_api_instance
        logger.info(f"Cliente de Meta Ads inicializado. API Version: {api_version}")
        return current_api_instance
    except Exception as e: raise ConnectionError(f"No se pudo inicializar el cliente de Meta Ads: {e}")

def _get_ad_account(params: Dict[str, Any]) -> AdAccount:
    effective_id = params.get("ad_account_id") or settings.META_ADS.BUSINESS_ACCOUNT_ID
    if not effective_id: raise ValueError("Se requiere 'ad_account_id' o META_ADS_BUSINESS_ACCOUNT_ID.")
    return AdAccount(f"act_{str(effective_id).replace('act_', '')}")

def _handle_meta_ads_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    log_message = f"Error en Meta Ads Action '{action_name}'"
    safe_params = {k: (v if k not in ['campaign_payload', 'update_payload', 'access_token'] else f"[{type(v).__name__} OMITIDO]") for k, v in (params_for_log or {}).items()}
    log_message += f" con params: {safe_params}"
    logger.error(log_message, exc_info=True)
    
    details_str = str(e); status_code_int = 500; api_error_code = None; api_error_subcode = None
    api_error_message_main = str(e); user_message_fb = None; user_title_fb = None; api_error_body_dict = {}

    if isinstance(e, FacebookRequestError):
        status_code_int = e.http_status() or 500
        api_error_code = e.api_error_code()
        api_error_subcode = e.api_error_subcode()
        api_error_message_main = e.api_error_message() or str(e)
        try:
            api_error_body_dict = e.body() or {} 
            if isinstance(api_error_body_dict, dict):
                error_content = api_error_body_dict.get('error', {})
                user_message_fb = error_content.get('error_user_msg')
                user_title_fb = error_content.get('error_user_title')
                if error_content.get('message'): api_error_message_main = error_content.get('message')
                details_str = json.dumps(api_error_body_dict)
            else: details_str = f"API Error Code: {api_error_code}, Subcode: {api_error_subcode}, Message: {api_error_message_main}"
        except Exception: details_str = f"API Error Code: {api_error_code}, Subcode: {api_error_subcode}, Message: {api_error_message_main}. Cuerpo de error no parseable."
    elif isinstance(e, (ValueError, ConnectionError)): 
        status_code_int = 503 if isinstance(e, ConnectionError) else 400; api_error_message_main = str(e)

    return {"status": "error", "action": action_name, "message": user_message_fb or api_error_message_main, 
            "http_status": status_code_int, "details": {
                "raw_exception_type": type(e).__name__, "raw_exception_message": str(e),
                "api_error_code": api_error_code, "api_error_subcode": api_error_subcode,
                "api_error_title_for_user": user_title_fb, "full_api_response_details": api_error_body_dict or details_str}}

def default_fields_for_campaign_read(): # Renombrado para claridad
    return [
        Campaign.Field.id, Campaign.Field.name, Campaign.Field.status, Campaign.Field.effective_status,
        Campaign.Field.objective, Campaign.Field.account_id, Campaign.Field.special_ad_categories,
        Campaign.Field.daily_budget, Campaign.Field.lifetime_budget, Campaign.Field.budget_remaining,
        Campaign.Field.start_time, Campaign.Field.stop_time, Campaign.Field.created_time, Campaign.Field.updated_time
    ]

def metaads_list_campaigns(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "metaads_list_campaigns"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    try:
        get_meta_ads_api_client(params.get("client_config_override"))
        ad_account = _get_ad_account(params)
        fields_to_request = params.get("fields", default_fields_for_campaign_read())
        api_params_sdk: Dict[str, Any] = {'fields': fields_to_request}
        if params.get("filtering"): api_params_sdk['filtering'] = params["filtering"]
        if params.get("limit"): api_params_sdk['limit'] = params["limit"]
        
        campaigns_cursor = ad_account.get_campaigns(params=api_params_sdk)
        campaigns_list = [campaign.export_all_data() for campaign in campaigns_cursor]
        return {"status": "success", "data": campaigns_list, "total_retrieved": len(campaigns_list)}
    except Exception as e: return _handle_meta_ads_api_error(e, action_name, params)

def metaads_create_campaign(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "metaads_create_campaign"
    logger.info(f"Ejecutando {action_name} (payload omitido del log)")
    campaign_payload: Optional[Dict[str, Any]] = params.get("campaign_payload")
    if not campaign_payload or not isinstance(campaign_payload, dict): return {"status": "error", "action": action_name, "message": "'campaign_payload' (dict) es requerido.", "http_status": 400}
    required = [Campaign.Field.name, Campaign.Field.objective, Campaign.Field.status, Campaign.Field.special_ad_categories]
    if not all(k in campaign_payload for k in required) or not isinstance(campaign_payload[Campaign.Field.special_ad_categories], list):
        return {"status": "error", "action": action_name, "message": f"Faltan campos o 'special_ad_categories' no es lista. Requeridos: {required}.", "http_status": 400}
    try:
        get_meta_ads_api_client(params.get("client_config_override"))
        ad_account = _get_ad_account(params)
        new_campaign = Campaign(parent_id=ad_account[AdAccount.Field.id])
        new_campaign.update(campaign_payload); new_campaign.remote_create()
        new_campaign.api_get(fields=default_fields_for_campaign_read())
        return {"status": "success", "data": new_campaign.export_all_data()}
    except Exception as e: return _handle_meta_ads_api_error(e, action_name, params)

def metaads_update_campaign(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "metaads_update_campaign"
    logger.info(f"Ejecutando {action_name} (payload omitido del log)")
    campaign_id: Optional[str] = params.get("campaign_id")
    update_payload: Optional[Dict[str, Any]] = params.get("update_payload")
    if not campaign_id: return {"status": "error", "action": action_name, "message": "'campaign_id' es requerido.", "http_status": 400}
    if not update_payload or not isinstance(update_payload, dict) or not update_payload: return {"status": "error", "action": action_name, "message": "'update_payload' (dict no vacío) es requerido.", "http_status": 400}
    try:
        get_meta_ads_api_client(params.get("client_config_override"))
        campaign_to_update = Campaign(campaign_id)
        campaign_to_update.update(update_payload); campaign_to_update.remote_update()
        campaign_to_update.api_get(fields=default_fields_for_campaign_read())
        return {"status": "success", "data": campaign_to_update.export_all_data()}
    except Exception as e: return _handle_meta_ads_api_error(e, action_name, params)

def metaads_delete_campaign(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "metaads_delete_campaign"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    campaign_id: Optional[str] = params.get("campaign_id")
    if not campaign_id: return {"status": "error", "action": action_name, "message": "'campaign_id' es requerido.", "http_status": 400}
    try:
        get_meta_ads_api_client(params.get("client_config_override"))
        campaign_to_delete = Campaign(campaign_id)
        campaign_to_delete.update({Campaign.Field.status: Campaign.Status.deleted})
        campaign_to_delete.remote_update() 
        return {"status": "success", "message": f"Campaña '{campaign_id}' marcada como eliminada."}
    except Exception as e: return _handle_meta_ads_api_error(e, action_name, params)

def metaads_get_insights(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "metaads_get_insights"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    object_id_param: Optional[str] = params.get("object_id"); level_param: str = params.get("level", "campaign").lower()
    if level_param not in ['campaign', 'adset', 'ad', 'account']: return {"status": "error", "message": "'level' debe ser 'campaign', 'adset', 'ad', o 'account'.", "http_status": 400}
    if level_param != 'account' and not object_id_param: return {"status": "error", "message": f"'object_id' requerido para nivel '{level_param}'.", "http_status": 400}
    
    api_params_sdk: Dict[str, Any] = {'fields': params.get("fields", ['campaign_name', 'adset_name', 'ad_name', 'impressions', 'spend', 'clicks'])}
    for p_key in ["date_preset", "time_range", "filtering", "breakdowns", "action_breakdowns", "time_increment", "limit", "sort"]:
        if params.get(p_key): api_params_sdk[p_key] = params[p_key]
    try:
        get_meta_ads_api_client(params.get("client_config_override"))
        target_object_sdk: Any; log_id = object_id_param
        if level_param == 'campaign': target_object_sdk = Campaign(object_id_param)
        elif level_param == 'adset': target_object_sdk = AdSet(object_id_param) # type: ignore
        elif level_param == 'ad': target_object_sdk = Ad(object_id_param) # type: ignore
        elif level_param == 'account': target_object_sdk = _get_ad_account(params); log_id = target_object_sdk[AdAccount.Field.id]
        else: raise ValueError(f"Nivel de insights desconocido: {level_param}")
        insights_cursor = target_object_sdk.get_insights(params=api_params_sdk)
        insights_list = [data.export_all_data() for data in insights_cursor]
        return {"status": "success", "data": insights_list, "total_retrieved": len(insights_list)}
    except Exception as e: return _handle_meta_ads_api_error(e, action_name, params)