# app/actions/metaads_actions.py
import logging
from typing import Dict, List, Optional, Any

# SDK de Facebook Business
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.exceptions import FacebookRequestError
import json

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient # No se usa directamente

logger = logging.getLogger(__name__)

_meta_ads_api_instance: Optional[FacebookAdsApi] = None

def get_meta_ads_api_client(client_config_override: Optional[Dict[str, Any]] = None) -> FacebookAdsApi:
    global _meta_ads_api_instance
    if _meta_ads_api_instance and not client_config_override:
        return _meta_ads_api_instance

    config_to_use: Dict[str, Optional[Any]]
    params_from_config = {}
    if client_config_override:
        logger.info("Utilizando configuración de Meta Ads proporcionada en 'client_config_override'.")
        config_to_use = client_config_override
        if "params" in client_config_override and isinstance(client_config_override["params"], dict):
            params_from_config = client_config_override["params"]
    else:
        config_to_use = {
            "app_id": settings.META_ADS.APP_ID,
            "app_secret": settings.META_ADS.APP_SECRET,
            "access_token": settings.META_ADS.ACCESS_TOKEN,
        }

    required_keys = ["app_id", "app_secret", "access_token"]
    missing_creds = [key for key in required_keys if not config_to_use.get(key)]

    if missing_creds:
        msg = (
            f"Faltan credenciales de Meta Ads en la configuración: {', '.join(missing_creds)}. "
            "Se requieren: APP_ID, APP_SECRET, ACCESS_TOKEN (ya sea de settings o de client_config_override)."
        )
        logger.critical(msg)
        raise ValueError(msg)

    logger.info("Inicializando cliente de Meta Ads (Facebook Marketing API)...")
    try:
        app_id_str = str(config_to_use["app_id"])
        app_secret_str = str(config_to_use["app_secret"])
        access_token_str = str(config_to_use["access_token"])
        api_version_str = str(params_from_config.get("api_version", "v19.0"))

        FacebookAdsApi.init(
            app_id=app_id_str,
            app_secret=app_secret_str,
            access_token=access_token_str,
            api_version=api_version_str
        )
        current_api_instance = FacebookAdsApi.get_default_api()
        if not current_api_instance:
             raise ConnectionError("FacebookAdsApi.get_default_api() devolvió None después de la inicialización.")

        if not client_config_override:
            _meta_ads_api_instance = current_api_instance

        logger.info(f"Cliente de Meta Ads inicializado exitosamente. API Version: {api_version_str}")
        return current_api_instance
    except Exception as e:
        logger.exception(f"Error crítico inicializando el cliente de Meta Ads: {e}")
        raise ConnectionError(f"No se pudo inicializar el cliente de Meta Ads: {e}")


