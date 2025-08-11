# app/actions/x_ads_actions.py
import logging
from typing import Dict, Any, Optional
from twitter_ads.client import Client
from twitter_ads.campaign import Campaign
from twitter_ads.error import Error

from app.core.config import settings

logger = logging.getLogger(__name__)

def _get_x_ads_client(params: Dict[str, Any]) -> Client:
    creds = settings.X_ADS
    if not all([creds.CONSUMER_KEY, creds.CONSUMER_SECRET, creds.ACCESS_TOKEN, creds.ACCESS_TOKEN_SECRET]):
        raise ValueError("Credenciales de X Ads (CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET) deben estar configuradas.")
    
    return Client(
        creds.CONSUMER_KEY,
        creds.CONSUMER_SECRET,
        creds.ACCESS_TOKEN,
        creds.ACCESS_TOKEN_SECRET
    )

def _handle_x_ads_api_error(e: Error, action_name: str) -> Dict[str, Any]:
    logger.error(f"Error en X Ads Action '{action_name}': {e}", exc_info=True)
    details = e.details[0] if e.details else {}
    return {
        "status": "error",
        "action": action_name,
        "message": f"Error en API de X Ads: {details.get('message', str(e))}",
        "details": details,
        "http_status": e.response.status_code if hasattr(e, 'response') else 500
    }

def x_ads_get_campaigns(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "x_ads_get_campaigns"
    try:
        x_client = _get_x_ads_client(params)
        account_id = settings.X_ADS.ACCOUNT_ID
        if not account_id:
            raise ValueError("Se requiere 'X_ADS_ACCOUNT_ID' en la configuración.")
        
        campaigns = Campaign.all(x_client, account_id)
        return {"status": "success", "data": [c.to_dict() for c in campaigns]}
    except Error as e:
        return _handle_x_ads_api_error(e, action_name)
    except Exception as e:
        return {"status": "error", "message": str(e), "http_status": 500}

def x_ads_create_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "x_ads_create_campaign"
    try:
        x_client = _get_x_ads_client(params)
        account_id = settings.X_ADS.ACCOUNT_ID
        payload = params.get("campaign_payload")
        if not account_id or not payload:
            raise ValueError("Se requieren 'X_ADS_ACCOUNT_ID' y 'campaign_payload'.")
        
        campaign = Campaign(x_client, account_id)
        for key, value in payload.items():
            setattr(campaign, key, value)
        campaign.save()
        return {"status": "success", "data": campaign.to_dict()}
    except Error as e:
        return _handle_x_ads_api_error(e, action_name)
    except Exception as e:
        return {"status": "error", "message": str(e), "http_status": 500}

def x_ads_update_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "x_ads_update_campaign"
    try:
        x_client = _get_x_ads_client(params)
        account_id = settings.X_ADS.ACCOUNT_ID
        campaign_id = params.get("campaign_id")
        update_payload = params.get("update_payload")
        if not account_id or not campaign_id or not update_payload:
            raise ValueError("Se requieren 'X_ADS_ACCOUNT_ID', 'campaign_id' y 'update_payload'.")

        campaign = Campaign.load(x_client, account_id, campaign_id)
        for key, value in update_payload.items():
            setattr(campaign, key, value)
        campaign.save()
        return {"status": "success", "data": campaign.to_dict()}
    except Error as e:
        return _handle_x_ads_api_error(e, action_name)
    except Exception as e:
        return {"status": "error", "message": str(e), "http_status": 500}

def x_ads_delete_campaign(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "x_ads_delete_campaign"
    try:
        x_client = _get_x_ads_client(params)
        account_id = settings.X_ADS.ACCOUNT_ID
        campaign_id = params.get("campaign_id")
        if not account_id or not campaign_id:
            raise ValueError("Se requieren 'X_ADS_ACCOUNT_ID' y 'campaign_id'.")
        
        campaign = Campaign.load(x_client, account_id, campaign_id)
        campaign.delete()
        return {"status": "success", "message": f"Campaña '{campaign_id}' eliminada."}
    except Error as e:
        return _handle_x_ads_api_error(e, action_name)
    except Exception as e:
        return {"status": "error", "message": str(e), "http_status": 500}

def x_ads_get_analytics(client: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    action_name = "x_ads_get_analytics"
    # Placeholder for analytics - requires more specific implementation based on needs
    return {"status": "not_implemented", "message": "La analítica de X Ads requiere una implementación más detallada."}