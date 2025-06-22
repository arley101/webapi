# app/actions/metaads_actions.py
import logging
import json
from typing import Dict, List, Optional, Any

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.exceptions import FacebookRequestError

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

_meta_ads_api_instance: Optional[FacebookAdsApi] = None

def get_meta_ads_api_client(client_config_override: Optional[Dict[str, str]] = None) -> FacebookAdsApi:
    """
    Inicializa y devuelve una instancia de la API de Facebook Ads.
    Reutiliza la instancia si ya ha sido creada y no hay override.
    """
    global _meta_ads_api_instance
    if _meta_ads_api_instance and not client_config_override:
        return _meta_ads_api_instance

    config_to_use: Dict[str, Optional[str]]
    if client_config_override:
        logger.info("Utilizando configuración de Meta Ads proporcionada en 'client_config_override'.")
        config_to_use = client_config_override
    else:
        required_vars = {
            "app_id": settings.META_ADS.APP_ID,
            "app_secret": settings.META_ADS.APP_SECRET,
            "access_token": settings.META_ADS.ACCESS_TOKEN,
        }
        missing = [key for key, value in required_vars.items() if not value]
        if missing:
            msg = f"Faltan credenciales de Meta Ads en settings: {', '.join(missing)}."
            logger.critical(msg)
            raise ValueError(msg)
        config_to_use = {k: str(v) for k, v in required_vars.items()}

    logger.info("Inicializando cliente de Meta Ads (Facebook Marketing API)...")
    try:
        FacebookAdsApi.init(
            app_id=config_to_use["app_id"],
            app_secret=config_to_use["app_secret"],
            access_token=config_to_use["access_token"],
            api_version="v19.0" 
        )
        current_api_instance = FacebookAdsApi.get_default_api()
        if not current_api_instance:
             raise ConnectionError("FacebookAdsApi.get_default_api() devolvió None después de la inicialización.")
        
        if not client_config_override:
            _meta_ads_api_instance = current_api_instance
            logger.info("Cliente de Meta Ads inicializado y cacheado exitosamente.")

        return current_api_instance
    except Exception as e:
        logger.exception(f"Error crítico inicializando el cliente de Meta Ads: {e}")
        raise ConnectionError(f"No se pudo inicializar el cliente de Meta Ads: {e}") from e