def _handle_meta_ads_api_error(
    e: Exception,
    action_name: str,
    params_for_log: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    log_message = f"Error en Meta Ads Action '{action_name}'"
    safe_params = {}
    if params_for_log:
        sensitive_keys = ['client_config_override', 'access_token', 'campaign_payload', 'update_payload', 'ad_object_payload']
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"

    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)

    details_str = str(e)
    status_code_int = 500
    api_error_code = None
    api_error_subcode = None
    api_error_message = str(e)
    user_message = None
    user_title = None
    fbtrace_id = None

    if isinstance(e, FacebookRequestError):
        status_code_int = e.http_status() or 500
        api_error_code = e.api_error_code()
        api_error_subcode = e.api_error_subcode()
        
        # Corrección: Obtener mensajes de forma segura
        _api_error_message_from_sdk = e.api_error_message()
        _user_message_from_sdk = e.api_error_user_message() if hasattr(e, 'api_error_user_message') else None
        _user_title_from_sdk = e.api_error_user_title() if hasattr(e, 'api_error_user_title') else None
        
        error_body_content = None
        try:
            error_body_content = e.body() # type: ignore
        except Exception:
             logger.debug(f"No se pudo obtener e.body() de FacebookRequestError para {action_name}")

        if error_body_content and isinstance(error_body_content, dict) and 'error' in error_body_content:
            error_obj = error_body_content['error']
            api_error_message = error_obj.get('message', _api_error_message_from_sdk or str(e))
            user_message = error_obj.get('error_user_msg', _user_message_from_sdk)
            user_title = error_obj.get('error_user_title', _user_title_from_sdk)
            if not api_error_code: api_error_code = error_obj.get('code')
            if not api_error_subcode: api_error_subcode = error_obj.get('error_subcode')
            fbtrace_id = error_obj.get('fbtrace_id')
            details_str = json.dumps(error_body_content)
        else:
            api_error_message = _api_error_message_from_sdk or str(e)
            user_message = _user_message_from_sdk
            user_title = _user_title_from_sdk
            details_str = f"API Error Code: {api_error_code}, Subcode: {api_error_subcode}, Message: {api_error_message}"
            if e.http_status() and hasattr(e, 'get_response_content') and e.get_response_content(): # type: ignore
                try:
                    details_str = json.dumps(json.loads(e.get_response_content())) # type: ignore
                except:
                     details_str = str(e.get_response_content())[:500] # type: ignore

    elif isinstance(e, (ValueError, ConnectionError)):
        status_code_int = 503 if isinstance(e, ConnectionError) else 400
        api_error_message = str(e)
        details_str = str(e)

    error_response: Dict[str, Any] = {
        "status": "error",
        "action": action_name,
        "message": user_message or api_error_message,
        "http_status": status_code_int,
        "details": {
            "raw_exception_type": type(e).__name__,
            "raw_exception_message": str(e),
            "api_error_code": api_error_code,
            "api_error_subcode": api_error_subcode,
            "api_error_title_for_user": user_title,
            "fbtrace_id": fbtrace_id,
            "full_api_response_details": details_str
        }
    }
    return error_response

def _get_ad_account(params: Dict[str, Any]) -> AdAccount:
    ad_account_id_from_params: Optional[str] = params.get("ad_account_id")
    effective_ad_account_id = ad_account_id_from_params or settings.META_ADS.BUSINESS_ACCOUNT_ID

    if not effective_ad_account_id:
        raise ValueError("Se requiere 'ad_account_id' en los parámetros de la acción o META_ADS_BUSINESS_ACCOUNT_ID en la configuración global.")

    effective_ad_account_id_str = str(effective_ad_account_id)
    if not effective_ad_account_id_str.startswith("act_"):
        effective_ad_account_id_str = f"act_{effective_ad_account_id_str.replace('act_', '')}"

    return AdAccount(effective_ad_account_id_str)

def default_fields_for_campaign_read():
    return [
        Campaign.Field.id, Campaign.Field.name, Campaign.Field.status, Campaign.Field.effective_status,
        Campaign.Field.objective, Campaign.Field.buying_type, Campaign.Field.start_time,
        Campaign.Field.stop_time, Campaign.Field.daily_budget, Campaign.Field.lifetime_budget,
        Campaign.Field.budget_remaining, Campaign.Field.created_time, Campaign.Field.updated_time,
        Campaign.Field.account_id, Campaign.Field.special_ad_categories
    ]

def metaads_list_campaigns(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "metaads_list_campaigns"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    fields_param: Optional[List[str]] = params.get("fields")
    filtering_param: Optional[List[Dict[str, Any]]] = params.get("filtering")
    limit_param: Optional[int] = params.get("limit")

    fields_to_request = fields_param if fields_param and isinstance(fields_param, list) else default_fields_for_campaign_read()

    try:
        get_meta_ads_api_client(params.get("client_config_override"))
        ad_account = _get_ad_account(params)

        logger.info(f"Listando campañas de Meta Ads para la cuenta '{ad_account[AdAccount.Field.id]}' con campos: {fields_to_request}")

        api_params_sdk: Dict[str, Any] = {'fields': fields_to_request}
        if filtering_param and isinstance(filtering_param, list):
            api_params_sdk['filtering'] = filtering_param
            logger.info(f"Aplicando filtros: {filtering_param}")
        if limit_param and isinstance(limit_param, int) and limit_param > 0:
            api_params_sdk['limit'] = limit_param

        campaigns_cursor = ad_account.get_campaigns(params=api_params_sdk)
        
        campaigns_list = []
        for campaign in campaigns_cursor:
            campaigns_list.append(campaign.export_all_data())
            if limit_param and len(campaigns_list) >= limit_param:
                break
                
        logger.info(f"Se encontraron {len(campaigns_list)} campañas para la cuenta '{ad_account[AdAccount.Field.id]}'.")
        return {"status": "success", "data": campaigns_list, "total_retrieved": len(campaigns_list)}

    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name, params)

