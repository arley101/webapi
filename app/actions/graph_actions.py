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
    
    required_vars = {
        "developer_token": settings.GOOGLE_ADS.DEVELOPER_TOKEN,
        "client_id": settings.GOOGLE_ADS.CLIENT_ID,
        "client_secret": settings.GOOGLE_ADS.CLIENT_SECRET,
        "refresh_token": settings.GOOGLE_ADS.REFRESH_TOKEN,
    }
    missing = [key for key, value in required_vars.items() if not value]
    if missing:
        raise ValueError(f"Faltan credenciales de Google Ads en settings: {', '.join(missing)}")
    
    effective_config = {
        "developer_token": str(settings.GOOGLE_ADS.DEVELOPER_TOKEN),
        "client_id": str(settings.GOOGLE_ADS.CLIENT_ID),
        "client_secret": str(settings.GOOGLE_ADS.CLIENT_SECRET),
        "refresh_token": str(settings.GOOGLE_ADS.REFRESH_TOKEN),
        "login_customer_id": str(settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID).replace("-", "") if settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID else None,
        "use_proto_plus": True,
    }

    try:
        _google_ads_client_instance = GoogleAdsClient.load_from_dict(effective_config)
        return _google_ads_client_instance
    except Exception as e:
        raise ConnectionError(f"No se pudo inicializar el cliente de Google Ads: {e}")

def _format_google_ads_row_to_dict(row: Any) -> Dict[str, Any]:
    return json_format.MessageToDict(row._pb, preserving_proto_field_name=True)

def _handle_google_ads_api_exception(ex: GoogleAdsException, action_name: str) -> Dict[str, Any]:
    errors = []
    for error in ex.failure.errors:
        errors.append({"message": error.message})
    logger.error(f"Google Ads API Exception en '{action_name}'. Request ID: {ex.request_id}. Errors: {errors}", exc_info=False)
    message = errors[0]['message'] if errors else "Error en la API de Google Ads."
    return {"status": "error", "action": action_name, "message": message, "details": {"errors": errors, "requestId": ex.request_id}, "http_status": 400}

def googleads_search_stream(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    customer_id = params.get("customer_id") or settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID
    query = params.get("query")
    if not customer_id or not query:
        return {"status": "error", "message": "'customer_id' y 'query' son requeridos.", "http_status": 400}
    
    customer_id_clean = str(customer_id).replace("-", "")
    try:
        gads_client = get_google_ads_client()
        ga_service = gads_client.get_service("GoogleAdsService")
        search_request = gads_client.get_type("SearchGoogleAdsStreamRequest")
        search_request.customer_id = customer_id_clean
        search_request.query = query
        stream = ga_service.search_stream(request=search_request)
        results = [_format_google_ads_row_to_dict(row) for batch in stream for row in batch.results]
        return {"status": "success", "data": {"results": results}}
    except GoogleAdsException as ex:
        return _handle_google_ads_api_exception(ex, "googleads_search_stream")
    except Exception as e:
        return {"status": "error", "action": "googleads_search_stream", "message": f"Error inesperado: {str(e)}", "http_status": 500}

def _create_campaign_operation(gads_client: GoogleAdsClient, op_dict: Dict[str, Any]) -> Any:
    operation = gads_client.get_type("CampaignOperation")
    campaign = operation.create
    gads_client.copy_from(campaign, op_dict["create"])
    return operation

def _update_campaign_operation(gads_client: GoogleAdsClient, op_dict: Dict[str, Any]) -> Any:
    update_data = op_dict["update"]
    resource_name = update_data.get("resource_name")
    if not resource_name:
        raise ValueError("La operación de 'update' debe contener 'resource_name'.")

    operation = gads_client.get_type("CampaignOperation")
    campaign_update = operation.update
    campaign_update.resource_name = resource_name

    # Traducir 'status' de string a enum
    if "status" in update_data:
        status_str = update_data["status"]
        campaign_update.status = gads_client.enums.CampaignStatusEnum[status_str]

    # Crear la máscara de campo (field_mask)
    # Lista solo los campos que se están actualizando (además de resource_name)
    update_mask_paths = [key for key in update_data.keys() if key != "resource_name"]
    field_mask = protobuf_helpers.field_mask(None, update_mask_paths)
    operation.update_mask.CopyFrom(field_mask)
    
    return operation

def _remove_campaign_operation(gads_client: GoogleAdsClient, op_dict: Dict[str, Any]) -> Any:
    operation = gads_client.get_type("CampaignOperation")
    operation.remove = op_dict["remove"]
    return operation

def googleads_mutate_campaigns(client_unused: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "googleads_mutate_campaigns"
    customer_id = params.get("customer_id") or settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID
    operations_payload = params.get("operations")
    if not customer_id or not operations_payload:
        return {"status": "error", "message": "'customer_id' y 'operations' son requeridos.", "http_status": 400}
    
    customer_id_clean = str(customer_id).replace("-", "")
    try:
        gads_client = get_google_ads_client()
        campaign_service = gads_client.get_service("CampaignService")
        
        operations = []
        for op_dict in operations_payload:
            if "create" in op_dict:
                operations.append(_create_campaign_operation(gads_client, op_dict))
            elif "update" in op_dict:
                operations.append(_update_campaign_operation(gads_client, op_dict))
            elif "remove" in op_dict:
                operations.append(_remove_campaign_operation(gads_client, op_dict))

        if not operations:
            return {"status": "error", "message": "No se proveyeron operaciones válidas.", "http_status": 400}
        
        response = campaign_service.mutate_campaigns(
            customer_id=customer_id_clean,
            operations=operations,
            partial_failure=params.get("partial_failure", False),
            validate_only=params.get("validate_only", False)
        )
        
        formatted_response = {"results": [_format_google_ads_row_to_dict(r) for r in response.results]}
        if response.partial_failure_error:
             failure_message = gads_client.get_type("GoogleAdsFailure")
             failure_message.ParseFromString(response.partial_failure_error.details[0].value)
             formatted_response["partial_failure_error"] = _extract_google_ads_errors(failure_message, gads_client)
            
        return {"status": "success", "data": formatted_response}

    except GoogleAdsException as ex:
        return _handle_google_ads_api_exception(ex, action_name)
    except Exception as e:
        return {"status": "error", "action": action_name, "message": f"Error inesperado: {str(e)}", "http_status": 500}

# Las funciones para adgroups, ads, y keywords seguirían un patrón similar de refactorización si fueran necesarias.
# Por ahora, nos centramos en la que está dando problemas.
def googleads_mutate_adgroups(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "not_implemented", "message": "Esta acción necesita ser refactorizada con el nuevo patrón."}

def googleads_mutate_ads(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "not_implemented", "message": "Esta acción necesita ser refactorizada con el nuevo patrón."}

def googleads_mutate_keywords(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "not_implemented", "message": "Esta acción necesita ser refactorizada con el nuevo patrón."}