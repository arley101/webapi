# app/actions/googleads_actions.py
import logging
from typing import Dict, List, Optional, Any
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import json_format
from google.api_core import protobuf_helpers

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

_google_ads_client_instance: Optional[GoogleAdsClient] = None

def get_google_ads_client() -> GoogleAdsClient:
    """Inicializa y devuelve una instancia singleton del cliente de Google Ads."""
    global _google_ads_client_instance
    if _google_ads_client_instance:
        return _google_ads_client_instance
    
    config = {
        "developer_token": settings.GOOGLE_ADS.DEVELOPER_TOKEN,
        "client_id": settings.GOOGLE_ADS.CLIENT_ID,
        "client_secret": settings.GOOGLE_ADS.CLIENT_SECRET,
        "refresh_token": settings.GOOGLE_ADS.REFRESH_TOKEN,
        "login_customer_id": settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID,
        "use_proto_plus": True,
    }
    if not all(config.values()):
        raise ValueError("Faltan credenciales de Google Ads en la configuración.")
    
    config["login_customer_id"] = str(config["login_customer_id"]).replace("-", "") if config["login_customer_id"] else None
    
    try:
        _google_ads_client_instance = GoogleAdsClient.load_from_dict(config)
        return _google_ads_client_instance
    except Exception as e:
        raise ConnectionError(f"No se pudo inicializar el cliente de Google Ads: {e}")

def _format_dict(row: Any) -> Dict[str, Any]:
    return json_format.MessageToDict(row._pb, preserving_proto_field_name=True)

def _handle_exception(ex: GoogleAdsException, action: str) -> Dict[str, Any]:
    errors = [{"message": error.message} for error in ex.failure.errors]
    logger.error(f"Google Ads API Exception en '{action}': {errors}", exc_info=False)
    message = errors[0]['message'] if errors else "Error en API de Google Ads."
    return {"status": "error", "action": action, "message": message, "details": {"errors": errors}, "http_status": 400}

def googleads_search_stream(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    customer_id = params.get("customer_id") or settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID
    query = params.get("query")
    if not customer_id or not query: 
        return {"status": "error", "message": "'customer_id' y 'query' son requeridos.", "http_status": 400}
    try:
        gads_client = get_google_ads_client()
        service = gads_client.get_service("GoogleAdsService")
        request = gads_client.get_type("SearchGoogleAdsStreamRequest")
        request.customer_id = str(customer_id).replace("-", "")
        request.query = query
        stream = service.search_stream(request=request)
        results = [_format_dict(row) for batch in stream for row in batch.results]
        return {"status": "success", "data": {"results": results}}
    except GoogleAdsException as ex:
        return _handle_exception(ex, "googleads_search_stream")
    except Exception as e:
        return {"status": "error", "action": "googleads_search_stream", "message": f"Error inesperado: {str(e)}", "http_status": 500}

def googleads_mutate_campaigns(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "googleads_mutate_campaigns"
    customer_id = params.get("customer_id") or settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID
    operations = params.get("operations")
    if not customer_id or not operations:
        return {"status": "error", "action": action_name, "message": "'customer_id' y 'operations' son requeridos.", "http_status": 400}
    try:
        gads_client = get_google_ads_client()
        campaign_service = gads_client.get_service("CampaignService")
        
        sdk_operations = []
        for op in operations:
            operation = gads_client.get_type("CampaignOperation")
            if "update" in op:
                update_data = op["update"]
                resource_name = update_data.get("resource_name")
                if not resource_name: raise ValueError("Update op debe tener 'resource_name'.")
                
                campaign = operation.update
                campaign.resource_name = resource_name
                
                if "status" in update_data:
                    status_enum_val = gads_client.enums.CampaignStatusEnum[update_data["status"]]
                    campaign.status = status_enum_val
                
                update_mask = gads_client.get_type("FieldMask")
                update_mask.paths.extend([key for key in update_data if key != "resource_name"])
                gads_client.copy_from(operation.update_mask, update_mask)

            else: continue
            sdk_operations.append(operation)

        response = campaign_service.mutate_campaigns(
            customer_id=str(customer_id).replace("-", ""),
            operations=sdk_operations,
            validate_only=params.get("validate_only", False)
        )
        return {"status": "success", "data": {"results": [_format_dict(r) for r in response.results]}}
    except GoogleAdsException as ex:
        return _handle_exception(ex, action_name)
    except Exception as e:
        return {"status": "error", "action": action_name, "message": f"Error inesperado: {str(e)}", "http_status": 500}

def googleads_mutate_adgroups(client, params): return {"status": "not_implemented"}
def googleads_mutate_ads(client, params): return {"status": "not_implemented"}
def googleads_mutate_keywords(client, params): return {"status": "not_implemented"}