def metaads_create_campaign(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "metaads_create_campaign"
    log_params = {k:v for k,v in params.items() if k != 'campaign_payload'}
    if 'campaign_payload' in params: log_params['campaign_payload_keys'] = list(params['campaign_payload'].keys())
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    campaign_payload: Optional[Dict[str, Any]] = params.get("campaign_payload")

    if not campaign_payload or not isinstance(campaign_payload, dict):
        return {"status": "error", "action": action_name, "message": "'campaign_payload' (dict) es requerido.", "http_status": 400}

    required_keys = [Campaign.Field.name, Campaign.Field.objective, Campaign.Field.status, Campaign.Field.special_ad_categories]
    if not all(key in campaign_payload for key in required_keys):
        missing = [key for key in required_keys if key not in campaign_payload]
        return {"status": "error", "action": action_name, "message": f"Faltan campos requeridos en 'campaign_payload': {missing}. Mínimo: name, objective, status, special_ad_categories (puede ser lista vacía []).", "http_status": 400}
    if not isinstance(campaign_payload.get(Campaign.Field.special_ad_categories), list):
         return {"status": "error", "action": action_name, "message": f"El campo '{Campaign.Field.special_ad_categories}' debe ser una lista (ej. [] o ['HOUSING']).", "http_status": 400}

    try:
        get_meta_ads_api_client(params.get("client_config_override"))
        ad_account = _get_ad_account(params)

        logger.info(f"Creando campaña de Meta Ads en la cuenta '{ad_account[AdAccount.Field.id]}' con nombre: '{campaign_payload.get('name')}'")

        new_campaign = Campaign(parent_id=ad_account[AdAccount.Field.id])
        new_campaign.update(campaign_payload)

        new_campaign.remote_create()

        logger.info(f"Campaña '{new_campaign[Campaign.Field.name]}' creada con ID: {new_campaign[Campaign.Field.id]}")
        new_campaign.api_get(fields=default_fields_for_campaign_read())
        return {"status": "success", "data": new_campaign.export_all_data()}

    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name, params)

def metaads_update_campaign(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "metaads_update_campaign"
    log_params = {k:v for k,v in params.items() if k != 'update_payload'}
    if 'update_payload' in params: log_params['update_payload_keys'] = list(params['update_payload'].keys())
    logger.info(f"Ejecutando {action_name} con params: {log_params}")

    campaign_id: Optional[str] = params.get("campaign_id")
    update_payload: Optional[Dict[str, Any]] = params.get("update_payload")

    if not campaign_id:
        return {"status": "error", "action": action_name, "message": "'campaign_id' es requerido.", "http_status": 400}
    if not update_payload or not isinstance(update_payload, dict) or not update_payload:
        return {"status": "error", "action": action_name, "message": "'update_payload' (dict no vacío con campos a actualizar) es requerido.", "http_status": 400}

    try:
        get_meta_ads_api_client(params.get("client_config_override"))

        logger.info(f"Actualizando campaña de Meta Ads ID: '{campaign_id}' con campos: {list(update_payload.keys())}")

        campaign_to_update = Campaign(campaign_id)
        campaign_to_update.update(update_payload)

        campaign_to_update.remote_update()

        logger.info(f"Campaña ID '{campaign_id}' actualizada.")
        campaign_to_update.api_get(fields=default_fields_for_campaign_read())
        return {"status": "success", "data": campaign_to_update.export_all_data()}

    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name, params)

def metaads_delete_campaign(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "metaads_delete_campaign"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    campaign_id: Optional[str] = params.get("campaign_id")

    if not campaign_id:
        return {"status": "error", "action": action_name, "message": "'campaign_id' es requerido.", "http_status": 400}

    try:
        get_meta_ads_api_client(params.get("client_config_override"))

        logger.info(f"Intentando eliminar la campaña de Meta Ads ID: '{campaign_id}'")

        campaign_to_delete = Campaign(campaign_id)
        campaign_to_delete.remote_delete()

        logger.info(f"Campaña ID '{campaign_id}' eliminada.")
        return {"status": "success", "message": f"Campaña '{campaign_id}' eliminada exitosamente."}

    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name, params)