def _handle_meta_ads_api_error(e: Exception, action_name: str, params_for_log: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Formatea una FacebookRequestError u otra excepción en una respuesta de error estándar."""
    log_message = f"Error en Meta Ads Action '{action_name}'"
    if params_for_log:
        sensitive_keys = ['campaign_payload', 'update_payload', 'access_token']
        safe_params = {k: (v if k not in sensitive_keys else f"[{type(v).__name__} OMITIDO]") for k, v in params_for_log.items()}
        log_message += f" con params: {safe_params}"
    
    logger.error(f"{log_message}: {type(e).__name__} - {str(e)}", exc_info=True)
    
    status_code_int = 500
    details_str = str(e)
    api_error_code = None
    api_error_subcode = None
    api_error_message = str(e)
    user_message = None
    user_title = None

    if isinstance(e, FacebookRequestError):
        status_code_int = e.http_status() or 500
        api_error_code = e.api_error_code()
        api_error_subcode = e.api_error_subcode()
        api_error_message = e.api_error_message() or str(e)
        
        # CORRECCIÓN: Llamar a api_error_user_message solo si el método existe.
        if hasattr(e, 'api_error_user_message'):
            user_message = e.api_error_user_message()
        if hasattr(e, 'api_error_user_title'):
            user_title = e.api_error_user_title()

        try:
            response_body_dict = e.get_response()
            if response_body_dict and isinstance(response_body_dict, dict):
                 details_str = json.dumps(response_body_dict)
            else:
                details_str = str(e.get_response())
        except Exception:
            details_str = "No se pudo obtener el cuerpo de la respuesta de error."

    elif isinstance(e, (ValueError, ConnectionError)):
        status_code_int = 400 if isinstance(e, ValueError) else 503
        api_error_message = str(e)
    
    return {
        "status": "error",
        "action": action_name,
        "message": user_message or api_error_message,
        "http_status": status_code_int,
        "details": {
            "api_error_code": api_error_code,
            "api_error_subcode": api_error_subcode,
            "api_error_title_for_user": user_title,
            "full_api_response_details": details_str
        }
    }


def _get_ad_account(params: Dict[str, Any]) -> AdAccount:
    """Obtiene el objeto AdAccount, priorizando el ID de los parámetros sobre la configuración global."""
    ad_account_id_from_params: Optional[str] = params.get("ad_account_id")
    effective_ad_account_id = ad_account_id_from_params or settings.META_ADS.BUSINESS_ACCOUNT_ID
    
    if not effective_ad_account_id:
        raise ValueError("Se requiere 'ad_account_id' en los params o META_ADS_BUSINESS_ACCOUNT_ID en la configuración.")
    
    id_str = str(effective_ad_account_id)
    if not id_str.startswith("act_"):
        id_str = f"act_{id_str}"
        
    return AdAccount(id_str)

# --- Funciones de Acción ---

def metaads_list_campaigns(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "metaads_list_campaigns"
    logger.info(f"Ejecutando {action_name} con params: {params}")

    default_fields = [
        Campaign.Field.id, Campaign.Field.name, Campaign.Field.status, Campaign.Field.effective_status,
        Campaign.Field.objective, Campaign.Field.account_id, Campaign.Field.start_time, Campaign.Field.stop_time,
        Campaign.Field.daily_budget, Campaign.Field.lifetime_budget
    ]
    fields_to_request = params.get("fields", default_fields)
    
    try:
        get_meta_ads_api_client(params.get("client_config_override"))
        ad_account = _get_ad_account(params)
        
        logger.info(f"Listando campañas de Meta Ads para la cuenta '{ad_account.get_id()}'")
        
        api_params_sdk = {'fields': fields_to_request, 'summary': True} # summary=True es buena práctica
        if "limit" in params:
            api_params_sdk['limit'] = params["limit"]
        if "filtering" in params:
            api_params_sdk['filtering'] = params["filtering"]

        campaigns = ad_account.get_campaigns(params=api_params_sdk)
        campaigns_list = [campaign.export_all_data() for campaign in campaigns]

        logger.info(f"Se encontraron {len(campaigns_list)} campañas para la cuenta '{ad_account.get_id()}'.")
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
        return {"status": "error", "action": action_name, "message": f"Faltan campos requeridos en 'campaign_payload': {missing}.", "http_status": 400}
    
    try:
        get_meta_ads_api_client(params.get("client_config_override"))
        ad_account = _get_ad_account(params)
        
        logger.info(f"Creando campaña en la cuenta '{ad_account.get_id()}' con nombre: '{campaign_payload.get('name')}'")
        
        created_campaign = ad_account.create_campaign(params=campaign_payload)
        
        logger.info(f"Campaña '{created_campaign[Campaign.Field.name]}' creada con ID: {created_campaign[Campaign.Field.id]}")
        return {"status": "success", "data": created_campaign.export_all_data()}
        
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
        return {"status": "error", "action": action_name, "message": "'update_payload' (dict no vacío) es requerido.", "http_status": 400}

    try:
        get_meta_ads_api_client(params.get("client_config_override"))
        
        logger.info(f"Actualizando campaña de Meta Ads ID: '{campaign_id}'")
        
        campaign_to_update = Campaign(campaign_id)
        campaign_to_update.remote_update(params=update_payload) 
        
        logger.info(f"Campaña ID '{campaign_id}' actualizada.")
        return {"status": "success", "data": {"id": campaign_id, "success": True}}

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
        
        logger.info(f"Eliminando la campaña de Meta Ads ID: '{campaign_id}'")
        
        campaign_to_delete = Campaign(campaign_id)
        # Cambiar estado a DELETED es más común que una eliminación física.
        campaign_to_delete.remote_update(params={'status': Campaign.Status.deleted})

        logger.info(f"Campaña ID '{campaign_id}' marcada como eliminada.")
        return {"status": "success", "message": f"Campaña '{campaign_id}' marcada como eliminada."}

    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name, params)

def metaads_get_insights(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "metaads_get_insights"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    level = params.get("level", "campaign")
    object_id = params.get("object_id")
    
    if level != 'account' and not object_id:
        return {"status": "error", "action": action_name, "message": f"'object_id' es requerido para el nivel '{level}'.", "http_status": 400}

    default_fields = ['campaign_name', 'adset_name', 'ad_name', 'impressions', 'spend', 'clicks', 'ctr', 'cpc', 'reach', 'frequency']
    
    insights_params = {
        'level': level,
        'fields': params.get('fields', default_fields),
        'date_preset': params.get('date_preset', 'last_30d'),
        'time_increment': params.get('time_increment', 1),
    }
    if 'time_range' in params:
        insights_params['time_range'] = params['time_range']
    if 'filtering' in params:
        insights_params['filtering'] = params['filtering']
    if 'breakdowns' in params:
        insights_params['breakdowns'] = params['breakdowns']

    try:
        get_meta_ads_api_client(params.get("client_config_override"))
        
        target_object: Any
        if level == 'campaign':
            target_object = Campaign(object_id)
        elif level == 'adset':
            target_object = AdSet(object_id)
        elif level == 'ad':
            target_object = Ad(object_id)
        elif level == 'account':
            target_object = _get_ad_account(params)
        else:
            raise ValueError(f"Nivel de insights no soportado: '{level}'")

        logger.info(f"Obteniendo insights para ID '{target_object.get_id()}' (Nivel: {level}).")
        
        insights_cursor = target_object.get_insights(params=insights_params)
        insights_list = [insight.export_all_data() for insight in insights_cursor]

        return {"status": "success", "data": insights_list, "total_retrieved": len(insights_list)}

    except Exception as e:
        return _handle_meta_ads_api_error(e, action_name, params)