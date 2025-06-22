# app/actions/googleads_actions.py
import logging
from typing import Dict, List, Optional, Any
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import json_format, field_mask_pb2

from app.core.config import settings
from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

_google_ads_client_instance: Optional[GoogleAdsClient] = None

def get_google_ads_client() -> GoogleAdsClient:
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
    if not all(k in config and config[k] for k in ["developer_token", "client_id", "client_secret", "refresh_token"]):
        raise ValueError("Faltan credenciales de Google Ads en la configuración.")
    
    if config.get("login_customer_id"):
        config["login_customer_id"] = str(config["login_customer_id"]).replace("-", "")
    
    try:
        _google_ads_client_instance = GoogleAdsClient.load_from_dict(config)
        return _google_ads_client_instance
    except Exception as e:
        raise ConnectionError(f"No se pudo inicializar el cliente de Google Ads: {e}")

def _handle_google_ads_exception(ex: GoogleAdsException, action_name: str) -> Dict[str, Any]:
    errors = [{"message": error.message} for error in ex.failure.errors]
    logger.error(f"Google Ads API Exception en '{action_name}': {errors}", exc_info=False)
    message = errors[0]['message'] if errors else "Error en API de Google Ads."
    return {"status": "error", "action": action_name, "message": message, "details": {"errors": errors}, "http_status": 400}

def _format_response(row: Any) -> Dict[str, Any]:
    return json_format.MessageToDict(row._pb, preserving_proto_field_name=True)

def googleads_search_stream(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    customer_id = params.get("customer_id") or settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID
    query = params.get("query")
    if not customer_id or not query:
        return {"status": "error", "message": "'customer_id' y 'query' son requeridos.", "http_status": 400}
    try:
        gads_client = get_google_ads_client()
        search_request = gads_client.get_type("SearchGoogleAdsStreamRequest")
        search_request.customer_id = str(customer_id).replace("-", "")
        search_request.query = query
        service = gads_client.get_service("GoogleAdsService")
        stream = service.search_stream(request=search_request)
        results = [_format_response(row) for batch in stream for row in batch.results]
        return {"status": "success", "data": {"results": results}}
    except GoogleAdsException as ex:
        return _handle_google_ads_exception(ex, "googleads_search_stream")
    except Exception as e:
        return {"status": "error", "message": f"Error inesperado: {str(e)}", "http_status": 500}

def googleads_mutate_campaigns(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    customer_id = params.get("customer_id") or settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID
    operations_payload = params.get("operations")
    if not customer_id or not operations_payload:
        return {"status": "error", "message": "'customer_id' y 'operations' son requeridos.", "http_status": 400}
    
    try:
        gads_client = get_google_ads_client()
        campaign_service = gads_client.get_service("CampaignService")
        
        mutate_operations = []
        for op in operations_payload:
            operation = gads_client.get_type("CampaignOperation")
            if "update" in op:
                update_data = op["update"]
                resource_name = update_data.get("resource_name")
                if not resource_name:
                    raise ValueError("La operación 'update' debe contener 'resource_name'.")
                
                campaign = operation.update
                campaign.resource_name = resource_name
                
                update_fields = []
                if "status" in update_data:
                    status_str = update_data["status"]
                    status_enum = gads_client.enums.CampaignStatusEnum[status_str]
                    campaign.status = status_enum.value
                    update_fields.append("status")
                
                # CORRECCIÓN DEFINITIVA: Usar field_mask_pb2 para crear el FieldMask
                operation.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=update_fields))
            
            # Aquí se añadiría la lógica para "create" y "remove" si fuera necesario
            else:
                continue
            mutate_operations.append(operation)

        response = campaign_service.mutate_campaigns(
            customer_id=str(customer_id).replace("-", ""),
            operations=mutate_operations,
            validate_only=params.get("validate_only", False)
        )
        return {"status": "success", "data": {"results": [_format_response(r) for r in response.results]}}
    except GoogleAdsException as ex:
        return _handle_google_ads_exception(ex, "googleads_mutate_campaigns")
    except Exception as e:
        logger.exception(f"Error inesperado en mutate_campaigns: {e}")
        return {"status": "error", "message": f"Error inesperado en el servidor: {str(e)}", "http_status": 500}

# Las demás funciones mutate permanecen como placeholders.
def googleads_mutate_adgroups(client, params): return {"status": "not_implemented"}
def googleads_mutate_ads(client, params): return {"status": "not_implemented"}
def googleads_mutate_keywords(client, params): return {"status": "not_implemented"}