def metaads_get_insights(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "metaads_get_insights"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    object_id_param: Optional[str] = params.get("object_id")
    level_param: Optional[str] = params.get("level", "campaign").lower()

    fields_param: Optional[List[str]] = params.get("fields")
    date_preset_param: Optional[str] = params.get("date_preset")
    time_range_param: Optional[Dict[str, str]] = params.get("time_range")
    filtering_param: Optional[List[Dict[str, Any]]] = params.get("filtering")
    breakdowns_param: Optional[List[str]] = params.get("breakdowns")
    action_breakdowns_param: Optional[List[str]] = params.get("action_breakdowns")
    time_increment_param: Optional[Any] = params.get("time_increment")
    limit_param: Optional[int] = params.get("limit")
    sort_param: Optional[List[str]] = params.get("sort")

    if level_param not in ['campaign', 'adset', 'ad', 'account']:
        return {"status": "error", "action": action_name, "message": "'level' debe ser 'campaign', 'adset', 'ad', o 'account'.", "http_status": 400}
    if level_param != 'account' and not object_id_param:
        return {"status": "error", "action": action_name, "message": f"'object_id' es requerido para el nivel '{level_param}'.", "http_status": 400}

    default_insight_fields = [
        'campaign_name', 'adset_name', 'ad_name', 'impressions', 'spend',
        'clicks', 'ctr', 'cpc', 'reach', 'frequency', 'objective', 'date_start', 'date_stop'
    ]
    fields_to_request = fields_param if fields_param and isinstance(fields_param, list) else default_insight_fields

    api_params_sdk: Dict[str, Any] = {'fields': fields_to_request}
    if date_preset_param: api_params_sdk['date_preset'] = date_preset_param
    if time_range_param and isinstance(time_range_param, dict): api_params_sdk['time_range'] = time_range_param
    if filtering_param and isinstance(filtering_param, list): api_params_sdk['filtering'] = filtering_param
    if breakdowns_param and isinstance(breakdowns_param, list): api_params_sdk['breakdowns'] = breakdowns_param
    if action_breakdowns_param and isinstance(action_breakdowns_param, list): api_params_sdk['action_breakdowns'] = action_breakdowns_param
    if time_increment_param: api_params_sdk['time_increment'] = time_increment_param
    if limit_param and isinstance(limit_param, int) and limit_param > 0: api_params_sdk['limit'] = limit_param
    if sort_param and isinstance(sort_param, list): api_params_sdk['sort'] = sort_param

    try:
        get_meta_ads_api_client(params.get("client_config_override"))
        target_object_sdk: Any
        log_object_id_desc = object_id_param

        if level_param == 'campaign':
            target_object_sdk = Campaign(object_id_param)
        elif level_param == 'adset':
            target_object_sdk = AdSet(object_id_param)
        elif level_param == 'ad':
            target_object_sdk = Ad(object_id_param)
        elif level_param == 'account':
            ad_account_params = {"ad_account_id": object_id_param} if object_id_param else params
            target_object_sdk = _get_ad_account(ad_account_params)
            log_object_id_desc = target_object_sdk[AdAccount.Field.id]
        else:
            raise ValueError(f"Nivel de insights desconocido: {level_param}")

        logger.info(f"Obteniendo insights de Meta Ads para ID '{log_object_id_desc}' (Nivel: {level_param}). Params SDK: {api_params_sdk}")
        
        insights_cursor = target_object_sdk.get_insights(params=api_params_sdk, is_async=False)
        
        insights_list = [insight_data.export_all_data() for insight_data in insights_cursor]

        logger.info(f"Se obtuvieron {len(insights_list)} registros de insights para ID '{log_object_id_desc}' (Nivel: {level_param}).")
        return {"status": "success", "data": insights_list, "total_retrieved": len(insights_list)}

    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name, params)