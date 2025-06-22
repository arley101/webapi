# app/actions/googleads_actions.py
import logging
from typing import Dict, List, Optional, Any

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import json_format, field_mask_pb2
from google.protobuf.json_format import ParseDict

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
    if not all(k in config and config[k] for k in ["developer_token", "client_id", "client_secret", "refresh_token"]):
        raise ValueError("Faltan credenciales de Google Ads en la configuración.")
    
    if config.get("login_customer_id"):
        config["login_customer_id"] = str(config["login_customer_id"]).replace("-", "")
    
    _google_ads_client_instance = GoogleAdsClient.load_from_dict(config)
    return _google_ads_client_instance

def _handle_google_ads_exception(ex: GoogleAdsException, action_name: str) -> Dict[str, Any]:
    errors = [{"message": error.message} for error in ex.failure.errors]
    logger.error(f"Google Ads API Exception en '{action_name}': {errors}", exc_info=True)
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

def _execute_mutate_operation(
    service_name: str, 
    operation_type_name: str, 
    resource_type_name: str,
    mutate_method_name: str, 
    request_type_name: str, 
    client_unused: Optional[AuthenticatedHttpClient], 
    params: Dict[str, Any]
) -> Dict[str, Any]:
    action_name = f"googleads_mutate_{resource_type_name.lower().replace('adgroupad', 'ad').replace('adgroupcriterion', 'keyword')}s"
    customer_id = params.get("customer_id") or settings.GOOGLE_ADS.LOGIN_CUSTOMER_ID
    operations_payload = params.get("operations")
    if not customer_id or not operations_payload:
        return {"status": "error", "action": action_name, "message": "'customer_id' y 'operations' son requeridos.", "http_status": 400}
    
    customer_id_clean = str(customer_id).replace("-", "")
    
    try:
        gads_client = get_google_ads_client()
        service_client = gads_client.get_service(service_name)
        
        sdk_operations = []
        for op_dict in operations_payload:
            operation = gads_client.get_type(operation_type_name)
            
            if "create" in op_dict and isinstance(op_dict["create"], dict):
                resource = gads_client.get_type(resource_type_name)
                ParseDict(op_dict["create"], resource)
                getattr(operation, "create").CopyFrom(resource)

            elif "update" in op_dict and isinstance(op_dict["update"], dict):
                update_dict = op_dict["update"]
                resource_name = update_dict.pop("resource_name", None)
                if not resource_name:
                    raise ValueError("El campo 'resource_name' es obligatorio en una operación de actualización.")

                resource_obj = gads_client.get_type(resource_type_name)
                ParseDict(update_dict, resource_obj)
                resource_obj.resource_name = resource_name

                getattr(operation, "update").CopyFrom(resource_obj)

                update_mask = field_mask_pb2.FieldMask(paths=update_dict.keys())
                operation.update_mask.CopyFrom(update_mask)

            elif "remove" in op_dict and isinstance(op_dict["remove"], str):
                operation.remove = op_dict["remove"]
            
            else:
                continue
            sdk_operations.append(operation)

        if not sdk_operations:
            return {"status": "error", "action": action_name, "message": "No se proveyeron operaciones válidas.", "http_status": 400}

        mutate_request = gads_client.get_type(request_type_name)
        mutate_request.customer_id = customer_id_clean
        mutate_request.operations.extend(sdk_operations)
        mutate_request.validate_only = params.get("validate_only", False)
        
        response = getattr(service_client, mutate_method_name)(request=mutate_request)
        
        formatted_response = {"results": [_format_response(r) for r in response.results]}
        if response.partial_failure_error:
            failure_message = gads_client.get_type("GoogleAdsFailure")
            failure_message.ParseFromString(response.partial_failure_error.details[0].value)
            formatted_response["partial_failure_error"] = _handle_google_ads_exception(GoogleAdsException(failure_message, None, None), action_name)["details"]

        return {"status": "success", "data": formatted_response}
    except GoogleAdsException as ex:
        return _handle_google_ads_exception(ex, action_name)
    except Exception as e:
        logger.exception(f"Error inesperado en {action_name}: {e}")
        return {"status": "error", "action": action_name, "message": f"Error inesperado en el servidor: {str(e)}", "http_status": 500}

def googleads_mutate_campaigns(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("CampaignService", "CampaignOperation", "Campaign", "mutate_campaigns", "MutateCampaignsRequest", client, params)

def googleads_mutate_adgroups(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("AdGroupService", "AdGroupOperation", "AdGroup", "mutate_ad_groups", "MutateAdGroupsRequest", client, params)

def googleads_mutate_ads(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("AdGroupAdService", "AdGroupAdOperation", "AdGroupAd", "mutate_ad_group_ads", "MutateAdGroupAdsRequest", client, params)

def googleads_mutate_keywords(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    return _execute_mutate_operation("AdGroupCriterionService", "AdGroupCriterionOperation", "AdGroupCriterion", "mutate_ad_group_criteria", "MutateAdGroupCriteriaRequest", client, params)